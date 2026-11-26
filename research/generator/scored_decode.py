"""Run decoder (atoms from frontier program values) on all scored structured puzzles; compare estimate vs best."""
import sys, json, csv, collections, math
sys.path.insert(0, 'src'); sys.path.insert(0, 'research/generator')
import decoder
from elf import load, BEST
P = load()
fam = {r['id']: r['family'] for r in csv.DictReader(open('research/generator/scored_family.csv'))}
agg = collections.defaultdict(lambda: collections.Counter())
out = open('research/generator/scored_decode.csv', 'w')
out.write('id,family,nt,explained,L1,L2,AFF,natoms,est_opt,est_pess,best\n')
for pid, pz in sorted(P.items()):
    f = fam[pid]
    if f not in ('shared', 'mixed', 'multiplicative'): continue
    prog = json.loads((BEST / f"{pid}.json").read_text()); L = len(prog)
    A = decoder.prog_atoms(pz, prog)
    dec = decoder.decode(pz, A, use_hubs=False)
    e1 = decoder.estimate_len2(pz, dec, 0.5)['total']; e2 = decoder.estimate_len2(pz, dec, 1.0)['total']
    k = collections.Counter(e[0] for e in dec['expl'].values())
    n = len(pz['targets'])
    out.write(f"{pid},{f},{n},{len(dec['expl'])},{k['L1']},{k['L2']},{k['AFF']},{len(A)},{e1},{e2},{L}\n"); out.flush()
    a = agg[f]; a['n'] += 1; a['nt'] += n; a['expl'] += len(dec['expl']); a['L1'] += k['L1']; a['L2'] += k['L2']; a['AFF'] += k['AFF']
    a['best'] += L; a['est_opt'] += e1; a['est_pess'] += e2
    a['better_opt'] += (e1 < L); a['gain_opt'] += max(0, L - e1)
out.close()
for f, a in agg.items():
    print(f, dict(a), 'expl frac %.3f' % (a['expl'] / a['nt']))
