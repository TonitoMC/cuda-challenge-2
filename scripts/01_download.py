"""01_download.py - Download hourly ERA5 total precipitation for Central America.

Source: ARCO-ERA5 (public Google Cloud mirror of Copernicus ERA5, no login needed;
the official CDS API needs a personal key). Same data, CC-BY 4.0, cite Hersbach et al. 2023.
Window: 7N-19N, 93W-77W (49 x 65 cells at 0.25 deg). Output: data/tp_YYYY_MM.npy
float32 array (hours, 49, 65) in metres of water per hour. Resumable (skips existing months).
Usage: python scripts/01_download.py 2024 2023 2022 ...   (years, in priority order)
"""
import sys, os, time, calendar
import numpy as np, xarray as xr
import multiprocessing as mp

URL = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"
OUT = os.path.join(os.path.dirname(__file__), "..", "data")
_sub = None

def _open():
    ds = xr.open_zarr(URL, storage_options={"token": "anon"}, consolidated=None)
    return ds, ds["total_precipitation"].sel(latitude=slice(19, 7), longitude=slice(267, 283))

def _init():
    global _sub
    _, _sub = _open()

def _day(i):
    return _sub.isel(time=slice(i, i + 24)).values.astype(np.float32)

if __name__ == "__main__":
    ds, sub = _open()
    np.save(os.path.join(OUT, "lat.npy"), sub.latitude.values)
    np.save(os.path.join(OUT, "lon.npy"), sub.longitude.values - 360)
    times = ds.time.values
    with mp.get_context("spawn").Pool(12, initializer=_init) as pool:
        for y in map(int, sys.argv[1:]):
            for m in range(1, 13):
                f = os.path.join(OUT, f"tp_{y}_{m:02d}.npy")
                if os.path.exists(f): continue
                t0 = time.time()
                i0 = int(np.searchsorted(times, np.datetime64(f"{y}-{m:02d}-01")))
                nd = calendar.monthrange(y, m)[1]
                arr = np.concatenate(pool.map(_day, [i0 + 24 * d for d in range(nd)]))
                np.save(f, arr)
                print(f"{y}-{m:02d} {arr.shape} {time.time()-t0:.0f}s", flush=True)
