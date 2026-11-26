import json,sys,math,collections
sys.path.insert(0,'src')
from elf import load
P=load(practice=True)
c=collections.Counter((p['family'],p['tier']) for p in P.values()); print(c)
shown=collections.Counter()
for pid,p in P.items():
    if shown[p['family']]>=2: continue
    shown[p['family']]+=1
    print('==',pid,p['family'],p['tier'],'starts',p['starts'],'limit',p['limit'],'n',len(p['targets']))
    print(p['targets'])
