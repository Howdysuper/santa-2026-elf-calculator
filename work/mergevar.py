import json,sys
V=json.load(open('work/var_all.json'))
add={}
for l in open(sys.argv[1]):
    x=l.split(); n=int(x[1]); add.setdefault(x[0],[]).append([[x[2+4*k],int(x[3+4*k]),int(x[4+4*k]),int(x[5+4*k])] for k in range(n)])
out={pid:V.get(pid,[])+progs for pid,progs in add.items()}
json.dump(out,open(sys.argv[2],'w')); print({k:len(v) for k,v in out.items()})
