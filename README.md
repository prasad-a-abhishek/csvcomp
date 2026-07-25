# csvcomp

Semantic CSV↔CSV diff (schema + rows + cells) with zero runtime dependencies.

`csvcomp` compares two CSV/TSV files and reports:

- **Schema** changes — columns added, removed, or (optionally) renamed.
- **Row** changes — rows inserted, deleted, or modified. Rows can be matched
  positionally or by a key column (or composite key).
- **Cell** changes — for each modified row, exactly which cells changed.

Everything is zero runtime deps — `dependencies = []` in `pyproject.toml`. The
whole library runs on Python 3.11+ stdlib only (`csv`, `io`, `datetime`,
`decimal`, `collections`, `difflib`, `json`, `argparse`).

## Why this exists

Existing CSV-diff tools either refuse the most common production case, or
aren't embeddable in Python:

- `pandas.DataFrame.compare()` raises `ValueError` on the first shape
  mismatch — a single added column in a new export breaks the diff. (Quoted
  verbatim from the pandas docs.)
- `paulfitz/daff` is a Java library with a Node CLI wrapper; no embeddable
  Python API.
- `csvkit` ships 13 subcommands; none of them is a diff.
- `yourlabs/csv-diff` targets JSON-line key-based diffs, not CSV↔CSV.

`csvcomp` fills the gap: a single-file-library pure-Python diff that works
in CI, scripts, and pipelines without dragging in pandas, numpy, or any
third-party CSV parser.

## Install

The package is not yet on PyPI. From a clean clone:

```bash
pip install git+https://github.com/prasad-a-abhishek/csvcomp.git
```

For local development:

```bash
git clone https://github.com/prasad-a-abhishek/csvcomp.git
cd csvcomp
pip install -e ".[test]"
pytest
```

## CLI usage

```bash
csvcomp a.csv b.csv --key order_id --coerce amount:number,shipped_at:date --format unified
```

```text
@@ columns @@
  order_id   (kept)
  amount     (kept)
  shipped_at (kept)
+ tracking_id (added)

@@ rows @@
  key=[1042]  ~row  amount '199.99' -> '219.99'
  key=[1099]  +row  order_id='1099'  amount='10.00'  shipped_at='2026-01-15'
  key=[1101]  -row  order_id='1101'  amount='5.00'   shipped_at='2026-01-12'
```

### Exit codes

| Code | Meaning                                   |
|------|-------------------------------------------|
| 0    | Files are identical (or `--exit-code` unset, output printed) |
| 1    | Files differ (with `--exit-code`)         |
| 2    | Parse error (bad encoding, bad CSV)       |
| 3    | Schema-incompatible (ragged rows)         |

### Common flags

| Flag                  | Default     | Purpose                                          |
|-----------------------|-------------|--------------------------------------------------|
| `--key col1,col2`     | positional  | Match rows by these columns                      |
| `--coerce col:kind`   | none        | Typed comparison (`number`, `date`, `datetime`, `boolean`, `int`, `decimal`, `string`) |
| `--dialect`           | `auto`      | `auto`, `excel`, `excel-tab`, `unix`             |
| `--format`            | `unified`   | `json`, `unified`, `sidebyside`                  |
| `--detect-renames`    | off         | Detect column renames by value overlap           |
| `--exit-code`         | off         | Exit code = 0/1 instead of printing the result   |

## Python API

```python
from csvcomp import diff

result = diff(
    "a.csv",
    "b.csv",
    keys=["order_id"],
    coerce={"amount": "number", "shipped_at": "datetime"},
    detect_renames=True,
)

result.added_columns      # list[str]
result.removed_columns    # list[str]
result.renamed_columns    # dict[old, new]
result.added_rows         # list[dict]
result.removed_rows       # list[dict]
result.modified_rows      # list[RowChange]
result.changed_cells      # list[CellChange]
result.is_empty           # bool — True if no changes at all
result.format("json")     # str — JSON representation
result.format("unified")  # str — git-style diff
result.format("sidebyside")  # str — two-column table
```

## Coercion kinds

| Kind        | Accepts                          | Notes                                |
|-------------|----------------------------------|--------------------------------------|
| `string`    | any                              | byte-for-byte comparison             |
| `number`/`float` | decimal text                | both sides must parse; otherwise string fallback |
| `int`       | integer text                     | strict int parse                     |
| `decimal`   | decimal text                     | `Decimal` arithmetic, exact          |
| `date`      | ISO 8601 `YYYY-MM-DD`            | `date.fromisoformat`                 |
| `datetime`  | ISO 8601 `YYYY-MM-DDTHH:MM:SS`   | `datetime.fromisoformat`             |
| `boolean`/`bool` | `true/false/yes/no/1/0` (case-insensitive) | falls back to string if unparseable on both sides |

Unknown coerce kinds raise `ValueError` (subclass `UnknownCoercionError` —
also a `CsvCompError`).

## NA semantics

The following cell values are treated as equal to `""` for comparison
purposes (case-insensitive, surrounding whitespace stripped):

`""`, `na`, `n/a`, `null`, `none`, `nan`, `-`

This means two rows that differ only in which NA spelling they use are
considered identical.

## Limitations / non-goals

These are deliberately out of scope, per spec:

- **No JSON / XML / Parquet / Excel support.** CSV/TSV only.
- **No streaming / chunked diff.** Operates on in-memory dicts. Files in the
  ~10k row range are fast; files in the millions are not.
- **No three-way diff.** Two files at a time.
- **No patch-file output.** Read-only diff.
- **No HTML / ANSI-coloured output.** Three formats only: JSON, unified
  text, side-by-side table.
- **No pandas adapter.** Zero-runtime-deps invariant forbids it.
- **No cursor / TUI.**
- **Rename detection has a 0.80 left-coverage threshold and is OFF by
  default.** Renames of columns whose values also legitimately appear in
  another column (e.g. `country_code` vs `country_iso2`) may mis-detect.
  See `src/csvcomp/diff.py` for the algorithm.
- **Encoding is UTF-8 only (with BOM stripping).** Other encodings raise
  `ParseError`.
- **Dialect sniffing is unreliable on samples <8 KB.** The spec calls this
  out (KeitaNakamura/diff-csv issue #1). Use `--dialect` explicitly for
  production data.
- **Trailing fully-empty rows are silently dropped.** This is intentional
  (matches `pandas.read_csv`'s default `skip_blank_lines=True`) and is
  documented in the spec.

## Development

```bash
pip install -e ".[test]"
pytest -v
```

The test suite has 126 tests covering every spec acceptance criterion. See
`tests/COVERAGE.md` for the criterion-to-test mapping.

## License

MIT. See `LICENSE`.
