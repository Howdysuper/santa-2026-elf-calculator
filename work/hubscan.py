import sys,json,numpy as np,time; sys.path.insert(0,'src')
from elf import load
P=load(); PP=load(practice=True)
H=np.arange(1<<12,1<<23,dtype=np.int64)
Hf=H.astype(np.float64)
def scan(T,top=10):
    sc=np.zeros(len(H)); cnt=np.zeros(len(H),dtype=np.int32)
    for t in T:
        r=np.int64(t)%H; m=np.minimum(r,H-r).astype(np.float64)
        bits=np.log2(Hf/(2*m+1))
        ok=(bits>8)&(Hf*Hf<=t)
        sc+=np.where(ok,bits-8,0); cnt+=ok
    idx=np.argsort(-sc)[:top]
    return [(int(H[i]),int(cnt[i]),round(float(sc[i]))) for i in idx]
for pid in sys.argv[1:]:
    pz=P.get(pid) or PP[pid]
    print(pid,pz.get('family'),len(pz['targets']),'starts',pz['starts'],scan(pz['targets']))
