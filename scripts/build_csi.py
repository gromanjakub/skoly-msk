#!/usr/bin/env python3
"""Parse ČŠI inspection reports downloaded by fetch_csi.py -> data/csi.csv.
One row per inspekční zpráva (newest, plus the previous one when the newest is pre-2022).
Sections copied verbatim (whitespace normalised, page footers dropped), cut to 600 chars.
Quantitative facts are verbatim sentences picked by keyword, plus a few parsed numbers.
"""
import csv, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIM = 600

H_STRONG = r"Silné stránky"
H_WEAK = r"Slabé stránky[^\n]*|Rizika[^\n]*|Oblasti ke zlepšení[^\n]*"
H_REC = r"Doporučení[^\n]*"
H_END = (r"Stanovení lhůty|Seznam dokladů|Poučení|Složení inspekčního týmu|Další zjištění|"
         r"Závěry|Vývoj školy|Hodnocení (podmínek|průběhu|výsledků)|Číselné označení odkazuje|"
         r"Připomínky ředitel|Údaje o zjištěních|Datum vyhotovení|Podpisy")
HEAD = re.compile(r"^\s*(%s|%s|%s|%s)\s*:?\s*$" % (H_STRONG, H_WEAK, H_REC, H_END), re.M)

def pdftext(p, layout=False):
    args = ["pdftotext"] + (["-layout"] if layout else []) + [str(p), "-"]
    return subprocess.run(args, capture_output=True, text=True).stdout

def clean(s):
    s = re.sub(r"^\s*\d+\s*/\s*\d+\s*$", " ", s, flags=re.M)          # page footer "3/7"
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"Česká školní inspekce\s+Inspekční zpráva\s+(?:\S+\s+){0,3}?inspektorát\s+Čj\.?:?\s*\S+", " ", s)
    s = re.sub(r"Číselné označení odkazuje.*?kriteria\.csicr\.cz\.?", "", s).strip()
    return s

def cut(s, n=LIM):
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"

def sections(t):
    """Map heading kind -> text, for the Závěry block (last occurrence of each heading)."""
    out = {}
    ms = list(HEAD.finditer(t))
    for i, m in enumerate(ms):
        h = m.group(1).strip()
        body = t[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(t)]
        if re.match(H_STRONG, h): k = "silne_stranky"
        elif re.match(H_WEAK, h): k = "slabe_stranky"
        elif re.match(H_REC, h): k = "doporuceni"
        else: continue
        b = clean(body)
        if b:
            out[k] = b; out[k + "_nadpis"] = h
    return out

def period(t):
    m = re.search(r"(?:Inspekční činnost na místě|Termín inspekční činnosti|Termín konání inspekce)\s+(.+?)\n\s*\n", t, re.S)
    return clean(m.group(1)) if m else ""

def ztype(flat):
    m = re.search(r"Předmět inspekční činnosti(.{0,700})", flat)
    p = m.group(1) if m else ""
    if re.search(r"stížnost", p, re.I): k = "šetření stížnosti"
    elif re.search(r"tematick", p, re.I): k = "tematická"
    elif re.search(r"podmínek,? průběhu a výsledků", p) or re.search(r"písm\. ?(b\),? (a )?c\)|a\) ?(až|-|–) ?c\))", p): k = "komplexní"
    elif re.search(r"písm\. ?d\)", p): k = "kontrola"
    else: k = "jiná"
    return k, cut(p.strip(), 300)

UNITS = {"jeden": 1, "jedna": 1, "dva": 2, "dvě": 2, "tři": 3, "čtyři": 4, "pět": 5, "šest": 6, "sedm": 7,
         "osm": 8, "devět": 9, "deset": 10, "jedenáct": 11, "dvanáct": 12, "třináct": 13, "čtrnáct": 14,
         "patnáct": 15, "šestnáct": 16, "sedmnáct": 17, "osmnáct": 18, "devatenáct": 19}
TENS = {"dvacet": 20, "třicet": 30, "čtyřicet": 40, "padesát": 50, "šedesát": 60, "sedmdesát": 70,
        "osmdesát": 80, "devadesát": 90}
NUMW = r"(?:%s)(?:\s+(?:%s))?|(?:%s)|\d{1,3}" % ("|".join(TENS), "|".join(UNITS), "|".join(UNITS))

def num(w):
    w = w.strip()
    if w.isdigit(): return int(w)
    parts = w.split()
    return sum(TENS.get(x, UNITS.get(x, 0)) for x in parts)

ABBR = r"(?:tzv|např|tj|mj|resp|aj|apod|atd|vč|č|odst|písm|Mgr|Ing|Bc|PhDr|PaedDr|RNDr|Dr|Sb|tř|roč|max|min|cca)"
KEY = r"žák|učitel|pedagog|kvalifik|tříd|vyučující|asistent|sbor"

