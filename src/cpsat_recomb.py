"""CP-SAT recombination (Aside, 11-19).
For each puzzle: node set = every value of every valid public variant (length <= REL x best) + the current best program
(+ optional extra values). Recipes = every one-instruction way (a op b) to make a node from two nodes/starts.
CP-SAT: bool x_v (node built), bool y_r (recipe used), int level l_v; sum_r y_r = x_v, y_r => x_a, x_b and l_v > l_a, l_b;
all targets built; minimize sum x_v. The current best is given as a hint (so the result is never worse).
Then schedule + register-allocate (<= 48 live) + replay-validate; write improvements to OUT (id n op a b d ...).
usage: python src/cpsat_recomb.py VARIANTS.json IDSFILE OUT [SEC=60] [WORKERS=8] [REL=1.3]
needs PYTHONPATH=<santa-2026>/ortools_lib
"""
import sys, json, time, collections, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, BEST, replay
from ortools.sat.python import cp_model

VJ = json.load(open(sys.argv[1])); ids = [l.strip() for l in open(sys.argv[2]) if l.strip()]; OUT = sys.argv[3]
SEC = float(sys.argv[4]) if len(sys.argv) > 4 else 60; WORK = int(sys.argv[5]) if len(sys.argv) > 5 else 8
REL = float(sys.argv[6]) if len(sys.argv) > 6 else 1.3
P = load()
import os
STRUCT = bool(os.environ.get('STRUCT')); WIDE = os.environ.get('STRUCT') == '2'; SCRATCH = bool(os.environ.get('SCRATCH')); NOFRONT = bool(os.environ.get('NOFRONT'))
LNSMODE = bool(os.environ.get('LNSMODE')); LNS_K = int(os.environ.get('LNS_K', '5')); LNS_D = int(os.environ.get('LNS_D', '2')); LNS_CAP = int(os.environ.get('LNS_CAP', '600')); LNS_T = float(os.environ.get('LNS_T', '10')); LNS_ZMAX = int(os.environ.get('LNS_ZMAX', '16'))
MITM = bool(os.environ.get('MITM')); MITM_SM = int(os.environ.get('MITM_SM', '400')); MITM_ALLBASE = bool(os.environ.get('MITM_ALLBASE')); MITM_K = int(os.environ.get('MITM_K', '30'))
CMAX = (1 << 15) if WIDE else (1 << 13); NC = 6 if WIDE else 3
HUBS = {}
if STRUCT and Path('work/hubs_all.txt').exists():
    for l in open('work/hubs_all.txt'):
        x = l.split(); HUBS[x[0]] = [(int(a), int(b), float(c)) for a, b, c in (t.split(':') for t in x[1:])]
