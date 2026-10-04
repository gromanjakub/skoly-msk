#!/usr/bin/env python3
"""Historie (not scored): national-round successes of MSK schools 2010/11-2020/21
for MO (A), FO (A), ChO (A, E), Olympiáda v informatice (MO kat. P) and Ekonomická olympiáda I-V.

In:  data/raw/historie/{mo,fo,cho,inf}/ (downloaded 2026-10-04, see notes/historie_sci.md)
     data/raw/olymp/eko/old_*.html (EO ročníky I-V)
Out: data/historie_sci.csv
     competition, year, round, category, placement, medal, school_raw, town, red_izo, source_url

What counts (one row per placed student, no names stored):
  MO, FO, P   section "Vítězové" (the official top tier) or place 1-3
  ChO         place 1-3 only (úspěšný řešitel can't be computed, point scale varies by year)
  EO          place 1-3 (no official tier); ročník IV (2019/20) only top 3 published (blog post)
Student names are used only in memory: FO pages print the school/kraj in a second table keyed
by name, and an MO/P/ChO name index (+-2 years) is the fallback if neither has the school.
School -> red_izo: scripts/olymp_match.py match(), with manual rows from
data/olymp_school_overrides.csv and data/historie_sci_overrides.csv (the latter wins).
"""
import csv, glob, html, json, os, re, subprocess, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = os.path.join(ROOT, 'data', 'raw', 'historie')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import olymp_match as M  # noqa: E402  (loads data/msk_schools.csv)

OUT = os.path.join(ROOT, 'data', 'historie_sci.csv')
COLS = ['competition', 'year', 'round', 'category', 'placement', 'medal', 'school_raw', 'town', 'red_izo', 'source_url']

# MSK towns; order matters (specific first). "Zábřeh" alone is Zábřeh na Moravě -> only with Ostrava.
TOWNS = [
    ('Frýdek-Místek', r'Frýd(ek|ku)[- ]*Míst(ek|ku)|F-?Místek|GPB'),
    ('Frýdlant nad Ostravicí', r'Frýdlant(u|ě)? *n(ad|\.) *O'),
    ('Frenštát pod Radhoštěm', r'Frenštát'),
    ('Nový Jičín', r'Nov(ý|ém|ého) Jičín|N\. ?Jičín'),
    ('Český Těšín', r'Česk(ý|ém|ého) Těšín|Polské G|Polskie Gimnazjum'),
    ('Ostrava', r'Ostrav(a|ě|y|u|ou)\b|Ostrava-|Wichterl|Matiční|Hladno|akademika Heyrovsk|SPŠChPRIGO|Olgy Havlové'),
    ('Opava', r'Opav(a|ě|y|u)\b|Mendelovo G|\b[SM]G Opav'),
    ('Karviná', r'Karvin'),
    ('Havířov', r'Havířov'),
    ('Třinec', r'Třin(ec|ci|ce)'),
    ('Bílovec', r'Bílov(ec|ci)|GMK|Koperník'),
    ('Kopřivnice', r'Kopřivnic'),
    ('Bruntál', r'Bruntál'),
    ('Krnov', r'Krnov'),
    ('Orlová', r'Orlov(á|é)'),
    ('Bohumín', r'Bohumín'),
    ('Příbor', r'Příbor'),
    ('Hlučín', r'Hlučín'),
    ('Studénka', r'Studénk'),
    ('Odry', r'\bOdr(y|ách)\b'),
    ('Rýmařov', r'Rýmařov'),
    ('Vítkov', r'Vítkov'),
    ('Fulnek', r'Fulnek'),
    ('Jablunkov', r'Jablunkov'),
    ('Kravaře', r'Kravař'),
    ('Klimkovice', r'Klimkovic'),
    ('Petřvald', r'Petřvald'),
    ('Město Albrechtice', r'Albrechtic'),
    ('Vratimov', r'Vratimov'),
    ('Rychvald', r'Rychvald'),
    ('Šenov', r'Šenov'),
    ('Brušperk', r'Brušperk'),
]


