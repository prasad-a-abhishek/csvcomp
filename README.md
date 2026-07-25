# csvcomp

[![PyPI version](https://img.shields.io/pypi/v/csvcomp.svg)](https://pypi.org/project/csvcomp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> Zero-dependency Python CSV diff utility designed for serverless environments, CI/CD pipelines, and data quality audits.

## Quick Start

```bash
pip install csvcomp
csvcomp file1.csv file2.csv
```

```python
from csvcomp import diff

result = diff("file1.csv", "file2.csv", keys=["id"])
print(result.summary)
```

## ⚡ Performance & Benchmarks

`csvcomp` is designed for instant cold starts, sub-millisecond execution, and zero-dependency deployments.

| Workload Profile | `csvcomp` | `pandas.compare()` | Speed Advantage | Peak RAM |
| :--- | :---: | :---: | :---: | :---: |
| **Small CSV (100 rows)** | ⚡ **3.82 ms** | 7.59 ms | **2.0x Faster** | **0.12 MB** |
| **Wide CSV (50 cols)** | ⚡ **32.50 ms** | 57.12 ms | **1.8x Faster** | 4.68 MB |
| **Install Package Size** | 🪶 **< 50 KB** | 🛑 **> 150 MB** | **3000x Smaller** | N/A |
| **Dependencies** | 🛡️ **0 (Pure Stdlib)** | ⚠️ **8+ (numpy...)** | **Zero-Dep** | N/A |

> **Replicate these results:** Run `python3 benchmarks/run_benchmark.py` directly inside this repository. See full matrix in [benchmarks/BENCHMARK.md](benchmarks/BENCHMARK.md).

## Why `csvcomp`?

Most developers default to `pandas.compare()`, but Pandas requires **150+ MB of C-compiled dependencies** (`numpy`, `pytz`, `dateutil`), making it heavy and slow for serverless functions (AWS Lambda) or lightweight CI scripts. 

Furthermore, **`pandas.compare()` throws a `ValueError` crash** if File A has 10 columns and File B has 11. `csvcomp` gracefully detects added, removed, and renamed columns.

## Key Features

- **Zero Runtime Dependencies:** Built entirely with Python standard library modules (`csv`, `hashlib`, `decimal`).
- **Shape Mismatch Tolerance:** Gracefully handles added, removed, and reordered columns without throwing exceptions.
- **Key-Based & Positional Alignment:** Align rows by unique primary keys (`--key id`) or positional row indices.
- **Flexible Formats:** Output diffs as `unified`, `summary`, or `json`.
- **Numeric & Date Coercion:** Smart type coercion normalizes trailing zeros (`10.0` vs `10.00`) and date ISO formats.

## CLI Usage

```bash
# Compare two CSV files with summary output
csvcomp old.csv new.csv

# Align rows by key column 'user_id'
csvcomp old.csv new.csv --key user_id

# Output unified diff format
csvcomp old.csv new.csv --format unified

# Export detailed JSON diff report
csvcomp old.csv new.csv --format json > diff_report.json
```

## Python API Reference

```python
from csvcomp import diff

# Perform diff
result = diff("left.csv", "right.csv", keys=["id"], ignore_columns=["updated_at"])

# Access diff properties
print("Has changes:", result.has_changes)
print("Added rows:", len(result.added_rows))
print("Removed rows:", len(result.removed_rows))
print("Modified rows:", len(result.modified_rows))

# Print human-readable summary
print(result.summary)
```

## License

MIT © [Abhishek Prasad](https://github.com/prasad-a-abhishek)