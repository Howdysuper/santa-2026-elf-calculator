import sys,math,json,collections; sys.path.insert(0,'src')
from elf import load,best_len
P=load()
def rel(a,b,PQ=1<<12,R=1<<16):
    # find small p,q with |q*a - p*b| <= R  (a>b)
    x,y=a,b; h0,h1=0,1; k0,k1=1,0; best=None
    while y:
        qq=x//y; x,y=y,x-qq*y
        h0,h1=h1,qq*h1+h0; k0,k1=k1,qq*k1+k0
        p,q=h1,k1
        if p>PQ or q>PQ: break
        r=abs(q*a-p*b)
        if r<=R:
            c=(0 if q==1 else 1)+(0 if p==1 else 1)+(0 if r==0 else 1)
            if best is None or c<best[0]: best=(c,p,q,r)
    return best
out=[]
for pid,pz in sorted(P.items()):
    T=pz['targets']; n=len(T)
    par=list(range(n))
    def f(x):
        while par[x]!=x: par[x]=par[par[x]]; x=par[x]
        return x
    ne=0; cost1=0
    for i in range(n):
        for j in range(i):
            r=rel(T[i],T[j])
            if r:
                ne+=1
                if f(i)!=f(j): par[f(i)]=f(j)
    comps=len({f(i) for i in range(n)})
    out.append((pid,max(pz['starts'])>=100,n,comps,ne,best_len(pid)))
with open('work/affine_struct.csv','w') as fh:
    fh.write('pid,indep,nt,comps,edges,len\n')
    for r in out: fh.write(','.join(map(str,r))+'\n')
agg=collections.defaultdict(lambda:[0,0,0,0])
for r in out:
    fr=1-r[3]/r[2]; k=('I' if r[1] else 'S', 'link>=.5' if fr>=.5 else 'link.2-.5' if fr>=.2 else 'link<.2')
    a=agg[k]; a[0]+=1; a[1]+=r[5]; a[2]+=r[2]; a[3]+=r[2]-r[3]
for k in sorted(agg): a=agg[k]; print(k,'puzzles',a[0],'instr',a[1],'targets',a[2],'linked',a[3],'per',round(a[1]/a[2],2))
