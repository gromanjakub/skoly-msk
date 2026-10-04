import sys, re, html, os
sys.path.insert(0, os.path.dirname(__file__)); from msk import *
D='/home/jakub/Documents/1personal_random/skoly-msk/data/raw/olymp/eko'
def cells(tr): return [re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',x))).strip() for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',tr,re.S)]
rows=[]
for f,y in [('rocnik_vii_2022-23.html','2022/23'),('rocnik_viii_2023-24.html','2023/24'),('rocnik_ix_2024-25.html','2024/25'),('rocnik_x_2025-26.html','2025/26')]:
    s=open(f'{D}/{f}',encoding='utf8').read()
    tables=[[cells(tr) for tr in re.findall(r'<tr.*?</tr>',t,re.S)] for t in re.findall(r'<table.*?</table>',s,re.S)]
    # roster with kraj (Jméno, Příjmení, Škola, Kraj)
    roster={}
    for t in tables:
        if t and t[0][:2]==['Jméno','Příjmení']:
            for c in t[1:]:
                if len(c)>=4: roster[(c[0],c[1])]=(c[2],c[3])
    res=tables[0]; n=0
    for c in res:
        if len(c)<4 or not re.match(r'^\d+\.',c[0]): continue
        n+=1
        if len(c)>=5 and 'kraj' in c[1].lower() or (len(c)>=5 and c[1].startswith('Hlavní')):
            rank,kraj,school,first,sur=c[:5]; school2=''
        else:
            rank,sur,first,school=c[:4]; school2,kraj=roster.get((first,sur),('',''))
        text=school+' | '+school2
        t=msk_town(text,kraj)
        if not t: continue
        r=int(re.match(r'\d+',rank).group())
        raw=school if not school2 or school2==school else f'{school} [roster: {school2}]'
        rows.append(dict(competition='Ekonomická olympiáda',year=y,round='ustredni',category='SŠ',
            student=initials(first,sur),school_raw=raw,town=t,placement=rank,successful=str(r<=3).lower(),team='individual'))
    print(y,n,'finalists; roster',len(roster))
write(D+'/rows_msk.csv',rows)
