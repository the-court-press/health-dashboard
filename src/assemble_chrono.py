#!/usr/bin/env python3
"""Inline the font subsets into src/chrono.template.html and write ../chronographs-health.html (data is inlined by build_chronographs.py)."""
import base64, os
SRC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SRC)
b = lambda n: base64.b64encode(open(os.path.join(SRC, "fonts", n), "rb").read()).decode()
t = open(os.path.join(SRC, "chrono.template.html")).read()
t = t.replace("/*CORM*/", b("corm.woff2")).replace("/*CORMI*/", b("corm-i.woff2")).replace("/*INTER*/", b("inter.woff2"))
p = os.path.join(ROOT, "chronographs-health.html")
open(p, "w").write(t); os.chmod(p, 0o600)
