"""Family classifier (rule based, from generator findings). Validated on practice labels; applied to scored.
Writes research/generator/scored_family.csv (id,family,nt,best_len,per_target)."""
import sys, math, json, collections
sys.path.insert(0, 'src')
from elf import load, BEST


def feats(pz):
    T = pz['targets']; n = len(T)
    D = math.ceil(math.log10(max(T) + 1))
    # decade with most targets among 10^(d-1)..10^d (d = 6..18)
    dec = collections.Counter(math.ceil(math.log10(t + 1)) for t in T)
    dbest, nbest = max(dec.items(), key=lambda x: (x[1], x[0]))
    bits = sorted(math.log2(t) for t in T)
    med = bits[n // 2]
    return dict(n=n, maxstart=max(pz['starts']), topdec=dec.get(D, 0) / n, dmode=dbest, fmode=nbest / n,
                med=med, minb=bits[0], maxb=bits[-1], span=bits[-1] - bits[0])


def classify(pz):
    f = feats(pz)
    if max(pz['starts']) <= 16 and f['maxb'] <= 4.1: return 'tiny'
    if f['maxstart'] >= 100 or (f['span'] < 3.4 and f['n'] > 3): return 'independent'
    # mixed: a block of ~half the targets uniform in one decade (12/15/18 or 6/9 for medium) sitting at the top
    if f['fmode'] >= 0.38 and f['dmode'] in (6, 9, 12, 15, 18) and f['span'] > 5:
        T = pz['targets']; d = f['dmode']
        inside = [t for t in T if 10 ** (d - 1) <= t < 10 ** d]
        below = [t for t in T if t < 10 ** (d - 1)]
        above = [t for t in T if t >= 10 ** d]
        if len(below) >= 0.25 * len(T) and len(above) <= 2 and min(inside) < 10 ** (d - 1) * 3:
            return 'mixed'
    # shared vs multiplicative: shared targets are larger (median ~2^33) ; multiplicative median ~2^22
    return 'multiplicative' if f['med'] < 27.5 else 'shared'


if __name__ == '__main__':
    PP = load(practice=True)
    conf = collections.Counter()
    for pid, pz in PP.items():
        conf[(pz['family'], classify(pz))] += 1
    fams = ['independent', 'shared', 'multiplicative', 'mixed', 'tiny']
    print('practice confusion (true -> predicted):')
    for a in fams:
        print(' ', a, {b: conf[(a, b)] for b in fams if conf[(a, b)]})
    acc = sum(v for (a, b), v in conf.items() if a == b) / len(PP)
    print('accuracy', round(acc, 3))
    # median bits per family to show separation
    for a in fams[:4]:
        m = sorted(feats(pz)['med'] for pz in PP.values() if pz['family'] == a)
        print(a, 'median-target-bits quartiles', [round(m[int(q * (len(m) - 1))], 1) for q in (0, .25, .5, .75, 1)])
    P = load()
    rows = []
    agg = collections.defaultdict(lambda: [0, 0, 0])
    for pid, pz in sorted(P.items()):
        fam = classify(pz); L = len(json.loads((BEST / f"{pid}.json").read_text())); n = len(pz['targets'])
        rows.append((pid, fam, n, L, round(L / n, 3)))
        a = agg[fam]; a[0] += 1; a[1] += L; a[2] += n
    with open('research/generator/scored_family.csv', 'w') as fh:
        fh.write('id,family,nt,best_len,per_target\n')
        for r in rows: fh.write(','.join(map(str, r)) + '\n')
    print('scored by predicted family: puzzles, instructions, targets, instr/target')
    for k, a in sorted(agg.items()): print(' ', k, a[0], a[1], a[2], round(a[1] / a[2], 2))
