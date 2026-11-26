import sys,math; sys.path.insert(0,'src')
from elf import load
from fractions import Fraction
P=load(); PP=load(practice=True)
def best_pair(a,b,QMAX=1<<20):
    # convergents of a/b
    best=(-99,0,0,0)
    x,y=a,b; h0,h1=0,1; k0,k1=1,0
    while y:
        q=x//y; x,y=y,x-q*y
        h0,h1=h1,q*h1+h0; k0,k1=k1,q*k1+k0
        p,qq=h1,k1
        if qq>QMAX or p>QMAX: break
        res=abs(qq*a-p*b)
        s=math.log2(b)-math.log2(max(qq,p))-math.log2(res+1)
        if s>best[0]: best=(s,p,qq,res)
    return best
for pid in sys.argv[1:]:
    pz=P.get(pid) or PP[pid]; T=pz['targets']; n=len(T)
    hits=[]
    for i in range(n):
        for j in range(i):
            s,p,q,res=best_pair(T[i],T[j])
            if s>12: hits.append((round(s),j,i,p,q,res))
    deg=[0]*n
    for h in hits: deg[h[1]]+=1; deg[h[2]]+=1
    print(pid,pz.get('family'),n,'pairs',len(hits),'targets linked',sum(1 for d in deg if d),'example',sorted(hits,reverse=True)[:4])
