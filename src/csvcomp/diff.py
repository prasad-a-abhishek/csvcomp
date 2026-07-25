"""Core diff algorithm for csvcomp.

Public entry point: ``diff(left, right, keys=..., coerce=..., dialect=...)``.
Pure stdlib; see ``__init__.py`` for the dependency note.
"""

from __future__ import annotations

import csv
import io
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Callable, Mapping, Sequence

from .errors import ParseError, SchemaIncompatibleError, UnknownCoercionError

# ---- Constants ---------------------------------------------------------------

NA_TOKENS = frozenset({"", "na", "n/a", "null", "none", "nan", "-"})
BOOL_TRUE = frozenset({"true", "t", "yes", "y", "1"})
BOOL_FALSE = frozenset({"false", "f", "no", "n", "0"})

# Spec risk callout: rename detection off by default; threshold is 80% overlap.
RENAME_OVERLAP_THRESHOLD = 0.80

# KeitaNakamura/diff-csv #1: small samples fool Sniffer; cap at 8 KB.
SNIFF_SAMPLE_BYTES = 8192

# ---- Data classes ------------------------------------------------------------


@dataclass(frozen=True)
class CellChange:
    """One changed cell inside a modified row."""

    column: str
    old: str
    new: str


@dataclass(frozen=True)
class RowChange:
    """One modified row: its key (or row index) plus the changed cells."""

    key: object  # tuple of key values, or int for positional match
    cells: tuple[CellChange, ...] = ()

    @property
    def changed_columns(self) -> tuple[str, ...]:
        return tuple(c.column for c in self.cells)


@dataclass
class DiffResult:
    """Result of comparing two CSVs.

    Attributes mirror the spec's library API surface:
        added_columns, removed_columns, renamed_columns,
        added_rows, removed_rows, modified_rows, changed_cells.
    """

    added_columns: list[str] = field(default_factory=list)
    removed_columns: list[str] = field(default_factory=list)
    renamed_columns: dict[str, str] = field(default_factory=dict)
    added_rows: list[dict] = field(default_factory=list)
    removed_rows: list[dict] = field(default_factory=list)
    modified_rows: list[RowChange] = field(default_factory=list)
    changed_cells: list[CellChange] = field(default_factory=list)
    left_header: tuple[str, ...] = ()
    right_header: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (
            self.added_columns
            or self.removed_columns
            or self.renamed_columns
            or self.added_rows
            or self.removed_rows
            or self.modified_rows
        )

    def format(self, kind: str) -> str:
        # Lazy import keeps diff.py focused on the algorithm.
        from .format import format_result

        return format_result(self, kind)

    def to_dict(self) -> dict:
        return {
            "added_columns": list(self.added_columns),
            "removed_columns": list(self.removed_columns),
            "renamed_columns": dict(self.renamed_columns),
            "added_rows": list(self.added_rows),
            "removed_rows": list(self.removed_rows),
            "modified_rows": [
                {
                    "key": list(rc.key) if isinstance(rc.key, tuple) else rc.key,
                    "changed_columns": list(rc.changed_columns),
                    "cells": [
                        {"column": c.column, "old": c.old, "new": c.new}
                        for c in rc.cells
                    ],
                }
                for rc in self.modified_rows
            ],
            "changed_cells": [
                {"column": c.column, "old": c.old, "new": c.new}
                for c in self.changed_cells
            ],
        }


# ---- File loading ------------------------------------------------------------


def _open_csv(
    path: str | bytes,
    dialect: str | None,
) -> tuple[type[csv.Dialect], list[str], list[list[str]]]:
    """Open ``path`` (or ``"-"`` for stdin) and return (dialect, header, rows)."""
    if isinstance(path, bytes):
        if path == b"-":
            text = _decode_stdin_bytes()
        else:
            raise ParseError(
                "byte paths are not supported; pass a filesystem path or '-' for stdin"
            )
    else:
        if path == "-":
            text = _decode_stdin_bytes()
        else:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                text = fh.read()
    return _parse_text(text, dialect)


