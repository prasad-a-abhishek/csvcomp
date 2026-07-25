"""Custom exceptions for csvcomp.

The CLI maps these to exit codes:
    CsvCompError / ValueError / IOError -> 2 (parse error)
    SchemaIncompatibleError             -> 3 (schema-incompatible)
    success                              -> 0
    success but diff non-empty           -> 1
"""

from __future__ import annotations


class CsvCompError(Exception):
    """Base class for all csvcomp-raised errors."""


class UnknownCoercionError(ValueError, CsvCompError):
    """Raised when a coerce mapping specifies an unknown coercion kind.

    Inherits from both ``ValueError`` (so existing callers using
    ``except ValueError`` keep working) and ``CsvCompError`` (so the CLI can
    route it through the parse-error exit code if it ever escapes).
    """


class ParseError(CsvCompError):
    """Raised when a CSV file cannot be parsed (bad encoding, bad CSV)."""


class SchemaIncompatibleError(CsvCompError):
    """Raised when the inputs are unambiguously shape-broken (ragged/short rows
    beyond what can be tolerated). Per spec acceptance criteria 19 & 20."""
