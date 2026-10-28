# Resting pulse reference — US males, NHANES 2015–2018

Reference data for the health dashboard, published for viewing only. Population data only; no personal data.

## Source
- **Survey:** CDC/NCHS National Health and Nutrition Examination Survey (NHANES), cycles **2015–2016 (I)** and **2017–2018 (J)** combined.
- **Files** (public XPT, downloaded to `raw/`):
  - BPX_I: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/BPX_I.xpt (docs: same path, `.htm`)
  - DEMO_I: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2015/DataFiles/DEMO_I.xpt
  - BPX_J: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/BPX_J.xpt
  - DEMO_J: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/DEMO_J.xpt
- **Variables:** `BPXPLS` (60-sec pulse = 30-sec count × 2), `RIAGENDR` (1 = male), `RIDAGEYR` (age, top-coded at 80), `WTMEC2YR`, `SDMVPSU`, `SDMVSTRA`.
- Not used: 2017–Mar 2020 pre-pandemic `P_BPXO` (oscillometric `BPXOPLS1–3`; a different method).
- Citation: CDC, NCHS. *National Health and Nutrition Examination Survey Data, 2015–2016 and 2017–2018.* Hyattsville, MD: U.S. DHHS, CDC. https://wwwn.cdc.gov/nchs/nhanes/

## Method
- Sample: males aged 18+ with non-missing `BPXPLS` (n = 5,254). Bands 18–24, 25–34, 35–44, 45–54, 55–64, 65–74, 75+ (75+ includes top-coded 80), plus all 18+.
- Weights: 4-year weight = `WTMEC2YR / 2`.
- Mean and SD are survey-weighted. The SE of the mean uses Taylor linearization (domain ratio mean, strata × PSU, with replacement, full exam sample kept in the design).
- Percentiles: pulse is recorded in 2-bpm steps, so each value v is spread uniformly over [v−1, v+1). This gives a continuous weighted CDF, and percentiles are read off it, so they can be non-integer. `percentile_lookup` holds that CDF × 100 at each bpm from 40 to 110. Because of the spreading, the lookup at 60 counts half of the men recorded at exactly 60, so it is a little higher than `share_recorded_below_60_pct`.
- Density: survey-weighted Gaussian KDE on a 1-bpm grid from 40 to 110. Bandwidth uses Silverman's rule, h = 0.9 · min(weighted SD, weighted IQR/1.34) · n_eff^(−1/5), with Kish n_eff = (Σw)²/Σw². h is about 2.9–3.4 bpm per band (2.3 for all 18+). Between 98.8% and 99.7% of the mass falls inside 40–110; the rest is tail.
- Facts are generated in code from the computed numbers only.
- Rebuild: `python3 scripts/build_rhr.py && python3 scripts/validate.py`

## Caveats
- This is **examiner-measured pulse** at the MEC, taken seated after about 5 minutes of rest from a 30-second count. It is not the "resting heart rate" a wearable reports, which usually comes from sleep or all-day minimums and **tends to run lower**. Compare a wearable value with care.
- The data are cross-sectional. The band-to-band differences are between different people, not changes over a lifetime.
- Pulse regularity (`BPXPULS`) and medications such as beta-blockers were not filtered. The data describe the whole population, not a "healthy" reference.
- The 75+ band includes everyone top-coded at 80. Bands of about 560–960 men each give SEs of the mean of about 0.5–0.8 bpm.
- Pulse was missing for 473 examined adult men, who were excluded. No imputation or weight adjustment was done.
