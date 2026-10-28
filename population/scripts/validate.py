#!/usr/bin/env python3
import json, os, numpy as np
d = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rhr_us_males_nhanes.json")))
for b in d["bands"]:
    x = np.array([p["bpm"] for p in b["density"]]); y = np.array([p["density"] for p in b["density"]])
    integ = np.trapezoid(y, x); look = [b["percentile_lookup"][str(i)] for i in range(40, 111)]
    assert len(x) == 71 and 0.98 < integ <= 1.0001, (b["band"], integ)
    assert all(a <= c for a, c in zip(look, look[1:])), b["band"]
    p = list(b["percentiles"].values()); assert p == sorted(p)
    print(f"{b['band']:8} OK  density integral 40-110 = {integ:.4f}  (KDE mass in range {b['kde']['mass_within_40_110']})")
print("JSON valid,", len(d["bands"]), "bands")
