import sys,json,subprocess,time; sys.path.insert(0,'src')
from elf import load,BEST,replay
P=load()
def vals(pz,prog):
    R=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    out=[]
    for op,i,j,d in prog:
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; out.append(c)
    return out
def solve(pid,targets,width=30):
    pz=P[pid]
    line=' '.join(map(str,[pid,pz['limit'],len(pz['starts']),len(targets),*pz['starts'],*targets]))
    t0=time.time()
    r=subprocess.run(['work/konbu.exe',str(width)],input=line+'\n',capture_output=True,text=True)
    prog=json.loads(r.stdout.split(' ',1)[1])
    return replay(pz,prog),round(time.time()-t0,1)
for pid in sys.argv[1:]:
    pz=P[pid]; T=sorted(pz['targets']); best=json.loads((BEST/f'{pid}.json').read_text())
    V=vals(pz,best); TS=set(T)
    atoms=sorted({v for v in V if (1<<14)<v<(1<<22) and v not in TS})
    big=sorted({v for v in V if v>=(1<<22) and v not in TS})
    print(pid,'frontier',len(best),'nt',len(T),'atoms',len(atoms),'big helpers',len(big))
    print('  plain        ',solve(pid,T))
    print('  +atoms first ',solve(pid,atoms+T))
    print('  +atoms+big   ',solve(pid,atoms+sorted(big+T)))
