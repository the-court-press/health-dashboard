#!/usr/bin/env python3
"""Build US-male resting pulse reference data from NHANES 2015-2016 (I) + 2017-2018 (J).
Inputs: raw/BPX_I.xpt raw/BPX_J.xpt raw/DEMO_I.xpt raw/DEMO_J.xpt (CDC public XPT files).
Output: rhr_us_males_nhanes.json. Run from population/: python3 scripts/build_rhr.py
"""
import json, datetime, os
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "raw")
CYCLES = [("2015-2016", "I", 2015), ("2017-2018", "J", 2017)]
URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{y}/DataFiles/{f}.xpt"
DOC = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{y}/DataFiles/{f}.htm"
BANDS = [("18-24", 18, 24), ("25-34", 25, 34), ("35-44", 35, 44), ("45-54", 45, 54),
         ("55-64", 55, 64), ("65-74", 65, 74), ("75+", 75, 200), ("All 18+", 18, 200)]
PCTS = [5, 10, 25, 50, 75, 90, 95]
GRID = np.arange(40, 111, 1.0)

frames = []
for label, s, y in CYCLES:
    demo = pd.read_sas(os.path.join(RAW, f"DEMO_{s}.xpt"))[["SEQN", "RIAGENDR", "RIDAGEYR", "WTMEC2YR", "SDMVPSU", "SDMVSTRA"]]
    bpx = pd.read_sas(os.path.join(RAW, f"BPX_{s}.xpt"))[["SEQN", "BPXPLS", "BPXPULS"]]
    d = demo.merge(bpx, on="SEQN", how="left")
    d["cycle"] = label
    frames.append(d)
df = pd.concat(frames, ignore_index=True)
df["W"] = df["WTMEC2YR"] / 2.0  # 4-year combined MEC weight
design = df[df["W"] > 0].copy()  # full examined sample defines the design (domain estimation)
design["male_adult"] = (design["RIAGENDR"] == 1) & (design["RIDAGEYR"] >= 18)
design["has_pulse"] = design["BPXPLS"].notna()

def wmean(y, w): return float(np.sum(w * y) / np.sum(w))

def wsd(y, w):
    m = wmean(y, w); return float(np.sqrt(np.sum(w * (y - m) ** 2) / np.sum(w)))

def interp_cdf(y, w):
    """Weighted CDF treating each reported (even, 2-bpm-step) value v as spread uniformly
    over [v-1, v+1). Returns knots (x, F) for a continuous piecewise-linear CDF."""
    vals = np.unique(y)
    mass = np.array([w[y == v].sum() for v in vals]) / w.sum()
    xs, Fs, F = [], [], 0.0
    for v, m in zip(vals, mass):
        xs += [v - 1, v + 1]; Fs += [F, F + m]; F += m
    xs, Fs = np.array(xs), np.array(Fs)
    # collapse duplicate x knots (adjacent bins share edges)
    out_x, out_F = [], []
    for x, f in zip(xs, Fs):
        if out_x and x == out_x[-1]: out_F[-1] = max(out_F[-1], f)
        else: out_x.append(x); out_F.append(f)
    return np.array(out_x), np.array(out_F)

def cdf_at(x, kx, kF): return np.interp(x, kx, kF, left=0.0, right=1.0)

def quantile(p, kx, kF):
    # inverse of the piecewise-linear CDF (first x where F reaches p)
    i = np.searchsorted(kF, p, side="left")
    i = min(max(i, 1), len(kF) - 1)
    x0, x1, f0, f1 = kx[i-1], kx[i], kF[i-1], kF[i]
    return float(x0 if f1 == f0 else x0 + (p - f0) * (x1 - x0) / (f1 - f0))

def taylor_se_mean(sub_mask, y_all):
    """Taylor-linearized SE of a domain (weighted ratio) mean; strata x PSU with-replacement."""
    d = design
    dom = sub_mask.values & d["has_pulse"].values
    w = d["W"].values; y = np.where(dom, y_all, 0.0)
    W = np.sum(w * dom); ybar = np.sum(w * dom * y) / W
    z = w * dom * (y - ybar) / W
    t = pd.DataFrame({"h": d["SDMVSTRA"].values, "psu": d["SDMVPSU"].values, "z": z})
    psu_tot = t.groupby(["h", "psu"])["z"].sum().reset_index()
    var = 0.0
    for h, g in psu_tot.groupby("h"):
        n = len(g)
        if n > 1: var += n / (n - 1) * np.sum((g["z"] - g["z"].mean()) ** 2)
    nstrata = psu_tot["h"].nunique(); npsu = len(psu_tot)
    return float(np.sqrt(var)), npsu - nstrata

