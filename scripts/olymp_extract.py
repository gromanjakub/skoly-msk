#!/usr/bin/env python3
"""Extract MSK rows from downloaded competition result lists.

Reads data/raw/olymp/{mo,fo,cho,bio,inf,soc}/ (downloaded by hand / curl, see
notes/olympiady.md), merges in data/raw/olymp/*/rows_msk.csv produced for the
other competitions, writes data/olymp_msk.csv.

No full student names are stored: only initials.
Stdlib only + pdftotext.
"""
import csv, glob, html, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw', 'olymp')
OUT = os.path.join(ROOT, 'data', 'olymp_msk.csv')
FIELDS = ['competition', 'year', 'round', 'category', 'student', 'school_raw',
          'town', 'placement', 'successful', 'team']

# MSK towns (canonical name, regex). Order matters: more specific first.
TOWNS = [
    ('Frýdek-Místek', r'Frýdek[- ]?Místek|F-?Místek|Místek'),
    ('Frýdlant nad Ostravicí', r'Frýdlant n(ad|\.) ?O'),
    ('Frenštát pod Radhoštěm', r'Frenštát'),
    ('Nový Jičín', r'Nov(ý|ém) Jičín|N\. ?Jičín'),
    ('Český Těšín', r'Česk(ý|ém) Těšín|Polské G|Polskie Gimnazjum'),
    ('Ostrava', r'Ostrav|Wichterl|Matiční G|Hladnov|chemická akademika Heyrovsk|PRIGO'),
    ('Opava', r'Opav|Mendelovo G'),
    ('Karviná', r'Karvin'),
    ('Havířov', r'Havířov'),
    ('Třinec', r'Třin(ec|ci)'),
    ('Bílovec', r'Bílovec|Bílovci'),
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


def town_of(school):
    for name, rx in TOWNS:
        if re.search(rx, school or ''):
            return name
    return ''


def initials(name):
    parts = [p for p in re.split(r'\s+', (name or '').strip()) if p]
    return ''.join(p[0] + '.' for p in parts if p[0].isalpha())


def pdftext(path, layout=True):
    args = ['pdftotext'] + (['-layout'] if layout else []) + [path, '-']
    return subprocess.run(args, capture_output=True, text=True).stdout


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


rows = []
msk_names = {}   # (comp, year) -> set of full names seen in MSK regional rounds (in memory only)


def add(**kw):
    kw.setdefault('team', 'individual')
    rows.append({k: kw.get(k, '') for k in FIELDS})


# ---------------------------------------------------------------- MO (PDF)
MO_ROW = re.compile(r'^\s*(\d+\.(?:\s*[–-]\s*\d+\.)?)?\s*(\S.*?)\s+(\d/\d)\s+(.+?)\s{2,}[\d\s]+$')


def parse_mo_pdf(path):
    out, section, rank = [], '', ''
    for line in pdftext(path).splitlines():
        st = line.strip()
        if re.match(r'^(Vítězové|Úspěšní řešitelé|Ostatní)', st):
            section, rank = st, ''
            continue
        m = MO_ROW.match(line)
        if not m:
            continue
        if m.group(1):
            rank = m.group(1).replace(' ', '')
        r = rank if not section.startswith('Ostatní') else ''
        out.append(dict(name=m.group(2).strip(), school=m.group(4).strip(),
                        placement=r, section=section,
                        successful=section.startswith(('Vítěz', 'Úspěšn'))))
    return out


def mo_year(r):
    s = r + 1950
    return f'{s}/{str(s + 1)[2:]}'


for f in sorted(glob.glob(os.path.join(RAW, 'mo', '*_k_cz080.pdf'))):
    r, cat = re.match(r'(\d+)_([abc])_k', os.path.basename(f)).groups()
    y = mo_year(int(r))
    for x in parse_mo_pdf(f):
        msk_names.setdefault(('MO', y, cat.upper()), set()).add(x['name'])
        add(competition='Matematická olympiáda', year=y, round='krajske',
            category=cat.upper(), student=initials(x['name']), school_raw=x['school'],
            town=town_of(x['school']), placement=x['placement'],
            successful=x['successful'])
for f in sorted(glob.glob(os.path.join(RAW, 'mo', '*_a_u_cz.pdf'))):
    r = int(os.path.basename(f)[:2])
    y = mo_year(r)
    known = msk_names.get(('MO', y, 'A'), set())
    for x in parse_mo_pdf(f):
        t = town_of(x['school'])
        if t or x['name'] in known:
            add(competition='Matematická olympiáda', year=y, round='ustredni',
                category='A', student=initials(x['name']), school_raw=x['school'],
                town=t, placement=x['placement'], successful=x['successful'])


# ---------------------------------------------------------------- FO (Osmo HTML)
def fo_year(r):
    s = r + 1958
    return f'{s}/{str(s + 1)[2:]}'


def osmo_tables(s):
    """Yield (kraj_or_None, list of (title, cells)) for each results table."""
    parts = re.split(r'(<h3>.*?</h3>)', s)
    kraj = None
    for p in parts:
        if p.startswith('<h3>'):
            kraj = clean(p)
            continue
        for tb in re.findall(r'<tbody>(.*?)</table>', p, re.S):
            trs = []
            for tr in re.split(r'<tr', tb)[1:]:
                title = re.search(r'title="([^"]*)"', tr.split('>')[0])
                cells = [clean(c) for c in re.split(r'<td[^>]*>', tr)[1:]]
                if len(cells) > 2 and re.match(r'\d/\d', cells[2]):
                    cells.insert(0, '')   # unranked row: no rank cell
                trs.append((title.group(1) if title else '', cells))
            yield kraj, trs


for f in sorted(glob.glob(os.path.join(RAW, 'fo', 'osmo_*-?-2.html'))):
    r, cat = re.search(r'osmo_(\d+)-([A-D])-2', f).groups()
    y = fo_year(int(r))
    for kraj, trs in osmo_tables(open(f, encoding='utf8').read()):
        if not kraj or 'Moravskoslez' not in kraj:
            continue
        rank = ''
        for title, c in trs:
            if len(c) < 4:
                continue
            rank = c[0] or (rank if title else '')
            msk_names.setdefault(('FO', y, cat), set()).add(c[1])
            add(competition='Fyzikální olympiáda', year=y, round='krajske', category=cat,
                student=initials(c[1]), school_raw=c[2], town=town_of(c[2]),
                placement=rank, successful=title in ('Vítěz', 'Úspěšný řešitel'))
for f in sorted(glob.glob(os.path.join(RAW, 'fo', 'osmo_*-A-3.html'))):
    r = int(re.search(r'osmo_(\d+)-A-3', f).group(1))
    y = fo_year(r)
    known = msk_names.get(('FO', y, 'A'), set())
    for _, trs in osmo_tables(open(f, encoding='utf8').read()):
        rank = ''
        for title, c in trs:
            if len(c) < 4:
                continue
            rank = c[0] or (rank if title else '')
            t = town_of(c[2])
            if t or c[1] in known:
                add(competition='Fyzikální olympiáda', year=y, round='ustredni', category='A',
                    student=initials(c[1]), school_raw=c[2], town=t,
                    placement=rank + (f' ({title})' if title else ''),
                    successful=title in ('Vítěz', 'Úspěšný řešitel'))


# ---------------------------------------------------------------- ChO, BiO (JSON from olympiada DB)
def db_rows(comp, folder, ok_threshold):
    for f in sorted(glob.glob(os.path.join(RAW, folder, '*.json'))):
        b = os.path.basename(f)
        m = re.match(r'(nk|kk_T)_(\d{4})_([A-E])\.json', b)
        if not m:
            continue
        kind, start, cat = m.groups()
        y = f'{start}/{str(int(start) + 1)[2:]}'
        rnd = 'ustredni' if kind == 'nk' else 'krajske'
        for r in json.load(open(f))['data']:
            if 'Moravskoslez' not in (r.get('student__profile__school__city__district__county__name') or ''):
                continue
            school = r['student__profile__school__name']
            city = r.get('student__profile__school__city__name') or ''
            pts = float(r['points'].replace(',', '.')) if r.get('points') else None
            thr = ok_threshold.get(rnd)
            add(competition=comp, year=y, round=rnd, category=cat,
                student=initials(f"{r['student__first_name']} {r['student__last_name']}"),
                school_raw=school, town=town_of(school + ' ' + city) or city,
                placement=f"{r['results__result_order']}." if r.get('results__result_order') else '',
                successful='' if thr is None or pts is None else pts >= thr)


# ChO: organizační řád — NK úspěšný řešitel >= 60 % bodů, KK >= 50 %; max assumed 100 (scaled)
db_rows('Chemická olympiáda', 'cho', {'ustredni': 60, 'krajske': 50})
# BiO: no flag in data; left blank
db_rows('Biologická olympiáda', 'bio', {})


# ---------------------------------------------------------------- Olympiáda v informatice (MO kat. P)
for f in sorted(glob.glob(os.path.join(RAW, 'inf', 'p_*_[23].html'))):
    r, k = re.search(r'p_(\d+)_(\d)', f).groups()
    y = mo_year(int(r))
    s = open(f, encoding='utf8').read()
    kraj, rank = None, ''
    for tr in re.split(r'<tr', s)[1:]:
        head = tr.split('>')[0]
        if '<th' in tr and 'colspan' in tr and k == '2':
            kraj = clean(tr.split('>', 1)[1])
            rank = ''
            continue
        cells = [clean(c) for c in re.split(r'<td[^>]*>', tr)[1:]]
        if len(cells) < 4 or not re.match(r'\d/\d', cells[3]):
            continue
        rank = cells[0] or rank
        succ = 'marked' in head or 'success' in head
        lab = ' (vítěz)' if 'marked' in head else ''
        if k == '2':
            if not kraj or 'Moravskoslez' not in kraj:
                continue
            msk_names.setdefault(('P', y), set()).add(cells[1])
            rnd = 'krajske'
        else:
            if not (town_of(cells[2]) or cells[1] in msk_names.get(('P', y), set())):
                continue
            rnd = 'ustredni'
        add(competition='Olympiáda v informatice (MO kat. P)', year=y, round=rnd, category='P',
            student=initials(cells[1]), school_raw=cells[2], town=town_of(cells[2]),
            placement=(rank + lab) if succ else '', successful=succ)


# ---------------------------------------------------------------- SOČ (PDF booklets)
for f in sorted(glob.glob(os.path.join(RAW, 'soc', 'vl_*.pdf'))):
    yy = re.search(r'vl_(\d{4})-(\d{2})', f)
    y = f'{yy.group(1)}/{yy.group(2)}'
    lines = [re.sub(r'\s+', ' ', re.sub(r'[\x00-\x1f]', ' ', l)).strip() for l in pdftext(f).splitlines()]
    obor, obor_no, rec, field = '', 0, None, None
    recs = []
    for l in lines:
        mo = re.match(r'^(\d{1,2})\s+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ].{3,})$', l)
        if mo and int(mo.group(1)) == obor_no + 1 and 'místo' not in l:
            obor_no = int(mo.group(1))
            obor = f'{obor_no} {mo.group(2).strip().capitalize()}'
            continue
        mp = re.match(r'^(\d+)\.\s*místo$', l)
        if mp or re.match(r'^(Host mimo pořadí|Nedostavil|Bez umístění|Mimo soutěž)', l):
            rec = {'place': mp.group(1) + '.' if mp else None, 'obor': obor}
            recs.append(rec)
            field = None
            continue
        if rec is None:
            continue
        mf = re.match(r'^(Název práce|Autor|Autoři|Autorka|Škola|Kraj|Video|Zvláštní cena|Cena)\b:?\s*(.*)$', l)
        if mf:
            field = mf.group(1)
            if field in ('Autor', 'Autoři', 'Autorka', 'Škola', 'Kraj'):
                rec[field] = mf.group(2).strip()
            continue
        if field == 'Škola' and l and not rec.get('Kraj'):
            rec['Škola'] = (rec.get('Škola', '') + ' ' + l).strip()
        elif field in ('Autor', 'Autoři', 'Autorka', 'Kraj') and l and not rec.get(field):
            rec[field] = l
    for rec in recs:
        if 'Moravskoslez' not in rec.get('Kraj', '') or not rec['place']:
            continue
        authors = rec.get('Autor') or rec.get('Autoři') or rec.get('Autorka') or ''
        names = [a for a in re.split(r',| a ', authors) if a.strip()]
        add(competition='SOČ', year=y, round='ustredni', category=rec['obor'],
            student=' + '.join(initials(a) for a in names), school_raw=rec.get('Škola', ''),
            town=town_of(rec.get('Škola', '')), placement=rec['place'],
            successful=int(rec['place'][:-1]) <= 3,
            team='team' if len(names) > 1 else 'individual')


# ---------------------------------------------------------------- merge rows from other collectors
for f in sorted(glob.glob(os.path.join(RAW, '*', 'rows_msk.csv'))):
    with open(f, encoding='utf8') as fh:
        for r in csv.DictReader(fh):
            add(**{k: r.get(k, '') for k in FIELDS})

for r in rows:
    if isinstance(r['successful'], bool):
        r['successful'] = 'true' if r['successful'] else 'false'

with open(OUT, 'w', newline='', encoding='utf8') as fh:
    w = csv.DictWriter(fh, FIELDS)
    w.writeheader()
    w.writerows(rows)

from collections import Counter
c = Counter((r['competition'], r['round'], r['year']) for r in rows)
for k in sorted(c):
    print(*k, c[k], sep='\t')
print('total', len(rows), '->', OUT)
