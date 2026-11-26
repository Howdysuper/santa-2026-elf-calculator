import sys,json,math,itertools; sys.path.insert(0,'src')
from elf import load,BEST
sys.argv=['x']
exec(open('work/decomp.py',encoding='utf-8').read().split('for pid in sys.argv[1:]:')[0])
rows=[]
for pid,pz in sorted(P.items()):
    prog=json.loads((BEST/f"{pid}.json").read_text())
    A,_=atoms(pz,values(pz,prog))
    good=0; nt=len(pz['targets'])
    for t in pz['targets']:
        b=decomp(t,A[:6],2) if A else None
        if b and b[0]<=30: good+=1
    rows.append((pid,max(pz['starts'])>=100,len(prog),nt,good,len(A),round(math.log2(max(pz['targets'])),1)))
with open('work/struct_fit.csv','w') as f:
    f.write('pid,indep,len,nt,good,natoms,bits\n')
    for r in rows: f.write(','.join(map(str,r))+'\n')
import collections
c=collections.Counter()
for r in rows:
    fr=r[4]/r[3]; k=('I' if r[1] else 'S', 'fit>=.8' if fr>=.8 else 'fit.4-.8' if fr>=.4 else 'fit<.4')
    c[k+('n',)]+=1; c[k+('len',)]+=r[2]; c[k+('nt',)]+=r[3]
for k in sorted({x[:2] for x in c}): print(k, c[k+('n',)], c[k+('len',)], round(c[k+('len',)]/c[k+('nt',)],2))
