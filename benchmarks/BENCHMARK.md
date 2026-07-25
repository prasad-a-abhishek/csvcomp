# csvcomp 100-Iteration Comparative Benchmark

Head-to-head performance, memory, and dependency benchmark comparing `csvcomp` v0.1.0 against `pandas.compare()`.

## ⚔️ Benchmark Results (10 Workload Profiles x 5 Runs Each)

| Workload Profile | Sample Size | `csvcomp` Mean Time | `pandas` Mean Time | `csvcomp` Peak RAM | `pandas` Peak RAM | Winner |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Small CSV** *(100 rows)* | 10 runs | ⚡ **3.83 ms** | 7.72 ms | **0.12 MB** | 0.29 MB | **`csvcomp` ⚡ (2x Faster)** |
| **Wide CSV** *(50 columns)* | 10 runs | ⚡ **33.01 ms** | 56.43 ms | 4.68 MB | **3.83 MB** | **`csvcomp` ⚡ (1.7x Faster)** |
| **CRLF Line Endings** | 10 runs | 15.71 ms | **8.39 ms** | 1.13 MB | 0.41 MB | `pandas` |
| **UTF-8 BOM Header** | 10 runs | 15.77 ms | **8.38 ms** | 1.13 MB | 0.44 MB | `pandas` |
| **Numeric Coercion** | 10 runs | 15.78 ms | **8.32 ms** | 1.14 MB | 0.41 MB | `pandas` |
| **Date Coercion** | 10 runs | 18.27 ms | **8.21 ms** | 1.37 MB | 0.41 MB | `pandas` |
| **Key Row Reorder** | 10 runs | 21.87 ms | **10.90 ms** | 1.94 MB | 0.51 MB | `pandas` |
| **Sparse NA CSV** | 10 runs | 20.76 ms | **19.50 ms** | 1.91 MB | 1.03 MB | `pandas` |
| **Medium CSV** *(2k rows)* | 10 runs | 37.98 ms | **12.24 ms** | 3.89 MB | 0.93 MB | `pandas` |
| **Large CSV** *(20k rows)* | 10 runs | 252.87 ms | **31.53 ms** | 19.42 MB | 5.64 MB | `pandas` |

## 📊 Dependency & Deployment Comparison

| Dimension | `csvcomp` | `pandas` |
| :--- | :---: | :---: |
| **Runtime Dependencies** | 🛡️ **0 (Pure Standard Library)** | ⚠️ **8+ (`numpy`, `pytz`...)** |
| **Install Size** | 🪶 **< 50 KB** | 🛑 **> 150 MB** |
| **Import Time** | ⚡ **< 1 ms** | 🐢 **~150 ms** |
| **CLI Tooling** | 💡 **Included (`csvcomp a.csv b.csv`)** | ❌ **None** |
| **Shape Mismatch** | 💡 **Graceful diff** | 🛑 **`ValueError` crash** |
