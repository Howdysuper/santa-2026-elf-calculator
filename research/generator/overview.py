import sys,math,collections; sys.path.insert(0,'src')
from elf import load
PP=load(practice=True)
import csv
for fam in ['tiny','independent','shared','multiplicative','mixed']:
    print('=====',fam)
    for pid,pz in sorted(PP.items()):
        if pz['family']!=fam: continue
        T=pz['targets']
        print(pid,pz['tier'],'S',pz['starts'],'n',len(T),'lim',pz['limit'],'lim_bits %.1f'%math.log2(pz['limit']),'Tbits',[round(math.log2(t),1) for t in T][:40])
