"""csvcomp — semantic CSV↔CSV diff with zero runtime dependencies.

All public surface is re-exported here for `from csvcomp import diff`.
See README.md for usage. Pure Python 3.11+ stdlib only.
"""

from __future__ import annotations

from .diff import diff, DiffResult, RowChange, CellChange
from .errors import CsvCompError, ParseError, SchemaIncompatibleError

__all__ = [
    "diff",
    "DiffResult",
    "RowChange",
    "CellChange",
    "CsvCompError",
    "ParseError",
    "SchemaIncompatibleError",
]

__version__ = "0.1.0"
