import sys,collections; sys.path.insert(0,'src')
from elf import load
P=load(practice=True)
def one(v,S):
    S=sorted(S)
    for a in S:
        for b in S:
            if a+b==v or a*b==v or (a>b and a-b==v) or (b and a%b==0 and a//b==v): return (a,b)
    return None
st=collections.defaultdict(lambda:[0,0])
for pid,p in P.items():
    pool=set(p['starts'])|set(p['targets'])
    for t in p['targets']:
        if t in p['starts']: continue
        S=pool-{t}
        st[p['family']][1]+=1
        if one(t,S): st[p['family']][0]+=1
for k,v in st.items(): print(k,v, round(v[0]/v[1],3))
p=P['practice_0004']; pool=set(p['starts'])|set(p['targets'])
for t in p['targets']: print(t, one(t,pool-{t}))
