"""Joint scaffold optimizer (prototype, Aside 11-19).
Node set = starts + targets + every value of the current best program + structural candidates (atoms, atom products,
multipliers k, offsets c, partial products k*M, 1-op closure of the small values). Recipes = every one-instruction way to make
a node from two nodes (op in + - * /). MILP (HiGHS via scipy.milp): choose nodes + one recipe each, all targets chosen,
acyclic (potentials), minimize instruction count. The current best program is feasible, so the optimum is <= its length
(registers ignored here; pal re-derives and allocates afterwards).
usage: python src/scaf_milp.py ID [TIMELIMIT] [ATOMSRC frontier|hubs] -> prints result, writes work/milp/<id>.items
"""
import sys, json, math, itertools, time, collections
from pathlib import Path
import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import coo_matrix
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, BEST, ROOT

pid = sys.argv[1]; TL = float(sys.argv[2]) if len(sys.argv) > 2 else 120; ATOMSRC = sys.argv[3] if len(sys.argv) > 3 else 'frontier'
P = load(); pz = P[pid]; LIM = pz['limit']; starts = pz['starts']; T = sorted(set(pz['targets']) - set(starts))
prog = json.loads((BEST / f'{pid}.json').read_text())
R = [None] * 48
for k, v in enumerate(starts): R[k] = v
fvals = []; uses = collections.Counter()
for op, i, j, d in prog:
    a, b = R[i], R[j]; uses[a] += 1; uses[b] += 1
    c = {'+': a + b, '-': a - b, '*': a * b, '/': a // b}[op]; R[d] = c; fvals.append(c)
TS = set(T)
if ATOMSRC == 'hubs':
    H = {}
    for l in open(ROOT / 'work' / 'hubs_all.txt'):
        x = l.split(); H[x[0]] = [(int(a), int(b), float(c)) for a, b, c in (t.split(':') for t in x[1:])]
    A = sorted(h for h, c, z in H[pid] if z >= 8)[:6]
else:
    A = sorted({c for c in fvals if (1 << 14) <= c < (1 << 24) and c not in TS and uses[c] >= 2})
STRUCT = bool(__import__('os').environ.get('STRUCTONLY'))
if STRUCT:
    # frontier values only for targets that do not fit k*M + c (their exclusive cones), plus the atoms' factor candidates
    nodes = set(starts) | TS | set(A)
    src = {}
    R3 = [None] * 48
    for k3, v3 in enumerate(starts): R3[k3] = v3
    for op, i, j, d in prog:
        a3, b3 = R3[i], R3[j]; c3 = {'+': a3 + b3, '-': a3 - b3, '*': a3 * b3, '/': a3 // b3}[op]; R3[d] = c3; src.setdefault(c3, (a3, b3))
    ATOMSET = set(A)
else:
    nodes = set(starts) | TS | set(fvals) | set(A)
prods = {a * b for a, b in itertools.combinations_with_replacement(A, 2) if a * b <= LIM}
nodes |= prods
Ms = sorted(set(A) | prods | TS)
small_needed = set()
for t in T:
    cands = []
    for M in Ms:
        if M >= t: continue
        q = t // M
        for k in (q, q + 1):
            if k < 1: continue
            c = t - k * M
            if abs(c) < (1 << 13) and k < (1 << 14):
                cands.append(((k > 1) * k.bit_length() + abs(c).bit_length(), M, k, c))
    cands.sort()
    for _, M, k, c in cands[:3]:
        if k > 1: small_needed.add(k); nodes.add(k * M)
        if c: small_needed.add(abs(c))
nodes |= small_needed
if STRUCT:
    fitted = set()
    for t in T:
        for M in Ms:
            if M >= t: continue
            q = t // M
            if any(abs(t - k * M) < (1 << 13) and 0 < k < (1 << 14) for k in (q, q + 1)): fitted.add(t); break
    def cone(v, out):
        if v in out or v in starts or v not in src or v in ATOMSET: return
        out.add(v); a3, b3 = src[v]; cone(a3, out); cone(b3, out)
    for t in T:
        if t not in fitted:
            cset = set(); cone(t, cset); nodes |= cset
    # atom factor candidates: atom = u*w + r, |r| <= 48, u,w < 2^14
    for at in A:
        for r in range(-48, 49):
            w = at - r
            if w < 4: continue
            for u in range(2, min(1 << 14, int(w ** 0.5) + 1)):
                if w % u == 0 and w // u < (1 << 14): nodes |= {u, w // u, u * (w // u)}; nodes.add(abs(r)) if r else None
    print('struct-only: unfit targets', len(T) - len(fitted))
import os
if os.environ.get('VARIANTS'):
    VJ = json.load(open(os.environ['VARIANTS'])).get(pid, [])
    nvar = 0
    for vp in VJ:
        if len(vp) > 1.25 * len(prog): continue
        nvar += 1; R2 = [None] * 48
        for k2, v2 in enumerate(starts): R2[k2] = v2
        for op, i, j, d in vp:
            a2, b2 = R2[i], R2[j]; c2 = {'+': a2 + b2, '-': a2 - b2, '*': a2 * b2, '/': a2 // b2}[op]; R2[d] = c2; nodes.add(c2)
    print('variants used', nvar)
# 1-op closure of small values (< 2^16) to give constants cheap recipes
small = sorted(v for v in nodes if v < (1 << 16))
if STRUCT:  # closure = values within 2 ops of the starts only (< 2^14)
    base = set(starts)
    for _ in range(2):
        nb = set(base)
        for a in base:
            for b in starts:
                for c in (a + b, abs(a - b), a * b, (a // b if b and a % b == 0 else 0), (b // a if a and b % a == 0 else 0)):
                    if 0 < c < (1 << 14): nb.add(c)
        base = nb
    small = []
    nodes |= base
    print('closure (2 ops from starts):', len(base))
clos = set()
for a in small:
    for b in small:
        if b < a: continue
        for c in (a + b, b - a, a * b, (b // a if b % a == 0 else 0)):
            if 0 < c < (1 << 16): clos.add(c)
if len(sys.argv) > 4 and sys.argv[4] == 'clos': nodes |= clos
nodes = sorted(nodes); idx = {v: i for i, v in enumerate(nodes)}; N = len(nodes)
SS = set(starts)
# recipes: v = a op b, a,b nodes
rec = []  # (v, a, b)
t0 = time.time()
for v in nodes:
    if v in SS: continue
    for a in nodes:
        if a > LIM: break
        # v = a + b (b >= a), v = a * b (b >= a), v = b - a, v = b / a, v = a - b, v = a / b
        if a <= v - a and (v - a) in idx: rec.append((v, a, v - a))
        if a > 1 and v % a == 0 and v // a >= a and (v // a) in idx: rec.append((v, a, v // a))
        if v + a <= LIM and (v + a) in idx: rec.append((v, v + a, a))
        if a > v and (a - v) in idx: rec.append((v, a, a - v))
        if a < LIM // max(v, 1) + 1 and a * v <= LIM and (a * v) in idx and a > 1: rec.append((v, a * v, a))
        if a > v and a % v == 0 and (a // v) in idx and v > 1: rec.append((v, a, a // v))
rec = list(dict.fromkeys(rec))
print(f'{pid}: nodes {N} recipes {len(rec)} atoms {len(A)} (built {time.time()-t0:.1f}s)', flush=True)
# ---- MILP with lazy cycle cuts ----
nonS = [v for v in nodes if v not in SS]; xi = {v: k for k, v in enumerate(nonS)}
nx = len(nonS); ny = len(rec); nv = nx + ny
cost = np.zeros(nv); cost[nx:] = 1.0
rows, cols, vals, lo, hi = [], [], [], [], []
r = 0
byv = collections.defaultdict(list)
for k, (v, a, b) in enumerate(rec): byv[v].append(k)
for v in nonS:
    for k in byv[v]: rows.append(r); cols.append(nx + k); vals.append(1)
    rows.append(r); cols.append(xi[v]); vals.append(-1); lo.append(0); hi.append(0); r += 1
for k, (v, a, b) in enumerate(rec):
    for u in {a, b}:
        if u in SS: continue
        rows += [r, r]; cols += [nx + k, xi[u]]; vals += [1, -1]; lo.append(-np.inf); hi.append(0); r += 1
lb = np.zeros(nv); ub = np.ones(nv)
for t in T: lb[xi[t]] = 1
integ = np.ones(nv)
cuts = []
t0 = time.time(); it = 0; best = None
while time.time() - t0 < TL:
    it += 1
    R2, C2, V2, L2, H2 = list(rows), list(cols), list(vals), list(lo), list(hi); rr = r
    for cyc in cuts:
        for k in cyc[:-1]: R2.append(rr); C2.append(nx + k); V2.append(1)
        L2.append(-np.inf); H2.append(-cyc[-1] - 1); rr += 1
    A_ = coo_matrix((V2, (R2, C2)), shape=(rr, nv)).tocsr()
    res = milp(cost, constraints=[LinearConstraint(A_, L2, H2)], bounds=Bounds(lb, ub), integrality=integ,
               options={'time_limit': max(5, TL - (time.time() - t0)), 'disp': False})
    if res.x is None: print('no solution', res.message); break
    x = res.x
    chosen_rec = {v: k for k, (v, a, b) in enumerate(rec) if x[nx + k] > 0.5}
    # find cycles in v -> operands graph
    color = {}; found = []
    def dfs(v, stack):
        color[v] = 1; stack.append(v)
        k = chosen_rec.get(v)
        if k is not None:
            for u in set(rec[k][1:]):
                if u in SS: continue
                if color.get(u) == 1:
                    cyc_nodes = set(stack[stack.index(u):])
                    found.append([kk for w in cyc_nodes for kk in byv[w] if (set(rec[kk][1:]) & cyc_nodes)] + [-len(cyc_nodes)])
                elif u not in color: dfs(u, stack)
        stack.pop(); color[v] = 2
    sys.setrecursionlimit(100000)
    for v in chosen_rec:
        if v not in color: dfs(v, [])
    print(f'  iter {it}: obj {res.fun:.0f} cycles {len(found)} ({time.time()-t0:.0f}s)', flush=True)
    if not found: best = (res.fun, chosen_rec); break
    cuts += found
print(f'RESULT {pid}: milp {best[0] if best else None} frontier {len(prog)}', flush=True)
if best:
    chosen_rec = best[1]
    # topological order of chosen helpers
    order = []; seen = set()
    def topo(v):
        if v in seen or v in SS: return
        seen.add(v); k = chosen_rec[v]
        for u in rec[k][1:]: topo(u)
        order.append(v)
    for v in sorted(chosen_rec): topo(v)
    helpers = [v for v in order if v not in TS]
    out = ROOT / 'work' / 'milp'; out.mkdir(exist_ok=True)
    (out / f'{pid}.items').write_text(pid + ' ' + ' '.join(map(str, order)) + '\n')
    print('chosen', len(order), 'helpers', len(helpers))