"""Statistical hub scan: H in [HMIN, HMAX) scored by binomial surprise of #targets with |t mod+- H| <= C.
Iterative: pick best H, dedupe divisors/multiples, repeat. Returns list of (H, hits, surprise, hitset)."""
import sys, math
import numpy as np
from scipy.stats import binom
sys.path.insert(0, 'src')

HMIN, HMAX = 1 << 10, 1 << 24
_H = np.arange(HMIN, HMAX, dtype=np.int64)


def residues(T):
    R = np.empty((len(T), len(_H)), dtype=np.int64)
    for k, t in enumerate(T):
        if t < (1 << 62):
            r = np.int64(t) % _H
        else:  # avoid overflow issues: split
            hi, lo = divmod(t, 1 << 31)
            r = ((np.int64(hi) % _H) * np.int64(1 << 31) + np.int64(lo)) % _H
        R[k] = np.minimum(r, _H - r)
    return R


def scan(T, C=1024, top=40, R=None, active=None):
    if R is None: R = residues(T)
    if active is None: active = np.ones(len(T), dtype=bool)
    hit = (R[active] <= C)
    # only count targets large enough: t >= H*2 (quotient >= 2)
    Ta = np.array([float(t) for t in np.array(T, dtype=object)[active]])
    big = Ta[:, None] >= 2.0 * _H[None, :]
    hit &= big
    nh = hit.sum(0)
    n = big.sum(0)
    p = np.minimum(1.0, (2 * C + 1) / _H.astype(np.float64))
    with np.errstate(divide='ignore'):
        s = -binom.logsf(nh - 1, n, p) / math.log(10)
    s[nh < 2] = 0
    idx = np.argsort(-s)[:top]
    return [(int(_H[i]), int(nh[i]), float(s[i])) for i in idx], R


def cluster_reps(T, C):
    act = np.ones(len(T), dtype=bool)
    for k in range(1, len(T)):
        if T[k] - T[k - 1] <= 2 * C: act[k] = False
    return act


def hubs(T, C=1024, maxh=10, thr=8.0):
    R = residues(T)
    act = cluster_reps(T, C)
    res, _ = scan(T, C, top=400, R=R, active=act)
    out = []
    for H, nh, s in res:
        if s < thr: break
        hs = frozenset(k for k in range(len(T)) if act[k] and R[k, H - HMIN] <= C and T[k] >= 2 * H)
        # sharpness: a real hub divides t-c; neighbours H+-1 must not share the hits (else it's a near-ratio artifact)
        nb = max(sum(1 for k in hs if HMIN <= H + d < HMAX and R[k, H + d - HMIN] <= C) for d in (-1, 1))
        if nb >= 0.5 * len(hs): continue
        dup = False
        for j, (H2, nh2, s2, hs2) in enumerate(out):
            if (H % H2 == 0 or H2 % H == 0) and len(hs & hs2) >= 0.6 * min(len(hs), len(hs2)):
                dup = True; break
        if not dup:
            out.append((H, nh, s, hs))
        if len(out) >= maxh: break
    return out


if __name__ == '__main__':
    from elf import load
    which = sys.argv[1]; ids = sys.argv[2:]
    P = load(practice=(which == 'practice'))
    for pid in ids:
        pz = P[pid]
        hb = hubs(pz['targets'])
        print(pid, pz.get('family'), len(pz['targets']), [(h, n, round(s, 1)) for h, n, s, _ in hb])

