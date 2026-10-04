"""Assemble docs/schools.json for the site: register info + per-unit pillar scores."""
import csv, json, os, re

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

extras = json.load(open(os.path.join(ROOT, "data/derived/extras.json")))
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
        **{(("tr_" + k) if k in ("years", "cj", "aj", "va", "n") else k): v
           for k, v in extras.get(s["redizo"] + "|" + s["unit"], {}).items()},
        "z": z, "bands": {k: band(v) if (ok or k in ("C", "E")) else None for k, v in z.items()},
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

hist = {}
for f in ("historie_sci.csv",):   # more parts (historie_*.csv) get added here as they're finished
    pth = os.path.join(ROOT, "data", f)
    if os.path.exists(pth):
        for h in csv.DictReader(open(pth)):
            if h["red_izo"]:
                hist.setdefault(h["red_izo"], []).append(
                    {"soutez": h["competition"], "rok": h["year"], "kat": h["category"], "misto": h["placement"], "medaile": h.get("medal", "")})
for v in hist.values():
    v.sort(key=lambda x: x["rok"], reverse=True)
ia = {}
for f in csv.DictReader(open(os.path.join(ROOT, "data/infoabsolvent.csv"))):
    if f["url"] and f["red_izo"] not in ia:
        ia[f["red_izo"]] = re.sub(r"(/Skola/\d+).*", r"\1", f["url"]) if "/Skola/" in f["url"] else f["url"]

out = []
for rid, r in reg.items():
    if r["has_maturita"] != "1" and r["has_nastavba"] != "1":
        continue
    t = [lab for flag, lab in (("has_gym8", "G8"), ("has_gym6", "G6"), ("has_gym4", "G4"), ("has_lyceum", "lyceum"),
                               ("has_sos_maturita", "SOŠ"), ("has_nastavba", "nástavba")) if r[flag] == "1"]
    out.append({"red_izo": rid, "nazev": (lambda d: d if len(d) >= 12 else (r["zkraceny_nazev"] or d))(display_name(r["nazev"])), "plny_nazev": r["nazev"],
                "obec": r["obec"] if r["sidlo_mimo_msk"] != "1" else r["obce_mist_vyuky_msk"].split(";")[0].strip(),
                "mista": [o.strip() for o in r["obce_mist_vyuky_msk"].split(";") if o.strip()], "zrizovatel": r["typ_zrizovatele_txt"], "typy": t,
                "kapacita": int(r["maturita_denni_obory_kapacita"] or 0),
                "mimo": r["kraj_sidla"] if r["sidlo_mimo_msk"] == "1" else None,
                "csi": csi.get(rid), "historie": hist.get(rid), "infoabsolvent": ia.get(rid), "vs_claim": vs_claim.get(rid),
                "fin": ({"rok": fin[rid]["rok"], "naklady_mil": round(fin[rid]["costs_total"] / 1e6, 1),
                         "osobni_pct": round(100 * fin[rid].get("personnel_costs", 0) / fin[rid]["costs_total"]),
                         "investice_mil": round(invest.get(rid, 0) / 1000, 1)}
                        if rid in fin and fin[rid].get("costs_total") else None),
                "units": sorted(units.get(rid, []), key=lambda u: list(UNIT_LABEL.values()).index(u["unit"]))})
out.sort(key=lambda x: (x["obec"], x["nazev"]))
with open(os.path.join(ROOT, "docs/skoly-msk.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["red_izo", "skola", "obec", "typ_studia", "maturantu_rocne", "hodnoceno", "A_z", "B_z", "C_z", "E_z", "souhrn_z",
                "prid_hodnota_percentilu", "cj_percentil", "uspesnost_pct", "aj_percentil", "c_bodu_na_100", "poptavka_p1_na_misto",
                "prijati_percentil", "naplnenost_pct"])
    for x in out:
        for u in x["units"]:
            w.writerow([x["red_izo"], x["plny_nazev"], x["obec"], u["unit"], u["n"], int(u["ok"]), u["z"].get("A"), u["z"].get("B"),
                        u["z"].get("C"), u["z"].get("E"), u["comp"], u["va"], u["cj_pct"], u["usp"], u.get("aj_pct"),
                        u.get("c_index"), u["poptavka"], u["adm_pct"], u.get("fill")])
missing = [s["redizo"] for s in scores if s["redizo"] not in reg]
json.dump(out, open(os.path.join(ROOT, "docs/schools.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print(len(out), "schools,", sum(len(x["units"]) for x in out), "units; scored schools not in register:", sorted(set(missing)))
