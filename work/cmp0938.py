import sys,json,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); pid='scored_0938'; pz=P[pid]; T=set(pz['targets']); S=set(pz['starts'])
def trace(prog):
    R=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    out=[]; src={}
    for op,i,j,d in prog:
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; out.append((c,op,a,b)); src.setdefault(c,(op,a,b))
    return out,src
pub=json.loads((BEST/f'{pid}.json').read_text())
x=open('work/prog_0938_own.txt').read().split(); n=int(x[1]); own=[[x[2+4*k],int(x[3+4*k]),int(x[4+4*k]),int(x[5+4*k])] for k in range(n)]
for name,prog in (('PUBLIC',pub),('OWN',own)):
    tr,src=trace(prog); uses=collections.Counter()
    for c,op,a,b in tr: uses[a]+=1; uses[b]+=1
    first=next(k for k,(c,*_) in enumerate(tr) if c in T)
    small=[c for c,*_ in tr if c not in T and c<(1<<16)]
    mid=[c for c,*_ in tr if c not in T and (1<<16)<=c<(1<<30)]
    big=[c for c,*_ in tr if c not in T and c>=(1<<30)]
    print(f'== {name} len {len(prog)} scaffold(before 1st target) {first} | helpers small {len(small)} mid {len(mid)} big {len(big)}')
    print('   small:',sorted(set(small)))
    print('   mid  :',sorted(set(mid)))
    print('   big helpers used>=2:',sorted({c for c in big if uses[c]>=2}))
    tcost=[]
    seen=set(); last=first
    for k,(c,*_) in enumerate(tr):
        if c in T and c not in seen: seen.add(c); tcost.append(k-last); last=k
    print('   per-target gaps:',tcost)
pt,_=trace(pub); ot,_=trace(own)
pv={c for c,*_ in pt}; ov={c for c,*_ in ot}
print('values only in PUBLIC:',sorted(v for v in pv-ov-T))
