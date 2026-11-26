import sys,json,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); out=[]; stats=[]
mode=sys.argv[1]; ids=sys.argv[2:]
for pid in ids:
    pz=P[pid]; prog=json.loads((BEST/f'{pid}.json').read_text()); T=set(pz['targets'])
    R=[None]*48; src={}
    for k,v in enumerate(pz['starts']): R[k]=v
    uses=collections.Counter(); vals=[]
    for op,i,j,d in prog:
        a,b=R[i],R[j]; uses[a]+=1; uses[b]+=1
        c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; vals.append(c); src.setdefault(c,(a,b))
    atoms={c for c in vals if (1<<14)<=c<(1<<24) and c not in T}
    keep=set()
    def cone(v):
        if v in keep or v in pz['starts'] or v not in src: return
        keep.add(v); a,b=src[v]; cone(a); cone(b)
    for a in atoms: cone(a)
    if mode=='conebig':
        for c in vals:
            if c>=(1<<24) and c not in T and uses[c]>=2: keep.add(c)
    keep-=T
    out.append(pid+' '+' '.join(map(str,sorted(keep)))); stats.append((pid,len(keep),len(prog)))
open(f'work/keep_{mode}.txt','w').write('\n'.join(out)+'\n')
print(mode,stats)
