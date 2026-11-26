import sys, csv, glob, json
from pathlib import Path
sys.path.insert(0,'src'); csv.field_size_limit(1<<26)
from elf import load, replay, ROOT
P=load(); want=set(sys.argv[2:]); var={p:set() for p in want}
files=[f for f in glob.glob(str(ROOT/'pub*'/'**'/'*.csv'),recursive=True) if Path(f).stat().st_size>100_000]
files+=glob.glob(str(ROOT/'work'/'alt'/'*.csv'))
for f in files:
    try:
        with open(f,newline='',encoding='utf-8') as fh:
            for r in csv.DictReader(fh):
                pid=r.get('id')
                if pid in want and r.get('program'): var[pid].add(r['program'].replace(' ',''))
    except Exception as e: pass
out={}
for pid,ss in var.items():
    good=[]
    for s in ss:
        try: prog=json.loads(s); replay(P[pid],prog); good.append(prog)
        except Exception: pass
    out[pid]=good
    print(pid,'files',len(files),'variants',len(good),'lengths',sorted(len(g) for g in good)[:12])
json.dump(out,open(sys.argv[1],'w'))
