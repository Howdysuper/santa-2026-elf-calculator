import sys,math,collections; sys.path.insert(0,'src')
from elf import load
PP=load(practice=True)
for pid in ['practice_0001','practice_0007']:
    T=PP[pid]['targets']; c=collections.Counter()
    for i in range(len(T)):
        for j in range(i):
            g=math.gcd(T[i],T[j])
            if g>1000: c[g]+=1
    print(pid, sorted(c.items(),key=lambda x:-x[0])[:25])
