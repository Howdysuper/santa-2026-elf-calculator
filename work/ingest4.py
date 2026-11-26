import sys,csv,glob,json; sys.path.insert(0,'src'); csv.field_size_limit(1<<26)
from elf import load,offer,best_len
P=load(); g=0
for f in glob.glob('pub4/**/*.csv',recursive=True):
    try:
        for r in csv.DictReader(open(f,encoding='utf-8')):
            pid=r.get('id'); s=r.get('program')
            if pid in P and s:
                try: g+=offer(P[pid],pid,json.loads(s),source='pub4:'+f.split('\\')[1])
                except Exception: pass
    except Exception as e: print('skip',f,e)
print('gain',g,'store',sum(best_len(p) for p in P))
