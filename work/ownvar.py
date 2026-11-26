import json,sys
add={}
for l in open(sys.argv[1]):
    x=l.split(); n=int(x[1]); add.setdefault(x[0],[]).append([[x[2+4*k],int(x[3+4*k]),int(x[4+4*k]),int(x[5+4*k])] for k in range(n)])
json.dump(add,open(sys.argv[2],'w')); print({k:sorted(len(p) for p in v) for k,v in add.items()})
