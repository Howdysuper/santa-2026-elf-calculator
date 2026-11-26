import sys, csv, glob, json, time
from pathlib import Path
sys.path.insert(0,'src'); csv.field_size_limit(1<<26)
from elf import load, replay, ROOT, best_len
P=load(); REL=1.3
bl={p:best_len(p) for p in P}
var={p:{} for p in P}
files=sorted(f for f in glob.glob(str(ROOT/'pub*'/'**'/'*.csv'),recursive=True) if Path(f).stat().st_size>100_000)
t0=time.time()
for k,f in enumerate(files):
    try:
        with open(f,newline='',encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                pid=r.get('id'); s=r.get('program')
                if pid not in var or not s: continue
                s=s.replace(' ','')
                if s.count('],[')+1 > REL*bl[pid]: continue
                var[pid].setdefault(hash(s),s)
    except Exception as e: pass
out={}; nv=0
for pid,d in var.items():
    good=[]
    for s in d.values():
        try: prog=json.loads(s); replay(P[pid],prog); good.append(prog)
        except Exception: pass
    out[pid]=good; nv+=len(good)
json.dump(out,open('work/var_all.json','w'))
print('files',len(files),'variants',nv,'avg/puzzle',round(nv/len(P),1),'secs',round(time.time()-t0))
