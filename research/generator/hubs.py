"""Statistical hub scan (chunked, low memory): H in [HMIN, HMAX) scored by binomial surprise of #targets with
|t mod+- H| <= C. Clustered targets (within 2C) count once. Neighbour-sharpness filter removes near-ratio artifacts.
hubs(T) -> list of (H, hits, surprise_log10, hitset)."""
import sys, math
import numpy as np
from scipy.stats import binom
sys.path.insert(0, 'src')

HMIN, HMAX = 1 << 11, 1 << 22
CH = 1 << 20


def _res(t, H):
    if t < (1 << 62):
        r = np.int64(t) % H
    else:
        hi, lo = divmod(t, 1 << 31)
        r = ((np.int64(hi) % H) * np.int64(1 << 31) + np.int64(lo)) % H
    return np.minimum(r, H - r)


def cluster_reps(T, C):
    act = [True] * len(T)
    for k in range(1, len(T)):
        if T[k] - T[k - 1] <= 2 * C: act[k] = False
    return act


def resid(t, H):
    r = t % H
    return min(r, H - r)


def hubs(T, C=1024, maxh=10, thr=8.0, top=300):
    act = cluster_reps(T, C)
    TA = [t for t, a in zip(T, act) if a]
    cands = []
    for h0 in range(HMIN, HMAX, CH):
        H = np.arange(h0, min(HMAX, h0 + CH), dtype=np.int64)
        nh = np.zeros(len(H), dtype=np.int32); n = np.zeros(len(H), dtype=np.int32)
        for t in TA:
            big = H * 2 <= t
            n += big
            nh += (_res(t, H) <= C) & big
        ok = nh >= 3
        if ok.any():
            Hs, nk, nn = H[ok], nh[ok], n[ok]
            p = np.minimum(1.0, (2 * C + 1) / Hs.astype(np.float64))
            with np.errstate(divide='ignore'):
                s = -binom.logsf(nk - 1, nn, p) / math.log(10)
            for i in np.argsort(-s)[:top]:
                if s[i] >= thr: cands.append((float(s[i]), int(Hs[i]), int(nk[i])))
    cands.sort(reverse=True)
    out = []
    for s, H, nh in cands:
        hs = frozenset(k for k in range(len(T)) if act[k] and T[k] >= 2 * H and resid(T[k], H) <= C)
        nb = max(sum(1 for k in hs if resid(T[k], H + d) <= C) for d in (-1, 1))
        if nb >= 0.5 * len(hs): continue
        if any((H % H2 == 0 or H2 % H == 0) and len(hs & hs2) >= 0.6 * min(len(hs), len(hs2)) for H2, _, _, hs2 in out):
            continue
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
        print(pid, pz.get('family'), len(pz['targets']), [(h, n, round(s, 1)) for h, n, s, _ in hb]); sys.stdout.flush()
