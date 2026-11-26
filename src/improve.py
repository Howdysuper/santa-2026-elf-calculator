"""Local improvement of stored best programs.

For each target: find its private cone (instructions whose results are used only on the way to that target),
remove them, and search for a shorter derivation from the values held in registers at that point.
Also removes dead instructions. Every accepted change is fully re-validated.

usage: python improve.py [--ids a,b] [--start i --end j] [--kmax 5] [--workers 12] [--passes 3]
"""
import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from elf import load, replay, offer, BEST  # noqa: E402
from search import Pool, check  # noqa: E402


def run(pz, prog):
    """Simulate; return per-instruction (value, producers(i), producers(j)) and first-cover index per target."""
    R = [None] * pz["regs"]; W = [-1] * pz["regs"]          # value and writer instruction per register
    for k, v in enumerate(pz["starts"]): R[k] = v
    targets = set(pz["targets"]); covered = set(pz["starts"]) & targets
    info, first = [], {}
    for n, (op, i, j, d) in enumerate(prog):
        a, b = R[i], R[j]
        c = a + b if op == "+" else a - b if op == "-" else a * b if op == "*" else a // b
        info.append((c, W[i], W[j]))
        if c in targets and c not in covered:
            covered.add(c); first[n] = c
        R[d] = c; W[d] = n
    return info, first


def dead_code(pz, prog):
    while True:
        info, first = run(pz, prog)
        used = set()
        for c, wi, wj in info:
            used.add(wi); used.add(wj)
        drop = [n for n in range(len(prog)) if n not in used and n not in first]
        if not drop: return prog
        ds = set(drop); prog = [ins for n, ins in enumerate(prog) if n not in ds]


def cone(prog, info, first, j):
    users = {}
    for n, (c, wi, wj) in enumerate(info):
        for p in {wi, wj}:
            if p >= 0: users.setdefault(p, set()).add(n)
    C = set(); cand = sorted({info[j][1], info[j][2]} - {-1}, reverse=True)
    stack = list(cand)
    while stack:
        stack.sort(); p = stack.pop()                  # highest index first
        if p in C or p in first: continue
        if users.get(p, set()) <= (C | {j}):
            C.add(p)
            for q in (info[p][1], info[p][2]):
                if q >= 0 and q not in C: stack.append(q)
    return C


def try_target(pz, prog, j, kmax):
    info, first = run(pz, prog)
    C = cone(prog, info, first, j)
    if not C: return None
    budget = min(kmax, len(C))                          # need <= len(C) new steps to gain >= 1
    rest = [ins for n, ins in enumerate(prog) if n not in C]
    jj = j - sum(1 for n in C if n < j)                 # index of the target instruction in rest
    # register state just before jj
    R = [None] * pz["regs"]
    for k, v in enumerate(pz["starts"]): R[k] = v
    for op, i, jx, d in rest[:jj]:
        a, b = R[i], R[jx]
        R[d] = a + b if op == "+" else a - b if op == "-" else a * b if op == "*" else a // b
    t = info[j][0]; dst = rest[jj][3]
    pool = [v for v in R if v is not None]
    P = Pool(pool, pz["limit"])
    deriv = P.find(t, budget)
    if deriv is None or len(deriv) > len(C): return None
    if len(deriv) == 0: deriv_ins = []
    # liveness after jj: a register is live if read before written in rest[jj+1:]
    live = set(); written = set()
    for op, i, jx, d in rest[jj + 1:]:
        for r in (i, jx):
            if r not in written: live.add(r)
        written.add(d)
    reg_of = {}
    for r, v in enumerate(R):
        if v is not None and v not in reg_of: reg_of[v] = r
    used_pool = {ref[1] for _, a, b in deriv for ref in (a, b) if ref[0] == "p"}
    protect = {reg_of[v] for v in used_pool} | live | {dst}
    free = [r for r in range(pz["regs"]) if r not in protect]
    free.sort(key=lambda r: (R[r] is not None, r))      # undefined registers first
    if len(deriv) - 1 > len(free): return None
    regs_new = free[: len(deriv) - 1] + [dst]
    new = []
    for k, (op, a, b) in enumerate(deriv):
        ra = reg_of[a[1]] if a[0] == "p" else regs_new[a[1]]
        rb = reg_of[b[1]] if b[0] == "p" else regs_new[b[1]]
        new.append([op, ra, rb, regs_new[k]])
    cand = rest[:jj] + new + rest[jj + 1:]
    try:
        replay(pz, cand)
    except ValueError:
        return None
    return cand


def improve_one(args):
    pid, pz, prog, kmax, passes = args
    start = len(prog)
    prog = dead_code(pz, prog)
    for _ in range(passes):
        changed = False
        info, first = run(pz, prog)
        order = sorted(first)                            # instruction indices that first cover a target
        k = 0
        while k < len(order):
            j = order[k]
            cand = try_target(pz, prog, j, kmax)
            if cand is not None and len(cand) < len(prog):
                prog = dead_code(pz, cand); changed = True
                info, first = run(pz, prog); order = sorted(first)
                continue                                 # indices shifted; re-scan from the same rank
            k += 1
        if not changed: break
    return pid, start, prog


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=""); ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=1000)
    ap.add_argument("--kmax", type=int, default=5); ap.add_argument("--workers", type=int, default=12); ap.add_argument("--passes", type=int, default=3)
    a = ap.parse_args()
    P = load()
    ids = a.ids.split(",") if a.ids else sorted(P)[a.start:a.end]
    jobs = [(pid, P[pid], json.loads((BEST / f"{pid}.json").read_text()), a.kmax, a.passes) for pid in ids]
    t0 = time.time(); gain = 0; done = 0
    with ProcessPoolExecutor(a.workers) as ex:
        for pid, before, prog in ex.map(improve_one, jobs, chunksize=1):
            done += 1
            g = offer(P[pid], pid, prog, source=f"improve_k{a.kmax}")
            gain += g
            if g: print(f"{pid}: {before} -> {len(prog)}", flush=True)
            if done % 50 == 0: print(f"[{done}/{len(jobs)}] gain {gain} {time.time() - t0:.0f}s", flush=True)
    print(f"total gain {gain} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
