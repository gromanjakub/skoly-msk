import re, csv
L = r'[A-Za-zÀ-žÁ-ž]'
NB = r'(?<![A-Za-zÀ-ž])'
NA = r'(?![A-Za-zÀ-ž])'
TOWNS = [
 ('Frýdek-Místek', r'Frýd(?:ek|ku)\s*-?\s*Míst(?:ek|ku)'),
 ('Frýdlant nad Ostravicí', r'Frýdlant(?:u|ě)?\s*n(?:ad|\.)\s*O'),
 ('Ostrava', r'Ostrav(?:a|ě|y|u)'),
 ('Opava', r'Opav(?:a|ě|y|u)'),
 ('Karviná', r'Karvin(?:á|é|ou)'),
 ('Havířov', r'Havířov(?:a|ě)?'),
 ('Nový Jičín', r'Nov(?:ý|ém|ého)\s+Jičín(?:ě|a)?'),
 ('Třinec', r'Třin(?:ec|ci|ce)'),
 ('Český Těšín', r'Česk(?:ý|ém|ého)\s+Těšín(?:ě|a)?'),
 ('Bílovec', r'Bílov(?:ec|ci|ce)'),
 ('Kopřivnice', r'Kopřivnic(?:e|i)'),
 ('Frenštát pod Radhoštěm', r'Frenštát(?:u|ě)?'),
 ('Bruntál', r'Bruntál(?:e|u)?'),
 ('Krnov', r'Krnov(?:ě|a)?'),
 ('Orlová', r'Orlov(?:á|é)'),
 ('Bohumín', r'Bohumín(?:ě|a)?'),
 ('Příbor', r'Příbo(?:r|ře|ru)'),
 ('Hlučín', r'Hlučín(?:ě|a)?'),
 ('Studénka', r'Studénk(?:a|ce|y)'),
 ('Odry', r'Odr(?:y|ách)'),
 ('Rýmařov', r'Rýmařov(?:ě|a)?'),
 ('Vítkov', r'Vítkov(?:ě|a)?'),
 ('Fulnek', r'Fulnek(?:u)?'),
 ('Kravaře', r'Kravař(?:e|ích)'),
 ('Jablunkov', r'Jablunkov(?:ě|a)?'),
 ('Klimkovice', r'Klimkovic(?:e|ích)'),
 ('Petřvald', r'Petřvald(?:u|ě)?'),
 ('Rychvald', r'Rychvald(?:u|ě)?'),
 ('Šenov', r'Šenov(?:ě|a)?'),
 ('Vratimov', r'Vratimov(?:ě|a)?'),
 ('Štramberk', r'Štramber(?:k|ku)'),
 ('Hradec nad Moravicí', r'Hradec\s+nad\s+Moravicí'),
 ('Dolní Benešov', r'Doln(?:í|ím)\s+Benešov'),
 ('Brušperk', r'Brušper(?:k|ku)'),
 ('Paskov', r'Paskov(?:ě|a)?'),
 ('Spálov', r'Spálov(?:ě|a)?'),
 ('Město Albrechtice', r'Město\s+Albrechtice'),
 ('Budišov nad Budišovkou', r'Budišov\s+nad\s+Budišovkou'),
 ('Horní Suchá', r'Horní\s+Suchá'),
 ('Vrbno pod Pradědem', r'Vrbno\s+pod\s+Pradědem'),
 ('Bystřice (nad Olší)', r'Bystřice\s+n(?:ad|\.)\s*Olší'),
]
TRE = [(t, re.compile(NB + p + NA, re.I)) for t, p in TOWNS]
PSC = re.compile(r'(?<!\d)(7[0-4]\d|79[2-5])\s?(\d{2})(?!\d|[,.]\d)')
# schools that are known MSK but often printed without a town
KNOWN = [('Wichterlovo gymn', 'Ostrava'), ('Moravskoslezská obchodní akademie', 'Ostrava'), ('Matiční gymn', 'Ostrava'), ('PRIGO', 'Ostrava'),
         ('Mendelovo gymn', 'Opava'), ('Slezské gymn', 'Opava'), ('Polské gymn', 'Český Těšín')]

def msk_town(text, kraj=None):
    if kraj and 'oravskoslez' in kraj:
        for t, r in TRE:
            if r.search(text): return t
        for k, t in KNOWN:
            if k.lower() in text.lower(): return t
        return '?(kraj=MSK)'
    for t, r in TRE:
        if r.search(text): return t
    m = PSC.search(text)
    if m: return 'PSČ %s %s' % m.groups()
    for k, t in KNOWN:
        if k.lower() in text.lower() and 'vsetín' not in text.lower(): return t
    return None

def initials(first, last):
    f = (first or '').strip(); l = (last or '').strip()
    if not f or not l: return ''
    return f[0] + '.' + l[0] + '.'

HEADER = ['competition','year','round','category','student','school_raw','town','placement','successful','team']
def write(path, rows):
    with open(path, 'w', newline='', encoding='utf8') as fh:
        w = csv.writer(fh); w.writerow(HEADER)
        for r in rows: w.writerow([r.get(k, '') for k in HEADER])
    print(path, len(rows))
