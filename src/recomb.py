"""Graph recombination: pool every known program for a puzzle into one value graph, add every one-step link
between known values, and pick the fewest values (one instruction each) that derive all targets (exact MILP).

usage:
  python recomb.py collect                       # gather valid program variants from pub*/ CSVs + best/ -> work/variants.json
  python recomb.py solve [--ids a,b] [--start i --end j] [--workers 12] [--tl 60]
"""
import argparse, csv, glob, heapq, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import coo_matrix

sys.path.insert(0, str(Path(__file__).parent))
from elf import load, replay, offer, best_len, BEST, ROOT  # noqa: E402

csv.field_size_limit(1 << 30)
VAR = ROOT / "work" / "variants.json"
REL = float(os.environ.get("REL", "0.08"))   # variants up to this much longer than the best take part
FULL = bool(int(os.environ.get("FULL", "0")))   # also enrich with - and / links (creates many cycles; slow)
NORANK = bool(int(os.environ.get("NORANK", "0")))   # keep recipes in any order (inverse-op rewrites); lazy cycle cuts keep it acyclic


def collect():
    P = load()
    var = {pid: set() for pid in P}
    files = [f for f in glob.glob(str(ROOT / "pub*" / "**" / "*.csv"), recursive=True) if Path(f).stat().st_size > 100_000]
    files += glob.glob(str(ROOT / "work" / "alt" / "*.csv"))
    for f in files:
        try:
            with open(f, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    pid, s = r.get("id"), r.get("program")
                    if pid in var and s: var[pid].add(s.replace(" ", ""))
        except Exception as e:
            print("skip", f, e)
    for pid in P:
        p = BEST / f"{pid}.json"
        if p.exists(): var[pid].add(p.read_text().replace(" ", ""))
    out, nv = {}, 0
    for pid, ss in var.items():
        good = []
        for s in ss:
            try:
                prog = json.loads(s); replay(P[pid], prog); good.append(prog)
            except Exception:
                pass
        out[pid] = good; nv += len(good)
    VAR.write_text(json.dumps(out))
    print(f"{len(files)} files, {nv} valid variants, {nv / len(P):.1f} per puzzle")


def simulate(pz, prog):
    R = [None] * pz["regs"]
    for k, v in enumerate(pz["starts"]): R[k] = v
    out = []
    for op, i, j, d in prog:
        a, b = R[i], R[j]
        c = a + b if op == "+" else a - b if op == "-" else a * b if op == "*" else a // b
        out.append((c, op, a, b)); R[d] = c
    return out


def enrich(vals, L):
    """All (c, op, a, b) with a, b, c in vals."""
    v = np.array(sorted(vals), dtype=np.uint64)
    A = v[:, None]; B = v[None, :]
    res = []
    def hits(C, mask, op):
        C = np.where(mask, C, np.uint64(0))
        idx = np.searchsorted(v, C); idx[idx >= len(v)] = 0
        ok = mask & (v[idx] == C)
        ia, ib = np.nonzero(ok)
        for x, y in zip(ia.tolist(), ib.tolist()):
            res.append((int(C[x, y]), op, int(v[x]), int(v[y])))
    L = np.uint64(L)
    with np.errstate(over="ignore"):
        up = np.triu(np.ones((len(v), len(v)), dtype=bool))
        hits(A + B, up & (A <= L - B), "+")
        hits(A * B, up & (A <= L // B), "*")
        if FULL:
            hits(A - B, A > B, "-")
            hits(A // B, (A % B == 0) & (A > B), "/")
    return res


BRIDGE = int(os.environ.get("BRIDGE", "0"))   # also add new one-step values x = a op b (a, b known) that give a known c = x op y


def bridges(vals, starts, L, rk):
    """Two-step links through one new value: x = a op b and c = x op y with a, b, c, y known.
    Returns {x: rank}, [(x, op, a, b)], [(c, op, x, y)]. Ranks keep the graph acyclic: rk(x) = max(rk a, rk b) + eps < rk(c)."""
    u = np.array(sorted(vals), dtype=np.uint64); n = len(u)
    r = np.array([rk(int(x)) for x in u])
    Lq = np.uint64(L)
    A = u[:, None]; B = u[None, :]
    RA = np.maximum(r[:, None], r[None, :])
    xs, ops, ia, ib = [], [], [], []
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        up = np.triu(np.ones((n, n), dtype=bool))
        for op, C, M in (("+", A + B, up & (A <= Lq - B)), ("*", A * B, up & (A <= Lq // B)),
                         ("-", A - B, A > B), ("/", A // B, (A > B) & (A % B == 0))):
            i, j = np.nonzero(M)
            xs.append(C[i, j]); ops.append(np.full(len(i), "+-*/".index(op), dtype=np.int8)); ia.append(i); ib.append(j)
    X = np.concatenate(xs); O = np.concatenate(ops); IA = np.concatenate(ia); IB = np.concatenate(ib)
    RX = np.maximum(r[IA], r[IB])
    known = np.isin(X, u)
    X, O, IA, IB, RX = X[~known], O[~known], IA[~known], IB[~known], RX[~known]
    order = np.lexsort((RX, X)); X, O, IA, IB, RX = X[order], O[order], IA[order], IB[order], RX[order]
    ux, first = np.unique(X, return_index=True)
    xr = RX[first] + 1e-6                                       # rank of each new value: its earliest recipe
    # c = x op y  <=>  x = c - y | c + y (x - y = c) | y - c (y - x = c) | c * y (x / y = c) | c / y (x * y = c) | y / c (y / x = c)
    Cc = u[:, None]; Y = u[None, :]
    found = []
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        for op, Xc, M in (("+", Cc - Y, Cc > Y), ("-", Cc + Y, Cc <= Lq - Y), ("r", Y - Cc, Y > Cc),
                          ("/", Cc * Y, Cc <= Lq // Y), ("*", Cc // Y, (Cc % Y == 0) & (Cc > Y)), ("q", Y // Cc, (Y % Cc == 0) & (Y > Cc))):
            Xc = np.where(M, Xc, np.uint64(0))
            k = np.searchsorted(ux, Xc); k[k >= len(ux)] = 0
            hit = M & (ux[k] == Xc)
            ci, yi = np.nonzero(hit)
            for c_, y_, kk in zip(ci.tolist(), yi.tolist(), k[ci, yi].tolist()):
                c, y = int(u[c_]), int(u[y_])
                if c in starts or not (xr[kk] < r[c_] and r[y_] < r[c_]): continue
                x = int(ux[kk])
                if op == "r": found.append((c, "-", y, x))
                elif op == "q": found.append((c, "/", y, x))
                else: found.append((c, op, x, y))
    if not found: return {}, [], []
    serves = {}
    for c, op, a, b in found:
        for x in (a, b):
            if x not in vals: serves.setdefault(x, set()).add(c)
    BMIN = int(os.environ.get("BMIN", "2"))
    found = [f for f in found if all(x in vals or len(serves[x]) >= BMIN for x in (f[2], f[3]))]
    need = {x for f in found for x in (f[2], f[3]) if x not in vals}
    newx = {}; xrec = []
    pos = np.searchsorted(ux, np.array(sorted(need), dtype=np.uint64))
    for x, kk in zip(sorted(need), pos.tolist()):
        newx[x] = float(xr[kk])
        s = first[kk]; e = first[kk + 1] if kk + 1 < len(first) else len(X)
        for t in range(s, e):
            if RX[t] + 1e-6 <= xr[kk] + 1e-9:
                xrec.append((x, "+-*/"[O[t]], int(u[IA[t]]), int(u[IB[t]])))
    return newx, xrec, found


HIGHS = int(os.environ.get("HIGHS", "0"))


def solve_highs(c, rows, cols, data, lo, hi, lb, ub, tl, x0):
    """Same model through highspy, warm-started from x0 (the best program) when given."""
    import highspy
    nv = len(c); A = coo_matrix((data, (rows, cols)), shape=(len(lo), nv)).tocsc()
    inf = highspy.kHighsInf
    lp = highspy.HighsLp()
    lp.num_col_ = nv; lp.num_row_ = len(lo)
    lp.col_cost_ = np.asarray(c, dtype=float); lp.col_lower_ = np.asarray(lb, dtype=float); lp.col_upper_ = np.asarray(ub, dtype=float)
    lp.row_lower_ = np.array([-inf if v == -np.inf else v for v in lo], dtype=float)
    lp.row_upper_ = np.array([inf if v == np.inf else v for v in hi], dtype=float)
    lp.a_matrix_.format_ = highspy.MatrixFormat.kColwise
    lp.a_matrix_.start_ = A.indptr; lp.a_matrix_.index_ = A.indices; lp.a_matrix_.value_ = A.data.astype(float)
    lp.integrality_ = [highspy.HighsVarType.kInteger] * nv
    h = highspy.Highs(); h.setOptionValue("output_flag", False); h.setOptionValue("time_limit", float(tl))
    h.setOptionValue("threads", 1)
    h.passModel(lp)
    if x0 is not None and not os.environ.get('NOWARM'):
        sol = highspy.HighsSolution(); sol.col_value = list(map(float, x0)); sol.value_valid = True
        h.setSolution(sol)
    h.run()
    s = h.getSolution()
    if os.environ.get("MIPINFO"):
        inf_ = h.getInfo(); print(f"  mip obj {inf_.objective_function_value:.1f} bound {inf_.mip_dual_bound:.1f} nodes {inf_.mip_node_count} status {h.modelStatusToString(h.getModelStatus())} sum {np.dot(c, s.col_value):.1f} x0 {np.dot(c, x0) if x0 is not None else None}", flush=True)
    if not s.value_valid: return None
    return np.array(s.col_value)


def solve_one(args):
    pid, pz, variants, tl = args
    starts = set(pz["starts"]); L = pz["limit"]
    targets = [t for t in pz["targets"] if t not in starts]
    bestprog = json.loads((BEST / f"{pid}.json").read_text())
    variants = [bestprog] + [v for v in variants if len(v) <= len(bestprog) * (1 + REL)]   # near-best only: small, fast models
    pos = {}                                                   # earliest relative position of each value in any variant
    vals = set(starts); recipes = set()
    for prog in variants:
        for n, (c, op, a, b) in enumerate(simulate(pz, prog)):
            vals.add(c); pos[c] = min(pos.get(c, 9.0), n / len(prog))
            if c not in starts and c != a and c != b: recipes.add((c, op, a, b))
    for c, op, a, b in enrich(vals, L):
        if c in starts or c == a or c == b: continue
        recipes.add((c, op, a, b))
    bpos = {}
    for n, (c, op, a, b) in enumerate(simulate(pz, bestprog)): bpos.setdefault(c, n / len(bestprog))
    rk = lambda v: -1.0 if v in starts else bpos.get(v, pos[v])
    nb = 0
    if BRIDGE:
        newx, xrec, brec = bridges(vals, starts, L, rk)
        pos.update(newx); vals |= set(newx); recipes |= set(xrec) | set(brec); nb = len(newx)
    if NORANK: recipes = sorted(r for r in recipes if r[0] not in (r[2], r[3]))
    else: recipes = sorted(r for r in recipes if rk(r[2]) < rk(r[0]) and rk(r[3]) < rk(r[0]))   # acyclic by construction
    nodes = sorted(vals - starts); xi = {v: k for k, v in enumerate(nodes)}
    n, m = len(nodes), len(recipes)
    rows, cols, data, lo, hi = [], [], [], [], []
    def row(entries, l, h):
        r = len(lo)
        for c, d in entries: rows.append(r); cols.append(c); data.append(d)
        lo.append(l); hi.append(h)
    into = [[] for _ in range(n)]
    for k, (c, op, a, b) in enumerate(recipes):
        into[xi[c]].append(k)
        for u in {a, b} - starts: row([(n + k, 1), (xi[u], -1)], -np.inf, 0)
    for v in range(n): row([(n + k, 1) for k in into[v]] + [(v, -1)], 0, np.inf)
    lb = np.zeros(n + m); ub = np.ones(n + m)
    for t in targets: lb[xi[t]] = 1
    cobj = np.concatenate([np.ones(n), np.zeros(m)])
    x0 = None                                                  # warm start: the best program's own values and recipes
    ri = {r: k for k, r in enumerate(recipes)}
    x0 = np.zeros(n + m)
    for c, op, a, b in simulate(pz, bestprog):
        if c in starts or x0[xi[c]]: continue
        k = ri.get((c, op, a, b))
        if k is None and op in "+*": k = ri.get((c, op, b, a))
        if k is None: x0 = None; break
        x0[xi[c]] = 1; x0[n + k] = 1
    t0 = time.time()
    for it in range(60):
        if HIGHS:
            rx = solve_highs(cobj, rows, cols, data, lo, hi, lb, ub, max(5, tl - (time.time() - t0)), x0)
            if rx is None: return pid, None, "no solution (highs)"
        else:
            A = coo_matrix((data, (rows, cols)), shape=(len(lo), n + m)).tocsr()
            r = milp(cobj, constraints=LinearConstraint(A, lo, hi), integrality=np.ones(n + m), bounds=Bounds(lb, ub),
                     options={"time_limit": max(5, tl - (time.time() - t0)), "disp": False})
            if r.x is None: return pid, None, f"no solution ({r.message})"
            rx = r.x
        X = {nodes[v] for v in range(n) if rx[v] > 0.5}
        Y = [recipes[k] for k in range(m) if rx[n + k] > 0.5 and recipes[k][0] in X]
        have = set(starts); chosen = {}
        changed = True
        while changed:
            changed = False
            for c, op, a, b in Y:
                if c not in have and a in have and b in have: have.add(c); chosen[c] = (op, a, b); changed = True
        U = X - have
        if not U: break
        for u in U:                                            # cycle cut
            ent = [(n + k, 1) for c in U for k in into[xi[c]] if not ({recipes[k][2], recipes[k][3]} & U)]
            row(ent + [(xi[u], -1)], 0, np.inf)
    else:
        return pid, None, "cycle cuts did not converge"
    obj = len(X)
    prog = None
    if obj < len(bestprog):                                    # only worth scheduling hard when it is shorter
        for sd in range(4):
            prog = order_and_allocate(pz, chosen, {v: rk(v) for v in chosen}, seed=sd)
            if prog: break
    else:
        prog = bestprog
    if prog is None: return pid, None, f"ilp {obj} but register allocation failed"
    return pid, prog, f"ilp {obj} ({n} values, {nb} bridges, {m} recipes, {it + 1} solves, {time.time() - t0:.0f}s)"


def alloc(pz, chosen, order):
    """Registers for a given order: overwrite the dead register written longest ago. Returns a valid program or None."""
    last = {}
    for k, c in enumerate(order):
        op, a, b = chosen[c]
        last[a] = k; last[b] = k
    R = [None] * pz["regs"]; when = [-2] * pz["regs"]; where = {}
    for k, v in enumerate(pz["starts"]): R[k] = v; where[v] = k; when[k] = -1
    prog = []
    for k, c in enumerate(order):
        op, a, b = chosen[c]
        ra, rb = where[a], where[b]
        best = None
        for r in range(pz["regs"]):
            v = R[r]
            if v is None or last.get(v, -1) <= k:
                if best is None or when[r] < when[best]: best = r
        if best is None: return None
        if R[best] is not None: where.pop(R[best], None)
        R[best] = c; where[c] = best; when[best] = k
        prog.append([op, ra, rb, best])
    try:
        replay(pz, prog); return prog
    except ValueError:
        return None


def order_and_allocate(pz, chosen, rank, tries=1500, seed=0):
    """Try the rank order, then randomized register-pressure-aware list schedules."""
    import random
    rng = random.Random(seed)
    deps = {c: {u for u in (a, b) if u in chosen} for c, (op, a, b) in chosen.items()}
    users = {c: set() for c in chosen}
    for c, ds in deps.items():
        for u in ds: users[u].add(c)
    readers = {}                                               # value -> chosen nodes reading it (starts included)
    for c, (op, a, b) in chosen.items():
        for u in {a, b}: readers.setdefault(u, set()).add(c)
    # 1) plain topological order by rank
    indeg = {c: len(ds) for c, ds in deps.items()}
    heap = [(rank.get(c, 9.0), c) for c in chosen if indeg[c] == 0]; heapq.heapify(heap)
    ind = dict(indeg); order = []
    while heap:
        _, c = heapq.heappop(heap); order.append(c)
        for w in users[c]:
            ind[w] -= 1
            if ind[w] == 0: heapq.heappush(heap, (rank.get(w, 9.0), w))
    if len(order) != len(chosen): return None
    prog = alloc(pz, chosen, order)
    if prog: return prog
    # 2) pressure-aware list scheduling with noise
    REGS = pz["regs"]
    for t in range(tries):
        noise = 0.3 + 2.0 * t / tries; alpha = rng.choice([0.0, 1.0, 3.0, 10.0])
        rem = {u: len(r) for u, r in readers.items()}
        live = {v for v in pz["starts"] if rem.get(v, 0) > 0}
        ind = dict(indeg); ready = {c for c in chosen if ind[c] == 0}; order = []; ok = True
        while ready:
            bestc, bests = None, None
            for c in ready:
                op, a, b = chosen[c]
                freed = sum(1 for u in {a, b} if rem.get(u, 0) == 1)
                if len(live) - freed + 1 > REGS: continue
                sc = freed - (1 if users[c] else 0) - alpha * rank.get(c, 9.0) + noise * rng.random()
                if bests is None or sc > bests: bestc, bests = c, sc
            if bestc is None: ok = False; break
            c = bestc; op, a, b = chosen[c]; ready.discard(c); order.append(c)
            for u in {a, b}:
                rem[u] -= 1
                if rem[u] == 0: live.discard(u)
            if users[c]: live.add(c)
            for w in users[c]:
                ind[w] -= 1
                if ind[w] == 0: ready.add(w)
        if ok and len(order) == len(chosen):
            prog = alloc(pz, chosen, order)
            if prog: return prog
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("--ids", default=""); ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=1000); ap.add_argument("--workers", type=int, default=12); ap.add_argument("--tl", type=float, default=60)
    a = ap.parse_args()
    if a.cmd == "collect": return collect()
    P = load(); V = json.loads(VAR.read_text())
    ids = a.ids.split(",") if a.ids else sorted(P)[a.start:a.end]
    jobs = [(pid, P[pid], V[pid], a.tl) for pid in ids]
    gain = 0; t0 = time.time()
    with ProcessPoolExecutor(a.workers) as ex:
        for pid, prog, msg in ex.map(solve_one, jobs, chunksize=1):
            g = offer(P[pid], pid, prog, source="recomb") if prog else 0
            gain += g
            print(f"{pid} best {best_len(pid)} {'len ' + str(len(prog)) if prog else ''} {msg}{'  GAIN ' + str(g) if g else ''}", flush=True)
    print(f"total gain {gain} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
