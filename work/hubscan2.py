import sys,json,numpy as np,time; sys.path.insert(0,'src')
from elf import load
P=load(); PP=load(practice=True)
H=np.arange(1<<14,1<<22,dtype=np.int64)
def scan(T,E=2600,top=10):
    cnt=np.zeros(len(H),dtype=np.int32)
    for t in T:
        r=np.int64(t)%H; m=np.minimum(r,H-r)
        cnt+=((m<=E)&(H*H<=t*8)).astype(np.int32)
    # expected random hits per h: sum_t (2E+1)/h
    exp=np.zeros(len(H))
    for t in T: exp+=np.where(H*H<=t*8,(2*E+1)/H,0)
    z=(cnt-exp)/np.sqrt(exp+1e-9)
    idx=np.argsort(-z)[:top]
    return [(int(H[i]),int(cnt[i]),round(float(z[i]),1)) for i in idx]
for pid in sys.argv[1:]:
    pz=P.get(pid) or PP[pid]; t0=time.time()
    print(pid,pz.get('family'),len(pz['targets']),scan(pz['targets']),round(time.time()-t0,1),'s',flush=True)
