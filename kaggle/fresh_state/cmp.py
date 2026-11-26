import sys, json
sys.path.insert(0, 'src')
from elf import load, best_len, replay
P = load(); better = 0; gain = 0; invalid = 0; rows = 0; ids = set()
for fn in sys.argv[1:]:
    for line in open(fn):
        x = line.split()
        if not x or x[0] not in P: continue
        n = int(x[1]); prog = [[x[2+4*k], int(x[3+4*k]), int(x[4+4*k]), int(x[5+4*k])] for k in range(n)]
        rows += 1
        try: replay(P[x[0]], prog)
        except ValueError: invalid += 1; continue
        b = best_len(x[0])
        if n < b: better += 1; gain += b - n; ids.add(x[0])
print(f"compare: {rows} rows read, {invalid} invalid, {better} strictly shorter than the store on {len(ids)} ids, total gain {gain}")
