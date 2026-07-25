"""Shared pytest fixtures for csvcomp.

Adds ``src/`` to sys.path so tests can import the package without an editable
install. Also provides a small helper for writing CSV files with optional BOM
and CRLF line endings.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def tmp(tmp_path: Path) -> Path:
    return tmp_path


def write_csv(
    path: Path,
    body: str,
    *,
    bom: bool = False,
    crlf: bool = False,
) -> Path:
    """Write a CSV file with optional BOM and CRLF line endings."""
    if bom:
        body = "\ufeff" + body
    if crlf:
        body = body.replace("\n", "\r\n")
    path.write_text(body, encoding="utf-8")
    return path
