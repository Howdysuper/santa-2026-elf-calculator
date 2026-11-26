import sys,math,collections; sys.path.insert(0,'src')
from elf import load
PP=load(practice=True)
by=collections.defaultdict(list)
for pid,pz in sorted(PP.items()):
    T=pz['targets']; r=pz['limit']/max(T)
    by[pz['family']].append((round(r,3),pid,pz['tier'],len(T),round(math.log2(pz['limit']),2)))
for f,v in by.items():
    rs=sorted(x[0] for x in v)
    print(f,len(v),'ratio min/med/max',rs[0],rs[len(rs)//2],rs[-1])
    print('   ',sorted(v)[:6], sorted(v)[-4:])
# check if limit relates to 10^k or 2^k
for f,v in by.items():
    print(f,[x[4] for x in v][:25])
