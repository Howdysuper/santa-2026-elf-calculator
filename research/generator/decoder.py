"""Generator decoder for structured Santa-2026 puzzles.

Model (validated in FINDINGS.md):
  target = k * M + c                      (level 1)
  target = m2 * (m1 * M + c1) + c2        (level 2, nested affine)
  M = product of 1..3 hidden atoms (hub values, ~10-24 bits), k/m1/m2 'multipliers', |c|,|c1|,|c2| <= C small.
Atoms come from (a) the statistical hub scan over the targets (hubs.py) and/or (b) values of an existing program.

API:
  decode(pz, atoms=None, C=4096) -> dict(atoms=[...], expl={t: expr}, unexplained=[...])
  estimate_len(pz, dec) -> estimated instruction count of a generator-aware construction
CLI:
  python decoder.py practice|scored [--prog] ids...   (--prog: take atoms from best/<id>.json values too)
"""
import sys, math, json, itertools, collections
sys.path.insert(0, 'src')
sys.path.insert(0, 'research/generator')

C_DEF = 4096


def strip_small(h, B=64):
    for p in range(2, B):
        while h % p == 0 and h > p: h //= p
    return h


def monomials(atoms, tmax, maxdeg=3):
    out = {}
    for d in range(1, maxdeg + 1):
        for comb in itertools.combinations_with_replacement(range(len(atoms)), d):
            M = math.prod(atoms[i] for i in comb)
            if M <= tmax and M not in out: out[M] = comb
    return out


def signed_mod(t, M):
    r = t % M
    return r - M if r > M // 2 else r


