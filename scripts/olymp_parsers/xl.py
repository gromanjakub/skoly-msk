# minimal stdlib xlsx reader
import zipfile,re,sys,xml.etree.ElementTree as ET
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def col2n(c):
    n=0
    for ch in c: n=n*26+ord(ch)-64
    return n-1
def sheets(path):
    z=zipfile.ZipFile(path)
    wb=ET.fromstring(z.read('xl/workbook.xml'))
    rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rm={r.get('Id'):r.get('Target') for r in rels}
    out=[]
    for s in wb.find('m:sheets',NS):
        t=rm[s.get('{%s}id'%NS['r'])]; t=t.lstrip('/'); t=t if t.startswith('xl/') else 'xl/'+t
        out.append((s.get('name'),t))
    return z,out
def read(path,sheet=None,maxrows=None):
    z,sh=sheets(path)
    ss=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t'%NS['m'])))
    name,t=sh[0] if sheet is None else [x for x in sh if x[0]==sheet or str(sheet)==x[0]][0]
    rows=[]
    for ev,el in ET.iterparse(z.open(t)):
        if el.tag=='{%s}row'%NS['m']:
            r={}
            for c in el.findall('m:c',NS):
                ref=re.match(r'[A-Z]+',c.get('r')).group(0); v=c.find('m:v',NS); typ=c.get('t')
                if typ=='inlineStr': val=''.join(x.text or '' for x in c.iter('{%s}t'%NS['m']))
                elif v is None: val=''
                elif typ=='s': val=ss[int(v.text)]
                else: val=v.text
                r[col2n(ref)]=val
            rows.append([r.get(i,'') for i in range(max(r)+1)] if r else [])
            el.clear()
            if maxrows and len(rows)>=maxrows: break
    return rows
if __name__=='__main__':
    p=sys.argv[1]; z,sh=sheets(p); print('SHEETS',[s[0] for s in sh])
    for s,_ in sh:
        rows=read(p,s,maxrows=int(sys.argv[2]) if len(sys.argv)>2 else 6)
        print('--',s); [print(r) for r in rows]
