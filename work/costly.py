import sys,json,csv; sys.path.insert(0,'src')
from elf import load,best_len
P=load(); fam={r['id']:r['family'] for r in csv.DictReader(open('research/generator/scored_family.csv'))}
H={}
for l in open('work/hubs_all.txt'):
    x=l.split(); H[x[0]]=[(int(a),int(b),float(c)) for a,b,c in (t.split(':') for t in x[1:])]
rows=[]
for pid,pz in P.items():
    if fam.get(pid)!='shared': continue
    n=best_len(pid); nt=len(pz['targets']); z=max([z for h,c,z in H.get(pid,[])]+[0])
    rows.append((round(n/nt,2),pid,n,nt,round(z,1)))
rows.sort(reverse=True)
import collections
b=collections.Counter(int(r[0]*2)/2 for r in rows); print(sorted(b.items()))
for r in rows[:25]: print(r)
