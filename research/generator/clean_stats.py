"""Per family: explained fraction counting only FP-clean forms (L1 with monomial degree>=2, AFF),
plus cluster stats; independent baseline included. Atoms from frontier programs (best/)."""
import sys, json, csv, collections
sys.path.insert(0, 'src'); sys.path.insert(0, 'research/generator')
import decoder
from elf import load, BEST
P = load()
fam = {r['id']: r['family'] for r in csv.DictReader(open('research/generator/scored_family.csv'))}
agg = collections.defaultdict(collections.Counter)
ks = collections.defaultdict(list); cs = collections.defaultdict(list); degs = collections.defaultdict(collections.Counter)
for pid, pz in sorted(P.items()):
    f = fam[pid]
    if f == 'tiny': continue
    if f == 'independent' and int(pid[-4:]) % 4: continue  # subsample
    prog = json.loads((BEST / f"{pid}.json").read_text())
    A = decoder.prog_atoms(pz, prog)
    dec = decoder.decode(pz, A, use_hubs=False)
    a = agg[f]; a['puz'] += 1; a['nt'] += len(pz['targets']); a['best'] += len(prog)
    prods = collections.Counter()
    for t, e in dec['expl'].items():
        if e[0] == 'L1' and len(e[1]) >= 2:
            a['clean'] += 1; ks[f].append(e[2]); cs[f].append(abs(e[3])); degs[f][len(e[1])] += 1
            prods[(e[1], e[2])] += 1
        elif e[0] == 'AFF': a['clean'] += 1; a['aff'] += 1
    a['clustered'] += sum(v for v in prods.values() if v > 1)
    a['natoms'] += len(A)
for f, a in agg.items():
    k = sorted(ks[f]); c = sorted(cs[f]); q = lambda v, x: v[int(x * (len(v) - 1))] if v else None
    print(f, dict(a), 'clean frac %.3f' % (a['clean'] / a['nt']), 'deg', dict(degs[f]),
          'k quartiles', [q(k, x) for x in (.1, .5, .9)], '|c| quartiles', [q(c, x) for x in (.5, .9, .99)])
