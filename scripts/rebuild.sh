#!/usr/bin/env bash
# Rebuild everything the site needs. ./scripts/rebuild.sh [--fetch]
# --fetch downloads the core public data (CERMAT, MŠMT register) into data/raw/ first.
# Other sources have their own fetch scripts (slow, polite scraping), run them by hand when needed:
#   olympiads   scripts/olymp_extract.py, then scripts/olymp_match.py
#   ČŠI         scripts/fetch_inspis.py, scripts/fetch_csi.py, scripts/build_csi.py
#   geo         scripts/build_geo.py
#   finance     scripts/build_finance.py --fetch ; kraj tables scripts/build_kraj.py
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--fetch" ]]; then
  mkdir -p data/raw/cermat data/raw/register
  while read -r path; do
    [[ -z "$path" ]] && continue
    f="data/raw/cermat/$(basename "$path")"
    [[ -s "$f" ]] || { curl -fsS "https://data.cermat.cz$path" -o "$f"; sleep 1; }
  done < scripts/cermat_urls.txt
  curl -fsS https://lkod-ftp.msmt.gov.cz/00022985/11f1f670-1a8a-4a8a-b188-0eed2d01fca7/RSSZ-Moravskoslezsky-kraj.jsonld \
       -o data/raw/register/RSSZ-Moravskoslezsky-kraj.jsonld
  curl -fsS https://lkod-ftp.msmt.gov.cz/00022985/88a7c12b-6084-4e47-8b50-46097c6e683f/RSSZ-cela-CR.jsonld \
       -o data/raw/register/RSSZ-cela-CR.jsonld
fi

python3 scripts/build_msk_schools.py
python3 scripts/build_cermat.py        # ~1 min
python3 scripts/build_scores.py        # pillars A, B, E
python3 scripts/build_pillar_c.py      # pillar C (needs data/olymp_msk_matched.csv)
python3 scripts/build_site.py          # docs/schools.json
