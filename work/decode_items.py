import sys,json,itertools; sys.path.insert(0,'src')
from elf import load
P=load()
H={}
for l in open('work/hubs_all.txt'):
    x=l.split(); H[x[0]]=[(int(a),int(b),float(c)) for a,b,c in (t.split(':') for t in x[1:])]
ids=[l.strip() for l in open(sys.argv[1]) if l.strip()]
zmin=float(sys.argv[3]) if len(sys.argv)>3 else 8
out=[]; st=[]
for pid in ids:
    pz=P[pid]; A=[h for h,c,z in H[pid] if z>=zmin][:6]
    Ms=set(A)|{a*b for a,b in itertools.combinations_with_replacement(A,2)}
    used=set(); fit=0
    for t in pz['targets']:
        best=None
        for M in Ms:
            if M>t: continue
            k=round(t/M); c=t-k*M
            if abs(c)<=2600 and k<(1<<22):
                sc=k.bit_length()+abs(c).bit_length()
                if best is None or sc<best[0]: best=(sc,M)
        if best: used.add(best[1]); fit+=1
    items=sorted(A)+sorted(m for m in used if m not in A)
    out.append(pid+' '+' '.join(map(str,items))); st.append((pid,len(A),len(used),fit,len(pz['targets'])))
open(sys.argv[2],'w').write('\n'.join(out)+'\n')
print('fit summary: total targets fitted',sum(s[3] for s in st),'of',sum(s[4] for s in st))
for s in st[:8]: print(s)
