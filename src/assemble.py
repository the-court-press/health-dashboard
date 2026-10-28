#!/usr/bin/env python3
"""Inline the font subsets into src/template.html and write ../dashboard.html (data is inlined later by build_dashboard.py)."""
import base64, os
SRC = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(SRC)
b = lambda n: base64.b64encode(open(os.path.join(SRC, "fonts", n), "rb").read()).decode()
t = open(os.path.join(SRC, "template.html")).read()
t = t.replace("/*CORM*/", b("corm.woff2")).replace("/*CORMI*/", b("corm-i.woff2")).replace("/*INTER*/", b("inter.woff2"))
t = t.replace("""    if(isNum(nowAvg))s+='<line x1="'+sx(nowAvg)+'" x2="'+R+'" y1="'+y+'" y2="'+y+'" stroke="'+C.ember+'" stroke-opacity=".0"/>';\n""", "")
p = os.path.join(ROOT, "dashboard.html")
open(p, "w").write(t); os.chmod(p, 0o600)
