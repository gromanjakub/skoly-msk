#!/usr/bin/env python3
"""Download ČŠI inspection reports (PDF) for maturita schools.
Uses the report lists cached by fetch_inspis.py (data/raw/register/inspis/zpravy_{rid}.html).
Newest first; an entry that turns out to be a protokol (not an inspekční zpráva) is kept
but skipped. Stops after the newest zpráva if it is from 2022+, else after two zprávy.
Writes data/raw/csi/{red_izo}/{YYYY-MM-DD}_{guid}.pdf and data/raw/csi/_index.csv.
"""
import csv, re, subprocess, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSP = ROOT / "data/raw/register/inspis"
OUT = ROOT / "data/raw/csi"
BASE = "https://portal.csicr.cz"
UA = {"User-Agent": "Mozilla/5.0 (skoly-msk pilot; contact via GitHub)"}

def iso(d):
    dd, mm, yy = d.split("."); return f"{yy}-{int(mm):02d}-{int(dd):02d}"

def fetch(url, path):
    if path.exists() and path.stat().st_size > 0:
        return
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        path.write_bytes(r.read())
    time.sleep(1.0)

def kind(path):
    t = subprocess.run(["pdftotext", "-l", "2", str(path), "-"], capture_output=True, text=True).stdout
    flat = re.sub(r"\s+", "", t).upper()
    if len(flat) < 200: return "scan"
    if "INSPEKČNÍZPRÁV" in flat: return "zprava"
    if "PROTOKOL" in flat: return "protokol"
    return "other"

def main():
    schools = [s for s in csv.DictReader(open(ROOT / "data/msk_schools.csv", encoding="utf-8")) if s["has_maturita"] == "1"]
    idx = []
    for s in schools:
        rid = s["red_izo"]
        f = INSP / f"zpravy_{rid}.html"
        if not f.exists():
            print(rid, "no list"); idx.append({"red_izo": rid, "start": "", "end": "", "url": "", "file": "", "kind": "no_list"}); continue
        lst = f.read_text(encoding="utf-8")
        reps = re.findall(r"<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>\s*<td[^>]*>\s*<a href=\"([^\"]+)\"", lst)
        reps = sorted(((iso(a), iso(b), BASE + h) for a, b, h in reps), reverse=True)
        d = OUT / rid; d.mkdir(parents=True, exist_ok=True)
        nz = 0
        for st, en, url in reps:
            guid = url.split("/Files/Get/")[1].split("?")[0]
            p = d / f"{st}_{guid}.pdf"
            try:
                fetch(url, p); k = kind(p)
            except Exception as e:
                k = f"error:{e}"
            idx.append({"red_izo": rid, "start": st, "end": en, "url": url, "file": str(p.relative_to(ROOT)), "kind": k})
            print(rid, st, k)
            if k in ("zprava", "scan"):
                nz += 1
                if st >= "2022-01-01" or nz >= 2: break
            if len([i for i in idx if i["red_izo"] == rid]) >= 6: break
    with open(OUT / "_index.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(idx[0])); w.writeheader(); w.writerows(idx)

if __name__ == "__main__":
    main()
