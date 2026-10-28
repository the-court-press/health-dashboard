#!/usr/bin/env python3
"""Re-inline the current data.json into dashboard.html (Arnold Institute of Broscience).

Run after each WHOOP pull:   python3 build_dashboard.py
(also re-inlines chronographs-health.html via build_chronographs.py)
- Replaces only the block between <!-- SNAPSHOT:BEGIN ... --> and <!-- SNAPSHOT:END -->.
- Strips any off-limits fields/strings before inlining (see OFF below), so the
  snapshot inside the HTML never carries them; also drops URL strings and the
  legacy keys in DROP_KEYS (e.g. hr_zones_bpm_from_max_180).
- Local only: no network, writes dashboard.html in place (atomic rename).
"""
import json, os, re, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data.json")
HTML = os.path.join(HERE, "dashboard.html")
OFF = re.compile("|".join(["sm" + "ok", "ci" + "gar", "nic" + "otin", "tob" + "acco", "va" + "pe", r"cut.?b" + "ack", r"\bqu" + "it"]), re.I)  # split so the words never appear verbatim

URL = re.compile(r"https?://|www\.", re.I)          # zero external URLs in the page
# legacy / unused blocks never inlined (Zone 2 comes only from hr_zones)
DROP_KEYS = {"hr_zones_bpm_from_max_180", "reference_norms_general_not_his_data"}
# per-metric sections: an entry that touches the off-limits topic is dropped whole
WHOLE = ("reference_bands", "goals")

def bad(v):
    return isinstance(v, str) and (OFF.search(v) or URL.search(v))

def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()
                if k not in DROP_KEYS and not OFF.search(k) and not bad(v)}
    if isinstance(o, list):
        return [clean(v) for v in o if not bad(v)]
    return o

def prune(data):
    for sect in WHOLE:
        block = data.get(sect)
        if isinstance(block, dict):
            data[sect] = {k: v for k, v in block.items()
                          if not k.startswith("_")   # notes for the builders, not for the page
                          and not OFF.search(k) and not OFF.search(json.dumps(v, ensure_ascii=False))}
    return data

def main():
    data = clean(prune(json.load(open(DATA, encoding="utf-8"))))
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/").replace("<!--", "<\\!--")
    html = open(HTML, encoding="utf-8").read()
    pat = re.compile(r"(<!-- SNAPSHOT:BEGIN[^>]*-->\n).*?(\n<!-- SNAPSHOT:END -->)", re.S)
    if not pat.search(html):
        sys.exit("SNAPSHOT markers not found in dashboard.html")
    block = '<script id="snapshot" type="application/json">' + blob + "</script>"
    html = pat.sub(lambda m: m.group(1) + block + m.group(2), html, count=1)
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(html)
    os.chmod(tmp, 0o600)
    os.replace(tmp, HTML)
    gen = data.get("meta", {}).get("generated", "?")
    print(f"inlined data.json (generated {gen}, {len(data.get('days', []))} cycles) -> {HTML}")
    # sibling page: Chronographs: Health (same privacy rules), rebuilt in the same chain
    if os.path.exists(os.path.join(HERE, "chronographs-health.html")):
        sys.path.insert(0, HERE)
        import build_chronographs
        build_chronographs.main()

if __name__ == "__main__":
    main()
