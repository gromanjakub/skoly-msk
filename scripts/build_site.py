"""Assemble docs/schools.json for the site: register info + per-unit pillar scores."""
import csv, json, os

ROOT = os.path.join(os.path.dirname(__file__), "..")
WEIGHTS = {"A": 30, "B": 20, "C": 15, "D": 15, "E": 10, "F": 10}
UNIT_LABEL = {"GY8": "G8", "GY6": "G6", "GY4": "G4", "LYC": "lyceum", "SOS": "SOŠ"}


def band(z):
    if z is None:
        return None
    for lim, b in ((1, 2), (0.33, 1), (-0.33, 0), (-1, -1)):
        if z >= lim:
            return b
    return -2


def display_name(full):
    """'Gymnázium, Ostrava-Poruba, Čs. exilu 669, příspěvková organizace' -> 'Gymnázium, Ostrava-Poruba'."""
    import re
    parts = [p.strip() for p in full.split(",")]
    keep = [p for p in parts if p and not re.search(r"\d|organizace|s\.r\.o|o\.p\.s|z\.ú|spolek", p)]
    return ", ".join(keep[:2]) if keep else full


def fnum(v, nd=1):
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


reg = {r["red_izo"]: r for r in csv.DictReader(open(os.path.join(ROOT, "data/msk_schools.csv")))}
scores = list(csv.DictReader(open(os.path.join(ROOT, "data/derived/scores.csv"))))

extra_pillars = {}   # filled later by other pillar builders: (redizo, unit) -> {"C": z, ...}
p = os.path.join(ROOT, "data/derived/pillars_extra.json")
if os.path.exists(p):
    for k, v in json.load(open(p)).items():
        extra_pillars[tuple(k.split("|"))] = v

units = {}
for s in scores:
    z = {"A": fnum(s["zA"], 2), "B": fnum(s["zB"], 2), "E": fnum(s["zE"], 2)}
    ex = extra_pillars.get((s["redizo"], s["unit"]), {})
    z.update(ex.get("z", {}))
    ok = s["enough_data"] == "1"
    have = {k: v for k, v in z.items() if v is not None}
    comp = (sum(WEIGHTS[k] * v for k, v in have.items()) / sum(WEIGHTS[k] for k in have)) if ok and len(have) >= 2 else None
    units.setdefault(s["redizo"], []).append({
        "unit": UNIT_LABEL[s["unit"]], "smo16": s["smo16"], "n": fnum(s["n_mz_per_year"], 0), "ok": ok,
        "cj_pct": fnum(s["cj_pct"]), "usp": fnum(s["usp"]), "va": fnum(s["va"]), "va_rel": fnum(s["va_rel"], 2), "va_cohorts": int(s["va_cohorts"] or 0),
        "poptavka": fnum(s["poptavka"], 2), "adm_pct": fnum(s["adm_pct"]),
        **ex.get("detail", {}),
        "z": z, "bands": {k: band(v) if ok else None for k, v in z.items()},
        "comp": round(comp, 2) if comp is not None else None, "comp_band": band(comp), "comp_pillars": sorted(have),
    })

geo = {}
for g in csv.DictReader(open(os.path.join(ROOT, "data/geo.csv"))):
    if g["v_msk"] == "1" and g["lat"] and (g["red_izo"] not in geo or g["kind"] == "sidlo"):
        geo[g["red_izo"]] = [round(float(g["lat"]), 5), round(float(g["lon"]), 5)]
csi = {}
for c in csv.DictReader(open(os.path.join(ROOT, "data/csi.csv"))):
    prev = csi.get(c["red_izo"])
    if c["report_date"] and (not prev or c["report_date"] > prev["datum"]):
        csi[c["red_izo"]] = {"datum": c["report_date"], "url": c["report_url"], "silne": c["silne_stranky"],
                             "slabe": c["slabe_stranky"], "doporuceni": c["doporuceni"],
                             "n_zaku": int(c["n_zaku"]) if c["n_zaku"].isdigit() else None}

fin = {}
for f in csv.DictReader(open(os.path.join(ROOT, "data/finance.csv"))):
    y = int(f["year"])
    if f["metric"] in ("costs_total", "personnel_costs") and y >= fin.get(f["red_izo"], {}).get("rok", 0):
        d = fin.setdefault(f["red_izo"], {})
        if y > d.get("rok", 0):
            d.clear(); d["rok"] = y
        d[f["metric"]] = float(f["value"])
invest = {}
for f in csv.DictReader(open(os.path.join(ROOT, "data/kraj_investice.csv"))):
    if f["red_izo"] and f["vydaje_v_roce_tis_kc"]:
        invest[f["red_izo"]] = invest.get(f["red_izo"], 0) + float(f["vydaje_v_roce_tis_kc"])
vs_claim = {}
vsr = {}
for f in csv.DictReader(open(os.path.join(ROOT, "data/vs_admissions_vyrocni_zpravy.csv"))):
    vsr.setdefault((f["red_izo"], f["cohort"]), {})[f["metric"]] = f
for (rid, coh), m in sorted(vsr.items()):
    if "n_admitted_vs" in m and "n_graduates" in m:
        try:
            share = round(100 * float(m["n_admitted_vs"]["value"]) / float(m["n_graduates"]["value"]))
        except (ValueError, ZeroDivisionError):
            continue
        vs_claim[rid] = {"rocnik": coh, "podil": share, "url": m["n_admitted_vs"]["source_url"]}

out = []
for rid, r in reg.items():
    if r["has_maturita"] != "1":
        continue
    t = [lab for flag, lab in (("has_gym8", "G8"), ("has_gym6", "G6"), ("has_gym4", "G4"), ("has_lyceum", "lyceum"),
                               ("has_sos_maturita", "SOŠ")) if r[flag] == "1"]
    out.append({"red_izo": rid, "nazev": (lambda d: d if len(d) >= 12 else (r["zkraceny_nazev"] or d))(display_name(r["nazev"])), "plny_nazev": r["nazev"],
                "obec": r["obec"] if r["sidlo_mimo_msk"] != "1" else r["obce_mist_vyuky_msk"].split(";")[0].strip(),
                "mista": [o.strip() for o in r["obce_mist_vyuky_msk"].split(";") if o.strip()], "zrizovatel": r["typ_zrizovatele_txt"], "typy": t,
                "kapacita": int(r["maturita_denni_obory_kapacita"] or 0),
                "geo": geo.get(rid), "csi": csi.get(rid), "vs_claim": vs_claim.get(rid),
                "fin": ({"rok": fin[rid]["rok"], "naklady_mil": round(fin[rid]["costs_total"] / 1e6, 1),
                         "osobni_pct": round(100 * fin[rid].get("personnel_costs", 0) / fin[rid]["costs_total"]),
                         "investice_mil": round(invest.get(rid, 0) / 1000, 1)}
                        if rid in fin and fin[rid].get("costs_total") else None),
                "units": sorted(units.get(rid, []), key=lambda u: list(UNIT_LABEL.values()).index(u["unit"]))})
out.sort(key=lambda x: (x["obec"], x["nazev"]))
missing = [s["redizo"] for s in scores if s["redizo"] not in reg]
json.dump(out, open(os.path.join(ROOT, "docs/schools.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print(len(out), "schools,", sum(len(x["units"]) for x in out), "units; scored schools not in register:", sorted(set(missing)))
