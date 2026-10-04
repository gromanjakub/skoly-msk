import sys, re, os, subprocess
sys.path.insert(0, os.path.dirname(__file__)); from msk import *
D='/home/jakub/Documents/1personal_random/skoly-msk/data/raw/olymp/zo'
NUM=r'\d+(?:[.,]\d+)?'
ROW=re.compile(r'^(?P<pre>\s*\S.*?)\s+(?P<nums>(?:'+NUM+r'\s+){5})(?P<rank>\d{1,2})(?:\s+(?P<rest>\S.*))?$')
KRAJE=['Hlavní město Praha','Praha','Středočeský','Jihočeský','Plzeňský','Karlovarský','Ústecký','Liberecký','Královéhradecký','Pardubický','Kraj Vysočina','Vysočina','Jihomoravský','Olomoucký','Zlínský','Moravskoslezský']
rows=[]
for y,order in [('2021-22','LF'),('2022-23','LF'),('2023-24','LF'),('2024-25','LF'),('2025-26','FL')]:
    lines=subprocess.run(['pdftotext','-layout',f'{D}/ck_{y}.pdf','-'],capture_output=True,text=True).stdout.splitlines()
    cat=None; recs=[]  # each: dict(idx, cat, pre, rank, rest)
    kind=[]  # per line: 'row', 'orphan', 'blank', 'hdr'
    for i,l in enumerate(lines):
        m=re.search(r'KATEGORIE\s+([A-D])',l)
        if m: cat=m.group(1); kind.append(('hdr',None)); continue
        m=ROW.match(l)
        if m and cat:
            recs.append(dict(i=i,cat=cat,pre=m['pre'].strip(),rank=m['rank'],rest=(m['rest'] or '').strip(),extra=[]))
            kind.append(('row',len(recs)-1)); continue
        if not l.strip(): kind.append(('blank',None)); continue
        if re.search(r'JMÉNO|PŘÍJMENÍ|ATLASEM|TERÉN|VÝSLEDK|Výsledková|Praha \d|TEST',l): kind.append(('hdr',None)); continue
        kind.append(('orphan',None))
    # attach orphan lines (text far right = school wrap; text far left = name wrap)
    def near(i,step):
        j=i+step
        while 0<=j<len(kind) and kind[j][0]=='blank': j+=step
        return j if 0<=j<len(kind) else None
    for i,(k,_) in enumerate(kind):
        if k!='orphan': continue
        l=lines[i]; indent=len(l)-len(l.lstrip())
        if indent<30: continue   # wrapped student name, ignore
        up=near(i,-1); dn=near(i,1)
        cu = kind[up][1] if up is not None and kind[up][0]=='row' else None
        cd = kind[dn][1] if dn is not None and kind[dn][0]=='row' else None
        # orphan directly above a row whose school is empty/short -> belongs below; else above
        if cd is not None and (cu is None or not recs[cd]['rest'] or (up is not None and kind[up][0]=='orphan')):
            recs[cd]['extra'].append(('pre',l.strip()))
        elif cu is not None:
            recs[cu]['extra'].append(('post',l.strip()))
        elif cd is not None:
            recs[cd]['extra'].append(('pre',l.strip()))
        else:
            # chain of orphans above/below: find nearest row in either direction
            j=near(i,1)
            while j is not None and kind[j][0]=='orphan': j=near(j,1)
            if j is not None and kind[j][0]=='row': recs[kind[j][1]]['extra'].append(('pre',l.strip()))
    for r in recs:
        rest=r['rest']; kraj=''
        for k in KRAJE:
            if rest.startswith(k):
                kraj=k; rest=rest[len(k):].strip(); break
        pre=[t for s,t in r['extra'] if s=='pre']; post=[t for s,t in r['extra'] if s=='post']
        school=' '.join(pre+[rest]+post).strip()
        town=msk_town(school, 'Moravskoslezský' if kraj=='Moravskoslezský' else None)
        if not town: continue
        toks=r['pre'].split()
        st=''
        if len(toks)==2:
            f,l2=(toks[1],toks[0]) if order=='LF' else (toks[0],toks[1]); st=initials(f,l2)
        rk=int(r['rank'])
        rows.append(dict(competition='Zeměpisná (Geografická) olympiáda',year=y.replace('-','/'),round='ustredni',
            category=r['cat']+(' (8.–9. tř. ZŠ / tercie–kvarta)' if r['cat']=='C' else ' (SŠ)'),student=st,school_raw=school,
            town=town,placement=r['rank']+'.',successful=str(rk<=3).lower(),team='individual'))
    for c in 'CD':
        rk=sorted(int(r['rank']) for r in recs if r['cat']==c)
        miss=sorted(set(range(1,max(rk)+1))-set(rk)) if rk else []
        print(y,c,len(rk),'max',max(rk) if rk else 0,'missing',miss)
write(D+'/rows_msk.csv',rows)