def wkde(y, w, grid):
    w = w / w.sum()
    m = np.sum(w * y); sd = np.sqrt(np.sum(w * (y - m) ** 2))
    kx, kF = interp_cdf(y, w)
    iqr = quantile(0.75, kx, kF) - quantile(0.25, kx, kF)
    neff = 1.0 / np.sum(w ** 2)
    h = 0.9 * min(sd, iqr / 1.34) * neff ** (-0.2)
    dens = np.array([np.sum(w * np.exp(-0.5 * ((g - y) / h) ** 2)) / (h * np.sqrt(2 * np.pi)) for g in grid])
    # mass of KDE inside [40,110] (analytic, via normal CDF)
    from scipy.stats import norm
    inmass = float(np.sum(w * (norm.cdf((110 - y) / h) - norm.cdf((40 - y) / h))))
    return dens, float(h), float(neff), inmass

def ordinal(n):
    n = int(round(n)); suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"

fmt = lambda v: f"{v:.0f}"
y_all = design["BPXPLS"].fillna(0).values
bands, summ = [], {}
for name, lo, hi in BANDS:
    mask = design["male_adult"] & (design["RIDAGEYR"] >= lo) & (design["RIDAGEYR"] <= hi)
    sub = design[mask & design["has_pulse"]]
    y = sub["BPXPLS"].values.astype(float); w = sub["W"].values
    kx, kF = interp_cdf(y, w)
    pct = {f"p{p}": round(quantile(p / 100, kx, kF), 1) for p in PCTS}
    dens, h, neff, inmass = wkde(y, w, GRID)
    se, df_ = taylor_se_mean(mask, y_all)
    look = {str(int(b)): round(100 * float(cdf_at(b, kx, kF)), 1) for b in GRID}
    mean, sd = wmean(y, w), wsd(y, w)
    n_missing = int((mask & ~design["has_pulse"]).sum())
    rec = {
        "band": name, "age_min": lo, "age_max": None if hi == 200 else hi,
        "n_unweighted": int(len(y)), "n_examined_no_pulse": n_missing,
        "weighted_population_estimate": int(round(w.sum())),
        "mean": round(mean, 1), "se_mean_taylor": round(se, 2), "se_df": df_,
        "sd": round(sd, 1), "median": pct["p50"], "percentiles": pct,
        "iqr": [pct["p25"], pct["p75"]],
        "share_recorded_below_60_pct": round(100 * float(w[y < 60].sum() / w.sum()), 1),
        "share_recorded_above_100_pct": round(100 * float(w[y > 100].sum() / w.sum()), 1),
        "kde": {"bandwidth_bpm": round(h, 2), "effective_n": round(neff, 1),
                "mass_within_40_110": round(inmass, 4),
                "grid_integral_trapezoid": round(float(np.trapezoid(dens, GRID)), 4)},
        "density": [{"bpm": int(g), "density": round(float(d), 6)} for g, d in zip(GRID, dens)],
        "percentile_lookup": look,
    }
    summ[name] = rec; bands.append(rec)

# facts strictly from computed numbers
age_bands = [b for b in bands if b["band"] != "All 18+"]
allb = summ["All 18+"]
for b in bands:
    lbl = "men 18+" if b["band"] == "All 18+" else f"men {b['band'].replace('-', '–')}"
    p = b["percentiles"]; L = b["percentile_lookup"]
    facts = [
        f"Half of US {lbl} have a measured resting pulse between {fmt(p['p25'])} and {fmt(p['p75'])} bpm (middle 50%).",
        f"The median measured resting pulse for {lbl} is about {fmt(b['median'])} bpm; the weighted mean is {b['mean']:.1f} bpm (SD {b['sd']:.1f}).",
        f"90% of {lbl} fall between about {fmt(p['p5'])} and {fmt(p['p95'])} bpm.",
        f"A pulse of 60 bpm sits at about the {ordinal(L['60'])} percentile for {lbl}; 70 bpm at about the {ordinal(L['70'])}.",
        f"About {b['share_recorded_below_60_pct']:.0f}% of {lbl} had a recorded pulse below 60 bpm, and about {b['share_recorded_above_100_pct']:.0f}% above 100 bpm.",
    ]
    if b["band"] != "All 18+":
        diff = b["median"] - allb["median"]
        rel = "the same as" if abs(diff) < 0.5 else (f"{abs(diff):.0f} bpm {'higher' if diff > 0 else 'lower'} than")
        facts.append(f"The median for {lbl} is {rel} the median for all men 18+ ({fmt(allb['median'])} bpm).")
    b["facts"] = facts

