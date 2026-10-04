#!/usr/bin/env python3
"""Per-school financial statements from Monitor státní pokladny (MF ČR, CSÚIS) -> data/finance.csv

Inputs: bulk CSV extracts in data/raw/monitor/ (download with --fetch):
  VYKZZ  = výkaz zisku a ztráty  https://monitor.statnipokladna.gov.cz/data/extrakty/csv/ZiskZtraty/{Y}_12_Data_CSUIS_VYKZZ.zip
  ROZV   = rozvaha               https://monitor.statnipokladna.gov.cz/data/extrakty/csv/Rozvaha/{Y}_12_Data_CSUIS_ROZV.zip
(URLs found via NKOD SPARQL, the SPA's own catalogue page is JS-only.)

Only units that file to CSÚIS are covered: příspěvkové organizace (kraj, obec),
state units. Private schools (s.r.o., o.p.s., z.ú., školská právnická osoba)
and church schools are not in Monitor.

Values are CZK (not thousands), for the full year (period 12), main + economic
activity summed unless the metric says otherwise. Each VYKZZ file also holds the
previous year; we use only the current-period columns of each file.
"""
import csv, io, sys, zipfile, subprocess, time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/monitor"
OUT = ROOT / "data/finance.csv"
YEARS = [2022, 2023, 2024, 2025]
BASE = "https://monitor.statnipokladna.gov.cz/data/extrakty/csv"

def num(s):
    s = s.strip()
    if not s:
        return 0.0
    neg = s.endswith("-")
    v = float(s.rstrip("-"))
    return -v if neg else v

# metric -> (selector on ZC_POLVYK or ZC_SYNUC)
VZZ_ROWS = {"A.": "costs_total", "B.": "revenue_total", "B.IV.": "revenue_transfers",
            "C.2.": "result_after_tax"}
VZZ_SYN = {
    "521": "wages",                    # mzdové náklady
    "524": "social_insurance",         # zákonné sociální pojištění
    "551": "depreciation",             # odpisy
    "558": "small_assets",             # náklady z drobného dlouhodobého majetku
    "501": "materials", "502": "energy", "511": "repairs", "518": "services",
    "672": "operating_subsidies",      # výnosy vybraných místních vládních institucí z transferů (provozní dotace)
}
PERSONNEL_SYN = {"521", "524", "525", "527", "528"}
OWN_SYN = {"601", "602", "603", "604", "609"}   # výnosy z vlastních výkonů a zboží
ROZV_ROWS = {"AKTIVA": "assets_total", "A.": "fixed_assets", "A.II.": "tangible_fixed_assets"}

def fetch():
    RAW.mkdir(parents=True, exist_ok=True)
    for y in YEARS:
        for folder, code, pre in (("ZiskZtraty", "VYKZZ", "VYKZZ"), ("Rozvaha", "ROZV", "ROZV")):
            dst = RAW / f"{pre}_{y}_12.zip"
            if dst.exists():
                continue
            url = f"{BASE}/{folder}/{y}_12_Data_CSUIS_{code}.zip"
            subprocess.run(["curl", "-sf", "-o", str(dst), url], check=True)
            time.sleep(1)

def rows(zpath):
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            with z.open(name) as f:
                rd = csv.reader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"), delimiter=";")
                next(rd)
                yield from rd

def main():
    if "--fetch" in sys.argv:
        fetch()
    schools = list(csv.DictReader(open(ROOT / "data/msk_schools.csv", encoding="utf-8")))
    ico2red = {}
    for s in schools:
        ico2red.setdefault(s["ico"].zfill(8), []).append(s["red_izo"])
    out = []
    found = defaultdict(set)
    for y in YEARS:
        acc = defaultdict(float)
        src = f"Monitor SP, VYKZZ {y}/12"
        zp = RAW / f"VYKZZ_{y}_12.zip"
        if zp.exists():
            for r in rows(zp):
                ico = r[4].zfill(8)
                if ico not in ico2red:
                    continue
                pol, syn = r[8], r[9]
                main_, hosp = num(r[10]), num(r[11])
                tot = main_ + hosp
                found[ico].add(y)
                if pol in VZZ_ROWS:
                    acc[(ico, VZZ_ROWS[pol])] += tot
                if syn in VZZ_SYN:
                    acc[(ico, VZZ_SYN[syn])] += tot
                if syn in PERSONNEL_SYN:
                    acc[(ico, "personnel_costs")] += tot
                if syn in OWN_SYN:
                    acc[(ico, "own_revenue")] += tot
                    acc[(ico, "own_revenue_hosp_cinnost")] += hosp
                if pol == "A.":
                    acc[(ico, "costs_hosp_cinnost")] += hosp
            for (ico, m), v in sorted(acc.items()):
                for red in ico2red[ico]:
                    out.append([red, ico, y, m, round(v, 2), src])
        acc = defaultdict(float)
        src = f"Monitor SP, ROZV {y}/12 (netto)"
        zp = RAW / f"ROZV_{y}_12.zip"
        if zp.exists():
            for r in rows(zp):
                ico = r[4].zfill(8)
                if ico in ico2red and r[8] in ROZV_ROWS:
                    acc[(ico, ROZV_ROWS[r[8]] + "_netto")] += num(r[12])
                    acc[(ico, ROZV_ROWS[r[8]] + "_brutto")] += num(r[10])
            for (ico, m), v in sorted(acc.items()):
                for red in ico2red[ico]:
                    out.append([red, ico, y, m, round(v, 2), src])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["red_izo", "ico", "year", "metric", "value", "source"])
        w.writerows(out)
    mat = {s["ico"].zfill(8) for s in schools if s["has_maturita"] == "1"}
    print(f"wrote {len(out)} rows; schools found: {len(found)} of {len(ico2red)}; "
          f"maturita schools found: {len(mat & set(found))} of {len(mat)}")
    for s in schools:
        if s["has_maturita"] == "1" and s["ico"].zfill(8) not in found and s["pravni_forma"] == "331":
            print("  missing PO:", s["ico"], s["nazev"][:70])

if __name__ == "__main__":
    main()
