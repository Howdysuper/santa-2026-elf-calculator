import sys,json; sys.path.insert(0,'src'); sys.path.insert(0,'research/generator')
import decoder
from elf import load,BEST
from sympy import factorint
P=load()
for pid in sys.argv[1:]:
    pz=P[pid]; prog=json.loads((BEST/f"{pid}.json").read_text())
    A=decoder.prog_atoms(pz,prog)
    dec=decoder.decode(pz,A,use_hubs=False)
    print(pid,'starts',pz['starts'],'atoms',A,[dict(factorint(a)) for a in A])
    for t in pz['targets']:
        e=dec['expl'].get(t)
        if e is None: print('  ',t,'??'); continue
        if e[0]=='L1': print('  ',t,'L1 atoms',e[1],'k',e[2],dict(factorint(e[2])) if e[2]>1 else '','c',e[3])
        elif e[0]=='L2': print('  ',t,'L2 atoms',e[1],'m1',e[2],'c1',e[3],'m2',e[4],'c2',e[5])
        else: print('  ',t,'AFF u',e[1],'m',e[2],'c',e[3])
