import json,sys; sys.path.insert(0,'src')
from elf import load,best_len
V=json.load(open('work/var_all.json')); P=load(); rows=[]
for pid in P:
    b=best_len(pid); near=[p for p in V.get(pid,[]) if len(p)<=b*1.08]
    distinct=len({json.dumps(p) for p in near})
    rows.append((distinct,b,pid))
rows.sort(reverse=True)
ids=[r[2] for r in rows if r[1]>20]
for k in range(3): open(f'work/p_div{k}.txt','w').write('\n'.join(ids[k::3]))
print('puzzles',len(ids),'top diversity',rows[:5])
