import sys,math; sys.path.insert(0,'src')
from elf import load
from sympy import factorint
PP=load(practice=True); P=load()
pid=sys.argv[1]; Hs=[int(x) for x in sys.argv[2:]]
pz=PP.get(pid) or P[pid]
for t in pz['targets']:
    row=[]
    for H in Hs:
        q,r=divmod(t,H)
        if H-r<r: q+=1; r-=H
        row.append(f"{q}*H{r:+d}")
    print(t,' | '.join(row))
