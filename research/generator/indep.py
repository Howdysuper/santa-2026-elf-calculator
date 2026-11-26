import sys,math,collections; sys.path.insert(0,'src')
from elf import load
from scipy.stats import kstest
PP=load(practice=True); P=load()
us=[];rows=[]
for pid,pz in sorted(PP.items()):
    if pz['family']!='independent': continue
    T=pz['targets']; D=math.ceil(math.log10(max(T)))
    lo,hi=10**(D-1),10**D
    inside=sum(lo<=t<hi for t in T)
    u=[(t-lo)/(hi-lo) for t in T]; us+=u
    rows.append((pid,D,len(T),inside, round(min(T)/lo,3), round(max(T)/hi,4), max(pz['starts']), len(pz['starts'])))
for r in rows: print(r)
print('KS pooled uniform-in-decade', kstest(us,'uniform'))
# scored: independent = max start >=100
cnt=collections.Counter(); ok=0; tot=0
for pid,pz in P.items():
    if max(pz['starts'])>=100:
        T=pz['targets']; D=math.ceil(math.log10(max(T))); cnt[(D,len(T)>=20)]+=1
        tot+=len(T); ok+=sum(10**(D-1)<=t for t in T)
print('scored indep decades',sorted(cnt.items()),'frac in decade',ok/tot)
# starts of independent
print('indep starts sizes', collections.Counter(len(pz['starts']) for pz in PP.values() if pz['family']=='independent'))
print('indep start range', min(min(pz['starts']) for pz in PP.values() if pz['family']=='independent'), max(max(pz['starts']) for pz in PP.values() if pz['family']=='independent'))
print('struct start range', max(max(pz['starts']) for pz in PP.values() if pz['family'] in('shared','mixed','multiplicative')))
