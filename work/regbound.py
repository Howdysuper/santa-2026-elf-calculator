import sys,json; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); out=[]
for pid in sorted(P):
    prog=json.loads((BEST/f"{pid}.json").read_text()); live=set(); pk=0
    for op,i,j,d in reversed(prog):
        live.discard(d); live.add(i); live.add(j); pk=max(pk,len(live))
    if pk>=47 and len(prog)<200: out.append(pid)
import random; random.seed(5); random.shuffle(out)
open('work/p_regbound.txt','w').write('\n'.join(out[:12]))
print(len(out))
