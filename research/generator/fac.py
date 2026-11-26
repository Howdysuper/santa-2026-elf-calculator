import sys,math; sys.path.insert(0,'src')
from elf import load
from sympy import factorint
PP=load(practice=True)
ids=sys.argv[2:] or [p for p in sorted(PP) if PP[p]['family']==sys.argv[1]][:4]
for pid in ids:
    pz=PP[pid]; print('==',pid,pz['family'],'S',pz['starts'],'lim',pz['limit'])
    for t in pz['targets']:
        f=factorint(t); fm=factorint(t-1); fp=factorint(t+1)
        print('  ',t, dict(f), '| -1:',dict(fm),'| +1:',dict(fp))
