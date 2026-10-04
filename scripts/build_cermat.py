"""Tidy national extracts (MSK is filtered later from the CERMAT school-level XLSX files).

Writes data/derived/{mz,jpz,pz}.csv. Source: CZVV (CERMAT), data.cermat.cz.
"""
import csv, glob, os, re, sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data/raw/cermat")
OUT = os.path.join(ROOT, "data/derived")
sys.path.insert(0, os.path.dirname(__file__))
from _xlsx_stdlib import read  # noqa: E402

os.makedirs(OUT, exist_ok=True)


def num(v):
    v = (v or "").strip()
    if v in ("", "-", "x"):
        return ""
    try:
        f = float(v)
    except ValueError:
        return ""
    return int(f) if f.is_integer() else round(f, 3)


def flatten(band_row, head_row):
    """Join a two-row header into 'BAND|METRIC', carrying the band to the right."""
    cols, band = [], ""
    for i, h in enumerate(head_row):
        b = band_row[i].strip() if i < len(band_row) else ""
        if b and not re.match(r"^\d{4}$", b) and "ZKOUŠKA" not in b and "JPZ" not in b:
            band = b
        cols.append(f"{band}|{h.strip()}" if band else h.strip())
    return cols


def kraj(rec):
    """Region name; the code column is inconsistent across files (CZ080/CZ081), the name is not."""
    for k in rec:
        if "KRAJ" in k and "NÁZEV" in k and rec[k].strip():
            return rec[k].strip()
    return ""


# --- maturita: use the 'jap' files (state after the autumn re-sits) ---
MZ_SUBJ = {"ČESKÝ JAZYK": "cj", "MATEMATIKA": "ma", "ANGLIČTINA": "aj"}
MZ_MET = {"PŘIHLÁŠENI": "prihl", "KONALI": "konali", "USPĚLI": "uspeli", "PRŮMĚRNÝ % SKÓR": "skor",
          "PRŮMĚRNÉ PERCENTILOVÉ UMÍSTĚNÍ": "pct", "PODÍL ÚSPĚŠNÝCH (%)": "usp", "PODÍL VOLBY PŘEDMĚTU (%)": "volba"}
mz_rows = []
for f in sorted(glob.glob(os.path.join(RAW, "MZ*jap_SC_skolobory.xlsx"))):
    year = int(re.search(r"MZ(\d{4})", f).group(1))
    rows = read(f)
    hi = next(i for i, r in enumerate(rows) if "REDIZO" in r)
    cols = flatten(rows[hi - 1], rows[hi])
    for r in rows[hi + 1:]:
        rec = dict(zip(cols, r))
        tr = rec.get("TŘÍDĚNÍ", "")
        if tr not in ("redizo", "redizo_smo16"):
            continue
        out = {"year": year, "redizo": rec["REDIZO"], "group": "CELKEM" if tr == "redizo" else rec.get("SMO16", ""),
               "nazev": rec.get("NÁZEV ŠKOLY", ""), "kraj": kraj(rec)}
        for k, v in rec.items():
            band, _, met = k.partition("|")
            if band == "SPOLEČNÁ ČÁST MZ CELKEM" and met in ("PŘIHLÁŠENI", "KONALI", "USPĚLI", "PODÍL ÚSPĚŠNÝCH (%)", "NEÚČAST (%)"):
                out["all_" + {"PŘIHLÁŠENI": "prihl", "KONALI": "konali", "USPĚLI": "uspeli",
                              "PODÍL ÚSPĚŠNÝCH (%)": "usp", "NEÚČAST (%)": "neucast"}[met]] = num(v)
            elif band in MZ_SUBJ and met in MZ_MET:
                out[f"{MZ_SUBJ[band]}_{MZ_MET[met]}"] = num(v)
        mz_rows.append(out)

# --- JPZ 2017-2023: mean percentile of all applicants, per school x group ---
jpz_rows = []
for f in sorted(glob.glob(os.path.join(RAW, "JPZ*_skoly-skolobory_vysledky.xlsx"))):
    year = int(re.search(r"JPZ(\d{4})", f).group(1))
    rows = read(f)
    hi = next(i for i, r in enumerate(rows) if any("OBOROVÁ SKUPINA" == c for c in r))
    cols = flatten(rows[hi - 1], rows[hi])
    idcol = cols[0]
    for r in rows[hi + 1:]:
        rec = dict(zip(cols, r))
        rid = (rec.get(idcol) or "").strip()
        if not re.fullmatch(r"\d{9}", rid):
            continue
        jpz_rows.append({
            "year": year, "redizo": rid, "group": rec.get("OBOROVÁ SKUPINA", ""), "rocnik": rec.get("ROČNÍK", ""),
            "nazev": rec.get("NÁZEV ŠKOLY", ""), "kraj": kraj(rec),
            "cj_konali": num(rec.get("ČESKÝ JAZYK|KONALI")), "cj_pct": num(rec.get("ČESKÝ JAZYK|PRŮMĚRNÉ PERCENTILOVÉ UMÍSTĚNÍ")),
            "ma_konali": num(rec.get("MATEMATIKA|KONALI")), "ma_pct": num(rec.get("MATEMATIKA|PRŮMĚRNÉ PERCENTILOVÉ UMÍSTĚNÍ")),
        })

# --- PZ 2024-2026, round 1: capacity, demand, admitted scores, per school x obor ---
PZ_COLS = {
    "KAPACITA": "kapacita", "INDEX POPTÁVKY (PŘIHLÁŠKY / KAPACITA)": "index_poptavky",
    "PŘIHLÁŠKY CELKEM": "prihlasky", "PŘIHLÁŠKY - PRIORITA 1": "prihlasky_p1", "PŘIJATÍ": "prijati",
    "ČJ+MA - KONALI (PŘIJATI)": "adm_n",
    "ČJ+MA - % SKÓR - PRŮMĚR (PŘIJATI)": "adm_skor200_mean", "ČJ+MA - % SKÓR - MIN (PŘIJATI)": "adm_skor200_min",
    "ČJ+MA - PERCENTIL - PRŮMĚR (PŘIJATI)": "adm_pct_mean", "ČJ - PERCENTIL - PRŮMĚR (PŘIJATI)": "adm_cj_pct_mean",
    "ČJ+MA - PERCENTIL - PRŮMĚR": "all_pct_mean",
}
pz_rows = []
for f in sorted(glob.glob(os.path.join(RAW, "PZ*_kolo1_skolobory_vysledky.xlsx"))):
    rows = read(f)
    cols = [c.strip() for c in rows[0]]
    for r in rows[1:]:
        rec = dict(zip(cols, r))
        out = {"year": int(rec["ROK"]), "redizo": rec["REDIZO"], "nazev": rec["NÁZEV ŠKOLY"], "kraj": rec.get("KRAJ - NÁZEV", "").strip(),
               "group": rec.get("SKUPINA OBORŮ (16)", ""), "kkov": rec.get("KKOV", ""), "obor": rec.get("OBOR - NÁZEV", ""),
               "zamereni": rec.get("ZAMĚŘENÍ OBORU", ""), "forma": rec.get("FORMA VZDĚLÁVÁNÍ", ""),
               "maturitni": rec.get("MATURITNÍ STATUS", "")}
        out.update({v: num(rec.get(k)) for k, v in PZ_COLS.items()})
        pz_rows.append(out)


def dump(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, keys)
        w.writeheader()
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows, {len({r['redizo'] for r in rows})} schools, "
          f"years {sorted({r['year'] for r in rows})}")


dump("mz.csv", mz_rows)
dump("jpz.csv", jpz_rows)
dump("pz.csv", pz_rows)
