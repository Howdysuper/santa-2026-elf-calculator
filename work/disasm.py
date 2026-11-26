import sys,json; sys.path.insert(0,'src')
from elf import load,BEST
P=load()
pid=sys.argv[1]
pz=P[pid]; prog=json.loads((BEST/f"{pid}.json").read_text())
R=[None]*48
for k,v in enumerate(pz['starts']): R[k]=v
T=set(pz['targets'])
print(pid,'starts',pz['starts'],'nt',len(T),'len',len(prog),'limit',pz['limit'])
seen=set()
for n,(op,i,j,d) in enumerate(prog):
    a,b=R[i],R[j]
    c={'+':a+b,'-':a-b,'*':a*b,'/':a//b if b else 0}[op]
    R[d]=c
    tag='T%d'%sorted(T).index(c) if c in T and c not in seen else ''
    seen.add(c)
    print(n, f"{a} {op} {b} = {c}", tag)
