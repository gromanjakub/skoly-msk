"""Pillar scores A (value added), B (exit results), E (demand) per school x comparison group.

Every indicator is first expressed against the national distribution of the same SMO16 obor group
(so a technical SOŠ is compared with technical SOŠ nationwide), then aggregated to the comparison
unit shown on the site: GY8, GY6, GY4, LYC, SOŠ (all other maturita groups of the school pooled).

Input: data/derived/{mz,jpz,pz}.csv (scripts/build_cermat.py). Output: data/derived/scores.csv
"""
import csv, math, os
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(ROOT, "data/derived")
MSK = "Moravskoslezský"
GYM = {"GY8", "GY6", "GY4", "LYC"}
LAG = {"GY8": 8, "GY6": 6}          # years between JPZ and maturita; 4 otherwise
B_YEARS = (2024, 2025, 2026)        # post-2021 maturita format; percentiles are within-year anyway
A_MZ_YEARS = range(2022, 2027)      # maturita cohorts used for value added
E_YEARS = (2024, 2025, 2026)
MIN_N = 10                          # minimum students per year on average for a unit to be scored


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(name):
    with open(os.path.join(D, name)) as fh:
        return list(csv.DictReader(fh))


def unit(group):
    return group if group in GYM else "SOS"


def wmean(pairs):
    pairs = [(v, w) for v, w in pairs if v is not None and w]
    sw = sum(w for _, w in pairs)
    return (sum(v * w for v, w in pairs) / sw, sw) if sw else (None, 0)


def zscorer(values_by_group):
    """values_by_group: group -> list of school-level values. Returns z(group, value)."""
    stats = {}
    for g, vals in values_by_group.items():
        vals = [v for v in vals if v is not None]
        if len(vals) < 5:
            continue
        m = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) or 1
        stats[g] = (m, sd)
    return lambda g, v: None if v is None or g not in stats else (v - stats[g][0]) / stats[g][1]


mz = [r for r in load("mz.csv") if r["group"] != "CELKEM"]
jpz = load("jpz.csv")
pz = [r for r in load("pz.csv") if r["maturitni"] == "maturitní" and r["forma"] == "den"]

# ---------- B: exit results (Czech percentile, success rate), maturita 2024-2026 ----------
b_cj, b_usp = defaultdict(list), defaultdict(list)       # (redizo, group) -> [(value, weight)]
for r in mz:
    if int(r["year"]) not in B_YEARS:
        continue
    k = (r["redizo"], r["group"])
    n = f(r["cj_konali"])
    b_cj[k].append((f(r["cj_pct"]), n))
    prihl, usp = f(r["all_prihl"]), f(r["all_uspeli"])
    if prihl:
        b_usp[k].append((100 * usp / prihl if usp is not None else None, prihl))

school_group = {}
for k in set(b_cj) | set(b_usp):
    cj, n = wmean(b_cj[k])
    usp, _ = wmean(b_usp[k])
    school_group[k] = {"cj_pct": cj, "usp": usp, "n_mz": n / len(B_YEARS)}
z_cj = zscorer({g: [v["cj_pct"] for (s, gg), v in school_group.items() if gg == g and v["n_mz"] >= MIN_N]
                for g in {g for _, g in school_group}})
z_usp = zscorer({g: [v["usp"] for (s, gg), v in school_group.items() if gg == g and v["n_mz"] >= MIN_N]
                 for g in {g for _, g in school_group}})

# ---------- A: value added = maturita Czech percentile vs entrance-exam percentile of the cohort ----------
jidx = {(r["redizo"], r["group"], int(r["year"])): r for r in jpz}
pairs = []   # (redizo, group, mz_year, x_cj, x_ma, y_cj, n)
for r in mz:
    y = int(r["year"])
    if y not in A_MZ_YEARS:
        continue
    j = jidx.get((r["redizo"], r["group"], y - LAG.get(r["group"], 4)))
    if not j:
        continue
    xc, xm, yc, n = f(j["cj_pct"]), f(j["ma_pct"]), f(r["cj_pct"]), f(r["cj_konali"])
    if None in (xc, xm, yc) or not n or n < 5:
        continue
    pairs.append((r["redizo"], r["group"], y, xc, xm, yc, n))


def ols(rows):
    """Weighted least squares y ~ 1 + x1 + x2 via normal equations (3x3)."""
    X = [[1, a, b] for a, b, _, _ in rows]
    Y = [y for _, _, y, _ in rows]
    W = [w for _, _, _, w in rows]
    A = [[sum(W[i] * X[i][p] * X[i][q] for i in range(len(X))) for q in range(3)] for p in range(3)]
    c = [sum(W[i] * X[i][p] * Y[i] for i in range(len(X))) for p in range(3)]
    for p in range(3):                       # Gauss-Jordan
        piv = A[p][p]
        A[p] = [v / piv for v in A[p]]; c[p] /= piv
        for q in range(3):
            if q != p:
                fct = A[q][p]
                A[q] = [A[q][i] - fct * A[p][i] for i in range(3)]; c[q] -= fct * c[p]
    return c


