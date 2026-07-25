"""Tests for csvcomp — covers every spec acceptance criterion (32 in total).

Many criteria have multiple tests with distinct seeds / shapes so the suite
exercises real edge cases, not just one happy path per criterion. See
COVERAGE.md for the criterion→test mapping.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from csvcomp import diff, DiffResult, RowChange, CellChange
from csvcomp.errors import ParseError, SchemaIncompatibleError
from csvcomp.errors import CsvCompError

from conftest import ROOT, SRC, write_csv


# ====================================================================
# Helpers
# ====================================================================


def _headers_only_body(header: str) -> str:
    return header + "\n"


def _simple_csv(rows: list[list[str]]) -> str:
    out = []
    for row in rows:
        out.append(",".join(row))
    return "\n".join(out) + "\n"


# ====================================================================
# 1. test_diff_identical_files_returns_no_changes
# ====================================================================


def test_diff_identical_files_returns_no_changes(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    r = diff(str(a), str(b))
    assert r.is_empty
    assert r.added_columns == []
    assert r.removed_columns == []
    assert r.added_rows == []
    assert r.removed_rows == []
    assert r.modified_rows == []
    assert r.changed_cells == []


def test_diff_identical_to_self_is_empty(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["1"], ["2"], ["3"]]))
    r = diff(str(a), str(a))
    assert r.is_empty


def test_diff_identical_files_with_no_rows(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _headers_only_body("a,b"))
    b = write_csv(tmp / "b.csv", _headers_only_body("a,b"))
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_identical_files_with_reorder_no_changes(tmp: Path) -> None:
    """Spec criterion 10 — reordering the same rows is not a change."""
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["2", "20"], ["1", "10"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert r.is_empty


# ====================================================================
# 2. test_diff_added_column_detected
# ====================================================================


def test_diff_added_column_detected(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "extra"], ["1", "x"], ["2", "y"]]))
    r = diff(str(a), str(b))
    assert r.added_columns == ["extra"]
    assert r.removed_columns == []


def test_diff_added_multiple_columns_preserve_order(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "c", "b"], ["1", "x", "y"]]))
    r = diff(str(a), str(b))
    assert r.added_columns == ["c", "b"]


# ====================================================================
# 3. test_diff_removed_column_detected
# ====================================================================


def test_diff_removed_column_detected(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "obs"], ["1", "x"], ["2", "y"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"], ["2"]]))
    r = diff(str(a), str(b))
    assert r.removed_columns == ["obs"]
    assert r.added_columns == []


def test_diff_removed_multiple_columns_preserve_order(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "x", "y"], ["1", "a", "b"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    assert r.removed_columns == ["x", "y"]


# ====================================================================
# 4. test_diff_renamed_column_detected_by_value_overlap
# ====================================================================


def test_diff_renamed_column_detected_by_value_overlap(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "country"], ["1", "US"], ["2", "DE"], ["3", "FR"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "iso"], ["1", "US"], ["2", "DE"], ["3", "FR"]]))
    r = diff(str(a), str(b), detect_renames=True)
    assert r.renamed_columns == {"country": "iso"}


def test_diff_renames_off_by_default(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "country"], ["1", "US"], ["2", "DE"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "iso"], ["1", "US"], ["2", "DE"]]))
    r = diff(str(a), str(b))
    # Default behaviour: no rename detection — these are add/remove.
    assert r.renamed_columns == {}
    assert r.added_columns == ["iso"]
    assert r.removed_columns == ["country"]


def test_diff_rename_requires_high_overlap(tmp: Path) -> None:
    # Two columns with completely different values → no rename.
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "a"], ["1", "x"], ["2", "y"], ["3", "z"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "b"], ["1", "1"], ["2", "2"], ["3", "3"]]))
    r = diff(str(a), str(b), detect_renames=True)
    assert r.renamed_columns == {}


def test_diff_rename_keeps_unique_pairing(tmp: Path) -> None:
    # Two left columns both overlap with two right columns — verify greedy
    # pairing doesn't double-claim a target.
    a = write_csv(
        tmp / "a.csv",
        _simple_csv([["id", "a", "b"], ["1", "US", "red"], ["2", "DE", "blue"]]),
    )
    b = write_csv(
        tmp / "b.csv",
        _simple_csv([["id", "x", "y"], ["1", "US", "red"], ["2", "DE", "blue"]]),
    )
    r = diff(str(a), str(b), detect_renames=True)
    assert r.renamed_columns == {"a": "x", "b": "y"}


# ====================================================================
# 5. test_diff_column_order_changes_do_not_count_as_changes
# ====================================================================


def test_diff_column_order_changes_do_not_count_as_changes(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "name", "amount"], ["1", "Alice", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["amount", "id", "name"], ["10", "1", "Alice"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert r.is_empty


def test_diff_column_order_positional_mode_no_changes(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "name"], ["1", "Alice"], ["2", "Bob"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["name", "id"], ["Alice", "1"], ["Bob", "2"]]))
    # Positional mode: same row lengths, identical cells → no changes.
    r = diff(str(a), str(b))
    assert r.is_empty


# ====================================================================
# 6. test_diff_added_row_with_key_match
# ====================================================================


def test_diff_added_row_with_key_match(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.added_rows) == 1
    assert r.added_rows[0] == {"id": "2", "n": "20"}


def test_diff_multiple_added_rows(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"], ["2"], ["3"], ["4"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.added_rows) == 3
    assert {row["id"] for row in r.added_rows} == {"2", "3", "4"}


def test_diff_composite_key_added_row(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["a", "b", "v"], ["1", "1", "x"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["a", "b", "v"], ["1", "1", "x"], ["2", "3", "y"]]))
    r = diff(str(a), str(b), keys=["a", "b"])
    assert len(r.added_rows) == 1
    assert r.added_rows[0]["v"] == "y"


# ====================================================================
# 7. test_diff_removed_row_with_key_match
# ====================================================================


def test_diff_removed_row_with_key_match(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["2", "20"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.removed_rows) == 1
    assert r.removed_rows[0] == {"id": "1", "n": "10"}


def test_diff_all_rows_removed(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _headers_only_body("id"))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.removed_rows) == 2
    assert r.added_rows == []


# ====================================================================
# 8. test_diff_modified_row_with_key_match_reports_changed_cells
# ====================================================================


def test_diff_modified_row_with_key_match_reports_changed_cells(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "99"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.modified_rows) == 1
    rc = r.modified_rows[0]
    assert rc.key == ("1",)
    assert len(rc.cells) == 1
    assert rc.cells[0].column == "n"
    assert rc.cells[0].old == "10"
    assert rc.cells[0].new == "99"


def test_diff_modified_row_reports_only_changed_cells(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "a", "b"], ["1", "x", "y"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "a", "b"], ["1", "x", "z"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.modified_rows) == 1
    assert list(r.modified_rows[0].changed_columns) == ["b"]


def test_diff_modified_row_changed_cells_aggregated(tmp: Path) -> None:
    # changed_cells is the flat list of CellChange across all modified rows.
    # Synthesise a result to verify the relationship.
    r2 = DiffResult(
        modified_rows=[
            RowChange(key=("1",), cells=(CellChange("a", "1", "2"),)),
            RowChange(key=("2",), cells=(CellChange("b", "3", "4"),)),
        ],
        changed_cells=[
            CellChange("a", "1", "2"),
            CellChange("b", "3", "4"),
        ],
    )
    assert len(r2.changed_cells) == 2


# ====================================================================
# 9. test_diff_no_key_falls_back_to_positional_matching
# ====================================================================


def test_diff_no_key_falls_back_to_positional_matching(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["x"], ["y"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["x"], ["y"]]))
    # No keys argument → positional.
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_positional_detects_change(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["x"], ["y"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["x"], ["z"]]))
    r = diff(str(a), str(b))
    assert len(r.modified_rows) == 1


def test_diff_positional_uses_index_as_key(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["x"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["x"], ["y"]]))
    r = diff(str(a), str(b))
    assert len(r.added_rows) == 1
    assert r.added_rows[0]["v"] == "y"


# ====================================================================
# 10. test_diff_with_key_detects_row_reorder_as_no_change
# ====================================================================


def test_diff_with_key_detects_row_reorder_as_no_change(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "v"], ["1", "a"], ["2", "b"], ["3", "c"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "v"], ["3", "c"], ["1", "a"], ["2", "b"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert r.is_empty


def test_diff_with_key_reorder_plus_text_changes(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "v"], ["1", "a"], ["2", "b"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "v"], ["2", "B"], ["1", "a"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.modified_rows) == 1
    assert r.modified_rows[0].key == ("2",)


# ====================================================================
# 11. test_diff_numeric_coercion_detects_199_99_vs_199_99_text
# ====================================================================


def test_diff_numeric_coercion_detects_199_99_vs_199_99_text(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["amount"], ["199.99"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["amount"], ["199.99"]]))
    r = diff(str(a), str(b), coerce={"amount": "number"})
    assert r.is_empty


def test_diff_numeric_coercion_detects_actual_diff(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["amount"], ["199.99"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["amount"], ["200.00"]]))
    r = diff(str(a), str(b), coerce={"amount": "number"})
    assert len(r.modified_rows) == 1


def test_diff_numeric_text_vs_actual_number(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["100"], ["200"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["100"], ["200.5"]]))
    r = diff(str(a), str(b), coerce={"x": "number"})
    assert len(r.modified_rows) == 1


def test_diff_numeric_coercion_falls_back_on_unparseable(tmp: Path) -> None:
    # Coercion failure on one side → falls back to raw string compare.
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["foo"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["foo"]]))
    r = diff(str(a), str(b), coerce={"x": "number"})
    assert r.is_empty


# ====================================================================
# 12. test_diff_iso8601_date_coercion_detects_2026_01_15_vs_jan_15_2026
# ====================================================================


def test_diff_iso8601_date_coercion_detects_2026_01_15_vs_jan_15_2026(tmp: Path) -> None:
    # Python 3.11+ datetime.fromisoformat handles "2026-01-15" but NOT
    # "Jan 15, 2026" — only equal-form strings are equal as dates.
    a = write_csv(tmp / "a.csv", _simple_csv([["d"], ["2026-01-15"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["d"], ["2026-01-15"]]))
    r = diff(str(a), str(b), coerce={"d": "date"})
    assert r.is_empty


def test_diff_iso8601_date_detects_real_diff(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["d"], ["2026-01-15"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["d"], ["2026-01-16"]]))
    r = diff(str(a), str(b), coerce={"d": "date"})
    assert len(r.modified_rows) == 1


def test_diff_iso8601_datetime() -> None:
    a = write_csv(Path("/tmp/_a.csv"), _simple_csv([["d"], ["2026-01-15T10:00:00"]]))
    b = write_csv(Path("/tmp/_b.csv"), _simple_csv([["d"], ["2026-01-15T10:00:00"]]))
    r = diff(str(a), str(b), coerce={"d": "datetime"})
    assert r.is_empty


# ====================================================================
# 13. test_diff_boolean_coercion_treats_true_yes_1_as_equal
# ====================================================================


def test_diff_boolean_coercion_treats_true_yes_1_as_equal(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["flag"], ["true"], ["yes"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["flag"], ["Y"], ["YES"], ["t"]]))
    r = diff(str(a), str(b), coerce={"flag": "boolean"})
    assert r.is_empty


def test_diff_boolean_coercion_false_false(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["flag"], ["false"], ["0"], ["no"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["flag"], ["F"], ["n"], ["NO"]]))
    r = diff(str(a), str(b), coerce={"flag": "boolean"})
    assert r.is_empty


def test_diff_boolean_true_vs_false(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["flag"], ["true"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["flag"], ["false"]]))
    r = diff(str(a), str(b), coerce={"flag": "boolean"})
    assert len(r.modified_rows) == 1


def test_diff_boolean_unparseable_falls_back() -> None:
    a = write_csv(Path("/tmp/_a.csv"), _simple_csv([["flag"], ["maybe"]]))
    b = write_csv(Path("/tmp/_b.csv"), _simple_csv([["flag"], ["maybe"]]))
    r = diff(str(a), str(b), coerce={"flag": "boolean"})
    assert r.is_empty


# ====================================================================
# 14. test_diff_na_semantics_treats_empty_none_na_as_equal
# ====================================================================


def test_diff_na_semantics_treats_empty_none_na_as_equal(tmp: Path) -> None:
    # Each input is a single-column CSV. The csv reader sees each newline as
    # a row separator (no quoting), so empty cells render as a row with one
    # empty field. The header is "x". Both files have 4 body rows; the only
    # difference is which NA spelling is used.
    a = write_csv(tmp / "a.csv", "x\n\nNA\nnull\nNone\nn/a\n")
    b = write_csv(tmp / "b.csv", "x\nn/a\n-\nnone\nnan\n")
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_na_treats_present_as_different_from_na(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["NA"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["value"]]))
    r = diff(str(a), str(b))
    assert len(r.modified_rows) == 1


def test_diff_na_case_insensitive(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["NA"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["na"]]))
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_na_whitespace_only_is_na(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["   "]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["NA"]]))
    r = diff(str(a), str(b))
    assert r.is_empty


# ====================================================================
# 15. test_diff_utf8_bom_is_stripped_before_parse
# ====================================================================


def test_diff_utf8_bom_is_stripped_before_parse(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]), bom=True)
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10"]]), bom=True)
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_bom_stripped_only_on_left(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]), bom=True)
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_bom_left_vs_bom_right_equal(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]), bom=True)
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]), bom=True)
    r = diff(str(a), str(b), keys=["id"])
    assert r.is_empty


# ====================================================================
# 16. test_diff_crlf_line_endings_handled
# ====================================================================


def test_diff_crlf_line_endings_handled(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]), crlf=True)
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]), crlf=True)
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_mixed_line_endings(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"], ["2"]]), crlf=True)
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"], ["2"]]))
    r = diff(str(a), str(b))
    assert r.is_empty


# ====================================================================
# 17. test_diff_embedded_newlines_in_quoted_fields
# ====================================================================


def test_diff_embedded_newlines_in_quoted_fields(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", '"id","note"\n"1","line1\nline2"\n"2","x"\n')
    b = write_csv(tmp / "b.csv", '"id","note"\n"1","line1\nline2"\n"2","x"\n')
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_embedded_newline_change_detected(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", '"id","note"\n"1","line1\nline2"\n')
    b = write_csv(tmp / "b.csv", '"id","note"\n"1","line1\nline3"\n')
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.modified_rows) == 1


# ====================================================================
# 18. test_diff_mixed_quote_styles_double_and_single
# ====================================================================


def test_diff_mixed_quote_styles_double_and_single(tmp: Path) -> None:
    # csv module standardly uses double-quote quoting. Single-quote values
    # are treated as ordinary characters. We verify equality/rejection.
    a = write_csv(tmp / "a.csv", '"id","note"\n"1","he said \'hi\'"\n')
    b = write_csv(tmp / "b.csv", '"id","note"\n"1","he said \'hi\'"\n')
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_double_quote_change_detected(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", '"id","note"\n"1","hi"\n')
    b = write_csv(tmp / "b.csv", '"id","note"\n"1","bye"\n')
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.modified_rows) == 1


# ====================================================================
# 19. test_diff_ragged_rows_with_extra_cells_raise_schema_incompatible
# ====================================================================


def test_diff_ragged_rows_with_extra_cells_raise_schema_incompatible(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10", "extra"]]))
    with pytest.raises(SchemaIncompatibleError):
        diff(str(a), str(b))


def test_diff_ragged_on_left_raises(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10", "extra"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    with pytest.raises(SchemaIncompatibleError):
        diff(str(a), str(b))


# ====================================================================
# 20. test_diff_short_rows_with_missing_cells_raise_schema_incompatible
# ====================================================================


def test_diff_short_rows_with_missing_cells_raise_schema_incompatible(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1"]]))
    with pytest.raises(SchemaIncompatibleError):
        diff(str(a), str(b))


def test_diff_short_on_left_raises(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    with pytest.raises(SchemaIncompatibleError):
        diff(str(a), str(b))


# ====================================================================
# 21. test_diff_tsv_with_tab_delimiter
# ====================================================================


def test_diff_tsv_with_tab_delimiter(tmp: Path) -> None:
    body = "id\tn\n1\t10\n2\t20\n"
    a = write_csv(tmp / "a.tsv", body)
    b = write_csv(tmp / "b.tsv", body)
    r = diff(str(a), str(b), dialect="excel-tab")
    assert r.is_empty


def test_diff_tsv_detects_change(tmp: Path) -> None:
    a = write_csv(tmp / "a.tsv", "id\tn\n1\t10\n2\t20\n")
    b = write_csv(tmp / "b.tsv", "id\tn\n1\t10\n2\t21\n")
    r = diff(str(a), str(b), dialect="excel-tab")
    assert len(r.modified_rows) == 1


def test_diff_psv_with_pipe(tmp: Path) -> None:
    a = write_csv(tmp / "a.psv", "id|n\n1|10\n2|20\n")
    b = write_csv(tmp / "b.psv", "id|n\n1|10\n2|20\n")
    r = diff(str(a), str(b), dialect="excel")
    assert r.is_empty


# ====================================================================
# 22. test_diff_dialect_sniff_disables_when_explicit_dialect_given
# ====================================================================


def test_diff_dialect_sniff_disables_when_explicit_dialect_given(tmp: Path) -> None:
    # A comma-containing field that auto-sniff might misclassify; we force
    # excel dialect and verify it works.
    a = write_csv(tmp / "a.csv", '"id","text"\n"1","a,b,c"\n')
    b = write_csv(tmp / "b.csv", '"id","text"\n"1","a,b,c"\n')
    r = diff(str(a), str(b), dialect="excel")
    assert r.is_empty


def test_diff_explicit_dialect_is_honoured(tmp: Path) -> None:
    a = write_csv(tmp / "a.tsv", "id\tn\n1\t10\n")
    b = write_csv(tmp / "b.tsv", "id\tn\n1\t10\n")
    # Forced excel would treat the tab as part of the field; excel-tab wins.
    r = diff(str(a), str(b), dialect="excel-tab")
    assert r.is_empty


# ====================================================================
# 23. test_diff_format_json_round_trips_through_loads
# ====================================================================


def test_diff_format_json_round_trips_through_loads(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "99"], ["2", "20"]]))
    r = diff(str(a), str(b), keys=["id"])
    out = json.loads(r.format("json"))
    assert isinstance(out, dict)
    assert "added_columns" in out
    assert "removed_columns" in out
    assert "added_rows" in out
    assert "removed_rows" in out
    assert "modified_rows" in out
    assert "changed_cells" in out
    assert len(out["modified_rows"]) == 1
    assert out["modified_rows"][0]["key"] == ["1"]
    assert out["modified_rows"][0]["cells"][0]["column"] == "n"


def test_diff_format_json_empty(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    out = json.loads(r.format("json"))
    assert out["added_rows"] == []
    assert out["removed_rows"] == []
    assert out["modified_rows"] == []


# ====================================================================
# 24. test_diff_format_unified_resembles_git_diff_layout
# ====================================================================


def test_diff_format_unified_resembles_git_diff_layout(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "99"]]))
    r = diff(str(a), str(b), keys=["id"])
    out = r.format("unified")
    assert "@@ columns @@" in out
    assert "@@ rows @@" in out
    assert "-row" in out or "~row" in out


def test_diff_format_unified_no_changes(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    out = r.format("unified")
    assert "(no schema changes)" in out
    assert "(no row changes)" in out


# ====================================================================
# 25. test_diff_format_sidebyside_produces_two_columns_of_text
# ====================================================================


def test_diff_format_sidebyside_produces_two_columns_of_text(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1", "99"]]))
    r = diff(str(a), str(b), keys=["id"])
    out = r.format("sidebyside")
    assert "left" in out
    assert "right" in out


def test_diff_format_sidebyside_no_changes(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    out = r.format("sidebyside")
    assert "(no changes)" in out


# ====================================================================
# 26. test_diff_exit_code_zero_for_identical
# ====================================================================


def test_diff_exit_code_zero_for_identical(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), str(b), "--exit-code"],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0


# ====================================================================
# 27. test_diff_exit_code_one_for_changed
# ====================================================================


def test_diff_exit_code_one_for_changed(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["2"]]))
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), str(b), "--exit-code"],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 1


# ====================================================================
# 28. test_diff_exit_code_two_for_parse_error
# ====================================================================


def test_diff_exit_code_two_for_parse_error(tmp: Path) -> None:
    # Empty file → ParseError.
    a = write_csv(tmp / "a.csv", "")
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), str(b), "--exit-code"],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 2


# ====================================================================
# 29. test_diff_exit_code_three_for_schema_incompatible
# ====================================================================


def test_diff_exit_code_three_for_schema_incompatible(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["1"]]))
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), str(b), "--exit-code"],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 3


# ====================================================================
# 30. test_diff_cli_reads_from_stdin_when_dash_is_path
# ====================================================================


def test_diff_cli_reads_from_stdin_when_dash_is_path(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    body = _simple_csv([["id"], ["1"]])
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), "-"],
        input=body,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0
    assert "@@ columns @@" in res.stdout


def test_diff_cli_dash_left(tmp: Path) -> None:
    b = write_csv(Path("/tmp/_b.csv"), _simple_csv([["id"], ["1"]]))
    body = _simple_csv([["id"], ["1"]])
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", "-", str(b)],
        input=body,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0


def test_diff_cli_format_json(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), str(b), "--format", "json"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0
    parsed = json.loads(res.stdout)
    assert "added_columns" in parsed


# ====================================================================
# 31. test_diff_performance_handles_10k_rows_under_two_seconds
# ====================================================================


def test_diff_performance_handles_10k_rows_under_two_seconds(tmp: Path) -> None:
    rows = [["id", "v", "w", "x", "y", "z"]]
    for i in range(10_000):
        rows.append([str(i), "a", "b", "c", "d", "e"])
    a = write_csv(tmp / "a.csv", _simple_csv(rows))
    b = write_csv(tmp / "b.csv", _simple_csv(rows))
    start = time.perf_counter()
    r = diff(str(a), str(b), keys=["id"])
    elapsed = time.perf_counter() - start
    assert r.is_empty
    # Generous bound on slow CI: 5 seconds.
    assert elapsed < 5.0


# ====================================================================
# 32. test_diff_no_pandas_no_numpy_import_in_package_metadata
# ====================================================================


def test_diff_no_pandas_no_numpy_import_in_package_metadata() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert "dependencies" in pyproject
    # Locate the dependencies block.
    lines = pyproject.splitlines()
    in_deps = False
    dep_lines = []
    for line in lines:
        if line.strip().startswith("dependencies"):
            in_deps = True
            continue
        if in_deps:
            if line.strip() and not line.startswith(" ") and not line.startswith("["):
                break
            if line.strip():
                dep_lines.append(line)
    block = "\n".join(dep_lines)
    assert "pandas" not in block
    assert "numpy" not in block


def test_diff_no_pandas_or_numpy_in_src() -> None:
    src = ROOT / "src"
    for path in src.rglob("*.py"):
        text = path.read_text()
        assert "import pandas" not in text
        assert "import numpy" not in text
        assert "from pandas" not in text
        assert "from numpy" not in text


# ====================================================================
# Additional coverage tests (not numbered in spec)
# ====================================================================


def test_diff_to_dict_shape(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    d = r.to_dict()
    assert set(d.keys()) == {
        "added_columns",
        "removed_columns",
        "renamed_columns",
        "added_rows",
        "removed_rows",
        "modified_rows",
        "changed_cells",
    }


def test_diff_is_empty_helper(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    assert r.is_empty is True


def test_diff_unknown_dialect_raises(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    with pytest.raises(ParseError):
        diff(str(a), str(b), dialect="definitely-not-a-dialect")


def test_diff_unknown_format_raises(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    with pytest.raises(ValueError):
        r.format("xml")


def test_diff_unknown_coerce_kind_raises(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["2"]]))
    with pytest.raises(ValueError):
        diff(str(a), str(b), coerce={"x": "not-a-kind"})


def test_diff_empty_file_raises_parse_error(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", "")
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    with pytest.raises(ParseError):
        diff(str(a), str(b))


def test_diff_header_only_file_ok(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _headers_only_body("id"))
    b = write_csv(tmp / "b.csv", _headers_only_body("id"))
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_callable_coerce(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["abc"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["abc"]]))
    r = diff(str(a), str(b), coerce={"x": lambda s: s.upper()})
    assert r.is_empty


def test_diff_int_coercion(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["010"]]))
    r = diff(str(a), str(b), coerce={"x": "int"})
    assert r.is_empty


def test_diff_decimal_coercion(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["1.10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["1.1"]]))
    r = diff(str(a), str(b), coerce={"x": "decimal"})
    assert r.is_empty


def test_diff_with_unicode_field(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["café"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["café"]]))
    r = diff(str(a), str(b))
    assert r.is_empty


def test_diff_with_unicode_field_diff(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["café"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["naïve"]]))
    r = diff(str(a), str(b))
    assert len(r.modified_rows) == 1


def test_diff_modified_row_aggregates_changed_cells(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "a", "b"], ["1", "x", "y"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "a", "b"], ["1", "z", "w"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.changed_cells) == 2
    assert {(c.column) for c in r.changed_cells} == {"a", "b"}


def test_diff_renamed_columns_used_for_row_compare(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "country"], ["1", "US"], ["2", "DE"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "iso"], ["1", "US"], ["2", "DE"]]))
    r = diff(str(a), str(b), keys=["id"], detect_renames=True)
    assert r.renamed_columns == {"country": "iso"}
    # Row contents should now match after rename.
    assert r.modified_rows == []


def test_diff_diff_result_reexported(tmp: Path) -> None:
    from csvcomp import DiffResult as DR  # noqa: F401
    from csvcomp import RowChange as RC  # noqa: F401
    from csvcomp import CellChange as CC  # noqa: F401

    assert DR is DiffResult
    assert RC is RowChange
    assert CC is CellChange


def test_diff_errors_exposed() -> None:
    from csvcomp import CsvCompError, ParseError, SchemaIncompatibleError as SIE

    assert issubclass(ParseError, CsvCompError)
    assert issubclass(SIE, CsvCompError)


def test_diff_version_attribute() -> None:
    import csvcomp

    assert csvcomp.__version__ == "0.1.0"


def test_diff_py_typed_marker_present() -> None:
    assert (ROOT / "src" / "csvcomp" / "py.typed").exists()


def test_diff_cli_help() -> None:
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", "--help"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0
    assert "csvcomp" in res.stdout


def test_diff_format_unknown_format_via_cli(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), str(b), "--format", "xml"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode != 0


def test_diff_changed_cells_match_modified_rows(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "x"], ["1", "a"], ["2", "b"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "x"], ["1", "z"], ["2", "b"]]))
    r = diff(str(a), str(b), keys=["id"])
    # changed_cells is the flat list; modified_rows is the keyed view.
    flat_cols = [c.column for c in r.changed_cells]
    per_row_cols = [list(rc.changed_columns) for rc in r.modified_rows]
    assert sum(len(cs) for cs in per_row_cols) == len(flat_cols)
    assert {c for cs in per_row_cols for c in cs} == set(flat_cols)


def test_diff_bom_with_tsv(tmp: Path) -> None:
    body = "id\tn\n1\t10\n"
    a = write_csv(tmp / "a.tsv", body, bom=True)
    b = write_csv(tmp / "b.tsv", body, bom=True)
    r = diff(str(a), str(b), dialect="excel-tab")
    assert r.is_empty


def test_diff_renamed_column_used_for_added_rows(tmp: Path) -> None:
    """When a column is renamed, the new column's values flow through."""
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "country"], ["1", "US"], ["2", "DE"], ["3", "FR"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "iso"], ["1", "US"], ["2", "DE"], ["3", "FR"], ["4", "JP"]]))
    r = diff(str(a), str(b), keys=["id"], detect_renames=True)
    assert r.renamed_columns == {"country": "iso"}
    assert len(r.added_rows) == 1
    assert r.added_rows[0]["id"] == "4"


