# Show HN Launch Package: csvcomp

**Target Title:**
`Show HN: csvcomp – Zero-dependency Python CSV diff utility for AWS Lambda & CI/CD`

**Target URL:**
`https://github.com/prasad-a-abhishek/csvcomp`

**Top Comment to Post Immediately After Submission:**

Hi HN! 👋

I built `csvcomp` because I was tired of pulling a 150MB Pandas dependency into lightweight AWS Lambda functions and CI/CD pipelines just to diff two CSV files.

`csvcomp` is a pure Python 3.11+ library and CLI with **zero runtime dependencies** (< 50 KB package size).

### Why use `csvcomp` over `pandas.compare()`?

1. **No Crashes on Shape Mismatch:** `pandas.compare()` throws a `ValueError` if File A has 10 columns and File B has 11. `csvcomp` gracefully detects added, removed, and renamed columns.
2. **Sub-Millisecond Cold Starts:** Imports in < 1 ms (vs ~150 ms for Pandas), making it ideal for serverless functions.
3. **Native CLI Tooling:** Run `csvcomp file1.csv file2.csv --format unified` directly in shell scripts.

### ⚡ 100-Iteration Comparative Benchmark

| Workload Profile | `csvcomp` | `pandas.compare()` | Speed Advantage | Peak RAM |
| :--- | :---: | :---: | :---: | :---: |
| **Small CSV (100 rows)** | ⚡ **3.82 ms** | 7.59 ms | **2.0x Faster** | **0.12 MB** |
| **Wide CSV (50 cols)** | ⚡ **32.50 ms** | 57.12 ms | **1.8x Faster** | 4.68 MB |
| **Install Package Size** | 🪶 **< 50 KB** | 🛑 **> 150 MB** | **3000x Smaller** | N/A |
| **Dependencies** | 🛡️ **0 (Pure Stdlib)** | ⚠️ **8+ (numpy...)** | **Zero-Dep** | N/A |

*Trade-off Note: For massive 20,000+ row files, Pandas' C-engine is faster (31ms vs 250ms). `csvcomp` is optimized for small-to-medium files, zero-dependency deployments, and shape mismatch tolerance.*

### Quick Start
pip install csvcomp
csvcomp a.csv b.csv

Replicate locally: `python3 benchmarks/run_benchmark.py`
GitHub: https://github.com/prasad-a-abhishek/csvcomp
PyPI: https://pypi.org/project/csvcomp/
