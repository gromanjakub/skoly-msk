#!/usr/bin/env python3
"""Build the school_raw -> RED_IZO lookup for olympiad results and the matched results file.

In:  data/olymp_msk.csv, data/msk_schools.csv, data/olymp_school_overrides.csv (optional, manual)
Out: data/olymp_school_lookup.csv  school_raw, town, red_izo, method, confidence, note
     data/olymp_msk_matched.csv    olymp_msk.csv + red_izo + source_quality

Methods: auto_exact (normalised name equals register full/short name), auto_fuzzy (token overlap
within town, with school-type and Ostrava-district filters), manual (row in the overrides file).
Only high/med matches get a red_izo; low ones keep the candidate in `note` for review.
Prints only aggregate numbers (school_raw can contain names of people; don't dump it).
"""
import csv, os, re, unicodedata, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, 'data', *p)

ABBR = {'g': 'gymnazium', 'gym': 'gymnazium', 'sps': 'stredni prumyslova skola',
        'sos': 'stredni odborna skola', 'ss': 'stredni skola', 'oa': 'obchodni akademie',
        'zs': 'zakladni skola', 'ms': 'materska skola', 'vos': 'vyssi odborna skola',
        'spsei': 'stredni prumyslova skola elektrotechniky informatiky',
        'sszs': 'stredni zdravotnicka skola', 'szs': 'stredni zdravotnicka skola',
        'sspu': 'stredni skola prumyslova umelecka', 'sou': 'stredni odborne uciliste',
        'spgs': 'stredni pedagogicka skola', 'msoa': 'moravskoslezska obchodni akademie',
        'eltech': 'elektrotechniky', 'inf': 'informatiky', 'chem': 'chemicka', 'stav': 'stavebni',
        'zdrav': 'zdravotnicka', 'prum': 'prumyslova', 'gymn': 'gymnazium', 'akad': 'akademika',
        'fr': 'frantiska', 'mikul': 'mikulase', 'soukr': 'soukrome', 'ped': 'pedagogicka'}
STOP = {'a', 'v', 've', 'na', 'nad', 'pod', 'p', 'o', 'prispevkova', 'organizace', 's', 'r', 'ops',
        'pravem', 'statni', 'jazykove', 'zkousky', 'skola', 'stredni', 'jazykova', 'cs', 'u', 'z',
        'spol', 'sro', 'im', 'okres', 'kraj', 'moravskoslezsky', 'psc', 'ulice', 'cr', 'czech', 'republic'}
OSTRAVA_PARTS = {'poruba', 'zabreh', 'hrabuvka', 'vitkovice', 'mariánske', 'marianske', 'hory',
                 'slezska', 'moravska', 'hulvaky', 'michalkovice', 'koblov', 'kuncicky', 'privoz',
                 'dubina', 'belsky', 'mar'}
TYPE_WORDS = ('gymnazium', 'lyceum', 'stredni', 'akademie', 'uciliste', 'prumyslova', 'odborna',
              'hotelova', 'zdravotnicka', 'umelecka', 'konzervator', 'obchodni')


