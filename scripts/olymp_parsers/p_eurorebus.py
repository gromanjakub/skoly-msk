import sys, re, subprocess, glob, os
sys.path.insert(0, os.path.dirname(__file__)); from msk import *
D='/home/jakub/Documents/1personal_random/skoly-msk/data/raw/olymp/eurorebus'
rows=[]; stats={}
for f in sorted(glob.glob(D+'/finale_*_*.pdf')):
    m=re.search(r'finale_(\d{4})-(\d\d)_(\w+)\.pdf',f); y=f'{m[1]}/{m[2]}'; kind=m[3]
    if kind not in ('soutez_skol','tridy_SS'): continue
    txt=subprocess.run(['pdftotext','-layout',f,'-'],capture_output=True,text=True).stdout
    n=0
    for line in txt.splitlines():
        c=re.split(r'\s{2,}',line.strip())
        if not c or not re.fullmatch(r'\d+\.',c[0]): continue
        n+=1
        if kind=='soutez_skol':
            if len(c)<5: print('WARN',f,c); continue
            rank,pts,school,street,town=c[0],c[1],c[2],c[3],c[-1]; cls=''
        else:
            if len(c)<6: print('WARN',f,c); continue
            rank,pts,cls,school,street,town=c[0],c[1],c[2],c[3],c[4],c[-1]
        psc=''
        if re.fullmatch(r'\d{5}',town) and len(c)>=(6 if kind=='soutez_skol' else 7):
            psc=town; town=c[-2]
        t=msk_town(town+' '+psc)
        if not t: continue
        if t.startswith('PSČ'): t=town+' (by PSČ)'
        r=int(rank.rstrip('.'))
        rows.append(dict(competition='Eurorebus',year=y,round='ustredni',
            category=('soutez skol (ZS+SS)' if kind=='soutez_skol' else 'soutez trid SS'+(f' [{cls}]' if cls else '')),
            student='',school_raw=f'{school}, {street}, {town}'+(f' {psc}' if psc else ''),town=t,placement=rank,
            successful=str(r<=3).lower(),team='team'))
    stats[(y,kind)]=n
print(stats)
write(D+'/rows_msk.csv',rows)
