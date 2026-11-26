import sys; sys.path.insert(0,'src')
from elf import load
from sympy import factorint
P=load(practice=True)
for pid in ['practice_0007','practice_0001']:
    p=P[pid]; print(pid,p['starts'])
    for t in p['targets']:
        print(t, factorint(t), '| -1:',factorint(t-1),'| +1:',factorint(t+1))
