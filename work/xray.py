import sys,json,re; sys.path.insert(0,'src')
from elf import load,best_len,replay
P=load()
nb=json.load(open('research/nb1119/santa-2026-the-elf-calculator-x-ray/santa-2026-the-elf-calculator-x-ray.ipynb',encoding='utf-8'))
txt='\n'.join(''.join(c.get('source','')) for c in nb['cells'])
for o in (oo for c in nb['cells'] for oo in c.get('outputs',[])):
    txt+='\n'+''.join(o.get('text',''))+''.join(o.get('data',{}).get('text/plain',''))
for pid in ['scored_0082','scored_0284','scored_0577','scored_0746','scored_0834']:
    print(pid,'ours',best_len(pid), 'mentions', [m.start() for m in re.finditer(pid,txt)][:5])
tiny=[p for p,z in P.items() if z['limit']<=16]
print('tiny',len(tiny),sum(best_len(p) for p in tiny))