def sentences(zone):
    z = re.sub(r"(\d)\.(\s+)(?=[\d(a-zá-ž])", r"\1<D>\2", zone)
    z = re.sub(r"\b(%s)\.(\s)" % ABBR, r"\1<D>\2", z)
    return [x.replace("<D>", ".").strip() for x in re.split(r"(?<=[.!?])\s+(?=[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ„])", z)]

def quant(flat):
    m = re.search(r"Charakteristika(.*?)(Hodnocení průběhu|Hodnocení výsledků|Závěry|$)", flat)
    zone = m.group(1) if m else flat
    keep = []
    for x in sentences(zone):
        if not re.search(KEY, x): continue
        bare = re.sub(r"\d{2}-\d{2}-[A-Z]/\d{2,3}|20\d\d/20?\d\d|\(\d+\.\d+\)|§\s*\d+|č\. ?\d+/\d+|\d{1,2}\. ?\d{1,2}\. ?(?:19|20)\d\d|(?:19|20)\d\d", "", x)
        if re.search(r"\d|\b(%s)\b" % NUMW, bare) and re.search(r"\d|\b(%s)\b\s+(?:\w+\s+){0,3}?(%s)" % (NUMW, KEY), bare):
            keep.append(x)
    joined = " ".join(keep)
    mz = re.search(r"(?:celkem|zapsáno|navštěvoval\w*|vzděláva\w*|vzdělává|studoval\w*|evidoval\w*)\s+(?:\w+\s+){0,6}?(\d{1,2} ?\d{3}|\d{1,4})\s+žák", zone)
    mu = re.search(r"(?:celkem|tvoří|tvořilo|působí|působilo|zajišťuje|zajišťovalo|zajišťují|pracuje|pracovalo|vyučuje|vyučovalo)\s+(?:\w+\s+){0,3}?(%s)\s+(?:\w+\s+){0,2}?(?:učitel\w*|pedagogů|pedagogických pracovník\w*|vyučujících)" % NUMW, zone)
    kv = [x for x in sentences(zone) if re.search(r"kvalifik", x) and re.search(r"pedagog|učitel|vyučující|sbor", x)]
    return {"n_zaku": mz.group(1).replace(" ", "") if mz else "",
            "n_ucitelu": num(mu.group(1)) if mu else "",
            "kvalifikace": cut(" ".join(kv), 400),
            "kvant_fakta": cut(" | ".join(keep), 1200)}

def main():
    idx = list(csv.DictReader(open(ROOT / "data/raw/csi/_index.csv", encoding="utf-8")))
    rows, skipped = [], []
    for r in idx:
        if r["kind"] not in ("zprava", "scan"):
            if r["kind"] != "no_list": skipped.append(r)
            continue
        base = {"red_izo": r["red_izo"], "report_date": r["end"], "report_date_src": "konec inspekce", "inspection_start": r["start"],
                "report_url": r["url"], "pdf": r["file"]}
        if r["kind"] == "scan":
            rows.append({**base, "type": "", "scan": 1}); continue
        p = ROOT / r["file"]
        t = pdftext(p, layout=True)
        flat = clean(t)
        k, pred = ztype(flat)
        cj = re.search(r"Čj\.\s*([^\s]+)", flat)
        dv = None
        for rx in (r"vyhotovení inspekční zprávy(.{0,600})", r"Datum vyhotovení(.{0,600})", r"V Ostravě(.{0,40})"):
            mm = re.search(rx, flat)
            if mm:
                dv = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(20\d\d)", mm.group(1))
                if dv: break
        sec = sections(t)
        rows.append({**base, "report_date": (f"{dv.group(3)}-{int(dv.group(2)):02d}-{int(dv.group(1)):02d}" if dv else r["end"]),
                     "report_date_src": "vyhotovení" if dv else "konec inspekce",
                     "inspection_period": period(t), "cj": cj.group(1) if cj else "",
                     "type": k, "predmet": pred, "scan": 0,
                     "silne_stranky": cut(sec.get("silne_stranky", "")),
                     "slabe_stranky_nadpis": sec.get("slabe_stranky_nadpis", ""),
                     "slabe_stranky": cut(sec.get("slabe_stranky", "")),
                     "doporuceni": cut(sec.get("doporuceni", "")),
                     **quant(flat)})
    cols = ["red_izo", "report_date", "report_date_src", "inspection_start", "inspection_period", "report_url", "pdf", "cj",
            "type", "predmet", "scan", "silne_stranky", "slabe_stranky_nadpis", "slabe_stranky", "doporuceni",
            "n_zaku", "n_ucitelu", "kvalifikace", "kvant_fakta"]
    with open(ROOT / "data/csi.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r.get(c, "") for c in cols})
    print(len(rows), "reports;", sum(int(r["scan"]) for r in rows), "scans;", len(skipped), "non-zpráva skipped")
    for c in ("silne_stranky", "slabe_stranky", "doporuceni", "n_zaku", "n_ucitelu", "kvalifikace"):
        print(c, sum(1 for r in rows if r.get(c)))

if __name__ == "__main__":
    main()
