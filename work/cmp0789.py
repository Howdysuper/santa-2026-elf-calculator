import sys,json; sys.path.insert(0,'src')
from elf import load
P=load(); pid=sys.argv[1]; pz=P[pid]; T=set(pz['targets'])
def run(prog):
    R=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    out=[]
    for op,i,j,d in prog:
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; out.append((op,a,b,c))
    return out
for f in ['best_backup_141363','best']:
    prog=json.load(open(f'{f}/{pid}.json')); o=run(prog)
    first=next(n for n,x in enumerate(o) if x[3] in T)
    print('==',f,len(prog),'first target at',first, 'starts',pz['starts'])
    print(' scaffold:',' '.join(f"{a}{op}{b}={c}" for op,a,b,c in o[:first]))
    nbig=[c for op,a,b,c in o if c not in T and c>=1<<16]
    print(' big non-target values',len(nbig))
