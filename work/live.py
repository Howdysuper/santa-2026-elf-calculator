import sys,json,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load()
hist=collections.Counter(); peak=collections.Counter(); tot=0
for pid,pz in P.items():
    prog=json.loads((BEST/f"{pid}.json").read_text())
    n=len(prog)
    # live = registers whose current value is read later before overwrite
    nxt_read=[None]*48
    live_at=[0]*n
    # backward pass
    live=set()
    for k in range(n-1,-1,-1):
        op,i,j,d=prog[k]
        live.discard(d)
        live.add(i); live.add(j)
        live_at[k]=len(live)
    p=max(live_at) if n else 0
    peak[min(p//4*4,48)]+=1
    for x in live_at: hist[min(x//4*4,48)]+=1
    tot+=n
print('peak live per puzzle (bucketed):',sorted(peak.items()))
print('instr-weighted live (bucketed):',sorted(hist.items()))
