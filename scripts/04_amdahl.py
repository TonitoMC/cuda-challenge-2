"""04_amdahl.py - Bottleneck + Amdahl's law analysis from measured numbers.

Uses results/benchmark.csv (last row = all months)
and a per-stage timing of the pipeline on CPU and GPU. Writes results/amdahl.json.
 * parallel fraction f = share of CPU compute time in stages that parallelise across cells
   (daily sum, scan, gamma fit, CDF/z-score); the dry-day run-length loop is sequential in time.
 * Amdahl on compute only:   S = 1 / ((1-f) + f/Sp)
 * Whole workflow (disk read + [host->GPU copy] + compute) speedup = T_cpu_total / T_gpu_total. The disk read is not
   accelerated by the GPU and the copy is an extra cost only the GPU pays, so this is the real Amdahl limit.
"""
import importlib.util, json, os, time
import numpy as np, pandas as pd, cupy as cp

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
spec = importlib.util.spec_from_file_location("spi", os.path.join(R, "scripts", "02_spi_benchmark.py"))
spi = importlib.util.module_from_spec(spec); spec.loader.exec_module(spi)

def med(fn, n=5):
    ts = []
    for _ in range(n):
        t = time.perf_counter(); fn(); ts.append(time.perf_counter() - t)
    return float(np.median(ts))

h = spi.load(); nh, ny, nx = h.shape; nd = nh // 24
def stages(xp, gammainc, ndtri, x):
    sync = (lambda: cp.cuda.Device().synchronize()) if xp is cp else (lambda: None)
    t = {}
    f = lambda: (x[: nd * 24].reshape(nd, 24, ny * nx).sum(1) * 1000.0, sync())[0]
    t["daily_sum"] = med(f); daily = f()
    g = lambda: (xp.concatenate([xp.zeros((1, ny * nx), daily.dtype), xp.cumsum(daily, 0)]), sync())[0]
    t["scan"] = med(g); cs = g()
    acc = cs[30:] - cs[:-30]
    t["gamma_fit_cdf_z"] = med(lambda: (spi._fit_cdf(xp, gammainc, ndtri, acc), sync()))
    t["dry_days_loop(sequential in time)"] = med(lambda: (spi.dry_run(xp, daily), sync()), 3)
    return t
cpu = stages(np, spi.sp_gammainc, spi.sp_ndtri, h)
gx = cp.asarray(h); stages(cp, spi.cp_gammainc, spi.cp_ndtri, gx)  # warm-up
gpu = stages(cp, spi.cp_gammainc, spi.cp_ndtri, gx)
tot = sum(cpu.values()); par = tot - cpu["dry_days_loop(sequential in time)"]
f = par / tot
b = pd.read_csv(os.path.join(R, "results", "benchmark.csv")).iloc[-1]
Sp = sum(cpu.values()) / sum(gpu.values())
wf_cpu = b.t_read + b.t_cpu                       # disk read + compute
wf_gpu = b.t_read + b.t_h2d + b.t_gpu_compute     # disk read + host->GPU copy + compute
out = dict(months=int(b.months), stage_times_cpu_s=cpu, stage_times_gpu_s=gpu, parallel_fraction_f=f,
           measured_compute_speedup=Sp, amdahl_limit_infinite_gpu=1 / (1 - f),
           amdahl_prediction_for_measured_Sp=1 / ((1 - f) + f / Sp),
           workflow_cpu_s=wf_cpu, workflow_gpu_s=wf_gpu, workflow_speedup=wf_cpu / wf_gpu,
           data_movement_share_of_gpu_workflow=(b.t_read + b.t_h2d) / wf_gpu,
           workflow_speedup_limit_if_compute_free=wf_cpu / (b.t_read + b.t_h2d))
json.dump(out, open(os.path.join(R, "results", "amdahl.json"), "w"), indent=2); print(json.dumps(out, indent=2))
