import sys,json,collections,math; sys.path.insert(0,'src')
from elf import load,BEST
P=load()
seg=collections.Counter(); segbits=collections.defaultdict(list)
for pid,pz in P.items():
    if max(pz['starts'])<100: continue
    prog=json.loads((BEST/f"{pid}.json").read_text()); T=set(pz['targets'])
    R=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    last=-1; seen=set(); first=True
    for n,(op,i,j,d) in enumerate(prog):
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c
        if c in T and c not in seen:
            seen.add(c)
            if not first:
                L=n-last; seg[min(L,15)]+=1; segbits[int(math.log2(c))//5*5].append(L)
            first=False; last=n
print(sorted(seg.items()))
for k in sorted(segbits): v=segbits[k]; print(k,len(v),round(sum(v)/len(v),2),'>=9:',sum(1 for x in v if x>=9),'sum excess over 8:',sum(max(0,x-8) for x in v))
