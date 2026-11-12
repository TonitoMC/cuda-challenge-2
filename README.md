# SPI drought index, CPU vs GPU (CC3069, Caso 4 – Corredor Seco)

Authors: Javier España (23361), Angel Esquit (23221), José Mérida (201105).
All numbers live in `results/`; this README has no hard-coded results. `data/` is not included (re-download with step 1).

## Deliverables
| File | What |
|---|---|
| `informe_final.pdf` (root) / `docs/informe_final.tex` | Final report (≤ 6 pages) |
| `diapositivas.pdf` (root) / `docs/diapositivas.html` | 5-minute slides (7 + sources). Open the `.html` in a browser and press F11 to present |
| `docs/guion_5min.md` | Who says what, with timings (3 speakers) |
| `results/` | `benchmark.csv`, `summary.json`, `amdahl.json`, `cleaning_report.json`, logs, figures |

## How to reproduce (NVIDIA GPU + CUDA 12, Linux)
```bash
python -m venv venv && venv/bin/pip install numpy scipy xarray "zarr>=3" gcsfs cupy-cuda12x matplotlib pandas netCDF4
venv/bin/python -I scripts/01_download.py 2023 2024     # ERA5 hourly precip (public ARCO-ERA5 mirror, no login); ~1 min/month; resumable
venv/bin/python -I scripts/01b_clean.py                 # QC: shape, NaN, negatives, range, keeps longest contiguous run of months
venv/bin/python -I scripts/02_spi_benchmark.py          # SPI on CPU (NumPy/SciPy) and GPU (CuPy) + timing + validation
venv/bin/python -I scripts/03_plots.py                  # figures
venv/bin/python -I scripts/04_amdahl.py                 # per-stage timing, Amdahl analysis, workflow speedup
```

## Data
ERA5 hourly single levels, `total_precipitation`, 0.25°, window 7–19N / 93–77W (49×65 cells). Hersbach et al. (2023), doi:10.24381/cds.adbb2d47, CC-BY 4.0.
Fetched from Google's ARCO-ERA5 copy (`gs://gcp-public-data-arco-era5`) because the official CDS API needs a personal key. Hardware: NVIDIA RTX 4070 SUPER, CUDA 12.9.

## Method / simplifications (state these in the report)
Hourly → daily mm → rolling 30/90-day sums (prefix sum) → per-cell gamma fit (closed-form Thom approximation, mixed with P(0)) → z = Φ⁻¹(F(x)) → reductions.
Gamma is fitted over all rolling windows per cell, **not per calendar month**; no municipality aggregation (Guatemala bounding box); disk-read timings are warm-cache;
the 10× scaling test tiles the grid (timing only). The loaded months are short, so SPI values are not drought findings.
