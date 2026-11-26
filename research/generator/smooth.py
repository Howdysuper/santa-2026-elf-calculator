"""Level-1 decoder: for every target t find offsets c (|c|<=C) with t-c fully factorable over primes < PMAX.
Large primes (>= LARGE) that recur across targets are 'atom primes'. A target is explained at level 1 if some
t-c = smooth(<LARGE) * product of atom primes.
Usage: python smooth.py [practice|scored] [C] [ids...]"""
import sys, math, collections, json
import numpy as np
sys.path.insert(0, 'src')
from elf import load

PMAX = 1 << 22
LARGE = 1 << 8


def primes_upto(n):
    s = np.ones(n + 1, dtype=bool); s[:2] = False
    for i in range(2, int(n ** .5) + 1):
        if s[i]: s[i * i::i] = False
    return np.nonzero(s)[0].astype(np.int64)


PR = primes_upto(PMAX)
PR_SMALL = PR[PR <= 2 * 4096 + 1]


def smooth_offsets(t, C):
    """dict c -> list of (prime, exponent) full factorization of t-c over primes<PMAX (only when fully smooth)."""
    hits = collections.defaultdict(list)
    r = np.int64(t) % PR if t < (1 << 63) else np.array([t % int(p) for p in PR], dtype=np.int64)
    big = PR > 2 * C
    # big primes: c = r or r-p
    pb, rb = PR[big], r[big]
    m1 = rb <= C
    for p, c in zip(pb[m1].tolist(), rb[m1].tolist()): hits[c].append(p)
    m2 = (pb - rb) <= C
    for p, c in zip(pb[m2].tolist(), (rb - pb)[m2].tolist()): hits[c].append(p)
    ps, rs = PR[~big].tolist(), r[~big].tolist()
    for p, rr in zip(ps, rs):
        c = rr - ((rr + C) // p) * p  # smallest c >= -C with c = rr mod p
        while c <= C:
            hits[c].append(p); c += p
    out = {}
    for c, plist in hits.items():
        s = t - c
        if s <= 0: continue
        fac = []
        for p in plist:
            e = 0
            while s % p == 0: s //= p; e += 1
            fac.append((p, e))
        if s == 1: out[c] = fac
    return out


def analyse(pz, C=2048, need=2):
    T = pz['targets']
    cand = {t: smooth_offsets(t, C) for t in T}
    # count large primes across targets
    cnt = collections.Counter()
    for t, d in cand.items():
        ps = set()
        for c, fac in d.items():
            for p, e in fac:
                if p >= LARGE: ps.add(p)
        cnt.update(ps)
    atomp = {p for p, k in cnt.items() if k >= need}
    expl = {}
    for t, d in cand.items():
        best = None
        for c, fac in d.items():
            L = [(p, e) for p, e in fac if p >= LARGE]
            if all(p in atomp for p, e in L) and L:
                key = (abs(c), c)
                if best is None or key < best[0]: best = (key, c, fac)
        if best: expl[t] = (best[1], best[2])
    return cand, cnt, atomp, expl


if __name__ == '__main__':
    which = sys.argv[1]; C = int(sys.argv[2]); ids = sys.argv[3:]
    P = load(practice=(which == 'practice'))
    if not ids: ids = sorted(P)
    for pid in ids:
        pz = P[pid]
        cand, cnt, atomp, expl = analyse(pz, C)
        top = [(p, k) for p, k in cnt.most_common(12)]
        print(pid, pz.get('family'), 'nt', len(pz['targets']), 'explained', len(expl), 'atomprimes', len(atomp), 'top', top)
        sys.stdout.flush()
