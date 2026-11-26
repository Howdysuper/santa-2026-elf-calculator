"""Run the cumulative-benefit planner (src/hcub.cpp -> work/hcub.exe) on top of each best program's scaffold.
The scaffold is the best program's first instructions: PREFIX=k keeps k of them, PREFIX=first (default) keeps everything before
the first target appears. The plan is pruned of unused values, scheduled onto 48 registers (recomb.order_and_allocate), replayed,
and offered to the best store (kept only if shorter).
usage: python hcub_run.py [--dry] ID [ID ...]      env: PREFIX, HSEC (seconds per puzzle), NOISE, FAR, SEED"""
import json, os, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, offer, BEST, ROOT
from recomb import simulate, order_and_allocate

EXE = ROOT / "work" / "hcub.exe"


def prefix_recipes(pz, prog, mode):
    sim = simulate(pz, prog); T = set(pz["targets"]); starts = set(pz["starts"])
    if mode == "first": k = next(n for n, (c, *_r) in enumerate(sim) if c in T and c not in starts)
    elif "." in mode: k = int(float(mode) * len(prog))
    else: k = int(mode)
    seen = set(starts); out = []
    for c, op, a, b in sim[:k]:
        if c in seen: continue
        seen.add(c); out.append((c, op, a, b))
    return out


def prune(pz, chosen, order):
    """Drop values that are neither targets nor read by a kept value."""
    T = set(pz["targets"]); keep = set(chosen)
    while True:
        used = {u for c in keep for u in chosen[c][1:]}
        dead = {c for c in keep if c not in T and c not in used}
        if not dead: break
        keep -= dead
    return {c: chosen[c] for c in order if c in keep}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]; dry = "--dry" in sys.argv
    P = load(); mode = os.environ.get("PREFIX", "first")
    lines, base = [], {}
    for pid in args:
        pz = P[pid]; prog = json.loads((BEST / f"{pid}.json").read_text()); base[pid] = len(prog)
        pre = prefix_recipes(pz, prog, mode)
        lines.append(" ".join(map(str, [pid, pz["limit"], len(pz["starts"]), len(pz["targets"]), *pz["starts"], *pz["targets"], "|", len(pre)]
                                   + [x for r in pre for x in r] + [len(prog) + 10])))
    r = subprocess.run([str(EXE)], input="\n".join(lines) + "\n", capture_output=True, text=True)
    total = 0
    for line in r.stdout.splitlines():
        x = line.split(); pid = x[0]; n = int(x[1]); pz = P[pid]
        recs = [(int(x[2 + 4 * k]), x[3 + 4 * k], int(x[4 + 4 * k]), int(x[5 + 4 * k])) for k in range(n)]
        chosen, order = {}, []
        for c, op, a, b in recs:
            if c in chosen or c in pz["starts"]: continue
            chosen[c] = (op, a, b); order.append(c)
        chosen = prune(pz, chosen, order)
        prog = order_and_allocate(pz, chosen, {c: k for k, c in enumerate(chosen)}, tries=300)
        got = len(prog) if prog else None
        gain = 0 if dry or not prog else offer(pz, pid, prog, source="hcub")
        total += gain
        print(f"{pid} best {base[pid]} plan {n} pruned {len(chosen)} allocated {got} gain {gain}", flush=True)
    print("total gain", total)


if __name__ == "__main__":
    main()
