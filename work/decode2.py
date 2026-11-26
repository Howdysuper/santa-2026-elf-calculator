"""Top-down items: decompose each target as k*M + c over atoms (from a source), output ordered helper list:
small constants (all k, |c| < 2^16) ascending, atoms ascending, products M ascending. usage: decode2.py SRC IDSFILE OUT
SRC = frontier (atoms = frontier non-target values 2^14..2^24 used >= 2x) or hubs (work/hubs_all.txt z >= ZMIN)"""
import sys,json,collections,itertools; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); src=sys.argv[1]; ids=[l.strip() for l in open(sys.argv[2]) if l.strip()]
ZMIN=float(sys.argv[4]) if len(sys.argv)>4 else 8
H={}
if src=='hubs':
    for l in open('work/hubs_all.txt'):
        x=l.split(); H[x[0]]=[(int(a),int(b),float(c)) for a,b,c in (t.split(':') for t in x[1:])]
out=[]
for pid in ids:
    pz=P[pid]; T=pz['targets']; TS=set(T)
    if src=='frontier':
        prog=json.loads((BEST/f'{pid}.json').read_text()); R=[None]*48; uses=collections.Counter(); vals=[]
        for k,v in enumerate(pz['starts']): R[k]=v
        for op,i,j,d in prog:
            a,b=R[i],R[j]; uses[a]+=1; uses[b]+=1; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c; vals.append(c)
        A=sorted({c for c in vals if (1<<14)<=c<(1<<24) and c not in TS and uses[c]>=2})
    else:
        A=sorted(h for h,c,z in H[pid] if z>=ZMIN)[:6]
    Ms=set(A)|{a*b for a,b in itertools.combinations_with_replacement(A,2)}|{a*b*c for a,b,c in itertools.combinations_with_replacement(A,3) if a*b*c<pz['limit']}
    consts=set(); used=set(); fit=0
    for t in T:
        best=None
        for M in Ms:
            if M>t: continue
            k=round(t/M); c=t-k*M
            if abs(c)<(1<<16) and k<(1<<24):
                sc=(k>1)*k.bit_length()+abs(c).bit_length()
                if best is None or sc<best[0]: best=(sc,M,k,c)
        if best:
            fit+=1; _,M,k,c=best; used.add(M)
            if 1<k<(1<<16): consts.add(k)
            if c: consts.add(abs(c))
    items=sorted(consts)+[a for a in A]+sorted(m for m in used if m not in A)
    out.append(pid+' '+' '.join(map(str,items)))
    print(pid,'atoms',len(A),'fit',fit,'/',len(T),'consts',len(consts),'products',len(used))
open(sys.argv[3],'w').write('\n'.join(out)+'\n')
