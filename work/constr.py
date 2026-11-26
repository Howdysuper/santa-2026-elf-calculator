import sys,json,csv,collections; sys.path.insert(0,'src')
from elf import load,BEST
P=load()
fam={r['id']:r['family'] for r in csv.DictReader(open('research/generator/scored_family.csv'))}
agg=collections.defaultdict(lambda:[0,0,0])
rows=[]
for pid,pz in P.items():
    prog=json.loads((BEST/f"{pid}.json").read_text()); T=set(pz['targets'])
    R=[None]*48
    for k,v in enumerate(pz['starts']): R[k]=v
    first=None
    for n,(op,i,j,d) in enumerate(prog):
        a,b=R[i],R[j]; c={'+':a+b,'-':a-b,'*':a*b,'/':a//b}[op]; R[d]=c
        if c in T: first=n; break
    nt=len(T); post=(len(prog)-first)/max(1,nt-1)
    f=fam.get(pid,'?'); k=(f,'old' if first<30 else 'new')
    agg[k][0]+=1; agg[k][1]+=len(prog); agg[k][2]+=nt
    rows.append((pid,f,first,round(post,2),len(prog),nt))
for k in sorted(agg): a=agg[k]; print(k,a[0],'puzzles',a[1],'instr',round(a[1]/a[2],2),'/t')
with open('work/construction.csv','w') as fh:
    fh.write('pid,family,first,post_per_t,len,nt\n')
    for r in rows: fh.write(','.join(map(str,r))+'\n')