def explain(t, monos, C, sigbits=6.0):
    """best explanation of t over the monomials; returns (score_bits, expr) or None.
    score = significance in bits (how unlikely by chance)."""
    best = None
    for M, comb in monos.items():
        if M * 2 > t and M != t: continue
        r = signed_mod(t, M)
        if abs(r) <= C:
            k = (t - r) // M
            sig = math.log2(M / (2 * abs(r) + 1)) if r else math.log2(M)
            if sig >= sigbits:
                e = ('L1', comb, k, r, sig)
                if best is None or sig > best[0]: best = (sig, e)
    if best: return best
    # level 2 (nested): only for large monomials where r = m2*c1 + c2 is small relative to M
    for M, comb in monos.items():
        if M < (1 << 30) or M * 2 > t: continue
        r = signed_mod(t, M)
        if abs(r) > (1 << 33) or abs(r) > M >> 6: continue
        for c2 in range(-1024, 1025):
            s, rr = t - c2, r - c2
            if rr == 0: continue
            g = math.gcd(s, abs(rr))
            if g < 2 or g > (1 << 24): continue
            c1 = rr // g
            if abs(c1) > C: continue
            m1 = (s // g - c1) // M
            sig = math.log2(M) - math.log2(abs(r) + 1) + math.log2(g) - 13  # rough
            e = ('L2', comb, m1, c1, g, c2, sig)
            if best is None or sig > best[0]: best = (sig, e)
            break
    return best


def decode(pz, atoms=None, C=C_DEF, use_hubs=True, maxdeg=3):
    T = pz['targets']
    A = set()
    if use_hubs:
        import hubs
        for H, n, s, hs in hubs.hubs(T, C=1024, maxh=6):
            A.add(H); hs2 = strip_small(H)
            if hs2 >= 512: A.add(hs2)
    if atoms: A |= {a for a in atoms if a >= 512}
    A = sorted(A)
    monos = monomials(A, max(T), maxdeg)
    expl, un = {}, []
    for t in T:
        b = explain(t, monos, C)
        if b: expl[t] = b[1]
        else: un.append(t)
    # target-from-target affine links for the rest: t = m*u + c, u earlier target or explained base
    for t in list(un):
        for u in T:
            if u >= t: break
            m = t // u
            for mm in (m, m + 1):
                c = t - mm * u
                if abs(c) <= (1 << 16) and mm <= (1 << 20) and math.log2(u / (2 * abs(c) + 1)) >= 12:
                    expl[t] = ('AFF', u, mm, c); un.remove(t); break
            if t in expl: break
    return dict(atoms=A, expl=expl, unexplained=un)


def bits(x): return max(1, abs(x).bit_length())


def estimate_len(pz, dec, per_const=1.0):
    """generator-aware program length estimate:
    atoms: ceil(bits/6.5)+1 each (built from starts + shared small constants),
    monomials: deg-1 multiplications each (shared), per target: (k!=1) + (c!=0) (+2 for level 2),
    distinct multipliers / offsets not trivially available: ~ceil(bits/7) each (shared across targets),
    unexplained targets: 'random' cost ~ bits/7 + 1."""
    A = dec['atoms']; used_atoms = set(); monos = set(); consts = set(); per = 0
    for t, e in dec['expl'].items():
        if e[0] == 'L1':
            _, comb, k, r, _ = e
            used_atoms |= set(comb); monos.add(comb)
            per += (k != 1) + (r != 0); consts |= {k, abs(r)}
        elif e[0] == 'L2':
            _, comb, m1, c1, g, c2, _ = e
            used_atoms |= set(comb); monos.add(comb)
            per += (m1 != 1) + (c1 != 0) + 1 + (c2 != 0); consts |= {m1, abs(c1), g, abs(c2)}
        else:
            _, u, mm, c = e
            per += (mm != 1) + (c != 0); consts |= {mm, abs(c)}
    consts -= {0, 1}; consts -= set(pz['starts'])
    cost_atoms = sum(math.ceil(bits(A[i]) / 6.5) + 1 for i in used_atoms)
    cost_monos = sum(len(c) - 1 for c in monos)
    cost_consts = sum(max(1, math.ceil((bits(k) - 4) / 7)) for k in consts)
    cost_un = sum(math.ceil(bits(t) / 7) + 1 for t in dec['unexplained'])
    return dict(total=cost_atoms + cost_monos + cost_consts + per + cost_un, atoms=cost_atoms, monos=cost_monos,
                consts=cost_consts, per_target=per, unexpl=cost_un)


def estimate_len2(pz, dec, const_cost=0.5):
    """Refined generator-aware estimate (shared (M,k) products counted once, small constants pooled):
    atoms ceil(bits/7)+1; monomials deg-1; each distinct (M,k) product 1 op (if k>1);
    per target 1 op for +c (0 if c==0 and product is the target); L2 adds 2, AFF 2;
    distinct small constants (k, |c|, m's) cost const_cost each (built from a shared small pool);
    unexplained targets bits/7+1."""
    A = dec['atoms']; used = set(); monos = set(); prods = set(); consts = set(); per = 0
    for t, e in dec['expl'].items():
        if e[0] == 'L1':
            _, comb, k, r, _ = e
            used |= set(comb); monos.add(comb)
            if k > 1 and (comb, k) not in prods: prods.add((comb, k)); per += 1
            per += (r != 0); consts |= {k, abs(r)}
        elif e[0] == 'L2':
            _, comb, m1, c1, g, c2, _ = e
            used |= set(comb); monos.add(comb)
            per += (m1 > 1) + (c1 != 0) + 1 + (c2 != 0); consts |= {m1, abs(c1), g, abs(c2)}
        else:
            _, u, mm, c = e
            per += (mm != 1) + (c != 0); consts |= {mm, abs(c)}
    consts -= {0, 1}; consts -= set(pz['starts'])
    ca = sum(math.ceil(bits(A[i]) / 7) + 1 for i in used)
    cm = sum(len(c) - 1 for c in monos)
    cc = const_cost * len(consts)
    cu = sum(math.ceil(bits(t) / 7) + 1 for t in dec['unexplained'])
    return dict(total=round(ca + cm + cc + per + cu), atoms=ca, monos=cm, consts=round(cc), per=per, unexpl=cu)


def prog_values(pz, prog):
    R = [None] * 48; out = []
    for k, v in enumerate(pz['starts']): R[k] = v
    for op, i, j, d in prog:
        a, b = R[i], R[j]
        c = {'+': a + b, '-': a - b, '*': a * b, '/': a // b if b else 0}[op]
        R[d] = c; out.append(c)
    return out


def prog_atoms(pz, prog, R=1 << 12, top=8):
    """candidate atoms from an existing program: values 2^12..2^26 that leave small residues on >= 3 targets"""
    T = pz['targets']; vals = sorted({v for v in prog_values(pz, prog) if (1 << 12) < v < (1 << 26)})
    sc = []
    for v in vals:
        s = sum(1 for t in T if t >= 2 * v and abs(signed_mod(t, v)) < R)
        sc.append((s, v))
    sc.sort(reverse=True); A = []
    for s, v in sc:
        if s < 3: break
        if any(v % a == 0 or a % v == 0 for a in A): continue
        A.append(v)
        if len(A) >= top: break
    return A


if __name__ == '__main__':
    from elf import load, BEST
    which = sys.argv[1]; args = sys.argv[2:]
    useprog = '--prog' in args; nohub = '--nohub' in args; args = [a for a in args if not a.startswith('--')]
    P = load(practice=(which == 'practice'))
    for pid in args:
        pz = P[pid]; atoms = None; L = None
        if useprog:
            prog = json.loads((BEST / f"{pid}.json").read_text()); L = len(prog)
            atoms = prog_atoms(pz, prog)
        dec = decode(pz, atoms, use_hubs=not nohub)
        est = estimate_len(pz, dec)
        n = len(pz['targets'])
        kinds = collections.Counter(e[0] for e in dec['expl'].values())
        print(pid, pz.get('family'), 'nt', n, 'expl', len(dec['expl']), dict(kinds), 'atoms', dec['atoms'], 'est', est, 'best', L)
        sys.stdout.flush()
