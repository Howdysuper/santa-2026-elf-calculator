"""Layered constructor (Aside, 11-23). For structured puzzles:
L0  = starts + every value in the best program's cones of the hidden atoms (taken as is, cost = their count)
PAL = small values (< 2^13): small L0 values, + one op of two of them (P1), + one op of P1 and a small L0 value (P2)
L2  = products of two atoms (incl. squares), atoms themselves
L3  = bases: X op p  (X in L2, p in PAL), and M +/- M'
TGT = target = Y op q (Y in L2 u L3, q in PAL u L2 u L3)   [1 instruction each]
      target = (Y op q) op q2 via a private intermediate     [2 instructions]
Unfit targets fall back to the best program's own derivation (its ancestors outside L0, fixed).
CP-SAT chooses which palette values, bases and recipes to build; layers are strictly increasing, so no ordering constraints.
usage: python src/layered.py IDS OUT [SEC=120] [WORKERS=8]   (PYTHONPATH=<santa-2026>/ortools_lib)
"""
import sys, json, time, collections, itertools, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, BEST, replay
from ortools.sat.python import cp_model

ids = [l.strip() for l in open(sys.argv[1]) if l.strip()]; OUT = sys.argv[2]
SEC = float(sys.argv[3]) if len(sys.argv) > 3 else 120; WORK = int(sys.argv[4]) if len(sys.argv) > 4 else 8
PALMAX = 1 << 13
P = load()
OPS = {'+': lambda a, b: a + b, '-': lambda a, b: a - b, '*': lambda a, b: a * b, '/': lambda a, b: a // b}

def trace(pz, prog):
    R = [None] * 48
    for k, v in enumerate(pz['starts']): R[k] = v
    out = []
    for op, i, j, d in prog:
        a, b = R[i], R[j]; c = OPS[op](a, b); R[d] = c; out.append((c, op, a, b))
    return out

def one_ops(a, b, lim):
    """all (value, op, x, y) with value = x op y for the pair a, b (both orders)"""
    res = [(a + b, '+', a, b), (a * b, '*', a, b)]
    if a > b: res.append((a - b, '-', a, b))
    if b > a: res.append((b - a, '-', b, a))
    if b > 1 and a % b == 0: res.append((a // b, '/', a, b))
    if a > 1 and b % a == 0: res.append((b // a, '/', b, a))
    return [r for r in res if 0 < r[0] <= lim]

def inv_ops(t, q, lim):
    """(y, op, x1, x2): t = x1 op x2 with q one operand and y the other"""
    res = []
    if t > q: res.append((t - q, '+', t - q, q))
    if t + q <= lim: res.append((t + q, '-', t + q, q))
    if q > t: res.append((q - t, '-', q, q - t))
    if q > 1 and t % q == 0: res.append((t // q, '*', t // q, q))
    if t * q <= lim and q > 1: res.append((t * q, '/', t * q, q))
    if t > 1 and q % t == 0: res.append((q // t, '/', q, q // t))
    return res

def allocate(pz, order, recipe):
    starts = pz['starts']; last = {}
    for k, v in enumerate(order):
        op, a, b = recipe[v]; last[a] = k; last[b] = k
    reg = {}; owner = [None] * 48
    for k, v in enumerate(starts):
        if v not in reg: reg[v] = k; owner[k] = v
    for k, v in enumerate(starts):
        if last.get(v, -1) < 0 and owner[k] == v: owner[k] = None
    prog = []
    for k, v in enumerate(order):
        op, a, b = recipe[v]; ra, rb = reg.get(a), reg.get(b)
        if ra is None or rb is None: return None
        if last.get(a) == k and owner[ra] == a: owner[ra] = None
        if last.get(b) == k and owner[rb] == b: owner[rb] = None
        rd = next((r for r in range(48) if owner[r] is None), None)
        if rd is None: return None
        prog.append([op, ra, rb, rd]); reg[v] = rd; owner[rd] = v if last.get(v, -1) > k else None
    return prog

def solve(pid):
    pz = P[pid]; LIM = pz['limit']; starts = pz['starts']; SS = set(starts); T = set(pz['targets']) - SS
    best = json.loads((BEST / f'{pid}.json').read_text())
    tr = trace(pz, best); src = {}; uses = collections.Counter()
    for c, op, a, b in tr:
        src.setdefault(c, (op, a, b)); uses[a] += 1; uses[b] += 1
    A = sorted({c for c, *_ in tr if (1 << 14) <= c < (1 << 24) and c not in T and uses[c] >= 2}, key=lambda c: -uses[c])[:int(os.environ.get('AMAX', '8'))]
    A = sorted(A)
    if os.environ.get('ATOMMODE', 'mul') == 'mul':  # atoms = operands of big x big multiplications in the best program
        cnt = collections.Counter()
        for c, op, a, b in tr:
            if op == '*' and min(a, b) >= (1 << 9) and max(a, b) < (1 << 24): cnt[a] += 1; cnt[b] += 1
        Am = sorted(cnt, key=lambda v: -cnt[v])[:int(os.environ.get('AMAX', '8'))]
        if len(Am) >= 2: A = sorted(Am)
    # L0: atom cones from the best program
    L0 = set(SS); L0rec = {}
    def cone(v):
        if v in L0: return
        op, a, b = src[v]; cone(a); cone(b); L0.add(v); L0rec[v] = (op, a, b)
    for a in A: cone(a)
    C0 = len(L0rec)
    # palette
    S0 = sorted(v for v in L0 if v < PALMAX)
    P1 = {}
    for a, b in itertools.combinations_with_replacement(S0, 2):
        for c, op, x, y in one_ops(a, b, LIM):
            if c < PALMAX and c not in L0: P1.setdefault(c, []).append((op, x, y))
    P2 = {}
    for a in P1:
        for b in S0:
            for c, op, x, y in one_ops(a, b, LIM):
                if c < PALMAX and c not in L0 and c not in P1: P2.setdefault(c, []).append((op, x, y))
    PAL = set(S0) | set(P1) | set(P2)
    print(f'  {pid} A {len(A)} S0 {len(S0)} P1 {len(P1)} P2 {len(P2)}', flush=True)
    # products and bases
    L2 = {}
    AB = A
    if os.environ.get('LBROAD'):
        AB = sorted(set(A) | {v for v in L0 if (1 << 9) <= v < (1 << 24)}, key=lambda v: -uses[v])[:30]
    for a, b in itertools.combinations_with_replacement(AB, 2):
        if a * b <= LIM and a * b not in L0: L2.setdefault(a * b, []).append(('*', a, b))
    Xs = set(A) | set(L2)
    L3 = {}
    PALB = PAL if len(Xs) <= 60 else (set(S0) | set(P1))
    for X in Xs:
        for p in PALB:
            for c, op, x, y in one_ops(X, p, LIM):
                if c > (1 << 20) and c not in L0 and c not in L2: L3.setdefault(c, []).append((op, x, y))
    for X1, X2 in itertools.combinations(sorted(L2), 2):
        for c in (X1 + X2, X2 - X1):
            if 0 < c <= LIM and c not in L0 and c not in L2: L3.setdefault(c, []).append(('+' if c == X1 + X2 else '-', X1 if c == X1 + X2 else X2, X2 if c == X1 + X2 else X1))
    Y = set(Xs) | set(L3)
    print(f'  L2 {len(L2)} L3 {len(L3)}', flush=True)
    # targets ranked by first cover in the best program; a target may use earlier targets
    pos0 = {}
    for k, (c, *_) in enumerate(tr): pos0.setdefault(c, k)
    TL_ = sorted(T, key=lambda t: pos0.get(t, 10 ** 9)); rank = {t: k for k, t in enumerate(TL_)}
    SQ = set(S0) | set(P1)                      # small operands for 2-step chains
    TR = collections.defaultdict(list); MID = {}; MIDT = {}; INT = {}   # INT: intermediate -> (layer, [recipes])
    Xl = sorted(Xs)
    def leaf(w, r):
        """layer of w if usable as an operand by something at target rank r, else None (registers pair recipes)"""
        if w in Y: return layer_base(w)
        if w in rank and rank[w] < r: return 10 + rank[w]
        return None
    def layer_base(w):
        return 0 if w in L0 or w in A else 3 if w in L2 else 4
    def pair_leaf(w, r):
        for X in Xl:
            for z, op, a, b in ((w - X, '+', w - X, X), (w + X, '-', w + X, X), (X - w, '-', X, X - w)):
                if z > 0 and z <= LIM:
                    lz = leaf(z, r)
                    if lz is not None: return max(lz, 3) + 0.2, (op, a, b)
        return None
    def add_int(v, lay, rcp):
        e = INT.get(v)
        if e is None: INT[v] = [lay, [rcp]]
        else:
            e[0] = min(e[0], lay)
            if rcp not in e[1]: e[1].append(rcp)
    S0s = sorted(v for v in L0 if v > 0 and v < (1 << 24))
    SQ = SQ | set(S0s)
    for t in TL_:
        r = rank[t]
        for q in PAL | Xs:
            for y, op, x1, x2 in inv_ops(t, q, LIM):
                if y in Y or y in PAL or (y in rank and rank[y] < r): TR[t].append((op, x1, x2))
        pl = pair_leaf(t, r)
        if pl: TR[t].append(pl[1])
        for q in SQ:
            for y1, op, x1, x2 in inv_ops(t, q, LIM):
                if y1 <= 0 or y1 in Y or y1 in T: continue
                ok1 = False
                small_q = q in S0
                pl = pair_leaf(y1, r) if small_q else None
                if pl: add_int(y1, pl[0], pl[1]); ok1 = True
                for s0 in S0s:
                    for y2, op2, z1, z2 in inv_ops(y1, s0, LIM):
                        if y2 <= 0: continue
                        l2 = leaf(y2, r)
                        if l2 is not None:
                            add_int(y1, l2 + 0.3, (op2, z1, z2)); ok1 = True; continue
                        if not small_q or y2 in T: continue
                        pl2 = pair_leaf(y2, r)
                        if pl2:
                            add_int(y2, pl2[0], pl2[1]); add_int(y1, pl2[0] + 0.3, (op2, z1, z2)); ok1 = True
                        for s1 in S0s:
                            for y3, op3, u1, u2 in inv_ops(y2, s1, LIM):
                                l3 = leaf(y3, r) if y3 > 0 else None
                                if l3 is not None:
                                    add_int(y2, l3 + 0.3, (op3, u1, u2)); add_int(y1, l3 + 0.6, (op2, z1, z2)); ok1 = True
                if ok1: TR[t].append((op, x1, x2))
    if os.environ.get('LCOVER'):
        tags = {}
        for c, op, a, b in tr:
            if c in tags: continue
            tags[c] = ('L0' if c in L0 else 'T' if c in T else 'P1' if c in P1 else 'P2' if c in P2 else 'L2' if c in L2
                       else 'L3' if c in L3 else 'MID' if c in MID else 'INT' if c in INT else 'OUT')
        print('  public program values by layer:', dict(collections.Counter(tags.values())), flush=True)
        for c, op, a, b in tr:
            if tags.get(c) == 'OUT': print(f'    OUT {c} = {a} {op} {b}  [{tags.get(a, "S")} {op} {tags.get(b, "S")}]')
        for c, op, a, b in tr:
            if tags.get(c) == 'T': print(f'    T {c} = [{tags.get(a, "S")} {op} {tags.get(b, "S")}]')
        raise SystemExit
    unfit = [t for t in T if not TR[t]]
    print(f'  targets: fit {sum(1 for t in T if TR[t])} intermediates {len(INT)} unfit {len(unfit)}', flush=True)
    # fallback: best program's ancestors for unfit targets (fixed)
    FIX = {}
    def fanc(v):
        if v in L0 or v in FIX: return
        op, a, b = src[v]; FIX[v] = (op, a, b); fanc(a); fanc(b)
    for t in unfit: fanc(t)
    # ---- model ----
    layer = {}
    for v in L0: layer[v] = 0
    for v in P1: layer.setdefault(v, 1)
    for v in P2: layer.setdefault(v, 2)
    for v in A: layer[v] = 0
    for v in L2: layer.setdefault(v, 3)
    for v in L3: layer.setdefault(v, 4)
    for v in MID: layer.setdefault(v, 5)
    for t in T: layer[t] = 10 + rank[t]
    for v, (lay, rl) in INT.items():
        if v not in layer: layer[v] = lay
    recs = []
    for D in (P1, P2, L2, L3, MID):
        for v, rl in D.items():
            for r in rl: recs.append((v,) + r)
    for v, (lay, rl) in INT.items():
        for r in rl: recs.append((v,) + tuple(r))
    for t, rl in TR.items():
        for r in rl: recs.append((t,) + r)
    recs = [r for r in dict.fromkeys(recs) if r[0] not in L0 and r[0] not in FIX
            and all(u in L0 or u in FIX or (u in layer and layer[u] < layer[r[0]]) for u in r[2:])]
    byout = collections.defaultdict(list)
    for r in recs: byout[r[0]].append(r)
    keep = set(); st = list(T)
    while st:
        v = st.pop()
        if v in keep: continue
        keep.add(v)
        for r in byout[v]:
            for u in r[2:]:
                if u not in L0 and u not in FIX and u not in keep: st.append(u)
    recs = [r for r in recs if r[0] in keep]
    print(f'  pruned: nodes {len(keep)} recs {len(recs)}', flush=True)
    while True:
        nodes = {r[0] for r in recs}
        nr = [r for r in recs if all(u in L0 or u in FIX or u in nodes for u in r[2:])]
        if len(nr) == len(recs): break
        recs = nr
    for _rep in range(5):
        have = {r[0] for r in recs}
        missing = [t for t in T if t not in have and t not in FIX and t not in L0]
        if not missing: break
        for t in missing: fanc(t)
        recs = [r for r in recs if r[0] not in FIX]
        while True:
            nodes = {r[0] for r in recs}
            nr = [r for r in recs if all(u in L0 or u in FIX or u in nodes for u in r[2:])]
            if len(nr) == len(recs): break
            recs = nr
    nodes = {r[0] for r in recs} | (set(T) - set(FIX) - L0)
    print(f'  buildable: nodes {len(nodes)} recs {len(recs)}', flush=True)
    m = cp_model.CpModel()
    X = {v: m.NewBoolVar('') for v in nodes if v not in FIX}
    byv = collections.defaultdict(list); Yv = []
    for k, (v, op, a, b) in enumerate(recs):
        if v not in X: continue
        y = m.NewBoolVar(''); Yv.append((y, k)); byv[v].append(y)
        for u in {a, b}:
            if u in X: m.AddImplication(y, X[u])
    for v, x in X.items(): m.Add(sum(byv[v]) == x)
    for t in T:
        if t in X and t not in L0: m.Add(X[t] == 1)
    m.Minimize(sum(X.values()))
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = SEC; s.parameters.num_workers = WORK
    t0 = time.time(); st = s.Solve(m)
    info = f'A {len(A)} C0 {C0} pal {len(PAL)} L2 {len(L2)} L3 {len(L3)} mid {len(MID)} unfit {len(unfit)} fix {len(FIX)} nodes {len(nodes)} recs {len(recs)}'
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE): return len(best), None, info + ' ' + s.StatusName(st)
    recipe = dict(L0rec); recipe.update(FIX)
    for y, k in Yv:
        if s.Value(y): v, op, a, b = recs[k]; recipe[v] = (op, a, b)
    est = C0 + len(FIX) + int(s.ObjectiveValue())
    bound = C0 + len(FIX) + int(s.BestObjectiveBound())
    # order: depth-first from targets, best-program order as tie-break
    pos = {c: k for k, (c, *_) in enumerate(tr)}
    def dfs(tl):
        seen = set(); out = []
        def visit(v):
            if v in seen or v in SS: return
            seen.add(v); op, a, b = recipe[v]
            for u in sorted({a, b}, key=lambda u: pos.get(u, 10 ** 9)): visit(u)
            out.append(v)
        for t in tl: visit(t)
        return out
    tl = sorted(T, key=lambda t: pos.get(t, 10 ** 9)); prog = None
    for order_t in (tl, sorted(T), sorted(T, reverse=True)):
        prog = allocate(pz, dfs(order_t), recipe)
        if prog: break
    info += f' est {est} bound {bound} {s.StatusName(st)} {time.time()-t0:.0f}s'
    if prog is None: return len(best), None, info + ' regfail'
    try: replay(pz, prog)
    except ValueError as e: return len(best), None, info + ' invalid ' + str(e)
    return len(best), prog, info

with open(OUT, 'a') as fo:
    for pid in ids:
        t0 = time.time()
        try: b, prog, info = solve(pid)
        except Exception as e:
            import traceback; traceback.print_exc(); print(pid, 'error', e, flush=True); continue
        L = len(prog) if prog else None
        if prog and os.environ.get('ALTOUT'):
            with open(os.environ['ALTOUT'], 'a') as ao: ao.write(pid + ' ' + str(L) + ' ' + ' '.join(f'{o} {a} {c} {d}' for o, a, c, d in prog) + '\n')
        if prog and L < b: fo.write(pid + ' ' + str(L) + ' ' + ' '.join(f'{o} {a} {c} {d}' for o, a, c, d in prog) + '\n'); fo.flush()
        print(f'{pid} best {b} -> {L} | {info} | {time.time()-t0:.0f}s', flush=True)