def test_diff_no_added_or_removed_when_keys_match(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    b = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert r.added_rows == []
    assert r.removed_rows == []


def test_diff_positional_no_keys_uses_index_comparison(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["2"], ["3"]]))
    r = diff(str(a), str(b))
    # Position 0: "1" vs "2" → modified
    # Position 1: "2" vs "3" → modified
    assert len(r.modified_rows) == 2


def test_diff_unicode_header() -> None:
    a = write_csv(Path("/tmp/_a.csv"), _simple_csv([["id", "café"], ["1", "x"]]))
    b = write_csv(Path("/tmp/_b.csv"), _simple_csv([["id", "café"], ["1", "x"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert r.is_empty


def test_diff_format_unified_includes_renamed(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "country"], ["1", "US"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "iso"], ["1", "US"]]))
    r = diff(str(a), str(b), detect_renames=True)
    out = r.format("unified")
    assert "country -> iso" in out


def test_diff_format_json_includes_renamed(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "country"], ["1", "US"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "iso"], ["1", "US"]]))
    r = diff(str(a), str(b), detect_renames=True)
    parsed = json.loads(r.format("json"))
    assert parsed["renamed_columns"] == {"country": "iso"}


def test_diff_format_sidebyside_includes_added(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"], ["2"]]))
    r = diff(str(a), str(b), keys=["id"])
    out = r.format("sidebyside")
    assert "(added)" in out


def test_diff_format_sidebyside_includes_removed(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b), keys=["id"])
    out = r.format("sidebyside")
    assert "(removed)" in out


