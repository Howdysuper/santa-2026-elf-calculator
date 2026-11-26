"""Offer solver output files (id n op a b d ...) to the best store. usage: python import_out.py FILE [...]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, offer, best_len
P = load()
for fn in sys.argv[1:]:
    gain = 0
    for line in open(fn):
        x = line.split()
        if not x or x[0] not in P: continue
        n = int(x[1]); prog = [[x[2 + 4 * k], int(x[3 + 4 * k]), int(x[4 + 4 * k]), int(x[5 + 4 * k])] for k in range(n)]
        gain += offer(P[x[0]], x[0], prog, source=Path(fn).parent.name)
    print(f"{fn}: gain {gain}; store total {sum(best_len(p) for p in P)}")
