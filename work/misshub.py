import sys,json,csv; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); fam={r['id']:r['family'] for r in csv.DictReader(open('research/generator/scored_family.csv'))}
H={}
for l in open('work/hubs_all.txt'):
    x=l.split(); H[x[0]]=[(int(a),int(b),float(c)) for a,b,c in (t.split(':') for t in x[1:])]
rows=[]
for pid,pz in P.items():
    if fam.get(pid) in ('independent','tiny'): continue
    strong=[h for h,c,z in H.get(pid,[]) if z>=8]
    if not strong: rows.append((pid,fam[pid],0,0,0)); continue
    prog=json.loads((BEST/f'{pid}.json').read_text()); R=[None]*48; V=set()
    for k,v in enumerate(pz['starts']): R[k]=v
    for op,i,j,d in prog:
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; V.add(c)
    have=sum(1 for h in strong if any(v%h==0 and v//h<64 for v in V if h<=v<h*64))
    rows.append((pid,fam[pid],len(strong),have,len(prog)))
import collections
c=collections.Counter((r[1],r[2]>0,r[2]-r[3]) for r in rows)
for k in sorted(c): print(k,c[k])
miss=[r for r in rows if r[2]>=2 and r[3]<=r[2]-2]
print('puzzles with >=2 strong hubs missing:',len(miss),'instr',sum(r[4] for r in miss))
open('work/p_missing_hubs.txt','w').write('\n'.join(r[0] for r in miss))
