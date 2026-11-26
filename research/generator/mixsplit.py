import sys,math,collections; sys.path.insert(0,'src')
from elf import load
PP=load(practice=True)
for fam in ['mixed','shared','multiplicative']:
    rows=[]
    for pid,pz in sorted(PP.items()):
        if pz['family']!=fam: continue
        T=pz['targets']; D=math.ceil(math.log10(max(T)))
        top=[t for t in T if t>=10**(D-1)]
        # count in top decade of any D in 12,15,18
        nd={d:sum(10**(d-1)<=t<10**d for t in T) for d in (6,9,12,15,18)}
        rows.append((pid,len(T),D,len(top),nd))
    print('==',fam)
    for r in rows[:60]: print(r)
