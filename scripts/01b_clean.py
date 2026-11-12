"""01b_clean.py - Data cleaning / QC of the downloaded ERA5 hourly precipitation.

Reads data/tp_YYYY_MM.npy, writes data/clean/tp_YYYY_MM.npy and results/cleaning_report.json.
Checks and fixes:
  * file shape: hours must equal days_in_month*24 and grid must be 49x65 (else file is rejected)
  * NaN / inf values: counted, replaced with 0 (no rain) -- reported per month
  * negative values (ERA5 accumulation round-off, ~-1e-8 m): clipped to 0
  * physical range: hourly precip > 0.2 m (200 mm/h) flagged as suspect (reported, not removed)
  * units: metres/hour -> kept in metres on disk; converted to mm only in the SPI step
  * keeps only the longest run of consecutive months (gaps would corrupt rolling sums)
  * Also reports per-month total (mm), wet-hour fraction (>0.1 mm/h) for a sanity look.
Skips files modified in the last 15 s (download may still be writing them).
"""
import glob, json, os, re, calendar, time
import numpy as np

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC, DST, RES = os.path.join(R, "data"), os.path.join(R, "data", "clean"), os.path.join(R, "results")
os.makedirs(DST, exist_ok=True); os.makedirs(RES, exist_ok=True)
report = {"months": {}, "rejected": []}
for f in sorted(glob.glob(os.path.join(SRC, "tp_*_*.npy"))):
    name = os.path.basename(f)
    if time.time() - os.path.getmtime(f) < 15:
        continue
    y, m = map(int, re.findall(r"tp_(\d+)_(\d+)", name)[0])
    a = np.load(f)
    exp = calendar.monthrange(y, m)[1] * 24
    if a.shape != (exp, 49, 65):
        report["rejected"].append({"file": name, "shape": list(a.shape), "expected_hours": exp}); continue
    nbad = int((~np.isfinite(a)).sum()); nneg = int((a < 0).sum()); nhigh = int((a > 0.2).sum())
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    a = np.clip(a, 0, None).astype(np.float32)
    np.save(os.path.join(DST, name), a)
    report["months"][f"{y}-{m:02d}"] = dict(hours=int(a.shape[0]), nan_or_inf=nbad, negative_clipped=nneg,
                                           suspect_gt_200mm_per_h=nhigh, max_mm_per_h=float(a.max() * 1000),
                                           mean_monthly_total_mm=float(a.sum(0).mean() * 1000),
                                           wet_hour_fraction=float((a > 1e-4).mean()))
# Keep only the longest run of CONSECUTIVE months (a gap would corrupt rolling accumulations / SPI)
ms = sorted(tuple(map(int, k.split("-"))) for k in report["months"])
idx = [y * 12 + m for y, m in ms]
best, cur = [], []
for i, v in enumerate(idx):
    cur = cur + [ms[i]] if cur and v == idx[i - 1] + 1 else [ms[i]]
    if len(cur) > len(best): best = cur
for ym in ms:
    if ym not in best:
        os.remove(os.path.join(DST, f"tp_{ym[0]}_{ym[1]:02d}.npy"))
        report["rejected"].append({"file": f"{ym[0]}-{ym[1]:02d}", "reason": "not part of longest contiguous run"})
        del report["months"][f"{ym[0]}-{ym[1]:02d}"]
report["period"] = f"{best[0][0]}-{best[0][1]:02d} .. {best[-1][0]}-{best[-1][1]:02d}" if best else None
tot = report["months"].values()
report["summary"] = dict(months_ok=len(report["months"]), months_rejected=len(report["rejected"]),
                         total_nan=sum(v["nan_or_inf"] for v in tot), total_negative=sum(v["negative_clipped"] for v in tot),
                         total_suspect=sum(v["suspect_gt_200mm_per_h"] for v in tot))
json.dump(report, open(os.path.join(RES, "cleaning_report.json"), "w"), indent=2)
print(json.dumps(report["summary"], indent=2))
