import sys,json,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load()
tot=collections.Counter()
for pid,pz in P.items():
    prog=json.loads((BEST/f"{pid}.json").read_text())
    T=set(pz['targets'])
    R=[None]*48; ids=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v; ids[k]=('s',k)
    first=None; defs=[]; uses=collections.defaultdict(list)
    for n,(op,i,j,d) in enumerate(prog):
        a,b=R[i],R[j]
        uses[ids[i]].append(n); uses[ids[j]].append(n)
        c={'+':a+b,'-':a-b,'*':a*b,'/':a//b if b else 0}[op]
        R[d]=c; ids[d]=('v',n)
        if c in T and first is None: first=n
    sc=first
    inter=sum(1 for n in range(sc) if any(u>=sc for u in uses[('v',n)]))
    tot['scaffold']+=sc; tot['interface']+=inter; tot['len']+=len(prog)
    tot['indep' if max(pz['starts'])>=100 else 'struct','scaf']+=sc
    tot['indep' if max(pz['starts'])>=100 else 'struct','int']+=inter
print(dict(tot))
