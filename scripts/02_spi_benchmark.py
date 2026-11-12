"""02_spi_benchmark.py - SPI drought index on CPU (NumPy/SciPy) vs GPU (CuPy) + benchmark.

Pipeline per cell (see propuesta.pdf section 3):
  (a) hourly precip -> daily (mm) -> rolling accumulation over k days (prefix-sum / scan)
  (b) gamma fit per cell (closed-form Thom/Greenwood MLE approximation, vectorised over cells)
  (c) z = Phi^-1( q + (1-q) * F_gamma(x) )  (q = P(x=0), mixed distribution); SPI < -1 => drought
  (d) reduction: fraction of Guatemala cells in drought; consecutive dry days (<1 mm)

SIMPLIFICATIONS (be honest in the report):
  * Only a few months of real data fit in the time budget, so the gamma is fitted per cell over ALL
    rolling windows of that scale (not per calendar month as the SPI standard requires).
  * Scales are in days (30 / 90 ~ SPI-1 / SPI-3); 180 d needs more data and is skipped if too short.
  * Thom closed-form fit instead of iterative MLE (same family; avoids a serial iterative loop).
  * No municipality shapefile: the reduction is over the Guatemala bounding box.
Usage: python scripts/02_spi_benchmark.py        (reads data/tp_*.npy, writes results/)
"""
import glob, json, os, time
import numpy as np
from scipy.special import gammainc as sp_gammainc, ndtri as sp_ndtri

import cupy as cp
from cupyx.scipy.special import gammainc as cp_gammainc, ndtri as cp_ndtri

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA, RES = os.path.join(ROOT, "data"), os.path.join(ROOT, "results")
SCALES = [30, 90]
REPS = 5


def _fit_cdf(xp, gammainc, ndtri, acc):
    """acc: (windows, cells) accumulations in mm -> SPI (windows, cells). Works for numpy or cupy."""
    pos = acc > 0
    n = acc.shape[0]
    q = 1.0 - pos.sum(0) / n                                   # P(zero) per cell
    npos = xp.maximum(pos.sum(0), 1)
    safe = xp.where(pos, acc, 1.0)
    mean = (xp.where(pos, acc, 0.0)).sum(0) / npos
    mean_ln = (xp.where(pos, xp.log(safe), 0.0)).sum(0) / npos
    A = xp.maximum(xp.log(xp.maximum(mean, 1e-9)) - mean_ln, 1e-6)
    alpha = (1 + xp.sqrt(1 + 4 * A / 3)) / (4 * A)             # Thom shape
    beta = mean / alpha                                        # scale
    cdf = q + (1 - q) * gammainc(alpha, safe / beta)
    cdf = xp.where(pos, cdf, q / 2 + 1e-6)                     # zeros -> mid of zero mass
    return ndtri(xp.clip(cdf, 1e-6, 1 - 1e-6))


def dry_run(xp, daily):
    """Max consecutive dry days (<1 mm) per cell, vectorised over cells (serial in time)."""
    dry = daily < 1.0
    run = xp.zeros(daily.shape[1], dtype=xp.int32)
    best = xp.zeros_like(run)
    for t in range(daily.shape[0]):
        run = xp.where(dry[t], run + 1, 0)
        best = xp.maximum(best, run)
    return best


def pipeline(xp, gammainc, ndtri, hourly, scales):
    nh, ny, nx = hourly.shape
    nd = nh // 24
    daily = hourly[: nd * 24].reshape(nd, 24, ny * nx).sum(1) * 1000.0   # mm/day
    out = {}
    cs = xp.concatenate([xp.zeros((1, ny * nx), daily.dtype), xp.cumsum(daily, 0)])   # scan
    for k in scales:
        if nd <= k + 10:
            continue
        acc = cs[k:] - cs[:-k]                                           # rolling k-day sums
        out[k] = _fit_cdf(xp, gammainc, ndtri, acc)
    out["dry"] = dry_run(xp, daily)
    return out


def load(months=None):
    files = sorted(glob.glob(os.path.join(DATA, "clean", "tp_*.npy")))
    files = files[:months] if months else files
    return np.concatenate([np.load(f) for f in files])


def timed(fn, reps=REPS):
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); r = fn(); ts.append(time.perf_counter() - t)
    return float(np.median(ts)), r