def _decode_stdin_bytes() -> str:
    import sys

    data = sys.stdin.buffer.read()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError(f"stdin is not valid UTF-8: {exc}") from exc


def _parse_text(
    text: str,
    dialect: str | None,
) -> tuple[type[csv.Dialect], list[str], list[list[str]]]:
    """Parse CSV text into (dialect class, header, rows)."""
    if not text:
        raise ParseError("input is empty")
    if dialect is None or dialect == "auto":
        try:
            sample = text[:SNIFF_SAMPLE_BYTES]
            effective = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            effective = csv.excel
    elif dialect == "excel":
        effective = csv.excel
    elif dialect == "excel-tab":
        effective = csv.excel_tab
    elif dialect == "unix":
        effective = csv.unix_dialect
    elif isinstance(dialect, csv.Dialect):
        effective = dialect
    else:
        raise ParseError(f"unknown dialect: {dialect!r}")
    reader = csv.reader(io.StringIO(text), dialect=effective)
    try:
        rows = [row for row in reader]
    except csv.Error as exc:
        raise ParseError(f"csv parse error: {exc}") from exc
    if not rows:
        raise ParseError("input has no header")
    header = rows[0]
    body = [r for r in rows[1:] if any(cell != "" for cell in r)]
    # Spec criteria 19 & 20: ragged / short rows are schema-incompatible.
    hlen = len(header)
    for i, row in enumerate(body, start=1):
        if len(row) > hlen:
            raise SchemaIncompatibleError(
                f"row {i + 1} has {len(row)} cells but header has {hlen} (extra)"
            )
        if len(row) < hlen:
            raise SchemaIncompatibleError(
                f"row {i + 1} has {len(row)} cells but header has {hlen} (missing)"
            )
    return effective, header, body


# ---- Coercion ----------------------------------------------------------------


def _coerce(value: str, kind: str | Callable[[str], object]) -> object:
    """Apply a coercion to a single cell value."""
    if callable(kind):
        return kind(value)
    if kind == "string":
        return value
    if kind in ("number", "float"):
        try:
            return float(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"cannot coerce {value!r} to number: {exc}") from exc
    if kind == "int":
        try:
            return int(value)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"cannot coerce {value!r} to int: {exc}") from exc
    if kind == "decimal":
        try:
            return Decimal(value)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"cannot coerce {value!r} to decimal: {exc}") from exc
    if kind == "date":
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"cannot coerce {value!r} to date: {exc}") from exc
    if kind == "datetime":
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"cannot coerce {value!r} to datetime: {exc}") from exc
    if kind in ("boolean", "bool"):
        norm = value.strip().lower()
        if norm in BOOL_TRUE:
            return True
        if norm in BOOL_FALSE:
            return False
        raise ValueError(f"cannot coerce {value!r} to boolean")
    raise UnknownCoercionError(f"unknown coercion kind: {kind!r}")


def _normalize_na(value: str) -> str:
    """Canonicalize the NA/None/empty family to a single sentinel ``""``."""
    if value is None:
        return ""
    return "" if value.strip().lower() in NA_TOKENS else value


def _values_equal(a: str, b: str, coerce_kind: str | Callable | None) -> bool:
    """Compare two string cells with optional coercion."""
    if _normalize_na(a) == _normalize_na(b):
        return True
    if coerce_kind is None:
        return a == b
    try:
        return _coerce(a, coerce_kind) == _coerce(b, coerce_kind)
    except UnknownCoercionError:
        raise
    except ValueError:
        return a == b


# ---- Column diff -------------------------------------------------------------


def _column_diff(
    left_header: Sequence[str],
    right_header: Sequence[str],
) -> tuple[list[str], list[str]]:
    """Return (added_columns, removed_columns) preserving order."""
    left_set = set(left_header)
    right_set = set(right_header)
    added = [c for c in right_header if c not in left_set]
    removed = [c for c in left_header if c not in right_set]
    return added, removed


