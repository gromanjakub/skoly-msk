import sys, re, os, subprocess
sys.path.insert(0, os.path.dirname(__file__)); from msk import *
D='/home/jakub/Documents/1personal_random/skoly-msk/data/raw/olymp/do'
NUMS=re.compile(r'((?:\s+(?:\d+(?:,\d+)?|nemoc)){3,})\s+(?=\S)')
TITLE=re.compile(r'^(Mgr|PhDr|PaedDr|PaeDr|Bc|Ing|RNDr|Dr|doc|prof|ThDr|JUDr|MgA)\b',re.I)
rows=[]
for y,f in [('2023/24','uk_2023-24_kat2'),('2024/25','uk_2024-25_kat2')]:
    lines=subprocess.run(['pdftotext','-layout',f'{D}/{f}.pdf','-'],capture_output=True,text=True).stdout.splitlines()
    recs=[]; cur=None
    for l in lines:
        if re.search(r'V Hradci Králové dne|Maximálně bylo',l): cur=None; continue
        m=NUMS.search(l)
        if m and re.match(r'^\s*(\d+\.|[A-ZÁ-Ž])',l) and not re.search(r'Pořadí|celkem',l):
            sc=m.end()
            head=l[:m.start()]
            rm=re.match(r'^\s*(\d+\.(?:\s*–)?)?\s*(.*)$',head)
            cur=dict(rank=(rm.group(1) or '').strip(),name=[rm.group(2).strip()],school=[l[sc:].strip()],col=sc,stop=False)
            recs.append(cur); continue
        if cur is None or not l.strip(): continue
        ind=len(l)-len(l.lstrip())
        if ind>=cur['col']-4:
            t=l.strip()
            if TITLE.match(t): cur['stop']=True
            if not cur['stop']: cur['school'].append(t)
        else:
            left=l[:cur['col']-4].strip(); right=l[cur['col']-4:].strip()
            if re.fullmatch(r'\d+\.',left.split()[0] if left else ''):
                cur['rank']+=' '+left.split()[0]; left=' '.join(left.split()[1:])
            if left: cur['name'].append(left)
            if right:
                if TITLE.match(right): cur['stop']=True
                if not cur['stop']: cur['school'].append(right)
    lastrank=''
    for r in recs:
        if r['rank']: lastrank=r['rank']
        school=re.sub(r'\s+',' ',' '.join(r['school'])).replace('- ','-').strip()
        town=msk_town(school)
        if not town: continue
        toks=' '.join(r['name']).split()
        st=initials(toks[0],toks[-1]) if len(toks)>=2 else ''
        rk=re.sub(r'\s+','',lastrank)
        n=int(re.match(r'\d+',rk).group())
        rows.append(dict(competition='Dějepisná olympiáda',year=y,round='ustredni',category='II. kategorie (SŠ)',student=st,
            school_raw=school,town=town,placement=rk,successful=str(n<=3).lower(),team='individual'))
    print(y,len(recs),'records')
write(D+'/rows_msk.csv',rows)