def main():
    os.makedirs(RES, exist_ok=True)
    nfiles = len(glob.glob(os.path.join(DATA, "clean", "tp_*.npy")))
    lat, lon = np.load(os.path.join(DATA, "lat.npy")), np.load(os.path.join(DATA, "lon.npy"))
    rows = []
    cp.cuda.Device().synchronize()
    pipeline(cp, cp_gammainc, cp_ndtri, cp.asarray(load(1)[:24 * 120]), SCALES)  # GPU warm-up
    cp.cuda.Device().synchronize()

    for nm in sorted({1, 2, 3, 4, 6, nfiles} & set(range(1, nfiles + 1))):
        t_read, h = timed(lambda: load(nm), 3)
        scales = SCALES
        t_cpu, rc = timed(lambda: pipeline(np, sp_gammainc, sp_ndtri, h, scales))

        def gpu_total():
            g = cp.asarray(h); r = pipeline(cp, cp_gammainc, cp_ndtri, g, scales); cp.cuda.Device().synchronize(); return r
        t_gpu_total, _ = timed(gpu_total)
        t_h2d, g = timed(lambda: (cp.asarray(h), cp.cuda.Device().synchronize())[0])

        def gpu_comp():
            r = pipeline(cp, cp_gammainc, cp_ndtri, g, scales); cp.cuda.Device().synchronize(); return r
        t_gpu_comp, rg = timed(gpu_comp)
        ks = [k for k in rc if k != "dry"]
        if not ks:
            continue  # too few days for any SPI scale
        maxdiff = max(float(np.nanmax(np.abs(rc[k] - cp.asnumpy(rg[k])))) for k in ks)
        rows.append(dict(months=nm, hours=int(h.shape[0]), values=int(h.size), MB=h.nbytes / 1e6,
                         t_read=t_read, t_cpu=t_cpu, t_h2d=t_h2d, t_gpu_compute=t_gpu_comp,
                         t_gpu_total=t_gpu_total, speedup_compute=t_cpu / t_gpu_comp,
                         speedup_end2end=t_cpu / (t_gpu_total + 0), max_abs_diff_spi=maxdiff))
        print(rows[-1], flush=True)

    # scaling x10 with SYNTHETIC tiling (timing only, flagged in the report)
    h = load()
    big = np.tile(h, (1, 3, 3))  # 9x more cells (finer/larger region proxy)
    t_cpu, _ = timed(lambda: pipeline(np, sp_gammainc, sp_ndtri, big, SCALES), 3)
    def gpu_big():
        g = cp.asarray(big); r = pipeline(cp, cp_gammainc, cp_ndtri, g, SCALES); cp.cuda.Device().synchronize(); return r
    t_gpu, _ = timed(gpu_big, 3)
    synth = dict(factor_cells=9, values=int(big.size), t_cpu=t_cpu, t_gpu_total=t_gpu, speedup=t_cpu / t_gpu)

    # Results on real data: Guatemala box (13.7-17.8N, 92.2-88.2W)
    r = pipeline(cp, cp_gammainc, cp_ndtri, cp.asarray(h), SCALES)
    ny, nx = len(lat), len(lon)
    gt = (lat[:, None] >= 13.7) & (lat[:, None] <= 17.8) & (lon[None, :] >= -92.2) & (lon[None, :] <= -88.2)
    gt = gt.reshape(-1)
    summary = {"months_real_data": nfiles, "scaling_synthetic_9x": synth}
    for k in SCALES:
        if k in r:
            z = cp.asnumpy(r[k])
            summary[f"spi{k}d_guatemala_frac_cells_below_-1_last_day"] = float((z[-1][gt] < -1).mean())
            summary[f"spi{k}d_guatemala_mean_last_day"] = float(z[-1][gt].mean())
            np.save(os.path.join(RES, f"spi{k}d_last.npy"), z[-1].reshape(ny, nx))
    dry = cp.asnumpy(r["dry"]).reshape(ny, nx)
    np.save(os.path.join(RES, "max_dry_days.npy"), dry)
    summary["max_consecutive_dry_days_guatemala_mean"] = float(dry.reshape(-1)[gt].mean())

    # CPU reference check: scipy gamma.fit MLE vs Thom on 10 Guatemala cells (scale 30d)
    from scipy import stats
    hh = h[: (h.shape[0] // 24) * 24].reshape(-1, 24, ny * nx).sum(1) * 1000
    c = np.concatenate([np.zeros((1, ny * nx)), np.cumsum(hh, 0)]); acc = c[30:] - c[:-30]
    idx = np.where(gt)[0][:: max(1, gt.sum() // 10)][:10]
    d = []
    for i in idx:
        x = acc[:, i]; x = x[x > 0]
        a, _, s = stats.gamma.fit(x, floc=0)
        z_ref = stats.norm.ppf(np.clip(stats.gamma.cdf(acc[-1, i], a, scale=s), 1e-6, 1 - 1e-6))
        d.append(abs(z_ref - float(cp.asnumpy(r[30])[-1, i])))
    summary["spi30_vs_scipy_gamma_fit_mean_abs_diff_10cells"] = float(np.mean(d))

    import csv
    with open(os.path.join(RES, "benchmark.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
    json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
