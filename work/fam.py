import json,sys,math
sys.path.insert(0,'src')
from elf import load, BEST
P=load()
rows=[]
for pid,pz in P.items():
    prog=json.loads((BEST/f"{pid}.json").read_text())
    nt=len(set(pz['targets'])-set(pz['starts']))
    ind = max(pz['starts'])>=100
    bits = math.log2(max(pz['targets']))
    rows.append((pid,ind,len(prog),nt,bits,len(pz['starts'])))
for flag in (True,False):
    r=[x for x in rows if x[1]==flag]
    print('indep' if flag else 'struct', len(r), 'instr',sum(x[2] for x in r),'targets',sum(x[3] for x in r), 'per',round(sum(x[2] for x in r)/sum(x[3] for x in r),3))
# by bits bucket for indep
import collections
b=collections.defaultdict(lambda:[0,0,0])
for x in rows:
    k=('I' if x[1] else 'S', int(x[4]//5*5))
    b[k][0]+=1;b[k][1]+=x[2];b[k][2]+=x[3]
for k in sorted(b): print(k,b[k][0],b[k][1],b[k][2],round(b[k][1]/b[k][2],2))
print('total',sum(x[2] for x in rows))
