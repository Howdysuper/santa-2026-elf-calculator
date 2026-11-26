import sys,json,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); pid='scored_0938'; pz=P[pid]; T=set(pz['targets'])
pub=json.loads((BEST/f'{pid}.json').read_text())
R=[None]*48
for k,v in enumerate(pz['starts']): R[k]=v
consumers=collections.defaultdict(list); src={}
for op,i,j,d in pub:
    a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c
    src.setdefault(c,(op,a,b)); consumers[a].append((c,op,b)); consumers[b].append((c,op,a))
atoms=[124780,618523,717923]
def desc(v):
    for a in atoms:
        for b in atoms:
            if a<=b and v%(a*b)==0 and v//(a*b)<1<<16: return f'{v//(a*b)}*{a}*{b}'
            if a<=b:
                q=round(v/(a*b)); c=v-q*a*b
                if q>0 and abs(c)<5000: return f'{q}*{a}*{b}{c:+d}'
    return '?'
for v in sorted(c for c in src if c not in T and c>=(1<<30)):
    cs=consumers[v]
    if len(cs)<2: continue
    op,a,b=src[v]
    print(f'{v} = {desc(v)} | built {a}{op}{b} | feeds:', '; '.join(f'{"T" if c in T else ""}{c} via {o}{x}' for c,o,x in cs))
