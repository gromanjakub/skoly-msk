"""Ekonomická olympiáda, ročník VI (2021/22): finalists table with kraj. Appends MSK rows to data/olymp_msk.csv.
Ročník I = 2016/17 (ekonomickaolympiada.cz/minule-rocniky lists VIII = 2023/24). Older ročníky (I-V) are
outside the scoring window; their pages are saved in data/raw/olymp/eko/old_*.html."""
import csv, html, os, re
ROOT = os.path.join(os.path.dirname(__file__), "../..")
D = os.path.join(ROOT, "data/raw/olymp/eko")
cells = lambda tr: [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()
                    for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
s = open(os.path.join(D, "old_vi-rocnik.html"), encoding="utf8").read()
rows = []
for tr in re.findall(r"<tr.*?</tr>", s, re.S):
    c = cells(tr)
    if len(c) >= 4 and re.match(r"^\d+\.", c[0]) and "Moravskoslez" in c[3]:
        name = c[1].split()
        ini = ".".join(w[0] for w in name) + "." if name else ""
        town = next((t for t in ("Ostrava", "Opava", "Frýdek-Místek", "Karviná", "Havířov", "Nový Jičín", "Bílovec",
                                 "Třinec", "Orlová", "Krnov", "Bruntál", "Kopřivnice", "Příbor", "Hlučín", "Frenštát")
                     if t.lower() in c[2].lower()), "")
        r = int(re.match(r"\d+", c[0]).group())
        rows.append(dict(competition="Ekonomická olympiáda", year="2021/22", round="ustredni", category="SŠ", student=ini,
                         school_raw=c[2], town=town, placement=c[0], successful=str(r <= 3).lower(), team="individual"))
p = os.path.join(ROOT, "data/olymp_msk.csv")
old = [r for r in csv.DictReader(open(p)) if not (r["competition"] == "Ekonomická olympiáda" and r["year"] == "2021/22")]
cols = list(old[0].keys())
with open(p, "w", newline="") as fh:
    w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(old + rows)
print(len(rows), "MSK finalists 2021/22:", [(r["placement"], r["school_raw"][:50]) for r in rows])
