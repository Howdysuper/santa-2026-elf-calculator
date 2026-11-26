import sys,json; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); pid=sys.argv[1]; pz=P[pid]; T=set(pz['targets'])
def parse(fn):
    for l in open(fn):
        x=l.split()
        if x[0]==pid:
            n=int(x[1]); return [[x[2+4*k],int(x[3+4*k]),int(x[4+4*k]),int(x[5+4*k])] for k in range(n)]
def run(prog):
    R=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    out=[]
    for op,i,j,d in prog:
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; out.append((op,a,b,c))
    return out
for name,prog in [('old',parse('work/cur5/programs.txt')),('new',json.loads((BEST/f'{pid}.json').read_text()))]:
    o=run(prog); first=next(n for n,x in enumerate(o) if x[3] in T)
    seg=[];last=first
    seen=set()
    for n,x in enumerate(o):
        if x[3] in T and x[3] not in seen:
            seen.add(x[3]); seg.append(n-last if n!=first else first+1); last=n
    mids=sorted({c for _,_,_,c in o if (1<<14)<c<(1<<24) and c not in T})
    print('==',name,len(prog),'first target at',first,'segments',seg)
    print('   mid values (2^14..2^24):',len(mids),mids[:30])
print('starts',pz['starts'],'nt',len(T))
