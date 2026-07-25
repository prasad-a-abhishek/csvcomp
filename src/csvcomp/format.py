"""Output formatters for ``DiffResult``.

Kept in a separate module so the algorithm in ``diff.py`` stays focused.
Pure stdlib. Public entry: ``format_result(result, kind)``.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .diff import DiffResult, RowChange


def format_result(result: "DiffResult", kind: str) -> str:
    if kind == "json":
        return format_json(result)
    if kind == "unified":
        return format_unified(result)
    if kind == "sidebyside":
        return format_sidebyside(result)
    raise ValueError(
        f"unknown format: {kind!r} (expected json|unified|sidebyside)"
    )


def format_json(result: "DiffResult") -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True, default=str)


def format_unified(result: "DiffResult") -> str:
    buf = io.StringIO()
    if (
        not result.added_columns
        and not result.removed_columns
        and not result.renamed_columns
    ):
        buf.write("@@ columns @@ (no schema changes)\n")
    else:
        buf.write("@@ columns @@\n")
        for c in sorted(set(result.left_header) - set(result.removed_columns)):
            buf.write(f"  {c} (kept)\n")
        for c in result.removed_columns:
            buf.write(f"- {c}\n")
        for c in result.added_columns:
            buf.write(f"+ {c}\n")
        for old, new in result.renamed_columns.items():
            buf.write(f"~ {old} -> {new} (renamed)\n")
    buf.write("\n@@ rows @@\n")
    if not (result.added_rows or result.removed_rows or result.modified_rows):
        buf.write("  (no row changes)\n")
    for rc in result.removed_rows:
        buf.write(_format_dict_row("-row", rc))
    for rc in result.added_rows:
        buf.write(_format_dict_row("+row", rc))
    for rc in result.modified_rows:
        buf.write(_format_change_row("~row", rc))
    return buf.getvalue()


def _format_dict_row(tag: str, row: dict) -> str:
    body = "  ".join(f"{k}={v!r}" for k, v in row.items())
    return f"  {tag}  {body}\n"


def _format_change_row(tag: str, rc: "RowChange") -> str:
    if isinstance(rc.key, tuple):
        key_repr = "[" + ",".join(str(k) for k in rc.key) + "]"
    else:
        key_repr = str(rc.key)
    parts = [f"{c.column} {c.old!r} -> {c.new!r}" for c in rc.cells]
    return f"  key={key_repr}  {tag}  " + "; ".join(parts) + "\n"


def format_sidebyside(result: "DiffResult") -> str:
    rows: list[tuple[str, str, str]] = []
    for r in result.removed_rows:
        for k, v in r.items():
            rows.append((f"(removed) {k}", str(v), ""))
    for r in result.added_rows:
        for k, v in r.items():
            rows.append((f"(added) {k}", "", str(v)))
    for rc in result.modified_rows:
        for c in rc.cells:
            rows.append((c.column, c.old, c.new))
    if not rows:
        return "(no changes)\n"
    widths = [0, 0, 0]
    for col, l, r in rows:
        widths[0] = max(widths[0], len(col))
        widths[1] = max(widths[1], len(l))
        widths[2] = max(widths[2], len(r))
    buf = io.StringIO()
    buf.write(
        f"{'column'.ljust(widths[0])}  {'left'.ljust(widths[1])}  "
        f"{'right'.ljust(widths[2])}\n"
    )
    buf.write("-" * (sum(widths) + 4) + "\n")
    for col, l, r in rows:
        buf.write(f"{col.ljust(widths[0])}  {l.ljust(widths[1])}  {r.ljust(widths[2])}\n")
    return buf.getvalue()
