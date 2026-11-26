import sys,math,itertools; sys.path.insert(0,'src')
from elf import load
from sympy import factorint
PP=load(practice=True)
for pid in sys.argv[1:]:
    T=PP[pid]['targets']; print('==',pid,PP[pid]['starts'])
    G={}
    for i,j in itertools.combinations(range(len(T)),2):
        g=math.gcd(T[i],T[j])
        # remove small-prime part
        g2=g
        for p in [2,3,5,7,11,13]:
            while g2%p==0: g2//=p
        if g2>50: G[(i,j)]=(g,g2)
    for k,v in sorted(G.items(), key=lambda x:-x[1][1])[:25]: print(k,v,factorint(v[1]))