def town_of(s):
    for name, rx in TOWNS:
        if re.search(rx, s or ''):
            return name
    return ''


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def fold(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def nkey(name):
    return ' '.join(sorted(re.findall(r'[a-z]+', fold(name))))


def pdftext(path):
    return subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True).stdout


def sy(start):
    return f'{start}/{str(start + 1)[2:]}'


def mo_year(r):  # MO/P ročník -> school year
    return sy(r + 1950)


def fo_year(r):
    return sy(r + 1958)


def rank_int(p):
    m = re.match(r'\s*(\d+)', p or '')
    return int(m.group(1)) if m else None


rows = []
FO_NO_SECTIONS = []
# name index for FO school lookup: nkey -> list of (start_year, school)
NAMES = {}


def remember(name, school, start):
    if name and school:
        NAMES.setdefault(nkey(name), []).append((start, school))


def add(**kw):
    kw.setdefault('round', 'ustredni')
    rows.append({k: kw.get(k, '') for k in COLS})


# ------------------------------------------------------------------ MO kategorie A (ÚK)
MO_ROW = re.compile(r'^\s*(\d+\.(?:\s*[–-]\s*\d+\.)?)?\s*(\S.*?)\s+(\d/\d)\s+(.+?)\s{2,}[\d\s–-]+$')
MO_URL = {}
for f in glob.glob(os.path.join(H, 'mo', 'roc_*.html')):
    r = re.search(r'roc_(\d+)', f).group(1)
    for u in re.findall(r'href="(/media/\d+/[^"]+\.pdf)"', open(f, encoding='utf8').read()):
        MO_URL[os.path.basename(u)] = 'https://www.matematickaolympiada.cz' + u
MO_FILES = sorted(f for f in glob.glob(os.path.join(H, 'mo', '*.pdf'))
                  if re.search(r'_(a\d+iiiv|a63v|a\d+list[^/]*|vysledky_70-a-0)\.pdf$', f))
for f in MO_FILES:
    r = int(os.path.basename(f)[:2])
    start = r + 1950
    section, rank = '', ''
    for line in pdftext(f).splitlines():
        st = line.strip()
        if re.match(r'^(Vítězové|Další úspěšní|Úspěšní řešitelé|Ostatní)', st):
            section, rank = st.split()[0], ''
            continue
        m = MO_ROW.match(line)
        if not m:
            continue
        if m.group(1):
            rank = m.group(1).replace(' ', '')
        name, school = m.group(2).strip(), m.group(4).strip()
        remember(name, school, start)
        t = town_of(school)
        win = section == 'Vítězové'
        if t and (win or (rank_int(rank) or 99) <= 3):
            add(competition='Matematická olympiáda', year=mo_year(r), category='A',
                placement=rank + (' (vítěz)' if win else ''), school_raw=school, town=t,
                source_url=MO_URL.get(os.path.basename(f)[3:], ''))

# ------------------------------------------------------------------ Olympiáda v informatice (P), ÚK
for f in sorted(glob.glob(os.path.join(H, 'inf', 'p_*_3.html'))):
    # three layouts: section rows ("Vítězové", ...) or class=marked (vítěz) / class=success (ÚŘ);
    # column order differs, so take the school column from the header row
    r = int(re.search(r'p_(\d+)_3', f).group(1))
    s = open(f, encoding='utf8').read()
    section, rank, i_sch, i_name = '', '', None, 1
    for tr in re.split(r'<tr', s)[1:]:
        head = tr.split('>')[0]
        cells = [clean(c) for c in re.split(r'<t[dh][^>]*>', tr)[1:]]
        if 'Pořadí' in cells:
            continue
        if len(cells) <= 2:
            if re.search(r'Vítěz|Úspěšn|Ostatní|Další|účastníci', ' '.join(cells)):
                section = ' '.join(cells)
            continue
        if len(cells) < 4 or not any(re.match(r'^\d/\d$', c) for c in cells):
            continue
        rank = cells[0] or rank
        # school = first cell after the name that contains letters (layouts differ in column order)
        name = cells[1]
        school = next(c for c in cells[2:] if re.search(r'[A-Za-zÁ-ž]{2}', c))
        remember(name, school, r + 1950)
        t = town_of(school)
        win = section.startswith('Vítěz') or 'marked' in head
        if t and os.environ.get('DEBUG'):
            print('PDBG', r, rank, section or head, school)
        if t and (win or (rank_int(rank) or 99) <= 3):
            add(competition='Olympiáda v informatice (MO kat. P)', year=mo_year(r), category='P',
                placement=rank + (' (vítěz)' if win else ''), school_raw=school, town=t,
                source_url=f'https://mo.mff.cuni.cz/p/{r}/vysledky-3.html')

