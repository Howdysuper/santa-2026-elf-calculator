import sys,json,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); out=[]
for pid in sys.argv[1:]:
    pz=P[pid]; prog=json.loads((BEST/f'{pid}.json').read_text()); T=set(pz['targets'])
    R=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    uses=collections.Counter(); vals=[]
    for op,i,j,d in prog:
        a,b=R[i],R[j]; uses[a]+=1; uses[b]+=1
        c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; vals.append(c)
    atoms=sorted({c for c in vals if (1<<14)<=c<(1<<24) and c not in T and uses[c]>=2})
    big=sorted({c for c in vals if c>=(1<<24) and c not in T and uses[c]>=2})
    out.append(pid+' '+' '.join(map(str,atoms+big)))
    print(pid,len(atoms),len(big))
open('work/items_test.txt','w').write('\n'.join(out)+'\n')