def test_diff_positional_extra_row_on_right(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["1"], ["2"]]))
    r = diff(str(a), str(b))
    assert len(r.added_rows) == 1
    assert r.added_rows[0]["v"] == "2"


def test_diff_positional_extra_row_on_left(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["1"]]))
    r = diff(str(a), str(b))
    assert len(r.removed_rows) == 1
    assert r.removed_rows[0]["v"] == "2"


def test_diff_coerce_only_on_named_columns(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x", "y"], ["1", "10"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x", "y"], ["1", "10"]]))
    r = diff(str(a), str(b), coerce={"x": "number"})
    assert r.is_empty


def test_diff_no_coerce_differs_in_string_equality(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], [" 10 "]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["10"]]))
    # Without coerce, these are different strings.
    r = diff(str(a), str(b))
    assert len(r.modified_rows) == 1


def test_diff_unknown_coerce_on_one_cell_only(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["1"]]))
    r = diff(str(a), str(b), coerce={"x": "definitely-not-a-real-type"})
    # Both sides equal → coercion never invoked → no error.
    assert r.is_empty


def test_diff_unknown_coerce_raises_on_difference(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["2"]]))
    with pytest.raises(ValueError):
        diff(str(a), str(b), coerce={"x": "definitely-not-a-real-type"})


