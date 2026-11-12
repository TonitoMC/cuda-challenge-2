"""03_plots.py - Figures from results/ : SPI-30d map, max dry days map, CPU vs GPU timing bars."""
import os, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D, O = os.path.join(R, "data"), os.path.join(R, "results")
lat, lon = np.load(f"{D}/lat.npy"), np.load(f"{D}/lon.npy")
ext = [lon.min(), lon.max(), lat.min(), lat.max()]
for name, f, cmap, lab, kw in [("spi30d_map", "spi30d_last.npy", "RdBu", "SPI (30 d) last day", dict(vmin=-3, vmax=3)),
                               ("dry_days_map", "max_dry_days.npy", "YlOrBr", "Max consecutive dry days (<1 mm)", {})]:
    fp = f"{O}/{f}"
    if not os.path.exists(fp): continue
    plt.figure(figsize=(6, 5)); plt.imshow(np.load(fp), extent=ext, cmap=cmap, **kw); plt.colorbar(label=lab)
    plt.title(lab); plt.xlabel("lon"); plt.ylabel("lat"); plt.tight_layout(); plt.savefig(f"{O}/{name}.png", dpi=130); plt.close()
b = pd.read_csv(f"{O}/benchmark.csv"); x = np.arange(len(b)); w = 0.25
plt.figure(figsize=(7, 4))
plt.bar(x - w, b.t_cpu * 1e3, w, label="CPU compute"); plt.bar(x, b.t_gpu_compute * 1e3, w, label="GPU compute")
plt.bar(x + w, b.t_h2d * 1e3, w, label="host->GPU transfer"); plt.plot(x, b.t_read * 1e3, "k--o", label="disk read (npy)")
plt.xticks(x, [f"{m} mo\n{mb:.0f} MB" for m, mb in zip(b.months, b.MB)]); plt.ylabel("ms (median)")
plt.legend(); plt.title("SPI pipeline timing"); plt.tight_layout(); plt.savefig(f"{O}/timing.png", dpi=130)
