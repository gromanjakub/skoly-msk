#!/usr/bin/env python3
"""Per-school tables from Moravskoslezský kraj documents -> data/kraj_*.csv

Sources (all downloaded into data/raw/kraj/, public materials of zastupitelstvo kraje,
https://www.msk.cz/kraj/zastupitelstvo/materialy.html?datum=YYYY-MM-DD, file
https://www.msk.cz/kraj/zastupitelstvo/soubory.html?id=N):

  zaverecny_ucet_{Y}_tabulky.xlsx  Závěrečný účet MSK za rok Y, "grafická a tabulková část"
      Y=2022 id=20376, 2023 id=22561, 2024 id=24205, 2025 id=26071
      * "Přehled poskytnutých finančních prostředků příspěvkovým organizacím kraje"
        (recipient by NAME, purpose, schváleno/čerpáno, tis. Kč) -> kraj_prispevky_po.csv
      * "Vypořádání finančních vztahů k ostatním FO a PO (včetně prostředků poskytnutých
        soukromým školám)" -> kraj_dotace_soukrome.csv (private schools only)
      * "Přehled čerpání akcí reprodukce majetku kraje" (tab 4, school in parentheses
        of the action name) -> kraj_investice.csv
  zavazne_ukazatele_PO_2026.xlsx   Rozpočet MSK 2026, příloha 7 (id=25048), závazné ukazatele
      (by IČO): příspěvek na provoz, its účelová část, investiční příspěvek -> kraj_rozpocet_2026.csv

Matching name -> RED_IZO is by normalised official name against data/msk_schools.csv,
then difflib fallback (cutoff 0.88); method recorded in column `match`.
"""
import csv, difflib, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from xlsx_read import sheets

RAW = ROOT / "data/raw/kraj"
ZU_IDS = {2022: 20376, 2023: 22561, 2024: 24205, 2025: 26071}
SRC_URL = "https://www.msk.cz/kraj/zastupitelstvo/soubory.html?id={}"

def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("prispevkova organizace", "po")
    s = re.sub(r"\b(spol\.\s*)?s\.?\s*r\.\s*o\.?", "sro", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())

SCHOOLS = list(csv.DictReader(open(ROOT / "data/msk_schools.csv", encoding="utf-8")))
BY_NORM = {norm(s["nazev"]): s for s in SCHOOLS}
BY_ICO = {s["ico"].zfill(8): s for s in SCHOOLS}

ALIAS = {}   # norm(old/other name) -> school row

def load_aliases():
    """Former names: ARES VR name history (companies), IČO+name pairs from the ZÚ
    'Výsledek hospodaření ... školství' tables (kraj PO), plus a short manual list."""
    import json
    for f in (ROOT / "data/raw/ares").glob("vr_*.json"):
        ico = f.stem[3:]
        if ico not in BY_ICO:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except ValueError:
            continue
        for z in d.get("zaznamy", []):
            for o in z.get("obchodniJmeno", []):
                ALIAS.setdefault(norm(o["hodnota"]), BY_ICO[ico])
    for y in ZU_IDS:
        S = sheets(RAW / f"zaverecny_ucet_{y}_tabulky.xlsx")
        rows = find_sheet(S, f"Výsledek hospodaření za rok {y} u příspěvkových organizací v odvětví školství")
        for r in rows[3:]:
            if r and re.fullmatch(r"\d{4,8}", str(r[0]).strip()) and len(r) > 1:
                ico = str(r[0]).strip().zfill(8)
                if ico in BY_ICO:
                    ALIAS.setdefault(norm(r[1]), BY_ICO[ico])
    # manual: the only Třinecké železárny school entity in ARES is IČO 27856216 (ŠPO, not in VR)
    ALIAS.setdefault(norm("Střední odborná škola Třineckých železáren"), BY_ICO["27856216"])
    ALIAS.setdefault(norm("Střední odborná škla Třineckých železáren"), BY_ICO["27856216"])  # typo in ZÚ 2024

def match(name):
    n = norm(name)
    if n in BY_NORM:
        return BY_NORM[n], "exact"
    if n in ALIAS:
        return ALIAS[n], "former_name"
    m = difflib.get_close_matches(n, BY_NORM.keys(), n=1, cutoff=0.88)
    if m:
        return BY_NORM[m[0]], f"fuzzy:{difflib.SequenceMatcher(None, n, m[0]).ratio():.2f}"
    return None, ""

def num(x):
    try:
        return round(float(x), 2)
    except (TypeError, ValueError):
        return ""

def find_sheet(S, needle):
    for n, rows in S.items():
        head = " ".join(x for r in rows[:3] for x in r if x)
        if needle in head:
            return rows
    raise KeyError(needle)

def blocks(rows):
    """Yield (recipient, schvaleno, cerpano, ucel) from recipient/amount/purpose tables."""
    cur = None
    for r in rows[3:]:
        r = (r + ["", "", "", ""])[:4]
        name, a, b, ucel = (x.strip() if isinstance(x, str) else x for x in r)
        if name and not a and not b:      # section header
            cur = None
            continue
        if name.startswith("Celkový součet"):
            cur = None
            continue
        if name:
            cur = " ".join(name.split())
        if cur and ucel and ucel != "Celkem":
            yield cur, num(a), num(b), " ".join(ucel.split())