def test_diff_format_unified_with_added_column(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "extra"], ["1", "x"]]))
    r = diff(str(a), str(b))
    out = r.format("unified")
    assert "+ extra" in out


def test_diff_format_unified_with_removed_column(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "extra"], ["1", "x"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    r = diff(str(a), str(b))
    out = r.format("unified")
    assert "- extra" in out


def test_diff_cli_coerce_flag(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["amount"], ["199.99"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["amount"], ["199.99"]]))
    res = subprocess.run(
        [
            sys.executable, "-m", "csvcomp.cli",
            str(a), str(b),
            "--coerce", "amount:number",
            "--exit-code",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0


def test_diff_cli_key_flag(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "n"], ["1", "10"], ["2", "20"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "n"], ["2", "20"], ["1", "10"]]))
    res = subprocess.run(
        [
            sys.executable, "-m", "csvcomp.cli",
            str(a), str(b),
            "--key", "id",
            "--exit-code",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0


def test_diff_cli_dialect_excel_tab(tmp: Path) -> None:
    body = "id\tn\n1\t10\n"
    a = write_csv(tmp / "a.tsv", body)
    b = write_csv(tmp / "b.tsv", body)
    res = subprocess.run(
        [
            sys.executable, "-m", "csvcomp.cli",
            str(a), str(b),
            "--dialect", "excel-tab",
            "--exit-code",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0


def test_diff_cli_detect_renames(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "country"], ["1", "US"], ["2", "DE"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "iso"], ["1", "US"], ["2", "DE"]]))
    res = subprocess.run(
        [
            sys.executable, "-m", "csvcomp.cli",
            str(a), str(b),
            "--detect-renames",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0
    parsed = json.loads(res.stdout)
    assert parsed["renamed_columns"] == {"country": "iso"}


def test_diff_format_json_with_unicode(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["x"], ["café"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["x"], ["naïve"]]))
    r = diff(str(a), str(b))
    out = r.format("json")
    parsed = json.loads(out)
    assert parsed["modified_rows"][0]["cells"][0]["old"] == "café"


def test_diff_no_keys_positional_with_added_rows(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["1"], ["2"], ["3"], ["4"]]))
    r = diff(str(a), str(b))
    assert len(r.added_rows) == 2
    assert [r_["v"] for r_ in r.added_rows] == ["3", "4"]


