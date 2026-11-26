"""Helper re-derivation pass. For every non-target value v of a best program, its private cone (instructions whose results feed only
v) is replaced by a shorter derivation of v from the values live in registers just before v's first use: v already present
(0 instructions), one instruction, or two (x op p / x op y with x, y one step away). Registers are re-allocated by a liveness
scan, the program is replayed, and the store keeps it only if it is valid and shorter. Repeats until nothing changes.
usage: python helper_rederive.py [pid ...]          (default: all puzzles)"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, offer, BEST

REGS = 48


def apply(op, a, b):
    if op == "+": return a + b
    if op == "-": return a - b if a > b else None
    if op == "*": return a * b
    return a // b if b and a % b == 0 else None


def to_nodes(pz, prog):
    """SSA nodes: (value, op, a, b) with a/b node ids; starts are op None. Returns nodes, ns, regs_before[k] (node ids live
    in registers before instruction k)."""
    nodes = [(v, None, -1, -1) for v in pz["starts"]]
    src = list(range(len(nodes))) + [None] * (REGS - len(nodes)); R = list(pz["starts"]) + [None] * (REGS - len(nodes))
    before = []
    for op, i, j, d in prog:
        before.append([s for s in src if s is not None])
        c = apply(op, R[i], R[j]); nodes.append((c, op, src[i], src[j])); R[d] = c; src[d] = len(nodes) - 1
    return nodes, len(pz["starts"]), before


def allocate(pz, nodes, ns):
    """Linear-scan register allocation of SSA nodes; returns the instruction list or None if more than 48 values are live."""
    N = len(nodes); last = [-1] * N
    for k in range(ns, N):
        _, _, a, b = nodes[k]; last[a] = max(last[a], k); last[b] = max(last[b], k)
    reg = [None] * N; holder = [None] * REGS
    for k in range(ns): reg[k] = k; holder[k] = k
    prog = []
    for k in range(ns, N):
        v, op, a, b = nodes[k]
        free = None
        for r in range(REGS):                     # a register whose value is dead after this instruction (operands may be reused)
            h = holder[r]
            if h is None or last[h] <= k:
                if h is None or last[h] < k or h in (a, b): free = r; break
        if free is None: return None
        prog.append([op, reg[a], reg[b], free]); reg[k] = free; holder[free] = k
    return prog


def one_steps(vals, L):
    """value -> (op, x, y) over all pairs of the given values (x, y values)"""
    out = {}
    vs = sorted(vals)
    for i, x in enumerate(vs):
        for y in vs[i:]:
            for op, a, b in (("+", x, y), ("*", x, y), ("-", y, x), ("-", x, y), ("/", y, x), ("/", x, y)):
                c = apply(op, a, b)
                if c is not None and 1 <= c <= L and c not in out: out[c] = (op, a, b)
    return out


def inverses(t, p, L):
    """(x, op, x_first): t = x op p (x_first) or t = p op x"""
    r = [(t - p, "+", True), (t + p, "-", True), (p - t, "-", False)]
    if t % p == 0: r.append((t // p, "*", True))
    r.append((t * p, "/", True))
    if p % t == 0: r.append((p // t, "/", False))
    return [(x, op, f) for x, op, f in r if 1 <= x <= L]


def improve_once(pz, prog):
    L = pz["limit"]; T = set(pz["targets"])
    nodes, ns, before = to_nodes(pz, prog)
    N = len(nodes)
    users = [[] for _ in range(N)]
    for k in range(ns, N):
        _, _, a, b = nodes[k]; users[a].append(k)
        if b != a: users[b].append(k)
    first = {}
    for k in range(ns, N):
        if nodes[k][0] in T and nodes[k][0] not in first: first[nodes[k][0]] = k
    tgt = set(first.values())
    cands = []
    for v in range(ns, N):
        if v in tgt or not users[v]: continue
        cone = {v}; changed = True
        while changed:
            changed = False
            for u in range(v - 1, ns - 1, -1):
                if u in cone or u in tgt or not users[u]: continue
                if all(w in cone for w in users[u]): cone.add(u); changed = True
        if len(cone) >= 2: cands.append((len(cone), v, cone))
    cands.sort(key=lambda x: -x[0])
    for c, v, cone in cands:
        fu = min(users[v]); val = nodes[v][0]
        pool = [s for s in before[fu - ns] if s not in cone]
        byval = {}
        for s in pool: byval.setdefault(nodes[s][0], s)
        new = None                                   # list of (value, op, a_val, b_val) to insert before fu
        if val in byval: new = []
        else:
            D1 = one_steps(byval.keys(), L)
            if val in D1: op, a, b = D1[val]; new = [(val, op, a, b)]
            elif c >= 3:
                for p in byval:
                    for x, op, xf in inverses(val, p, L):
                        if x in D1: new = [(x,) + D1[x], (val, op, x, p) if xf else (val, op, p, x)]; break
                    if new: break
                if new is None:
                    for x in D1:
                        for y, op, yf in inverses(val, x, L):
                            if y in D1 and y != x: new = [(x,) + D1[x], (y,) + D1[y], (val, op, y, x) if yf else (val, op, x, y)]; break
                        if new: break
        if new is None or len(new) >= c: continue
        # rebuild the node list: drop the cone, insert the new derivation right before fu
        keep = [k for k in range(N) if k not in cone]
        out, idmap, vmap = [], {}, dict(byval)        # vmap: value -> new node id (for the inserted instructions)
        for k in keep:
            if k == fu:
                for nv, op, a, b in new:
                    ia, ib = vmap.get(a), vmap.get(b)
                    if ia is None or ib is None: break
                    out.append((nv, op, ia, ib)); vmap.setdefault(nv, len(out) - 1)
                vid = vmap.get(val)
                if vid is None: break
                idmap[v] = vid
            vv, op, a, b = nodes[k]
            if op is None: out.append((vv, None, -1, -1))
            else: out.append((vv, op, idmap[a], idmap[b]))
            idmap[k] = len(out) - 1
            # pool references for later inserts use new ids
            if k in byval.values():
                for val2, s in byval.items():
                    if s == k: vmap[val2] = len(out) - 1
        else:
            cand = allocate(pz, out, ns)
            if cand is not None and len(cand) < len(prog): return cand
    return None


def main():
    P = load(); ids = sys.argv[1:] or sorted(P); total = 0
    for pid in ids:
        pz = P[pid]; prog = json.loads((BEST / f"{pid}.json").read_text()); g = 0
        while True:
            new = improve_once(pz, prog)
            if new is None: break
            gain = offer(pz, pid, new, source="helper_rederive")
            if not gain: break
            g += gain; prog = new
        if g: print(pid, len(prog) + g, "->", len(prog), flush=True)
        total += g
    print("total gain", total)


if __name__ == "__main__":
    main()
