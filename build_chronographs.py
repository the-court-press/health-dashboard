#!/usr/bin/env python3
"""Re-inline data into chronographs-health.html ("Chronographs: Health").

Called by build_dashboard.py (so Arnold's chain build.py -> build_dashboard.py covers both pages);
can also be run on its own:   python3 build_chronographs.py
- Inlines only what the page needs: my per-cycle resting HR (+ notes), age, RHR goal,
  and the NHANES population reference (population/rhr_us_males_nhanes.json).
- Drops every URL and any off-limits field/string (OFF) before inlining.
- Replaces only the block between <!-- SNAPSHOT:BEGIN ... --> and <!-- SNAPSHOT:END -->.
- Local only: no network. Writes in place (atomic rename), mode 600.
"""
import json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data.json")
POP = os.path.join(HERE, "population", "rhr_us_males_nhanes.json")
HTML = os.path.join(HERE, "chronographs-health.html")
OFF = re.compile("|".join(["sm" + "ok", "ci" + "gar", "nic" + "otin", "tob" + "acco", "va" + "pe", r"cut.?b" + "ack", r"\bqu" + "it"]), re.I)  # split so the words never appear verbatim
URL = re.compile(r"https?://|www\.", re.I)

def bad(v):
    return isinstance(v, str) and (OFF.search(v) or URL.search(v))

def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items() if not OFF.search(k) and not bad(v)}
    if isinstance(o, list):
        return [clean(v) for v in o if not bad(v)]
    return o

DAY_KEYS = ("cycle_start", "rhr", "note", "cycle_hours", "ongoing")
BAND_KEYS = ("band", "age_min", "age_max", "n_unweighted", "mean", "sd", "median", "percentiles", "iqr",
             "share_recorded_below_60_pct", "share_recorded_above_100_pct", "density", "percentile_lookup", "facts")

def goal_rhr(d):
    """RHR goal only when the data carries it (goals.rhr), with its status."""
    g = (d.get("goals") or {}).get("rhr") or {}
    if isinstance(g.get("value"), (int, float)) and g.get("status") in ("confirmed", "proposed"):
        return {"value": g["value"], "status": g["status"]}
    return None

def rhr_fitness(d):
    """Arnold's fitness-category bands for RHR (reference_bands.rhr): bands, current reading, source label."""
    r = (d.get("reference_bands") or {}).get("rhr") or {}
    if not r or OFF.search(json.dumps(r, ensure_ascii=False)):
        return None
    cur = r.get("current") or {}
    return {
        "label": r.get("label"),
        "source": (r.get("source") or {}).get("label"),
        "bands": [{k: b.get(k) for k in ("min", "max", "label", "tone")} for b in r.get("bands", [])],
        "current": {k: cur.get(k) for k in ("value", "window", "category", "recent", "recent_window", "recent_category")},
    }

def main():
    d = json.load(open(DATA, encoding="utf-8"))
    p = json.load(open(POP, encoding="utf-8"))
    prof = d.get("profile", {}) or {}
    me = {
        "generated": (d.get("meta") or {}).get("generated"),
        "age": prof.get("age"),
        "goal_rhr": goal_rhr(d),
        "rhr_fitness": rhr_fitness(d),
        "days": [{k: x.get(k) for k in DAY_KEYS} for x in d.get("days", [])],
    }
    bands = [{k: b.get(k) for k in BAND_KEYS if k in b} for b in p.get("bands", [])]
    pop = {
        "title": p.get("title"),
        "generated": p.get("generated"),
        "cycles": (p.get("source") or {}).get("cycles"),
        "citation": (p.get("source") or {}).get("suggested_citation"),
        "n_total": sum(b.get("n_unweighted") or 0 for b in bands if not re.search(r"all", b.get("band", ""), re.I)),
        "global_facts": p.get("global_facts", []),
        "bands": bands,
    }
    snap = clean({"me": me, "population": pop})
    blob = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = open(HTML, encoding="utf-8").read()
    pat = re.compile(r"(<!-- SNAPSHOT:BEGIN[^>]*-->\n).*?(\n<!-- SNAPSHOT:END -->)", re.S)
    if not pat.search(html):
        sys.exit("SNAPSHOT markers not found in chronographs-health.html")
    block = '<script id="snapshot" type="application/json">' + blob + "</script>"
    html = pat.sub(lambda m: m.group(1) + block + m.group(2), html, count=1)
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(html)
    os.chmod(tmp, 0o600)
    os.replace(tmp, HTML)
    print(f"inlined {len(me['days'])} cycles + {len(bands)} population bands -> {HTML}")

if __name__ == "__main__":
    main()
