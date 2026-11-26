import sys,math; sys.path.insert(0,'src')
from elf import load
exec(open('work/pairs.py',encoding='utf-8').read().split('for pid in')[0])
pz=PP['practice_0003']; T=pz['targets']; n=len(T)
print(pz['starts'])
for i in range(n):
    best=None
    for j in range(n):
        if i==j: continue
        a,b=(T[i],T[j]) if T[i]>T[j] else (T[j],T[i])
        s,p,q,res=best_pair(a,b,1<<24)
        if best is None or s>best[0]: best=(round(s,1),j,p,q,res)
    print(i,T[i],T[i].bit_length(),best)