def fold(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def toks(s, keep_stop=False):
    s = re.sub(r'\d+[/\d]*\w?', ' ', fold(s))
    out = []
    for t in re.findall(r'[a-z]+', s):
        out += ABBR.get(t, t).split()
    return [t for t in out if (keep_stop or t not in STOP) and len(t) > 1]


def exact_key(s):
    return ' '.join(toks(s, keep_stop=True))


reg = list(csv.DictReader(open(D('msk_schools.csv'), encoding='utf8')))
for r in reg:
    r['_t'] = set(toks(' '.join([r['nazev'], r['zkraceny_nazev'], r['adresa'], r['cast_obce'] or ''])))
    r['_name_t'] = set(toks(r['nazev'] + ' ' + r['zkraceny_nazev']))
    r['_towns'] = {fold(r['obec'])} | {fold(x.strip()) for x in (r['obce_mist_vyuky'] or '').split(';') if x.strip()}
    r['_gym'] = any(r[c] == '1' for c in ('has_gym8', 'has_gym6', 'has_gym4')) or 'gymnazium' in r['_name_t']
    r['_generic_gym'] = fold(r['nazev']).startswith('gymnazium,')
    r['_secondary'] = r['has_maturita'] == '1' or r['has_vyucni'] == '1'
EXACT = {}
for r in reg:
    for n in (r['nazev'], r['zkraceny_nazev']):
        EXACT.setdefault(exact_key(n), set()).add(r['red_izo'])
ALL_TOWNS = set().union(*(r['_towns'] for r in reg))
BYID = {r['red_izo']: r for r in reg}


def town_key(town):
    t = fold(town).replace('?', '').strip()
    return t


def candidates(town):
    t = town_key(town)
    if not t:
        return []
    base = t.split('-')[0].strip() if t.startswith('ostrava') else t
    return [r for r in reg if any(base == x or x.startswith(base + ' ') or base.startswith(x) for x in r['_towns'])]


def is_zs(raw_t):
    s = set(raw_t)
    zs = 'zakladni' in s
    secondary = bool(s & {'gymnazium', 'lyceum', 'akademie', 'uciliste', 'prumyslova', 'odborna', 'stredni'})
    return zs and not secondary


def score(raw_t, r):
    # a raw token counts if it is in the register tokens, or is a >=3-letter prefix of one
    # (PDF names are cut off / abbreviated: "Heyrovského, Os . . .", "eltech.")
    t = set(raw_t)
    hit = sum(1 for x in t if x in r['_t'] or (len(x) >= 3 and any(y.startswith(x) for y in r['_t'])))
    return hit / max(1, len(t))


def match(raw, town):
    raw_t = toks(raw)
    k = exact_key(raw)
    if k in EXACT and len(EXACT[k]) == 1:
        return next(iter(EXACT[k])), 'auto_exact', 'high', ''
    if is_zs(raw_t):
        return '', 'auto_fuzzy', 'high', 'ZŠ'
    cands = candidates(town)
    if not cands:
        if town_key(town) and not any(town_key(town).split()[0] in x for x in ALL_TOWNS):
            return '', 'auto_fuzzy', 'med', 'mimo MSK (obec mimo rejstřík MSK)'
        cands = reg  # no usable town -> whole register
    rt = set(raw_t)
    # school-type filter: "gymnazium" in raw -> only schools that teach a gymnázium obor
    if 'gymnazium' in rt:
        f = [r for r in cands if r['_gym']]
        cands = f or cands
    # Ostrava district filter
    parts = rt & OSTRAVA_PARTS
    if parts:
        f = [r for r in cands if parts & set(toks(r['cast_obce'] + ' ' + r['nazev']))]
        cands = f or cands
    sc = sorted(((score(raw_t, r), r) for r in cands), key=lambda x: -x[0])
    distinctive = rt - {'gymnazium'} - set(toks(town)) - OSTRAVA_PARTS
    if 'gymnazium' in rt and not distinctive:
        gen = [r for r in cands if r['_generic_gym']]
        if len(gen) == 1:
            return gen[0]['red_izo'], 'auto_fuzzy', 'med', 'generický „G, obec" → Gymnázium, obec'
    if not sc:
        return '', 'auto_fuzzy', 'low', 'bez kandidáta'
    best = sc[0]
    second = sc[1][0] if len(sc) > 1 else 0
    if best[0] >= 0.6 and best[0] - second >= 0.2:
        conf = 'high'
    elif best[0] >= 0.5 and best[0] - second >= 0.15:
        conf = 'med'
    elif len(sc) == 1 and best[0] >= 0.3:
        conf = 'med'
    else:
        # tie-break among the near-best: reverse coverage = share of the register name's
        # distinctive tokens that appear in the raw name ("Sportovní" G at the same street loses
        # to plain "G ..., Volgogradská" because 'sportovni', 'zatopkovych' are missing)
        top = [r for s_, r in sc if s_ >= best[0] - 0.05 and s_ >= 0.4]
        if len(top) > 1:
            rt_all = set(raw_t) | {y for y in (rr for r in top for rr in r['_name_t'])
                                    if any(len(x) >= 3 and y.startswith(x) for x in raw_t)}
            def cov(r):
                dist = r['_name_t'] - set(toks(r['obec'])) - set(TYPE_WORDS) - {'gymnazium', 'skola'}
                return len(dist & rt_all) / len(dist) if dist else 0.0
            cs = sorted(((cov(r), r) for r in top), key=lambda x: -x[0])
            if cs[0][0] - cs[1][0] >= 0.3:
                return cs[0][1]['red_izo'], 'auto_fuzzy', 'med', \
                    f'remíza skóre {best[0]:.2f}, rozhodlo pokrytí názvu {cs[0][0]:.2f} vs {cs[1][0]:.2f}'
        return '', 'auto_fuzzy', 'low', f'kandidát {best[1]["red_izo"]} (skóre {best[0]:.2f}, druhý {second:.2f})'
    note = '' if conf == 'high' else f'skóre {best[0]:.2f}, druhý {second:.2f}'
    return best[1]['red_izo'], 'auto_fuzzy', conf, note


def main():
    rows = list(csv.DictReader(open(D('olymp_msk.csv'), encoding='utf8')))
    pairs = collections.OrderedDict()
    for r in rows:
        pairs.setdefault((r['school_raw'], r['town']), 0)
        pairs[(r['school_raw'], r['town'])] += 1
    overrides = {}
    if os.path.exists(D('olymp_school_overrides.csv')):
        for o in csv.DictReader(open(D('olymp_school_overrides.csv'), encoding='utf8')):
            overrides[(o['school_raw'], o['town'])] = o
    lookup = []
    for (raw, town), n in pairs.items():
        if (raw, town) in overrides:
            o = overrides[(raw, town)]
            rec = dict(school_raw=raw, town=town, red_izo=o['red_izo'], method='manual',
                       confidence=o.get('confidence') or 'high', note=o.get('note', ''))
        else:
            rid, method, conf, note = match(raw, town)
            rec = dict(school_raw=raw, town=town, red_izo=rid, method=method, confidence=conf, note=note)
        rec['_n'] = n
        lookup.append(rec)
    cols = ['school_raw', 'town', 'red_izo', 'method', 'confidence', 'note']
    with open(D('olymp_school_lookup.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, cols, extrasaction='ignore'); w.writeheader()
        w.writerows(sorted(lookup, key=lambda x: (-x['_n'], x['school_raw'])))

    lk = {(x['school_raw'], x['town']): x for x in lookup}
    LANG = ('Olympiáda v anglickém', 'Olympiáda v německém', 'Olympiáda ve francouzském',
            'Olympiáda ve španělském', 'Olympiáda v ruském')
    out_cols = list(rows[0].keys()) + ['red_izo', 'source_quality']
    for r in rows:
        r['red_izo'] = lk[(r['school_raw'], r['town'])]['red_izo']
        r['source_quality'] = 'transcribed' if (r['competition'].startswith(LANG) and r['year'] in ('2023/24', '2024/25')) else 'parsed'
    with open(D('olymp_msk_matched.csv'), 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, out_cols); w.writeheader(); w.writerows(rows)

    # aggregate report only
    c = collections.Counter((x['method'], x['confidence'], bool(x['red_izo'])) for x in lookup)
    print('distinct school_raw x town:', len(lookup))
    for k, v in sorted(c.items()): print('  ', k, v)
    notes = collections.Counter(x['note'].split(' (')[0] if x['note'] in ('ZŠ',) or x['note'].startswith('mimo') else '' for x in lookup)
    print('  special notes:', {k: v for k, v in notes.items() if k})
    tot = collections.Counter(); hit = collections.Counter(); excl = collections.Counter()
    for r in rows:
        tot[r['competition']] += 1
        l = lk[(r['school_raw'], r['town'])]
        if r['red_izo']: hit[r['competition']] += 1
        elif l['note'] == 'ZŠ' or l['note'].startswith('mimo'): excl[r['competition']] += 1
    print(f'{"competition":45s} rows matched  ZŠ/mimo  unresolved')
    for k in sorted(tot):
        print(f'{k:45s} {tot[k]:4d} {hit[k]:4d} {100*hit[k]/tot[k]:5.1f}%  {excl[k]:3d}  {tot[k]-hit[k]-excl[k]:3d}')
    T, H, E = sum(tot.values()), sum(hit.values()), sum(excl.values())
    print(f'{"TOTAL":45s} {T:4d} {H:4d} {100*H/T:5.1f}%  {E:3d}  {T-H-E:3d}')
    print('source_quality:', collections.Counter(r['source_quality'] for r in rows))


if __name__ == '__main__':
    main()
