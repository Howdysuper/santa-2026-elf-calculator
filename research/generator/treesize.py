"""Minimal expression-TREE size (no sharing) of each target from the starts, up to 5 ops (MITM),
compared with random controls of the same magnitude. Tests 'targets = short formulas of the starts'."""
import sys, random, collections
sys.path.insert(0, 'src')
from elf import load


def ops(a, b, lim):
    out = [a + b, a * b]
    if a > b: out.append(a - b)
    if b > a: out.append(b - a)
    if a % b == 0: out.append(a // b)
    if b % a == 0: out.append(b // a)
    return [v for v in out if 0 < v <= lim]


def levels(S, lim, K=3, cap=3_000_000):
    L = [set(S)]
    allv = set(S)
    for k in range(1, K + 1):
        new = set()
        for i in range(0, k):
            j = k - 1 - i
            if j < i: break
            A, B = L[i], L[j]
            for a in A:
                for b in B:
                    for v in ops(a, b, lim):
                        if v not in allv: new.add(v)
            if len(new) > cap: break
        L.append(new); allv |= new
    return L


def size_of(t, L):
    for k, s in enumerate(L):
        if t in s: return k
    K = len(L) - 1
    # sizes K+1 .. K+2 via t = a op b, a in L[i], b in L[j], i+j+1 = size
    for size in (K + 1, K + 2):
        for i in range(0, size):
            j = size - 1 - i
            if j > K or i > K or i > j: continue
            for a in L[i]:
                for b in (t - a, a - t, t + a):
                    if b > 0 and b in L[j]: return size
                if a and t % a == 0 and (t // a) in L[j]: return size
                if a % t == 0 and (a // t) in L[j]: return size
                if (t * a) in L[j]: return size
    return 99


if __name__ == '__main__':
    which = sys.argv[1]; ids = sys.argv[2:]
    P = load(practice=(which == 'practice'))
    rnd = random.Random(1)
    agg = collections.defaultdict(collections.Counter)
    for pid in ids:
        pz = P[pid]; lim = pz['limit']
        L = levels(pz['starts'], lim, 3)
        real = [size_of(t, L) for t in pz['targets']]
        ctrl = [size_of(rnd.randint(t * 9 // 10, t * 11 // 10), L) for t in pz['targets']]
        fam = pz.get('family')
        agg[fam + '_real'].update(real); agg[fam + '_ctrl'].update(ctrl)
        print(pid, fam, 'real', sorted(real), 'ctrl', sorted(ctrl)); sys.stdout.flush()
    for k, v in sorted(agg.items()): print(k, sorted(v.items()))
