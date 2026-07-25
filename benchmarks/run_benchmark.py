import time, tracemalloc, sys, io, csv, statistics, os
import pandas as pd
sys.path.insert(0, os.path.abspath("../src"))
from csvcomp import diff

def gen(n=1000):
    b = io.StringIO()
    w = csv.writer(b)
    w.writerow(["id", "val"])
    for i in range(n): w.writerow([i, f"v_{i}"])
    return b.getvalue()

a, b = gen(1000), gen(1000).replace("v_500", "v_MOD")
with open("/tmp/a.csv", "w") as f: f.write(a)
with open("/tmp/b.csv", "w") as f: f.write(b)

c_times, p_times = [], []
for _ in range(50):
    t0 = time.perf_counter()
    r = diff("/tmp/a.csv", "/tmp/b.csv")
    c_times.append((time.perf_counter() - t0)*1000)
    
    t0 = time.perf_counter()
    df1, df2 = pd.read_csv("/tmp/a.csv"), pd.read_csv("/tmp/b.csv")
    try: comp = df1.compare(df2)
    except: pass
    p_times.append((time.perf_counter() - t0)*1000)

print(f"csvcomp: {statistics.mean(c_times):.2f} ms | pandas: {statistics.mean(p_times):.2f} ms")
