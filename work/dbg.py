import json,sys; sys.path.insert(0,'src')
from elf import load, replay
P=load(); pz=P['scored_0938']; V=json.load(open('work/var_own0938.json'))['scored_0938']
own=sorted(V,key=len); p=own[0]; print(len(p), replay(pz,p))
R=[None]*48
for k,v in enumerate(pz['starts']): R[k]=v
vals=[]
for op,i,j,d in p:
    a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; vals.append(c)
print(15570048413 in vals, 15570048413 in pz['targets'])