def _value_overlap(a: Sequence[str], b: Sequence[str]) -> float:
    """Left-coverage overlap: fraction of ``a``'s non-NA values found in ``b``.

    This is the natural metric for rename detection: "does the old column's
    value set survive in the new column?". 1.0 means every old value is
    present in the new column; 0.0 means no overlap. Jaccard over-penalises
    asymmetric row counts (e.g. an old column of 3 values vs a new column of
    4 where the 3 are all present: Jaccard = 3/4 = 0.75, left-coverage = 1.0).
    """
    a_set = {_normalize_na(v) for v in a if v is not None}
    b_set = {_normalize_na(v) for v in b if v is not None}
    a_set = {v for v in a_set if v != ""}
    b_set = {v for v in b_set if v != ""}
    if not a_set:
        return 0.0
    inter = len(a_set & b_set)
    return inter / len(a_set)


def _detect_renames(
    left_header: Sequence[str],
    right_header: Sequence[str],
    left_rows: Sequence[Mapping[str, str]],
    right_rows: Sequence[Mapping[str, str]],
    threshold: float = RENAME_OVERLAP_THRESHOLD,
) -> dict[str, str]:
    """Detect column renames by value overlap (spec: opt-in)."""
    removed = [c for c in left_header if c not in right_header]
    added = [c for c in right_header if c not in left_header]
    if not removed or not added:
        return {}
    left_vals = {c: [r.get(c, "") for r in left_rows] for c in removed}
    right_vals = {c: [r.get(c, "") for r in right_rows] for c in added}
    renames: dict[str, str] = {}
    used_right: set[str] = set()
    for lc in removed:
        best_score = -1.0
        best_match: str | None = None
        for rc in added:
            if rc in used_right:
                continue
            overlap = _value_overlap(left_vals[lc], right_vals[rc])
            if overlap > best_score:
                best_score = overlap
                best_match = rc
        if best_match is not None and best_score >= threshold:
            renames[lc] = best_match
            used_right.add(best_match)
    return renames


# ---- Row diff ----------------------------------------------------------------


def _row_diff(
    left_header: Sequence[str],
    right_header: Sequence[str],
    left_rows: Sequence[list[str]],
    right_rows: Sequence[list[str]],
    keys: Sequence[str] | None,
    coerce: Mapping[str, str | Callable],
    renames: Mapping[str, str],
) -> tuple[
    list[dict],
    list[dict],
    list[RowChange],
    list[CellChange],
]:
    left_dicts = _dicts(left_header, left_rows)
    right_dicts = _dicts(right_header, right_rows)
    if renames:
        right_dicts = [_apply_renames(d, renames) for d in right_dicts]
    if keys:
        return _row_diff_keyed(left_dicts, right_dicts, keys, coerce)
    return _row_diff_positional(left_dicts, right_dicts, coerce)


def _dicts(header: Sequence[str], rows: Sequence[Sequence[str]]) -> list[dict]:
    return [dict(zip(header, row)) for row in rows]


def _apply_renames(row: dict, renames: Mapping[str, str]) -> dict:
    """Project a right-side dict into the left-side schema by renaming keys."""
    out = dict(row)
    for old, new in renames.items():
        if new in row and old not in row:
            out[old] = row[new]
    return out


def _row_diff_keyed(
    left: Sequence[dict],
    right: Sequence[dict],
    keys: Sequence[str],
    coerce: Mapping[str, str | Callable],
) -> tuple[list[dict], list[dict], list[RowChange], list[CellChange]]:
    left_index = _build_key_index(left, keys)
    right_index = _build_key_index(right, keys)
    added: list[dict] = []
    removed: list[dict] = []
    modified: list[RowChange] = []
    changed_cells: list[CellChange] = []
    for k, row in left_index.items():
        if k not in right_index:
            removed.append(row)
        else:
            cells = _compare_cells(row, right_index[k], coerce)
            if cells:
                modified.append(RowChange(key=k, cells=tuple(cells)))
                changed_cells.extend(cells)
    for k, row in right_index.items():
        if k not in left_index:
            added.append(row)
    return added, removed, modified, changed_cells


