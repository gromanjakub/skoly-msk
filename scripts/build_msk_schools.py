#!/usr/bin/env python3
"""Build data/msk_schools.csv from the MŠMT RŠŠZ JSON-LD for Moravskoslezský kraj.

One row per RED_IZO that runs a C00 (střední škola) seated in MSK, plus (if the
national file is present) schools seated elsewhere with a C00 místo výuky in MSK
(sidlo_mimo_msk=1; their obor flags describe the whole school, not the MSK branch). Flags count only obory
that are NOT dobíhající (being phased out), in any form of study.
Source: https://lkod-ftp.msmt.gov.cz/00022985/11f1f670-1a8a-4a8a-b188-0eed2d01fca7/RSSZ-Moravskoslezsky-kraj.jsonld
"""
import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data/raw/register/RSSZ-Moravskoslezsky-kraj.jsonld"
# optional: national file, used only to catch schools seated in another kraj
# that teach at a místo výuky in MSK (e.g. PORG Ostrava)
SRC_CR = ROOT / "data/raw/register/RSSZ-cela-CR.jsonld"
MSK_OKRESY = {"Ostrava-město", "Karviná", "Opava", "Frýdek-Místek", "Nový Jičín", "Bruntál"}
OUT = ROOT / "data/msk_schools.csv"

# typZrizovatele (číselník BAZS) -- labels verified against zrizovatele names in the data
ZRIZ = {"1": "MŠMT", "2": "obec", "3": "jiný ústřední orgán", "5": "soukromý",
        "6": "církev", "7": "kraj"}
FORMA = {"10": "denní", "22": "dálková", "23": "večerní", "24": "distanční", "30": "kombinovaná"}

def addr(a):
    u = a.get("ulice") or a.get("castObce") or a.get("obec") or ""
    n = str(a.get("cisloDomovni") or "")
    if a.get("cisloOrientacni"):
        n += f"/{a['cisloOrientacni']}{a.get('dodatekOrientacnihoCisla') or ''}"
    return f"{u} {n}".strip()

def classify(kod):
    m = re.fullmatch(r"(\d\d)-(\d\d)-([A-Z])/(\d\d)", kod)
    if not m:
        return "other"
    obor, kat, suf = m.group(1) + "-" + m.group(2), m.group(3), m.group(4)
    if kat == "K" and obor.startswith("79-4"):
        return {"81": "gym8", "61": "gym6", "41": "gym4"}.get(suf, "other")
    if kat == "M" and obor == "78-42":
        return "lyceum"
    if kat == "M" or (kat == "L" and suf.startswith("0")):
        return "sos_maturita"
    if kat == "L" and suf.startswith("5"):
        return "nastavba"
    if kat == "H":
        return "vyucni"
    if kat in "EC":
        return "ec"
    return "other"

def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    subjects = [(p, 0) for p in data["list"]]
    if SRC_CR.exists():
        for p in json.loads(SRC_CR.read_text(encoding="utf-8"))["list"]:
            if p["kraj"] != "Moravskoslezský kraj" and any(
                    s["druh"] == "C00" and any(m["adresa"].get("okres") in MSK_OKRESY for m in s["mistaVyuky"])
                    for s in p["skolyAZarizeni"]):
                subjects.append((p, 1))
    rows = []
    for p, outside in subjects:
        schools = [s for s in p["skolyAZarizeni"] if s["druh"] == "C00"]
        if not schools:
            continue
        s = schools[0]  # verified: max one C00 per RED_IZO in MSK
        active = [o for o in s["obory"] if not o["dobihajiciObor"]]
        cats = {}
        cap = {}
        for o in active:
            c = classify(o["kod"])
            cats.setdefault(c, []).append(o["kod"])
            if o["formaVzdelavani"] == "10":
                cap[c] = cap.get(c, 0) + (o.get("kapacita") or 0)
        mat = [c for c in ("gym8", "gym6", "gym4", "lyceum", "sos_maturita") if c in cats]
        a = p["adresa"]
        zr = "; ".join(z.get("nazevOsoby") or "" for z in p["zrizovatele"])
        other_druhy = sorted({x["druh"] for x in p["skolyAZarizeni"]} - {"C00"})
        rows.append({
            "red_izo": p["redIzo"], "izo": s["izo"], "ico": p["ico"],
            "nazev": p["uplnyNazev"], "zkraceny_nazev": p["zkracenyNazev"],
            "adresa": addr(a), "obec": a.get("obec"), "cast_obce": a.get("castObce"),
            "psc": a.get("psc"), "okres_kod": a.get("okres"), "orp_kod": a.get("uzemiDleORP"),
            "ruian_adm": a.get("kodRUIAN"),
            "typ_zrizovatele": p["typZrizovatele"],
            "typ_zrizovatele_txt": ZRIZ.get(p["typZrizovatele"], "?"),
            "zrizovatel": zr, "pravni_forma": p["pravniForma"],
            "email": "; ".join(p.get("emaily") or []),
            "sidlo_mimo_msk": outside, "kraj_sidla": p["kraj"],
            "n_mist_vyuky": len(s["mistaVyuky"]),
            "obce_mist_vyuky": "; ".join(sorted({m["adresa"].get("obec") or "" for m in s["mistaVyuky"]})),
            "obce_mist_vyuky_msk": "; ".join(sorted({m["adresa"].get("obec") or "" for m in s["mistaVyuky"] if m["adresa"].get("okres") in MSK_OKRESY})),
            "kapacita_skoly": sum(k["nejvyssiPovolenyPocet"] for k in s["kapacity"] if k["mernaJednotka"] == "01"),
            "has_gym8": int("gym8" in cats), "has_gym6": int("gym6" in cats),
            "has_gym4": int("gym4" in cats), "has_lyceum": int("lyceum" in cats),
            "has_sos_maturita": int("sos_maturita" in cats),
            "has_nastavba": int("nastavba" in cats), "has_vyucni": int("vyucni" in cats),
            "has_maturita": int(bool(mat)),
            "maturita_denni_obory_kapacita": sum(cap.get(c, 0) for c in mat),
            "kap_gym_denni": sum(cap.get(c, 0) for c in ("gym8", "gym6", "gym4")),
            "kap_lyceum_denni": cap.get("lyceum", 0),
            "kap_sos_maturita_denni": cap.get("sos_maturita", 0),
            "obory_maturitni": " ".join(sorted({k for c in mat for k in cats[c]})),
            "obory_vsechny_aktivni": " ".join(sorted({o["kod"] for o in active})),
            "formy": " ".join(sorted({FORMA.get(o["formaVzdelavani"], o["formaVzdelavani"]) for o in active})),
            "jine_soucasti": " ".join(other_druhy),
            "datum_zahajeni": s.get("datumZahajeniCinnosti"),
        })
    rows.sort(key=lambda r: (r["obec"] or "", r["nazev"]))
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"datumVystupu={data['datumVystupu']} rows={len(rows)} "
          f"maturita={sum(r['has_maturita'] for r in rows)} "
          f"seated_outside={sum(r['sidlo_mimo_msk'] for r in rows)} -> {OUT}", file=sys.stderr)

if __name__ == "__main__":
    main()
