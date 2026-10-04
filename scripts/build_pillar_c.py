"""Pillar C (excellence): competition results per 100 students, 2021/22-2025/26.

Points per result (team result counts once):
  national round: placed 1st-3rd 5, successful solver 3, other participant 1.5
  regional round (MO, FO, ChO, BiO, informatics): successful 0.5, other participant 0.2
Rows transcribed from images (language olympiads 2023-25) are included: 3 of 3 spot checks against
the original sheets matched (FJ SŠ 2024, NJ SŠ 2024, ŠJ ZŠ/VG II 2025).
School size = maturita candidates per year (all study types) x 4 upper-secondary years.
z-scores are within MSK only (no national competition data): gymnázia (G8/G6/G4) and
others (lyceum, SOŠ) separately, on log(1 + points per year per 100 students).
"""
import csv, json, math, os
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(ROOT, "data/derived")
YEARS = 5


def points(r):
    succ = r["successful"] == "true"
    if r["round"] == "ustredni":
        place = r["placement"].strip().rstrip(".")
        if succ and place in ("1", "2", "3"):
            return 5
        return 3 if succ else 1.5
    return 0.5 if succ else 0.2


pts = defaultdict(float)
cnt = defaultdict(lambda: defaultdict(int))
for r in csv.DictReader(open(os.path.join(ROOT, "data/olymp_msk_matched.csv"))):
    if not r["red_izo"]:
        continue
    pts[r["red_izo"]] += points(r)
    key = "nat" if r["round"] == "ustredni" else ("reg_succ" if r["successful"] == "true" else "reg")
    cnt[r["red_izo"]][key] += 1
    if r["round"] == "ustredni":
        cnt[r["red_izo"]]["comp_" + r["competition"]] += 1

scores = list(csv.DictReader(open(os.path.join(D, "scores.csv"))))
size = defaultdict(float)
for s in scores:
    size[s["redizo"]] += float(s["n_mz_per_year"] or 0) * 4

idx = {}
for s in scores:
    rid = s["redizo"]
    if size[rid] >= 40:
        idx[(rid, s["unit"])] = 100 * pts[rid] / YEARS / size[rid]

cat = lambda u: "gym" if u in ("GY8", "GY6", "GY4") else "other"
vals = defaultdict(list)
for (rid, u), v in idx.items():
    vals[cat(u)].append(math.log1p(v))
stat = {}
for c, v in vals.items():
    m = sum(v) / len(v)
    stat[c] = (m, math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1)))

out = {}
for (rid, u), v in idx.items():
    m, sd = stat[cat(u)]
    nat = {k[5:]: n for k, n in cnt[rid].items() if k.startswith("comp_")}
    out[f"{rid}|{u}"] = {"z": {"C": round((math.log1p(v) - m) / sd, 2)},
                         "detail": {"c_index": round(v, 2), "c_nat": cnt[rid]["nat"], "c_reg_succ": cnt[rid]["reg_succ"],
                                    "c_nat_by": nat}}
json.dump(out, open(os.path.join(D, "pillars_extra.json"), "w"), ensure_ascii=False, indent=1)
print(len(out), "units with C;", sum(1 for k in pts if pts[k] > 0), "schools with any result")
top = sorted(((v, k) for k, v in idx.items()), reverse=True)[:12]
for v, k in top:
    print(round(v, 2), k, cnt[k[0]]["nat"], cnt[k[0]]["reg_succ"])
