#!/usr/bin/env python3
"""For each school in data/msk_schools.csv, query ČŠI InspIS PORTÁL by RED_IZO:
- inspection report list (dates + PDF links)
- the school's self-filled profile (aktuální počet žáků, web, ...)
Raw HTML cached in data/raw/register/inspis/. Output: data/msk_inspis.csv.
Undocumented endpoints reverse-engineered from portal.csicr.cz JS (2026-10-04).
"""
import csv, html, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/register/inspis"; RAW.mkdir(parents=True, exist_ok=True)
BASE = "https://portal.csicr.cz"
UA = {"User-Agent": "Mozilla/5.0 (skoly-msk pilot; contact via GitHub)",
      "X-Requested-With": "XMLHttpRequest"}

def get(url, data=None, cache=None):
    if cache and cache.exists():
        return cache.read_text(encoding="utf-8")
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        t = r.read().decode("utf-8", "replace")
    if cache:
        cache.write_text(t, encoding="utf-8")
    time.sleep(1.0)
    return t

def text(t):
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))

def after(s, label, start=0):
    m = re.compile(re.escape(label) + r"\s*:?\s*([^:]*?)(?=\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][^:]{0,60}:|$)").search(s, start)
    return m.group(1).strip() if m else ""

def main():
    schools = list(csv.DictReader(open(ROOT / "data/msk_schools.csv", encoding="utf-8")))
    out = []
    for s in schools:
        rid, izo = s["red_izo"], s["izo"]
        res = get(f"{BASE}/Search/SchoolSearch?Length=6", {
            "FilterType": "Default", "advancedFilter": "false", "pageSize": "25",
            "totalFound": "0", "page": "1", "a03REDIZO": rid, "a05ID": "0", "a09ID": "0",
            "PouzeSkolySVyplnenymProfilem": "false", "RowsCondition": "AND"},
            cache=RAW / f"search_{rid}.html")
        m = re.search(r'data-id="(\d+)" data-redizo="%s"' % rid, res)
        row = {"red_izo": rid, "izo": izo, "nazev": s["nazev"], "inspis_id": m.group(1) if m else ""}
        reports = []
        if m:
            lst = get(f"{BASE}/Search/InspekcniZpravyList/{m.group(1)}?redizo={rid}",
                      cache=RAW / f"zpravy_{rid}.html")
            for d1, d2, href in re.findall(
                    r"<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*<a href=\"([^\"]+)\"", lst):
                reports.append((d1, d2, BASE + href))
        def iso(d):
            dd, mm, yy = d.split("."); return f"{yy}-{int(mm):02d}-{int(dd):02d}"
        reports.sort(key=lambda r: iso(r[0]), reverse=True)
        row["n_zprav"] = len(reports)
        row["posledni_inspekce_od"] = iso(reports[0][0]) if reports else ""
        row["posledni_inspekce_do"] = iso(reports[0][1]) if reports else ""
        row["posledni_zprava_url"] = reports[0][2] if reports else ""
        row["vsechny_inspekce_od"] = " ".join(iso(r[0]) for r in reports)
        prof = text(get(f"{BASE}/School/{rid}", cache=RAW / f"school_{rid}.html"))
        i = prof.find(f"IZO: {izo}")
        row["profil_ma_izo_c00"] = int(i >= 0)
        i = max(i, 0)
        row["profil_aktualni_pocet_zaku"] = after(prof, "Aktuální počet žáků", i)
        row["profil_nejvyssi_povoleny_pocet"] = after(prof, "Nejvyšší povolený počet žáků", i)
        row["profil_web"] = after(prof, "Web")
        row["profil_dod"] = after(prof, "Dny otevřených dveří (termín/y)", i)[:80]
        row["profil_skolne"] = after(prof, "Roční školné v Kč", i)
        out.append(row)
        print(rid, row["inspis_id"], row["n_zprav"], row["posledni_inspekce_od"], row["profil_aktualni_pocet_zaku"])
    with open(ROOT / "data/msk_inspis.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)

if __name__ == "__main__":
    main()