OPS = {'+': lambda a, b: a + b, '-': lambda a, b: a - b, '*': lambda a, b: a * b, '/': lambda a, b: a // b}

def values(pz, prog):
    R = [None] * 48
    for k, v in enumerate(pz['starts']): R[k] = v
    out = []
    for op, i, j, d in prog:
        a, b = R[i], R[j]; c = OPS[op](a, b); R[d] = c; out.append((c, op, a, b))
    return out

def allocate(pz, order, recipe):
    """order: node values in build order; recipe[v] = (op, a, b). Returns instruction list or None (> 48 live)."""
    starts = pz['starts']; pos = {v: k for k, v in enumerate(order)}
    last = {}
    for k, v in enumerate(order):
        op, a, b = recipe[v]
        last[a] = k; last[b] = k
    reg = {}; owner = [None] * 48
    for k, v in enumerate(starts):
        if v not in reg: reg[v] = k; owner[k] = v
    for k, v in enumerate(starts):
        if last.get(v, -1) < 0 and owner[k] == v: owner[k] = None  # never read: free
    prog = []
    for k, v in enumerate(order):
        op, a, b = recipe[v]
        if a not in reg or b not in reg or owner[reg[a]] != a and a not in starts or owner[reg[b]] != b and b not in starts:
            pass
        ra, rb = reg.get(a), reg.get(b)
        if ra is None or rb is None: return None
        if last.get(a) == k and owner[ra] == a: owner[ra] = None
        if last.get(b) == k and owner[rb] == b: owner[rb] = None
        rd = next((r for r in range(48) if owner[r] is None), None)
        if rd is None: return None
        prog.append([op, ra, rb, rd])
        reg[v] = rd; owner[rd] = v if last.get(v, -1) > k else None
    return prog

import numpy as np, random
def build_recipes(nodes, SS, LIM):
    arr = np.array(nodes, dtype=np.int64); N = len(arr)
    def member(q):
        i = np.searchsorted(arr, q); i = np.clip(i, 0, N - 1); return arr[i] == q
    rec = []
    for v in nodes:
        if v in SS: continue
        A = arr[2 * arr <= v]
        if len(A):
            d = v - A; mk = member(d)
            rec += [(v, '+', int(a), int(b)) for a, b in zip(A[mk], d[mk])]
        r = int(math.isqrt(v)); A = arr[(arr > 1) & (arr <= r)]
        if len(A):
            mk = (v % A) == 0; A2 = A[mk]; q = v // A2; mk2 = member(q)
            rec += [(v, '*', int(a), int(b)) for a, b in zip(A2[mk2], q[mk2])]
        A = arr[arr <= LIM - v]
        if len(A):
            sm = v + A; mk = member(sm)
            rec += [(v, '-', int(b), int(a)) for a, b in zip(A[mk], sm[mk])]
        A = arr[(arr > 1) & (arr <= LIM // v)]
        if len(A):
            p = A * v; mk = member(p)
            rec += [(v, '/', int(b), int(a)) for a, b in zip(A[mk], p[mk])]
    return list(dict.fromkeys(rec))

def lns_solve(pz, nodes, rec, hint_rec, best, T, SS):
    byv = collections.defaultdict(list)
    for k, r in enumerate(rec): byv[r[0]].append(k)
    # initial solution: recipes of the hint program, restricted to what the targets need
    cur = {}
    def need(v):
        if v in SS or v in cur: return
        cur[v] = hint_rec[v]; op, a, b = cur[v]; need(a); need(b)
    for t in T: need(t)
    best_sol = dict(cur); t_end = time.time() + SEC; it = 0; acc = 0
    TL = sorted(T)
    while time.time() < t_end:
        it += 1
        # consumers in current solution
        cons = collections.defaultdict(set)
        for v, (op, a, b) in cur.items(): cons[a].add(v); cons[b].add(v)
        # neighbourhood: k targets (random, or all targets downstream of a random shared base)
        if random.random() < 0.8:
            bases = [v for v in cur if v not in T and len(cons[v]) >= 2 and v > (1 << 20)]
            Z = set()
            for b0 in random.sample(bases, min(len(bases), random.choice((1, 1, 2)))):
                st = [b0]
                while st:
                    x = st.pop()
                    for c in cons[x]:
                        if c in T: Z.add(c)
                        st.append(c)
            if len(Z) > LNS_ZMAX: Z = set(random.sample(sorted(Z), LNS_ZMAX))
            if not Z: Z = {random.choice(TL)}
        else:
            Z = set(random.sample(TL, min(len(TL), LNS_K)))
        # ancestors needed by targets outside Z stay fixed
        keep = set()
        def anc(v):
            if v in SS or v in keep: return
            keep.add(v); op, a, b = cur[v]; anc(a); anc(b)
        for t in T - Z: anc(t)
        fixed = keep  # values (with their recipes) kept as is
        zone = set(cur) - fixed  # exclusive cones of Z (incl. Z)
        Z = Z - fixed
        if not Z: continue
        # candidate free nodes: backward closure in recipe graph from Z, depth LNS_D
        free = set(zone); frontier = set(Z)
        for _ in range(LNS_D):
            nxt = set()
            for v in frontier:
                for k in byv[v]:
                    _, op, a, b = rec[k]
                    for u in (a, b):
                        if u not in SS and u not in fixed and u not in free: nxt.add(u)
            if len(free) + len(nxt) > LNS_CAP: nxt = set(random.sample(sorted(nxt), max(0, LNS_CAP - len(free))))
            free |= nxt; frontier = nxt
        avail = fixed | SS
        m = cp_model.CpModel()
        X = {v: m.NewBoolVar('') for v in free}
        Lv = {v: m.NewIntVar(0, len(free) + 1, '') for v in free}
        Y = []; yv = collections.defaultdict(list)
        for v in free:
            for k in byv[v]:
                _, op, a, b = rec[k]
                if not all(u in avail or u in free for u in (a, b)): continue
                y = m.NewBoolVar(''); Y.append((y, k)); yv[v].append(y)
                for u in {a, b}:
                    if u in free:
                        m.AddImplication(y, X[u]); m.Add(Lv[v] >= Lv[u] + 1).OnlyEnforceIf(y)
        for v in free: m.Add(sum(yv[v]) == X[v])
        for t in Z: m.Add(X[t] == 1)
        m.Minimize(sum(X.values()))
        for v in free: m.AddHint(X[v], 1 if v in zone else 0)
        for y, k in Y: m.AddHint(y, 1 if rec[k][0] in zone and cur.get(rec[k][0]) == rec[k][1:] else 0)
        s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = min(LNS_T, max(1, t_end - time.time()))
        s.parameters.num_workers = WORK
        st = s.Solve(m)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): continue
        new_zone = {}
        for y, k in Y:
            if s.Value(y): v, op, a, b = rec[k]; new_zone[v] = (op, a, b)
        cand = {v: cur[v] for v in fixed}; cand.update(new_zone)
        if len(cand) <= len(cur):
            if len(cand) < len(cur): acc += 1
            cur = cand
            if len(cur) < len(best_sol):
                best_sol = dict(cur)
                print(f'  lns it {it}: {len(best_sol)} (zone {len(zone)} free {len(free)} Z {len(Z)})', flush=True)
    # schedule + allocate best_sol
    recipe = best_sol; chosen = list(recipe)
    bestpos = {}
    for k2, (c, op, a, b) in enumerate(values(pz, best)): bestpos.setdefault(c, k2)
    def dfs_order(tlist):
        seen = set(); out = []
        def visit(v):
            if v in seen or v in SS: return
            seen.add(v); op, a, b = recipe[v]
            for u in sorted({a, b}, key=lambda u: bestpos.get(u, 10**9)): visit(u)
            out.append(v)
        for t in tlist: visit(t)
        return out
    tl = sorted(T, key=lambda t: bestpos.get(t, 10**9)); prog = None
    for tlist in (tl, sorted(T), sorted(T, reverse=True), tl[::-1]):
        prog = allocate(pz, dfs_order(tlist), recipe)
        if prog is not None: break
    info = f'LNS it {it} improving {acc} sol {len(best_sol)}'
    if prog is None: return len(best), None, len(nodes), len(rec), info + ' regfail', None
    try: replay(pz, prog)
    except ValueError as e: return len(best), None, len(nodes), len(rec), 'invalid ' + str(e), None
    return len(best), prog, len(nodes), len(rec), info, None
def solve(pid):
    pz = P[pid]; starts = pz['starts']; SS = set(starts); T = set(pz['targets']) - SS; LIM = pz['limit']
    best = json.loads((BEST / f'{pid}.json').read_text())
    progs = [best] + [p for p in VJ.get(pid, []) if len(p) <= REL * len(best)]
    if NOFRONT:  # constructor test: only our own constructions (VARIANTS), shortest one is the hint; public best kept for atoms
        own = sorted(VJ.get(pid, []), key=len)
        if not own: raise ValueError('no own construction')
        atoms_src = best; best = own[0]; progs = own + ([atoms_src] if os.environ.get('INCLUDE_PUB') else [])
        print(f'{pid} nofront: {len(own)} own constructions, shortest {len(best)}, public best {len(atoms_src)}', flush=True)
    nodes = set(SS) | T
    hint_rec = {}
    for k, p in enumerate(progs):
        for c, op, a, b in values(pz, p):
            nodes.add(c)
            if k == 0 and c not in hint_rec and c not in SS: hint_rec[c] = (op, a, b)
    FV = set(nodes)
    if SCRATCH:  # from-scratch constructor: frontier values only used to find atoms + fallback cones of unfit targets
        nodes = set(SS) | T; hint_rec = {}
    if STRUCT or SCRATCH:  # structural candidates: atoms (frontier mid values used >= 2x + strong hubs), products, k, |c|, k*M
        import itertools
        uses = collections.Counter(); srcb = {}
        for c, op, a, b in values(pz, best): uses[a] += 1; uses[b] += 1; srcb.setdefault(c, (a, b))
        A = {c for c in FV if (1 << 14) <= c < (1 << 24) and c not in T and uses[c] >= 2}
        A |= {h for h, cnt, z in HUBS.get(pid, []) if z >= (6 if WIDE else 8)}
        A = sorted(A)[:12]
        Ms = set(A) | {a * b for a, b in itertools.combinations_with_replacement(A, 2) if a * b <= LIM}
        if WIDE: Ms |= {a * b * c for a, b, c in itertools.combinations_with_replacement(A[:8], 3) if a * b * c <= LIM}
        add = set(A) | Ms
        for t in T:
            cands = []
            for M in Ms:
                if M >= t: continue
                q = t // M
                for k in (q, q + 1):
                    c = t - k * M
                    if k >= 1 and abs(c) < CMAX and k < (1 << 14): cands.append(((k > 1) * k.bit_length() + abs(c).bit_length(), M, k, c))
            cands.sort()
            for _, M, k, c in cands[:NC]:
                if k > 1: add |= {k, k * M}
                if c: add.add(abs(c))
                if k > 1 and abs(c) >= k:  # nested: t = k*(M + c1) + c2
                    c1 = round(c / k); c2 = c - k * c1
                    if M + c1 > 0: add |= {M + c1, k * (M + c1), abs(c1)}
                    if c2: add.add(abs(c2))
        # target-to-target affine links: Tj = p*Ti + r (p small, |r| small)
        TL = sorted(T)
        for i, ti in enumerate(TL):
            for tj in TL[i + 1:]:
                p = tj // ti
                for pp in (p, p + 1):
                    if pp < 1 or pp > 4096: continue
                    r = tj - pp * ti
                    if abs(r) < (1 << 13):
                        if pp > 1: add |= {pp, pp * ti}
                        if r: add.add(abs(r))
        nodes |= {v for v in add if 0 < v <= LIM}
        if MITM:  # palette chains: target <- (op s) <- (op s2) <- F1, F1 = M op s; s from a shared small palette
            base = set(starts)
            for _ in range(2):
                nb = set(base)
                for a in base:
                    for b in starts:
                        for c in (a + b, abs(a - b), a * b, (a // b if a % b == 0 else 0), (b // a if b % a == 0 else 0)):
                            if 0 < c < (1 << 13): nb.add(c)
                base = nb
                if _ == 0: base1 = set(nb)
            Sm = sorted(base)[:MITM_SM]
            ops = lambda u, s: (u - s, u + s, u // s if s > 1 and u % s == 0 else 0)
            F1 = {}
            for M in Ms:
                F1[M] = None
                for s in Sm:
                    for f in (M * s, M + s, M - s):
                        if 0 < f <= LIM: F1.setdefault(f, (M, s))
            # pass 1: how many distinct targets each palette value can serve in a <= 3-step chain
            cover = collections.defaultdict(set)
            for t in T:
                for s in Sm:
                    for u in ops(t, s):
                        if u <= 0: continue
                        if u in F1:
                            cover[s].add(t)
                            if F1[u]: cover[F1[u][1]].add(t)
                        for s2 in Sm:
                            for w in ops(u, s2):
                                if w > 0 and w in F1:
                                    cover[s].add(t); cover[s2].add(t)
                                    if F1[w]: cover[F1[w][1]].add(t)
            P2 = set(sorted(cover, key=lambda s: (-len(cover[s]), s))[:MITM_K])
            if os.environ.get('MITM_PAL'): P2 = {int(v) for v in os.environ['MITM_PAL'].split(',')}
            # pass 2: keep only chains whose palette values are all in P2
            chains = 0; usedS = collections.Counter()
            for t in T:
                for s in P2:
                    for u in ops(t, s):
                        if u <= 0: continue
                        if u in F1 and (F1[u] is None or F1[u][1] in P2): nodes.add(u); usedS[s] += 1; chains += 1
                        for s2 in P2:
                            for w in ops(u, s2):
                                if w > 0 and w in F1 and (F1[w] is None or F1[w][1] in P2):
                                    nodes |= {u, w}; usedS[s] += 1; usedS[s2] += 1; chains += 1
            # depth-4 chains restricted to the selected palette: F2p = (M op p) op p2, B2 = (t op p) op p2; meet in the middle
            fwd = {}
            for M in Ms:
                for p in P2:
                    for f in (M * p, M + p, M - p):
                        if 0 < f <= LIM: fwd.setdefault(f, (M,))
            lvl1 = list(fwd)
            for f in lvl1:
                for p in P2:
                    for g in (f * p, f + p, f - p, (f // p if p > 1 and f % p == 0 else 0)):
                        if 0 < g <= LIM: fwd.setdefault(g, (f,))
            for M in Ms: fwd[M] = ()
            d4 = 0
            for t in T:
                frontier = {t: ()}
                for depth in range(2):
                    nxt = {}
                    for u, path in frontier.items():
                        for p in P2:
                            for w in ops(u, p):
                                if w > 0: nxt.setdefault(w, path + (u,))
                    for w, path in nxt.items():
                        if w in fwd:
                            chain = set(path[1:]) | {w}; v = w
                            while fwd.get(v): v = fwd[v][0]; chain.add(v)
                            nodes |= chain; d4 += 1
                    frontier = nxt
            # near-copies of atoms (atom +/- small palette / small values) used as stepping stones
            for at in A:
                for p in P2:
                    for v in (at + p, at - p):
                        if v > 0: nodes.add(v)
            print(f'{pid} depth-4 chains {d4}', flush=True)            # big-with-big: bases B = F1 values on found chains (and Ms); targets/intermediates = B1 +/- B2, 2*B; keep if
            # the result is a target or a chain node
            Bs = sorted({v for v in nodes if v > (1 << 24) and v not in T} | set(Ms))[:600]
            want = set(T) | {v for v in nodes if v > (1 << 24)}
            bb = 0
            for i1, b1 in enumerate(Bs):
                for b2 in Bs[i1:]:
                    for c in (b1 + b2, b2 - b1):
                        if c > 0 and c in want: nodes |= {b1, b2}; bb += 1
                        if c > 0 and c <= LIM:
                            for s in P2:
                                for c2 in (c - s, c + s):
                                    if c2 in T: nodes |= {b1, b2, c}; bb += 1
            print(f'{pid} big-with-big links {bb}', flush=True)
            print(f'{pid} palette top coverage:', [(s, len(cover[s])) for s in sorted(P2, key=lambda s: -len(cover[s]))[:12]], flush=True)
            nodes |= {s for s in usedS} | (base if MITM_ALLBASE else set())
            # closure intermediates so palette values have recipes
            nodes |= {s for s in base if s in usedS or s < 64} | base1
            print(f'{pid} mitm: palette {len(Sm)} -> {len(P2)} F1 {len(F1)} chains {chains} nodes {len(nodes)}', flush=True)
        if SCRATCH:
            # small-constant closure: values within 2 ops of the starts (< 2^14)
            base = set(starts)
            for _ in range(2):
                nb = set(base)
                for a in base:
                    for b in starts:
                        for c in (a + b, abs(a - b), a * b, (a // b if a % b == 0 else 0), (b // a if b % a == 0 else 0)):
                            if 0 < c < (1 << 14): nb.add(c)
                base = nb
            nodes |= base
            # atom factor candidates: atom = u*w + r, |r| <= 32, 2 <= u <= w < 2^14
            for at in A:
                for r in range(-32, 33):
                    w = at - r
                    if w < 4: continue
                    u = 2
                    while u * u <= w:
                        if w % u == 0 and w // u < (1 << 14): nodes |= {u, w // u, w}; nodes.add(abs(r)) if r else None
                        u += 1
            # fallback: best program's cone for targets that fit no k*M + c form (stop at atoms / starts)
            fitted = set()
            for t in T:
                for M in Ms:
                    if M < t and any(abs(t - k * M) < CMAX and 0 < k < (1 << 14) for k in (t // M, t // M + 1)): fitted.add(t); break
            def cone(v, out):
                if v in out or v in SS or v not in srcb or v in A: return
                out.add(v); a, b = srcb[v]; cone(a, out); cone(b, out)
            for t in T - fitted:
                cs = set(); cone(t, cs); nodes |= cs
            print(f'{pid} scratch: atoms {len(A)} unfit targets {len(T - fitted)}', flush=True)
    if NOFRONT and os.environ.get('COVERCHECK'):
        pv = [c for c, op, a, b in values(pz, atoms_src)]
        miss = [c for c in dict.fromkeys(pv) if c not in nodes]
        print(f'{pid} COVERCHECK: public program {len(atoms_src)} values, {len(miss)} not in candidates:', miss, flush=True)
        raise SystemExit
    nodes = sorted(nodes); NS = set(nodes)
    rec = build_recipes(nodes, SS, LIM)
    if LNSMODE:
        return lns_solve(pz, nodes, rec, hint_rec, best, T, SS)
    m = cp_model.CpModel(); n = len(nodes)
    X = {v: m.NewBoolVar('') for v in nodes if v not in SS}
    Lv = {v: m.NewIntVar(0, n, '') for v in nodes if v not in SS}
    byv = collections.defaultdict(list); Y = []
    for k, (v, op, a, b) in enumerate(rec):
        y = m.NewBoolVar(''); Y.append(y); byv[v].append(k)
        for u in {a, b}:
            if u in SS: continue
            m.AddImplication(y, X[u])
            m.Add(Lv[v] >= Lv[u] + 1).OnlyEnforceIf(y)
    for v in X:
        m.Add(sum(Y[k] for k in byv[v]) == X[v])
    for t in T: m.Add(X[t] == 1)
    m.Minimize(sum(X.values()))
    # hint = current best program
    hset = set(hint_rec)
    hpos = {}
    for k2, (c, op, a, b) in enumerate(values(pz, best)): hpos.setdefault(c, k2 + 1)
    for v, x in (X.items() if not SCRATCH else []): m.AddHint(x, 1 if v in hset else 0)
    for v, lv in (Lv.items() if not SCRATCH else []): m.AddHint(lv, hpos.get(v, 0) if v in hset else 0)
    for k, (v, op, a, b) in (enumerate(rec) if not SCRATCH else []):
        m.AddHint(Y[k], 1 if hint_rec.get(v) == (op, a, b) else 0)
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = SEC; s.parameters.num_workers = WORK
    s.parameters.repair_hint = True
    t0 = time.time(); st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return len(best), None, n, len(rec), s.StatusName(st), None
    chosen = [v for v in X if s.Value(X[v])]
    recipe = {}
    for k, (v, op, a, b) in enumerate(rec):
        if s.Value(Y[k]): recipe[v] = (op, a, b)
    # scheduling: depth-first post-order from targets (several target orders), first one that fits 48 registers wins
    bestpos = {}
    for k2, (c, op, a, b) in enumerate(values(pz, best)): bestpos.setdefault(c, k2)
    def dfs_order(tlist):
        seen = set(); out = []
        def visit(v):
            if v in seen or v in SS: return
            seen.add(v); op, a, b = recipe[v]
            for u in sorted({a, b}, key=lambda u: bestpos.get(u, 10**9)): visit(u)
            out.append(v)
        for t in tlist: visit(t)
        for v in chosen: visit(v)
        return out
    tl = sorted(T, key=lambda t: bestpos.get(t, 10**9))
    prog = None
    for tlist in (tl, sorted(T), sorted(T, reverse=True), tl[::-1]):
        prog = allocate(pz, dfs_order(tlist), recipe)
        if prog is not None: break
    if prog is None:
        order = sorted(chosen, key=lambda v: (s.Value(Lv[v]), bestpos.get(v, 10**9)))
        prog = allocate(pz, order, recipe)
    bound = s.BestObjectiveBound()
    if prog is None: return len(best), None, n, len(rec), s.StatusName(st) + ' regfail obj %d' % s.ObjectiveValue(), bound
    try: L = replay(pz, prog)
    except ValueError as e: return len(best), None, n, len(rec), 'invalid ' + str(e), bound
    return len(best), prog, n, len(rec), s.StatusName(st), bound

tot = 0
with open(OUT, 'a') as fo:
    for pid in ids:
        t0 = time.time()
        try: b, prog, n, nr, st, bound = solve(pid)
        except Exception as e:
            import traceback; traceback.print_exc(); print(pid, 'error', e, flush=True); continue
        L = len(prog) if prog else None
        if prog and L < b:
            tot += b - L; fo.write(pid + ' ' + str(L) + ' ' + ' '.join(f'{o} {a} {c} {d}' for o, a, c, d in prog) + '\n'); fo.flush()
        print(f'{pid} best {b} -> {L} bound {bound} [{st}] nodes {n} recipes {nr} {time.time()-t0:.0f}s', flush=True)
print('total gain', tot)