def _build_key_index(rows: Sequence[dict], keys: Sequence[str]) -> dict:
    """Index rows by their key tuple. Duplicate keys: first wins (documented)."""
    index: dict = OrderedDict()
    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        if key in index:
            continue
        index[key] = row
    return index


def _row_diff_positional(
    left: Sequence[dict],
    right: Sequence[dict],
    coerce: Mapping[str, str | Callable],
) -> tuple[list[dict], list[dict], list[RowChange], list[CellChange]]:
    """Position-based diff: rows are matched by index, not by content."""
    added: list[dict] = []
    removed: list[dict] = []
    modified: list[RowChange] = []
    changed_cells: list[CellChange] = []
    n = max(len(left), len(right))
    for i in range(n):
        l = left[i] if i < len(left) else None
        r = right[i] if i < len(right) else None
        if l is None and r is not None:
            added.append(r)
            continue
        if r is None and l is not None:
            removed.append(l)
            continue
        assert l is not None and r is not None  # type narrowing for type checkers
        cells = _compare_cells(l, r, coerce)
        if cells:
            modified.append(RowChange(key=i, cells=tuple(cells)))
            changed_cells.extend(cells)
    return added, removed, modified, changed_cells


def _compare_cells(
    left: dict,
    right: dict,
    coerce: Mapping[str, str | Callable],
) -> list[CellChange]:
    """Return the list of cells that differ between two dicts."""
    out: list[CellChange] = []
    for col in left:
        if col not in right:
            continue
        a = left[col]
        b = right[col]
        kind = coerce.get(col)
        if not _values_equal(a, b, kind):
            out.append(CellChange(column=col, old=a, new=b))
    return out


# ---- Public entry point ------------------------------------------------------


def diff(
    left: str,
    right: str,
    *,
    keys: Sequence[str] | None = None,
    coerce: Mapping[str, str | Callable] | None = None,
    dialect: str | None = "auto",
    detect_renames: bool = False,
) -> DiffResult:
    """Compare two CSV files and return a ``DiffResult``.

    Parameters
    ----------
    left, right:
        Paths to the two CSV files. Use ``"-"`` for stdin (only one at a time
        in v1).
    keys:
        Column names to use for row matching. ``None`` means match by position.
    coerce:
        Mapping of column name to coercion kind. Supported kinds: ``"string"``,
        ``"number"``/``"float"``, ``"int"``, ``"decimal"``, ``"date"``,
        ``"datetime"``, ``"boolean"``/``"bool"``. Callables are also accepted.
    dialect:
        ``"auto"`` (default), ``"excel"``, ``"excel-tab"``, ``"unix"``, or an
        explicit ``csv.Dialect``.
    detect_renames:
        Opt-in column rename detection by value overlap (default ``False``).
    """
    coerce_map: dict[str, str | Callable] = dict(coerce or {})
    _, lh, lrows = _open_csv(left, dialect)
    _, rh, rrows = _open_csv(right, dialect)
    added_cols, removed_cols = _column_diff(lh, rh)
    renames: dict[str, str] = {}
    if detect_renames:
        renames = _detect_renames(
            lh, rh, _dicts(lh, lrows), _dicts(rh, rrows)
        )
    added_rows, removed_rows, modified_rows, changed_cells = _row_diff(
        lh, rh, lrows, rrows, keys, coerce_map, renames
    )
    return DiffResult(
        added_columns=added_cols,
        removed_columns=removed_cols,
        renamed_columns=renames,
        added_rows=added_rows,
        removed_rows=removed_rows,
        modified_rows=modified_rows,
        changed_cells=changed_cells,
        left_header=tuple(lh),
        right_header=tuple(rh),
    )