# ------------------------------------------------------------------ ChO (NK, database JSON)
CHO_URL = ('https://olympiada.vscht.cz/cs/administrace/student-radek-bez-autentikace/'
           '?order&points&category_code={c}&all_results&round={rnd}&year={y}&area_code={a}')
msk_cho = set()
for f in sorted(glob.glob(os.path.join(H, 'cho', 'kk_T_*.json'))):
    y, c = re.search(r'kk_T_(\d{4})_([A-E])', f).groups()
    for x in json.load(open(f))['data']:
        nm = f"{x['student__first_name']} {x['student__last_name']}"
        msk_cho.add((int(y), nkey(nm)))
        remember(nm, x.get('student__profile__school__name', ''), int(y))
for f in sorted(glob.glob(os.path.join(H, 'cho', 'nk_*.json'))):
    y, c = re.search(r'nk_(\d{4})_([A-E])', f).groups()
    y = int(y)
    if y > 2020:
        continue
    for x in json.load(open(f))['data']:
        nm = f"{x['student__first_name']} {x['student__last_name']}"
        school = x.get('student__profile__school__name') or ''
        city = x.get('student__profile__school__city__name') or ''
        remember(nm, school, y)
        kraj = x.get('student__profile__school__city__district__county__name')
        t = town_of(school + ' ' + city)
        if kraj is not None and 'Moravskoslez' not in kraj:
            continue
        if kraj is None and not (t or (y, nkey(nm)) in msk_cho):
            continue
        pts = x.get('points')
        pts = float(str(pts).replace(',', '.')) if pts not in (None, '') else None
        rk = x.get('results__result_order')
        rk = int(rk) if rk not in (None, '') else None
        # úspěšný řešitel (>= 60 % of max) can't be computed: the point scale differs by year
        # (2016/17 A: 41 of 43 have >= 60 b.; E max 118.65) -> places 1-3 only
        ur = False
        if rk and rk <= 3:
            add(competition='Chemická olympiáda', year=sy(y), category=c,
                placement=(f'{rk}.' if rk else '') + (' (úspěšný řešitel)' if ur else ''),
                school_raw=school, town=t or city, source_url=CHO_URL.format(c=c, rnd=4, y=y, a='CZ'))