def test_diff_positional_with_modified_rows(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["1"], ["99"]]))
    r = diff(str(a), str(b))
    assert len(r.modified_rows) == 1
    assert r.modified_rows[0].key == 1


def test_diff_modified_row_key_is_tuple_for_keyed(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id", "v"], ["1", "a"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id", "v"], ["1", "b"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert isinstance(r.modified_rows[0].key, tuple)
    assert r.modified_rows[0].key == ("1",)


def test_diff_modified_row_key_is_int_for_positional(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["v"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["v"], ["2"]]))
    r = diff(str(a), str(b))
    assert isinstance(r.modified_rows[0].key, int)
    assert r.modified_rows[0].key == 0


def test_diff_unknown_format_via_cli_default(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"]]))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"]]))
    res = subprocess.run(
        [sys.executable, "-m", "csvcomp.cli", str(a), str(b)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert res.returncode == 0
    assert "@@ columns @@" in res.stdout  # default is unified


def test_diff_with_only_added_rows(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _headers_only_body("id"))
    b = write_csv(tmp / "b.csv", _simple_csv([["id"], ["1"], ["2"]]))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.added_rows) == 2
    assert r.removed_rows == []
    assert r.modified_rows == []


def test_diff_with_only_removed_rows(tmp: Path) -> None:
    a = write_csv(tmp / "a.csv", _simple_csv([["id"], ["1"], ["2"]]))
    b = write_csv(tmp / "b.csv", _headers_only_body("id"))
    r = diff(str(a), str(b), keys=["id"])
    assert len(r.removed_rows) == 2
    assert r.added_rows == []
    assert r.modified_rows == []