def main():
    load_aliases()
    po, priv, inv, unmatched = [], [], [], set()
    for y, fid in ZU_IDS.items():
        S = sheets(RAW / f"zaverecny_ucet_{y}_tabulky.xlsx")
        src = f"Závěrečný účet MSK {y}, tab. část ({SRC_URL.format(fid)})"
        rows = find_sheet(S, "Přehled poskytnutých finančních prostředků příspěvkovým organizacím kraje")
        in_school = False
        cur = None
        for r in rows[3:]:
            r = (r + ["", "", "", ""])[:4]
            if r[0] and "odvětví" in r[0] and not r[1]:
                in_school = "školství" in r[0] and not r[0].startswith("Celkový")
                continue
            if not in_school:
                continue
            if r[0].startswith("Celkový součet"):
                in_school = False
                continue
            if r[0]:
                cur = " ".join(r[0].split())
            ucel = " ".join(str(r[3]).split())
            if not cur or not ucel or ucel == "Celkem":
                continue
            s, how = match(cur)
            if not s:
                unmatched.add(("po", cur))
                continue
            po.append([s["red_izo"], s["ico"], y, ucel, num(r[1]), num(r[2]), cur, how, src])
        rows = find_sheet(S, "soukromým školám")
        for name, a, b, ucel in blocks(rows):
            if not re.search(r"škol|škla|gymn|akademie|lyceum|učiliště|educa|prigo|dakol|porg|ahol", name, re.I):
                continue
            s, how = match(name)
            if not s:
                if "soukrom" in ucel.lower():
                    unmatched.add(("priv", name))
                continue
            priv.append([s["red_izo"], s["ico"], y, ucel, a, b, name, how, src])
        # investment actions: school name in parentheses at end of action name
        rows = S["tab 4"]
        hdr = next(i for i, r in enumerate(rows) if any("Výdaje v roce" in str(x) for x in r))
        H = rows[hdr]
        col_y = next(i for i, x in enumerate(H) if f"Výdaje v roce {y}" in str(x))
        name_col = next(i for i, x in enumerate(H) if "Název akce" in str(x))
        col_tot = next(i for i, x in enumerate(H) if "Výdaje na akci celkem" in str(x))
        for r in rows[hdr + 1:]:
            if len(r) <= col_y:
                continue
            akce = " ".join(str(r[name_col]).split())
            m = re.search(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", akce)
            if not m:
                continue
            s, how = match(m.group(1))
            if not s:
                continue
            inv.append([s["red_izo"], s["ico"], y, akce, num(r[col_y]), num(r[col_tot]), how, src])

    def write(path, header, rows):
        with open(ROOT / path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(header); w.writerows(rows)
        print(f"{path}: {len(rows)} rows, {len({r[0] for r in rows})} schools")

    write("data/kraj_prispevky_po.csv",
          ["red_izo", "ico", "year", "ucel", "schvaleno_tis_kc", "cerpano_tis_kc", "nazev_v_dokumentu", "match", "source"], po)
    write("data/kraj_dotace_soukrome.csv",
          ["red_izo", "ico", "year", "ucel", "schvaleno_tis_kc", "cerpano_tis_kc", "nazev_v_dokumentu", "match", "source"], priv)
    write("data/kraj_investice.csv",
          ["red_izo", "ico", "year", "akce", "vydaje_v_roce_tis_kc", "vydaje_na_akci_celkem_tis_kc", "match", "source"], inv)

    # rozpočet 2026 – závazné ukazatele (by IČO)
    S = sheets(RAW / "zavazne_ukazatele_PO_2026.xlsx")
    out = []
    src = f"Rozpočet MSK 2026, příl. 7 závazné ukazatele ({SRC_URL.format(25048)})"
    for sheet, metric in (("TAB-6", "prispevek_na_provoz_celkem"), ("TAB-6 účel", "prispevek_na_provoz_ucelovy"),
                          ("TAB-7", "investicni_prispevek")):
        ico = None
        for r in S[sheet]:
            r = (r + [""] * 4)[:4]
            if re.fullmatch(r"\d{8}", r[0]):
                ico = r[0]
            elif r[0]:
                ico = None if r[0] != "" else ico
            if not ico or ico not in BY_ICO:
                continue
            s = BY_ICO[ico]
            if sheet == "TAB-6":
                val, ucel = r[2], ""
            else:
                val, ucel = r[3], " ".join(r[2].split())
            if num(val) == "":
                continue
            out.append([s["red_izo"], ico, 2026, metric, ucel, num(val), src])
    write("data/kraj_rozpocet_2026.csv", ["red_izo", "ico", "year", "metric", "ucel", "tis_kc", "source"], out)
    for kind, n in sorted(unmatched):
        print(f"  unmatched {kind}: {n}")

if __name__ == "__main__":
    main()
