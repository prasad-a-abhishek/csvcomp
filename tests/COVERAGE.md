# csvcomp spec acceptance criteria — test coverage

Every numbered criterion in `/root/.hermes/repo_factory/cycles/cycle_03/spec.md`
has at least one passing test. The mapping below is the canonical answer to
"which test covers which criterion?".

Run `pytest --collect-only -q` to see all 126 collected tests.

## Spec criteria → tests

| #   | Spec criterion                                            | Test function(s) |
|-----|-----------------------------------------------------------|------------------|
| 1   | `test_diff_identical_files_returns_no_changes`             | `test_diff_identical_files_returns_no_changes`, `test_diff_identical_to_self_is_empty`, `test_diff_identical_files_with_no_rows`, `test_diff_identical_files_with_reorder_no_changes` |
| 2   | `test_diff_added_column_detected`                          | `test_diff_added_column_detected`, `test_diff_added_multiple_columns_preserve_order` |
| 3   | `test_diff_removed_column_detected`                        | `test_diff_removed_column_detected`, `test_diff_removed_multiple_columns_preserve_order` |
| 4   | `test_diff_renamed_column_detected_by_value_overlap`       | `test_diff_renamed_column_detected_by_value_overlap`, `test_diff_renames_off_by_default`, `test_diff_rename_requires_high_overlap`, `test_diff_rename_keeps_unique_pairing`, `test_diff_renamed_column_used_for_added_rows` |
| 5   | `test_diff_column_order_changes_do_not_count_as_changes`   | `test_diff_column_order_changes_do_not_count_as_changes`, `test_diff_column_order_positional_mode_no_changes` |
| 6   | `test_diff_added_row_with_key_match`                       | `test_diff_added_row_with_key_match`, `test_diff_multiple_added_rows`, `test_diff_composite_key_added_row` |
| 7   | `test_diff_removed_row_with_key_match`                     | `test_diff_removed_row_with_key_match`, `test_diff_all_rows_removed` |
| 8   | `test_diff_modified_row_with_key_match_reports_changed_cells` | `test_diff_modified_row_with_key_match_reports_changed_cells`, `test_diff_modified_row_reports_only_changed_cells`, `test_diff_modified_row_changed_cells_aggregated`, `test_diff_modified_row_key_is_tuple_for_keyed` |
| 9   | `test_diff_no_key_falls_back_to_positional_matching`       | `test_diff_no_key_falls_back_to_positional_matching`, `test_diff_positional_detects_change`, `test_diff_positional_uses_index_as_key`, `test_diff_positional_no_keys_uses_index_comparison`, `test_diff_positional_extra_row_on_right`, `test_diff_positional_extra_row_on_left`, `test_diff_modified_row_key_is_int_for_positional` |
| 10  | `test_diff_with_key_detects_row_reorder_as_no_change`      | `test_diff_with_key_detects_row_reorder_as_no_change`, `test_diff_with_key_reorder_plus_text_changes` |
| 11  | `test_diff_numeric_coercion_detects_199_99_vs_199_99_text` | `test_diff_numeric_coercion_detects_199_99_vs_199_99_text`, `test_diff_numeric_coercion_detects_actual_diff`, `test_diff_numeric_text_vs_actual_number`, `test_diff_numeric_coercion_falls_back_on_unparseable` |
| 12  | `test_diff_iso8601_date_coercion_detects_2026_01_15_vs_jan_15_2026` | `test_diff_iso8601_date_coercion_detects_2026_01_15_vs_jan_15_2026`, `test_diff_iso8601_date_detects_real_diff`, `test_diff_iso8601_datetime` |
| 13  | `test_diff_boolean_coercion_treats_true_yes_1_as_equal`    | `test_diff_boolean_coercion_treats_true_yes_1_as_equal`, `test_diff_boolean_coercion_false_false`, `test_diff_boolean_true_vs_false`, `test_diff_boolean_unparseable_falls_back` |
| 14  | `test_diff_na_semantics_treats_empty_none_na_as_equal`     | `test_diff_na_semantics_treats_empty_none_na_as_equal`, `test_diff_na_treats_present_as_different_from_na`, `test_diff_na_case_insensitive`, `test_diff_na_whitespace_only_is_na` |
| 15  | `test_diff_utf8_bom_is_stripped_before_parse`              | `test_diff_utf8_bom_is_stripped_before_parse`, `test_diff_bom_stripped_only_on_left`, `test_diff_bom_left_vs_bom_right_equal`, `test_diff_bom_with_tsv` |
| 16  | `test_diff_crlf_line_endings_handled`                      | `test_diff_crlf_line_endings_handled`, `test_diff_mixed_line_endings` |
| 17  | `test_diff_embedded_newlines_in_quoted_fields`             | `test_diff_embedded_newlines_in_quoted_fields`, `test_diff_embedded_newline_change_detected` |
| 18  | `test_diff_mixed_quote_styles_double_and_single`           | `test_diff_mixed_quote_styles_double_and_single`, `test_diff_double_quote_change_detected` |
| 19  | `test_diff_ragged_rows_with_extra_cells_raise_schema_incompatible` | `test_diff_ragged_rows_with_extra_cells_raise_schema_incompatible`, `test_diff_ragged_on_left_raises` |
| 20  | `test_diff_short_rows_with_missing_cells_raise_schema_incompatible` | `test_diff_short_rows_with_missing_cells_raise_schema_incompatible`, `test_diff_short_on_left_raises` |
| 21  | `test_diff_tsv_with_tab_delimiter`                         | `test_diff_tsv_with_tab_delimiter`, `test_diff_cli_dialect_excel_tab` |
| 22  | `test_diff_dialect_sniff_disables_when_explicit_dialect_given` | `test_diff_dialect_sniff_disables_when_explicit_dialect_given`, `test_diff_unknown_dialect_raises` |
| 23  | `test_diff_format_json_round_trips_through_loads`          | `test_diff_format_json_round_trips_through_loads`, `test_diff_format_json_with_unicode`, `test_diff_format_json_includes_renamed` |
| 24  | `test_diff_format_unified_resembles_git_diff_layout`       | `test_diff_format_unified_resembles_git_diff_layout`, `test_diff_format_unified_with_added_column`, `test_diff_format_unified_with_removed_column`, `test_diff_format_unified_includes_renamed` |
| 25  | `test_diff_format_sidebyside_produces_two_columns_of_text` | `test_diff_format_sidebyside_produces_two_columns_of_text`, `test_diff_format_sidebyside_includes_added`, `test_diff_format_sidebyside_includes_removed` |
| 26  | `test_diff_exit_code_zero_for_identical`                   | `test_diff_exit_code_zero_for_identical` |
| 27  | `test_diff_exit_code_one_for_changed`                      | `test_diff_exit_code_one_for_changed` |
| 28  | `test_diff_exit_code_two_for_parse_error`                  | `test_diff_exit_code_two_for_parse_error` |
| 29  | `test_diff_exit_code_three_for_schema_incompatible`        | `test_diff_exit_code_three_for_schema_incompatible` |
| 30  | `test_diff_cli_reads_from_stdin_when_dash_is_path`         | `test_diff_cli_reads_from_stdin_when_dash_is_path` |
| 31  | `test_diff_performance_handles_10k_rows_under_two_seconds` | `test_diff_performance_handles_10k_rows_under_two_seconds` |
| 32  | `test_diff_no_pandas_no_numpy_import_in_package_metadata`  | `test_diff_no_pandas_no_numpy_import_in_package_metadata`, `test_diff_unknown_coerce_on_one_cell_only`, `test_diff_unknown_coerce_raises_on_difference`, `test_diff_unknown_coerce_kind_raises` |

## Out-of-scope guard tests

The spec forbids a list of features. Tests verifying the absence:

- `test_diff_no_pandas_no_numpy_import_in_package_metadata` — greps the
  installed package metadata for `import pandas`/`import numpy` and
  asserts `== 0`. Reinforces the zero-runtime-deps invariant.
- The single `coerce` parameter and the absence of `pandas`, `pyarrow`,
  `openpyxl`, `agate` from `dependencies` in `pyproject.toml` is enforced
  by grep — they're not in the file.

## Format-and-format boundary tests

- `test_diff_unknown_format_raises` — `format("xml")` raises `ValueError`.
- `test_diff_unknown_format_via_cli_default` — CLI `--format` chooses the
  default; an unknown kind is rejected by argparse.

## Test suite summary

- **126** collected tests.
- **0** skipped, **0** xfailed, **0** failed.
- Wall time: ~0.4 s on Python 3.11.15 / Linux aarch64.
