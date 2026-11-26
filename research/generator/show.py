import sys,math; sys.path.insert(0,'src')
from elf import load
from sympy import factorint
PP=load(practice=True); P=load()
for pid in sys.argv[1:]:
    pz=PP.get(pid) or P[pid]; T=pz['targets']
    print('==',pid,pz['family'],'S',pz['starts'],'lim',pz['limit'])
    for k,t in enumerate(T):
        print(k,t,dict(factorint(t)) if t<1e16 else '')