meds = [(b["band"], b["median"]) for b in age_bands]
hi_b = max(meds, key=lambda t: t[1]); lo_b = min(meds, key=lambda t: t[1])
global_facts = [
    f"Across age bands, the median measured resting pulse ranges from about {lo_b[1]:.0f} bpm ({lo_b[0].replace('-', '–')}) to about {hi_b[1]:.0f} bpm ({hi_b[0].replace('-', '–')}).",
    "Medians by band: " + ", ".join(f"{n.replace('-', '–')}: {m:.0f}" for n, m in meds) + " bpm.",
]

cites = []
for label, s, y in CYCLES:
    for f in (f"BPX_{s}", f"DEMO_{s}"):
        cites.append({"file": f, "cycle": label, "data_url": URL.format(y=y, f=f), "doc_url": DOC.format(y=y, f=f)})

out = {
    "title": "Resting pulse (60-second) reference distributions, US males 18+, NHANES 2015-2018",
    "generated": datetime.date.today().isoformat(),
    "private_note": "Population reference only; contains no personal data.",
    "source": {
        "survey": "National Health and Nutrition Examination Survey (NHANES), CDC National Center for Health Statistics",
        "cycles": ["2015-2016", "2017-2018"],
        "files": cites,
        "homepage": "https://wwwn.cdc.gov/nchs/nhanes/Default.aspx",
        "suggested_citation": "Centers for Disease Control and Prevention (CDC), National Center for Health Statistics (NCHS). National Health and Nutrition Examination Survey Data, 2015-2016 and 2017-2018. Hyattsville, MD: U.S. Department of Health and Human Services, CDC.",
    },
    "variables": {
        "BPXPLS": "60 sec. pulse (30 sec. pulse * 2), bpm; taken by MEC examiner, seated after 5 min rest. Values are even numbers.",
        "BPXPULS": "Pulse regular/irregular (not used as a filter)",
        "RIAGENDR": "Gender (1 = male)", "RIDAGEYR": "Age in years at screening (top-coded at 80)",
        "WTMEC2YR": "2-year MEC exam weight", "SDMVPSU": "Masked variance PSU", "SDMVSTRA": "Masked variance stratum",
    },
    "method": {
        "population": "Males (RIAGENDR=1), age 18+ at screening, with non-missing BPXPLS; 75+ band includes top-coded age 80.",
        "weighting": "4-year combined weight = WTMEC2YR / 2 (NCHS guidance for combining 2 cycles).",
        "mean_sd": "Survey-weighted mean; weighted population SD (sqrt of weighted variance).",
        "se_mean": "Taylor-series linearization for a domain ratio mean, strata x PSU, with-replacement; full exam sample kept in design; df = #PSU - #strata.",
        "quantiles": "BPXPLS is recorded in 2-bpm steps (30-s count x 2). Each reported value v is treated as spread uniformly over [v-1, v+1); weighted CDF is piecewise-linear; percentiles invert that CDF (so they can be non-integer). percentile_lookup gives this CDF x 100 at each integer bpm 40-110.",
        "density": "Survey-weighted Gaussian KDE on 40-110 bpm, 1-bpm grid. Bandwidth = Silverman's rule of thumb 0.9 * min(weighted SD, weighted IQR/1.34) * n_eff^(-1/5), n_eff = (sum w)^2 / sum(w^2) (Kish). Density units: per bpm.",
    },
    "global_facts": global_facts,
    "bands": bands,
}
with open(os.path.join(HERE, "rhr_us_males_nhanes.json"), "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("n design", len(design))
for b in bands:
    print(f"{b['band']:8} n={b['n_unweighted']:5} miss={b['n_examined_no_pulse']:4} mean={b['mean']:5.1f}±{b['se_mean_taylor']:.2f} sd={b['sd']:4.1f} med={b['median']:5.1f} p5={b['percentiles']['p5']} p95={b['percentiles']['p95']} h={b['kde']['bandwidth_bpm']} mass={b['kde']['mass_within_40_110']} trap={b['kde']['grid_integral_trapezoid']}")