resid = defaultdict(list)
fit_info = {}
for g in {p[1] for p in pairs}:
    rows = [(p[3], p[4], p[5], p[6]) for p in pairs if p[1] == g]
    if len(rows) < 30:
        continue
    beta = ols(rows)
    ybar = sum(r[2] * r[3] for r in rows) / sum(r[3] for r in rows)
    ss_res = sum(r[3] * (r[2] - (beta[0] + beta[1] * r[0] + beta[2] * r[1])) ** 2 for r in rows)
    ss_tot = sum(r[3] * (r[2] - ybar) ** 2 for r in rows)
    fit_info[g] = {"n_pairs": len(rows), "r2": round(1 - ss_res / ss_tot, 3), "beta": [round(b, 3) for b in beta]}
    for p in pairs:
        if p[1] == g:
            resid[(p[0], g)].append((p[5] - (beta[0] + beta[1] * p[3] + beta[2] * p[4]), p[6], p[2]))
# Shrink toward 0 by reliability. One cohort of median size (27 students) has year-to-year r = 0.40,
# so per-student noise K = 27 * (1 - 0.4) / 0.4 ~ 40; reliability = N / (N + K), N = students over all cohorts.
K_VA = 40
va, va_rel = {}, {}
for k, v in resid.items():
    N = sum(w for _, w, _ in v)
    va_rel[k] = N / (N + K_VA)
    va[k] = (wmean([(e, w) for e, w, _ in v])[0] * va_rel[k], len(v))
z_va = zscorer({g: [v for (s, gg), (v, c) in va.items() if gg == g] for g in {g for _, g in va}})

# ---------- E: demand = first-priority applications per place, percentile of admitted ----------
e = defaultdict(lambda: {"p1": 0, "kap": 0, "adm": []})
for r in pz:
    if int(r["year"]) not in E_YEARS:
        continue
    k = (r["redizo"], r["group"])
    p1, kap = f(r["prihlasky_p1"]), f(r["kapacita"])
    if p1 is not None and kap:
        e[k]["p1"] += p1; e[k]["kap"] += kap
    e[k]["adm"].append((f(r["adm_pct_mean"]), f(r["adm_n"])))
e_val = {k: {"poptavka": (v["p1"] / v["kap"]) if v["kap"] else None, "adm_pct": wmean(v["adm"])[0]} for k, v in e.items()}
z_pop = zscorer({g: [math.log(v["poptavka"]) for (s, gg), v in e_val.items() if gg == g and v["poptavka"]]
                 for g in {g for _, g in e_val}})
z_adm = zscorer({g: [v["adm_pct"] for (s, gg), v in e_val.items() if gg == g] for g in {g for _, g in e_val}})

# ---------- aggregate SMO16 groups to comparison units, MSK only ----------
msk = {r["redizo"] for r in mz if r["kraj"] == MSK} | {r["redizo"] for r in pz if r["kraj"] == MSK}
names = {}
for r in mz + pz:
    if r["redizo"] in msk:
        names[r["redizo"]] = r["nazev"]

agg = defaultdict(lambda: defaultdict(list))
for (s, g), v in school_group.items():
    if s not in msk:
        continue
    u, w = (s, unit(g)), v["n_mz"]
    agg[u]["groups"].append(g)
    agg[u]["n_mz"].append((v["n_mz"], 1))
    if v["n_mz"] >= MIN_N / 2:
        agg[u]["cj_pct"].append((v["cj_pct"], w)); agg[u]["usp"].append((v["usp"], w))
        agg[u]["zB"].append(((lambda a, b: None if a is None or b is None else (a + b) / 2)(z_cj(g, v["cj_pct"]), z_usp(g, v["usp"])), w))
for (s, g), (v, c) in va.items():
    if s in msk:
        w = school_group.get((s, g), {}).get("n_mz", 1)
        agg[(s, unit(g))]["va"].append((v, w)); agg[(s, unit(g))]["zA"].append((z_va(g, v), w))
        agg[(s, unit(g))]["va_cohorts"].append((c, 1))
        agg[(s, unit(g))]["va_rel"].append((va_rel[(s, g)], w))
for (s, g), v in e_val.items():
    if s in msk:
        w = e[(s, g)]["kap"] or 1
        agg[(s, unit(g))]["poptavka"].append((v["poptavka"], w)); agg[(s, unit(g))]["adm_pct"].append((v["adm_pct"], w))
        zp = z_pop(g, math.log(v["poptavka"])) if v["poptavka"] else None
        za = z_adm(g, v["adm_pct"])
        agg[(s, unit(g))]["zE"].append((None if zp is None or za is None else (zp + za) / 2, w))
        agg[(s, unit(g))]["groups"].append(g)

out = []
for (s, u), d in sorted(agg.items()):
    row = {"redizo": s, "nazev": names.get(s, ""), "unit": u, "smo16": " ".join(sorted(set(d["groups"])))}
    row["n_mz_per_year"] = round(sum(v for v, _ in d["n_mz"]), 1) if d["n_mz"] else 0
    for k in ("cj_pct", "usp", "va", "va_rel", "poptavka", "adm_pct", "zA", "zB", "zE"):
        v, _ = wmean(d[k])
        row[k] = round(v, 3) if v is not None else ""
    row["va_cohorts"] = max((v for v, _ in d["va_cohorts"]), default=0)
    row["enough_data"] = int(row["n_mz_per_year"] >= MIN_N)
    out.append(row)

with open(os.path.join(D, "scores.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, list(out[0]))
    w.writeheader(); w.writerows(out)
with open(os.path.join(D, "va_fit.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["smo16", "n_pairs", "r2", "b0", "b_cj", "b_ma"])
    for g, v in sorted(fit_info.items()):
        w.writerow([g, v["n_pairs"], v["r2"], *v["beta"]])
print(len(out), "units;", sum(r["enough_data"] for r in out), "with enough data")
for g, v in sorted(fit_info.items()):
    print(g, v)
