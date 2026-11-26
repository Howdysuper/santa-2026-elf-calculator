import sys,json,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); out=[]
mode=sys.argv[1]; ids=sys.argv[2:]
for pid in ids:
    pz=P[pid]; prog=json.loads((BEST/f'{pid}.json').read_text()); T=set(pz['targets'])
    R=[None]*48; vid=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    uses=collections.Counter(); vals=[]
    for op,i,j,d in prog:
        a,b=R[i],R[j]; uses[a]+=1; uses[b]+=1
        c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; vals.append(c)
    keep=set()
    for c in vals:
        if c in T: continue
        if mode=='atoms' and (1<<14)<=c<(1<<24): keep.add(c)
        if mode in('atoms','atomsbig') and (1<<14)<=c<(1<<24): keep.add(c)
        if mode=='atomsbig' and c>=(1<<24) and uses[c]>=2: keep.add(c)
    out.append(pid+' '+' '.join(map(str,sorted(keep))))
open(f'work/keep_{mode}.txt','w').write('\n'.join(out)+'\n')
print(mode,[len(o.split())-1 for o in out])
