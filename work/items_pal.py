import sys,json; sys.path.insert(0,'src')
from elf import load,BEST
P=load()
lines=[l.split() for l in open('work/items_miss.txt')]
out=[]
for x in lines:
    pid=x[0]; pz=P[pid]; prog=json.loads((BEST/f'{pid}.json').read_text()); T=set(pz['targets'])
    R=[None]*48; small=[]
    for k,v in enumerate(pz['starts']): R[k]=v
    for op,i,j,d in prog:
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c
        if c<(1<<14) and c not in T and c not in small: small.append(c)
    out.append(' '.join([pid]+[str(v) for v in small]+x[1:]))
open('work/items_miss_pal.txt','w').write('\n'.join(out)+'\n')
print(len(out))
