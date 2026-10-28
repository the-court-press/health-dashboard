Copyright (c) 2026 The Court Press. All rights reserved. Published for viewing only; no licence is granted to reuse or redistribute the code or data. Bundled fonts (Cormorant Garamond, Inter) are licensed separately under the SIL Open Font License 1.1; see src/fonts/OFL.txt. Not medical advice: figures are personal estimates. Not affiliated with or endorsed by WHOOP, The Cooper Institute, Concept2, the American Heart Association or the CDC; their names are used only to identify data sources, and their reference figures belong to them.

# Health dashboard (Arnold Institute of Broscience)

A personal health dashboard built from WHOOP data plus manual logs, published for viewing only.
Two self-contained pages, with fonts and data inlined, that make no network requests:

- [`dashboard.html`](dashboard.html): daily ledger (today, sleep, training, lung levers, VO2max estimate, every metric against its reference band).
- [`chronographs-health.html`](chronographs-health.html): resting pulse against US-male population curves (NHANES 2015–2018).
- [`index.html`](index.html): the cover page linking both.

Times are local wall-clock times. Percentiles, categories and the VO2max figure are estimates, not a measurement or medical advice.

## Sources
- Resting pulse population curves: CDC/NCHS, National Health and Nutrition Examination Survey 2015–2016 and 2017–2018 (see `population/METHOD.md`).
- Blood pressure categories: AHA/ACC 2025 high blood pressure guideline.
- VO2max categories: The Cooper Institute norms, men 40–49 only.
- Rowing references: a few percentile figures from the Concept2 logbook rankings (2025, men 40–49), credited where shown.
- WHOOP: recovery, strain, sleep and member-average figures as published by WHOOP, named for identification only.

## Layout
- `build.py`: WHOOP pull + `manual.json` → `data.json` (Arnold's builder).
- `build_dashboard.py`: inlines a cleaned snapshot of `data.json` into `dashboard.html`, then runs `build_chronographs.py`.
- `src/`: page templates, the assemble scripts and the font subsets (Cormorant Garamond and Inter, SIL OFL).
- `population/`: NHANES resting-pulse reference (`rhr_us_males_nhanes.json`), `METHOD.md` and `scripts/`.
- `dashboard-spec.md`: design spec.

## Rebuild
```
python3 build.py                     # new data.json from the newest WHOOP pulls
                                     # (default dir ../whoop/weekly; override with
                                     #  WHOOP_WEEKLY_DIR=/path/to/weekly, or pass one pull file as an argument)
./run_all.sh                         # src/ templates → dashboard.html + chronographs-health.html (runs build_dashboard.py)
```
WHOOP pulls and API credentials live outside this repo and are never committed (see `.gitignore`).

## Population raw data (not committed)
The four public CDC NHANES files are left out to keep the repo light. To rebuild the reference JSON:
```
mkdir -p population/raw && cd population/raw
for f in 2015/DataFiles/BPX_I 2015/DataFiles/DEMO_I 2017/DataFiles/BPX_J 2017/DataFiles/DEMO_J; do
  curl -fLO "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/$f.xpt"; done
cd .. && python3 scripts/build_rhr.py && python3 scripts/validate.py
```
