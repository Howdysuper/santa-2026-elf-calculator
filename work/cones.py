import sys,json,csv,collections,math; sys.path.insert(0,'src')
from elf import load,BEST
P=load(); fam={r['id']:r['family'] for r in csv.DictReader(open('research/generator/scored_family.csv'))}
hist=collections.defaultdict(collections.Counter); excess=collections.Counter(); ntar=collections.Counter()
for pid,pz in P.items():
    f=fam.get(pid,'?'); prog=json.loads((BEST/f'{pid}.json').read_text()); T=set(pz['targets'])
    ns=len(pz['starts']); R=list(range(ns))+[None]*(48-ns); vals=list(pz['starts']); rv=list(pz['starts'])+[None]*(48-ns)
    deps=[]; users=collections.defaultdict(set); cover={}
    for n,(op,i,j,d) in enumerate(prog):
        a,b=R[i],R[j]; nid=ns+n
        va,vb=rv[i],rv[j]; c={'+':va+vb,'-':va-vb,'*':va*vb,'/':va//vb}[op]
        deps.append((a,b)); users[a].add(nid); users[b].add(nid)
        R[d]=nid; rv[d]=c
        if c in T and c not in cover: cover[c]=nid
    N=ns+len(prog)
    # exclusive cone of target node t: ancestors whose every user is inside the cone (iterate)
    for t,tn in cover.items():
        cone={tn}; changed=True
        anc=set(); st=[tn]
        while st:
            x=st.pop()
            if x<ns: continue
            for y in deps[x-ns]:
                if y>=ns and y not in anc: anc.add(y); st.append(y)
        while changed:
            changed=False
            for x in anc-cone:
                if users[x] and users[x]<=cone and x not in cover.values(): cone.add(x); changed=True
        k=len(cone); b=int(math.log2(t))//10*10
        hist[(f,b)][min(k,12)]+=1; ntar[f]+=1
        if k>=8: excess[f]+=k-7
for f in ntar: print(f,'targets',ntar[f],'sum of (cone-7) over cones>=8:',excess[f])
for key in sorted(hist):
    if key[1]>=40: print(key,sorted(hist[key].items()))
