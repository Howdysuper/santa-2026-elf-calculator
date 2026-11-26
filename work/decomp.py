import sys,json,math,itertools; sys.path.insert(0,'src')
from elf import load,BEST
P=load()
def values(pz,prog):
    R=[None]*48; out=[]
    for k,v in enumerate(pz['starts']): R[k]=v
    for op,i,j,d in prog:
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b if b else 0}[op]; R[d]=c; out.append(c)
    return out
def atoms(pz,vals,R=1<<14):
    T=pz['targets']; cand=sorted({v for v in vals if (1<<12)<v<(1<<26)})
    sc=[]
    for v in cand:
        s=sum(1 for t in T if t>v*v//4 and min(t%v, v-t%v)<R)
        sc.append((s,v))
    sc.sort(reverse=True)
    A=[]
    for s,v in sc:
        if s<3: break
        if any(v%a==0 or a%v==0 for a in A): continue
        A.append(v)
        if len(A)>=8: break
    return A,sc[:10]
def decomp(t,A,maxdeg=3):
    best=None
    for d in range(1,maxdeg+1):
        for comb in itertools.combinations_with_replacement(A,d):
            M=math.prod(comb)
            if M>t: continue
            a=round(t/M); 
            for aa in (a-1,a,a+1):
                if aa<1: continue
                b=t-aa*M; cost=aa.bit_length()+abs(b).bit_length()
                if best is None or cost<best[0]: best=(cost,comb,aa,b)
    return best
for pid in sys.argv[1:]:
    pz=P[pid]; prog=json.loads((BEST/f"{pid}.json").read_text())
    A,sc=atoms(pz,values(pz,prog))
    print('==',pid,'len',len(prog),'nt',len(pz['targets']),'starts',pz['starts'],'atoms',A)
    for t in pz['targets']:
        b=decomp(t,A) if A else None
        print('  ',t, b and (b[1],b[2],b[3]))
