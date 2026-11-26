import sys,math,collections,random; sys.path.insert(0,'src')
from elf import load
from sympy import factorint
PP=load(practice=True)
rnd=random.Random(2)
def lpf_ratio(t):
    f=factorint(t); return math.log(max(f))/math.log(t)
res=collections.defaultdict(list)
for pid,pz in sorted(PP.items()):
    fam=pz['family']
    if fam in ('tiny','independent'): continue
    for t in pz['targets']:
        if t<1000: continue
        res[fam].append(lpf_ratio(t))
        res[fam+'_ctrl'].append(lpf_ratio(rnd.randint(t//2,t*2)))
for k,v in sorted(res.items()):
    v=sorted(v); n=len(v)
    print(k,n,'median lpf ratio %.3f'%v[n//2],'frac<=0.5 %.3f'%(sum(x<=0.5 for x in v)/n),'frac<=0.33 %.3f'%(sum(x<=0.33 for x in v)/n),'frac<=0.25 %.3f'%(sum(x<=0.25 for x in v)/n))
