import sys, json, csv, collections, random
sys.path.insert(0, 'src'); sys.path.insert(0, 'research/generator')
import decoder
from elf import load, BEST
P = load()
fam = {r['id']: r['family'] for r in csv.DictReader(open('research/generator/scored_family.csv'))}
ids = [p for p in sorted(P) if fam[p] == 'independent']
random.Random(3).shuffle(ids)
c = collections.Counter()
for pid in ids[:40]:
    pz = P[pid]; prog = json.loads((BEST / f"{pid}.json").read_text())
    A = decoder.prog_atoms(pz, prog)
    dec = decoder.decode(pz, A, use_hubs=False)
    c['nt'] += len(pz['targets']); c['expl'] += len(dec['expl'])
    for e in dec['expl'].values():
        c[e[0]] += 1
        if e[0] == 'L1' and len(e[1]) >= 2: c['L1deg2+'] += 1
print('independent FP (40 puzzles, frontier atoms):', dict(c), 'frac %.3f' % (c['expl'] / c['nt']))
