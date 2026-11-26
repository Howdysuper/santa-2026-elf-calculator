import json,sys
V=json.load(open('work/var_all.json')); ids=[l.strip() for l in open('work/p_bench11.txt') if l.strip()]
add={}
for l in open('work/alt_layered.txt'):
    x=l.split(); n=int(x[1]); add.setdefault(x[0],[]).append([[x[2+4*k],int(x[3+4*k]),int(x[4+4*k]),int(x[5+4*k])] for k in range(n)])
out={p:V.get(p,[])+add.get(p,[]) for p in ids}
json.dump(out,open('work/var_bench11.json','w')); print({p:(len(V.get(p,[])),len(add.get(p,[]))) for p in ids})
