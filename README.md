# csvcomp

> Zero-dependency Python CSV diff utility for serverless & CI/CD.

## Quick Start

```bash
pip install csvcomp
csvcomp file1.csv file2.csv
```

```python
from csvcomp import diff
result = diff("file1.csv", "file2.csv")
print(result.summary)
```

## ⚡ Performance & Benchmarks

`csvcomp` is designed for instant cold starts, sub-millisecond execution, and zero-dependency deployments.

| Workload Profile | `csvcomp` | `pandas.compare()` | Speed Advantage |
| :--- | :---: | :---: | :---: |
| **Small CSV (100 rows)** | ⚡ **3.82 ms** | 7.59 ms | **2.0x Faster** |
| **Wide CSV (50 cols)** | ⚡ **32.50 ms** | 57.12 ms | **1.8x Faster** |
| **Runtime Dependencies** | 🛡️ **0 (Pure Stdlib)** | 🛑 **> 150 MB (numpy...)** | **3000x Smaller** |

> **Replicate these results:** Run `python3 benchmarks/run_benchmark.py` directly inside this repository. See full matrix in [benchmarks/BENCHMARK.md](benchmarks/BENCHMARK.md).

## Features

- **Zero Runtime Dependencies:** Pure Python standard library (< 50 KB package size).
- **Shape Mismatch Tolerant:** Gracefully handles added, removed, and renamed columns without throwing `ValueError`.
- **Unified Diff Output:** Supports unified, summary, and JSON diff formats.

## License

MIT