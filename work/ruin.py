import sys,random,json
sys.path.insert(0,'../src')
x=open('prog_0938_own.txt').read().split(); pid=x[0]; n=int(x[1])
prog=[[x[2+4*k],int(x[3+4*k]),int(x[4+4*k]),int(x[5+4*k])] for k in range(n)]
from elf import load
pz=load()[pid]; R=[None]*48
for k,v in enumerate(pz['starts']): R[k]=v
vals=[]
for op,i,j,d in prog:
    a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; vals.append(c)
T=set(pz['targets']); helpers=[v for v in dict.fromkeys(vals) if v not in T]
for s in range(12):
    random.seed(s); keep=[v for v in helpers if random.random()>0.3]
    open(f'keep_r{s}.txt','w').write(pid+' '+' '.join(map(str,keep))+'\n')
print(len(helpers),'helpers')