# ------------------------------------------------------------------ FO kategorie A (celostátní kolo)
# fyzikalniolympiada.cz/archiv/celostatni-kola/NN: the result table (with "Vítězové" section rows)
# plus, most years, a second table of the invited contestants with kraj and school.
def fo_tables(s):
    for tb in re.findall(r'<table.*?</table>', s, re.S):
        if 'Zadání úloh' in tb:
            continue
        trs = [[clean(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
               for tr in re.findall(r'<tr.*?</tr>', tb, re.S)]
        if trs:
            yield [h.lower() for h in trs[0]], trs[1:]


def col(hd, *keys):
    for i, h in enumerate(hd):
        if any(h.startswith(k) for k in keys):
            return i
    return None


def is_msk_kraj(k):
    return bool(re.match(r'(MS|Moravskoslez)', k or ''))


def fo_name(c, hd):
    i_last, i_first = col(hd, 'příjmení'), col(hd, 'jméno')
    i_full = col(hd, 'příjmení a jméno', 'příjmení, jméno', 'soutěžící')
    try:
        if i_full is not None:
            return c[i_full]
        if i_last is not None and i_first is not None:
            return f'{c[i_first]} {c[i_last]}'
        if i_first is not None:
            return c[i_first]
    except IndexError:
        return ''
    return ''


for f in sorted(glob.glob(os.path.join(H, 'fo', 'ck_*.html'))):
    r = int(re.search(r'ck_(\d+)', f).group(1))
    if r > 61:
        continue
    start = r + 1958
    tabs = [(hd, b) for hd, b in fo_tables(open(f, encoding='utf8').read())
            if col(hd, 'příjmení', 'jméno', 'soutěžící') is not None]
    info = {}
    for hd, body in tabs:
        i_sch, i_kraj = col(hd, 'škola'), col(hd, 'kraj')
        for c in body:
            nm = fo_name(c, hd)
            if not re.search(r'[A-Za-zÁ-ž]{2}', nm):
                continue
            d = info.setdefault(nkey(nm), {})
            if i_sch is not None and i_sch < len(c) and c[i_sch] and not d.get('school'):
                d['school'] = re.split(r',\s*(Mgr|RNDr|PaedDr|Ing|PhDr|Bc)\b', c[i_sch])[0]
            if i_kraj is not None and i_kraj < len(c) and c[i_kraj]:
                d['kraj'] = c[i_kraj]
    hd, body = tabs[0]
    i_sch = col(hd, 'škola')
    section, rank, has_sect = '', '', False
    for c in body:
        sect = [x for x in c if re.match(r'^(Vítězové|Úspěšní|Ostatní|Další)', x)]
        if sect:
            section, has_sect = sect[0], True
            continue
        nm = fo_name(c, hd)
        if not re.search(r'[A-Za-zÁ-ž]{2}', nm):
            continue
        rank = c[0] if re.match(r'^\d+', c[0] or '') else rank
        k = nkey(nm)
        d = info.get(k, {})
        school = (c[i_sch] if i_sch is not None and i_sch < len(c) else '') or d.get('school', '')
        kraj = d.get('kraj', '')
        how = 'list'
        if not school:  # name index from MO/P/ChO lists of the same or neighbouring years
            cand = [sc for (yy, sc) in NAMES.get(k, []) if abs(yy - start) <= 2]
            if cand:
                school, how = cand[0], 'xref'
        t = town_of(school)
        msk = is_msk_kraj(kraj) or (not kraj and bool(t))
        win = section.startswith('Vítěz')
        rk = rank.rstrip('.') + '.' if rank else ''
        if msk and os.environ.get('DEBUG'):
            print('FODBG', r, rk, section[:8], how, school[:45], kraj, [x for x in NAMES.get(k, []) if 'Hav' in x[1]] if 'Hav' in school else '')
        if msk and (win or (rank_int(rank) or 99) <= 3):
            add(competition='Fyzikální olympiáda', year=fo_year(r), category='A',
                placement=rk + (' (vítěz)' if win else ''), school_raw=school or '?', town=t,
                source_url=f'https://fyzikalniolympiada.cz/archiv/celostatni-kola/{r}')
    if not has_sect:
        FO_NO_SECTIONS.append(fo_year(r))


# FO 62 (2020/21) from Osmo
OS = os.path.join(H, 'fo', 'osmo_62-A-3.html')
if os.path.exists(OS):
    s = open(OS, encoding='utf8').read()
    for tb in re.findall(r'<tbody>(.*?)</table>', s, re.S):
        rank = ''
        for tr in re.split(r'<tr', tb)[1:]:
            title = re.search(r'title="([^"]*)"', tr.split('>')[0])
            title = title.group(1) if title else ''
            c = [clean(x) for x in re.split(r'<td[^>]*>', tr)[1:]]
            if len(c) > 2 and re.match(r'\d/\d', c[2]):
                c.insert(0, '')
            if len(c) < 4:
                continue
            rank = c[0] or (rank if title else '')
            t = town_of(c[2])
            if t and (title == 'Vítěz' or (rank_int(rank) or 99) <= 3):
                add(competition='Fyzikální olympiáda', year=fo_year(62), category='A',
                    placement=rank + (' (vítěz)' if title == 'Vítěz' else ''), school_raw=c[2], town=t,
                    source_url='https://osmo.fyzikalniolympiada.cz/public/kolo/62-A-3/vysledky')

# ------------------------------------------------------------------ Ekonomická olympiáda I-V (finále)
EO = [('old_rocnik-2017-18.html', 2016, 'https://ekonomickaolympiada.cz/minule-rocniky/rocnik-2017-18/'),   # shows ročník I
      ('old_rocnik-2016-17.html', 2017, 'https://ekonomickaolympiada.cz/minule-rocniky/rocnik-2016-17/'),   # shows ročník II
      ('old_iii-rocnik-2018-2019.html', 2018, 'https://ekonomickaolympiada.cz/minule-rocniky/iii-rocnik-2018-2019/'),
      ('old_v-rocnik.html', 2020, 'https://ekonomickaolympiada.cz/o-soutezi-informace-o-soutezi-2/minule-rocniky/v-rocnik/')]
for fn, start, url in EO:
    p = os.path.join(ROOT, 'data', 'raw', 'olymp', 'eko', fn)
    s = open(p, encoding='utf8').read()
    tb = re.findall(r'<table.*?</table>', s, re.S)
    if not tb:
        continue
    trs = re.findall(r'<tr.*?</tr>', tb[0], re.S)
    hd = [clean(x).lower() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', trs[0], re.S)]
    i_sch = col(hd, 'škola', 'název školy')
    i_kraj = col(hd, 'kraj')
    for tr in trs[1:]:
        c = [clean(x) for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)]
        if len(c) <= i_sch or not re.match(r'\d', c[0]):
            continue
        school = c[i_sch]
        kraj = c[i_kraj] if i_kraj is not None and i_kraj < len(c) else ''
        t = town_of(school)
        msk = kraj in ('MS', 'Moravskoslezský', 'Moravskoslezský kraj') or (not kraj and t)
        if msk and (rank_int(c[0]) or 99) <= 3:
            add(competition='Ekonomická olympiáda', year=sy(start), category='SŠ',
                placement=c[0].rstrip('.') + '.', school_raw=school, town=t, source_url=url)

# ------------------------------------------------------------------ red_izo
ov = {}
for fn in ('olymp_school_overrides.csv', 'historie_sci_overrides.csv'):
    p = os.path.join(ROOT, 'data', fn)
    if os.path.exists(p):
        for o in csv.DictReader(open(p, encoding='utf8')):
            ov[(o['school_raw'], o['town'])] = o['red_izo']
for r in rows:
    k = (r['school_raw'], r['town'])
    if k in ov:
        r['red_izo'] = ov[k]
    elif r['school_raw'] and r['school_raw'] != '?':
        rid, method, conf, note = M.match(r['school_raw'], r['town'])
        r['red_izo'] = rid if conf in ('high', 'med') else ''
        r['_note'] = f'{method}/{conf} {note}'

rows.sort(key=lambda r: (r['competition'], r['year'], r['category'], rank_int(r['placement']) or 99))
with open(OUT, 'w', newline='', encoding='utf8') as fh:
    w = csv.DictWriter(fh, COLS, extrasaction='ignore')
    w.writeheader()
    w.writerows(rows)

from collections import Counter
print('rows', len(rows), '->', OUT)
for k, v in sorted(Counter((r['competition'], r['year']) for r in rows).items()):
    print(*k, v, sep='\t')
print('FO years without section marks (top 3 only):', FO_NO_SECTIONS)
print('without red_izo:', [(r['school_raw'][:50], r['town'], r.get('_note', '')) for r in rows if not r['red_izo']])
