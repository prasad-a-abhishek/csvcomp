"""Command-line interface for csvcomp.

Exit codes (per spec):
    0  identical
    1  changed (diff is non-empty)
    2  parse error
    3  schema-incompatible
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .diff import diff
from .errors import CsvCompError, ParseError, SchemaIncompatibleError

EXIT_IDENTICAL = 0
EXIT_CHANGED = 1
EXIT_PARSE_ERROR = 2
EXIT_SCHEMA_INCOMPATIBLE = 3


def _parse_coerce_list(spec: str | None) -> dict[str, str]:
    """Parse ``col:kind,col:kind`` into a dict."""
    if not spec:
        return {}
    out: dict[str, str] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise SystemExit(f"--coerce: expected col:kind, got {item!r}")
        col, kind = item.split(":", 1)
        col = col.strip()
        kind = kind.strip()
        if not col or not kind:
            raise SystemExit(f"--coerce: expected col:kind, got {item!r}")
        out[col] = kind
    return out


def _parse_keys(spec: str | None) -> list[str] | None:
    if not spec:
        return None
    return [k.strip() for k in spec.split(",") if k.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csvcomp",
        description="Semantic CSV↔CSV diff (schema + rows + cells).",
    )
    parser.add_argument("left", help="Left CSV file path or '-' for stdin")
    parser.add_argument("right", help="Right CSV file path or '-' for stdin")
    parser.add_argument(
        "--key",
        dest="keys",
        default=None,
        help="Comma-separated key columns for row matching (default: positional).",
    )
    parser.add_argument(
        "--coerce",
        default=None,
        help="Comma-separated col:kind pairs (e.g. amount:number,shipped_at:datetime).",
    )
    parser.add_argument(
        "--dialect",
        choices=["auto", "excel", "excel-tab", "unix"],
        default="auto",
        help="CSV dialect (default: auto-sniff first 8 KB).",
    )
    parser.add_argument(
        "--format",
        choices=["json", "unified", "sidebyside"],
        default="unified",
        help="Output format (default: unified).",
    )
    parser.add_argument(
        "--detect-renames",
        action="store_true",
        help="Detect column renames by value overlap (off by default).",
    )
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="Exit with status code instead of printing result.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        coerce_map = _parse_coerce_list(args.coerce)
        keys = _parse_keys(args.keys)
        result = diff(
            args.left,
            args.right,
            keys=keys,
            coerce=coerce_map,
            dialect=args.dialect,
            detect_renames=args.detect_renames,
        )
    except SchemaIncompatibleError as exc:
        sys.stderr.write(f"csvcomp: schema-incompatible: {exc}\n")
        return EXIT_SCHEMA_INCOMPATIBLE
    except (ParseError, CsvCompError) as exc:
        sys.stderr.write(f"csvcomp: parse error: {exc}\n")
        return EXIT_PARSE_ERROR
    if args.exit_code:
        return EXIT_IDENTICAL if result.is_empty else EXIT_CHANGED
    sys.stdout.write(result.format(args.format))
    return EXIT_IDENTICAL


if __name__ == "__main__":
    raise SystemExit(main())
