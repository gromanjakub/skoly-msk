#!/usr/bin/env python3
"""Coordinates for school seats and teaching sites (místa výuky of the C00 component).
Addresses + RÚIAN address-point codes from the MŠMT register (ČR JSON-LD, so out-of-kraj
seats are covered). Points from ČÚZK ArcGIS REST, layer AdresniMisto, outSR=4326 (WGS84).
Output: data/geo.csv (red_izo, kind, adresa, lat, lon, source, ruian_kod).
"""
import csv, json, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MSK_OKRESY = {"CZ0801", "CZ0802", "CZ0803", "CZ0804", "CZ0805", "CZ0806", "Ostrava-město", "Karviná", "Opava", "Frýdek-Místek", "Nový Jičín", "Bruntál"}
SVC = "https://ags.cuzk.gov.cz/arcgis/rest/services/RUIAN/Prohlizeci_sluzba_nad_daty_RUIAN/MapServer/1/query"
RAW = ROOT / "data/raw/geo"; RAW.mkdir(parents=True, exist_ok=True)

def fmt(a):
    ul = a.get("ulice") or a.get("castObce") or a.get("obec") or ""
    cp = a.get("cisloDomovni"); co = a.get("cisloOrientacni")
    num = f"{cp}" + (f"/{co}{a.get('dodatekOrientacnihoCisla') or ''}" if co else "") if cp else ""
    return f"{ul} {num}".strip() + f", {a.get('psc') or ''} {a.get('obec') or ''}".rstrip()

def query(codes):
    q = {"where": "kod in (%s)" % ",".join(map(str, codes)), "outFields": "kod,adresa",
         "outSR": "4326", "returnGeometry": "true", "f": "json"}
    req = urllib.request.Request(SVC + "?" + urllib.parse.urlencode(q), headers={"User-Agent": "skoly-msk pilot"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    time.sleep(1.0)
    return {f["attributes"]["kod"]: (f["geometry"]["y"], f["geometry"]["x"], f["attributes"]["adresa"]) for f in d["features"]}

def main():
    want = {s["red_izo"] for s in csv.DictReader(open(ROOT / "data/msk_schools.csv", encoding="utf-8"))}
    reg = json.load(open(ROOT / "data/raw/register/RSSZ-cela-CR.jsonld", encoding="utf-8"))["list"]
    rows = []
    for subj in reg:
        rid = str(subj.get("redIzo"))
        if rid not in want: continue
        a = subj["adresa"]
        rows.append({"red_izo": rid, "kind": "sidlo", "adresa": fmt(a), "ruian_kod": a.get("kodRUIAN"), "v_msk": int(a.get("okres") in MSK_OKRESY)})
        seen = {a.get("kodRUIAN")}
        for c in subj["skolyAZarizeni"]:
            if c["druh"] != "C00": continue
            for m in c["mistaVyuky"]:
                k = m["adresa"].get("kodRUIAN")
                if k in seen: continue  # teaching site at the seat address -> not repeated
                seen.add(k)
                rows.append({"red_izo": rid, "kind": "misto_vyuky", "adresa": fmt(m["adresa"]), "ruian_kod": k, "v_msk": int(m["adresa"].get("okres") in MSK_OKRESY)})
    codes = sorted({r["ruian_kod"] for r in rows if r["ruian_kod"]})
    pts = {}
    for i in range(0, len(codes), 100):
        pts.update(query(codes[i:i + 100]))
    json.dump({str(k): v for k, v in pts.items()}, open(RAW / "ruian_points.json", "w"), ensure_ascii=False)
    for r in rows:
        p = pts.get(r["ruian_kod"])
        r["lat"], r["lon"] = (f"{p[0]:.6f}", f"{p[1]:.6f}") if p else ("", "")
        r["source"] = "RUIAN AdresniMisto (ags.cuzk.gov.cz, outSR=4326)" if p else "not found: RUIAN code from register not in AdresniMisto (likely abolished)"
    rows.sort(key=lambda r: (r["red_izo"], r["kind"] != "sidlo", r["adresa"]))
    with open(ROOT / "data/geo.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["red_izo", "kind", "adresa", "lat", "lon", "source", "ruian_kod", "v_msk"])
        w.writeheader(); w.writerows(rows)
    print(len(want), "schools;", len({r['red_izo'] for r in rows}), "found in register;", len(rows), "rows;",
          sum(1 for r in rows if r["lat"]), "geocoded")

if __name__ == "__main__":
    main()
