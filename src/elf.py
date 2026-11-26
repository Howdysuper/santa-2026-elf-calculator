"""Shared helpers: load puzzles, replay/validate programs, keep a per-puzzle best store, write submissions."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BEST = ROOT / "best"            # best/<id>.json = program (list of instructions); the source of truth
BEST.mkdir(exist_ok=True)


def load(practice=False):
    f = DATA / ("practice_puzzles.csv" if practice else "puzzles.csv")
    out = {}
    with open(f, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[r["id"]] = dict(starts=json.loads(r["starting_values"]), targets=json.loads(r["targets"]),
                                limit=int(r["value_limit"]), regs=int(r["registers"]),
                                family=r.get("family"), tier=r.get("design_tier"))
    return out


def replay(pz, prog):
    """Return instruction count if prog is valid for puzzle pz, else raise ValueError with the reason."""
    if not isinstance(prog, list) or len(prog) > 4096:
        raise ValueError("not a list or too long")
    R = [None] * pz["regs"]
    for k, v in enumerate(pz["starts"]):
        R[k] = v
    need = set(pz["targets"]) - set(pz["starts"])
    lim = pz["limit"]
    for n, ins in enumerate(prog):
        if not (isinstance(ins, list) and len(ins) == 4):
            raise ValueError(f"{n}: bad instruction {ins}")
        op, i, j, d = ins
        if op not in "+-*/" or len(op) != 1:
            raise ValueError(f"{n}: bad op")
        for r in (i, j, d):
            if type(r) is not int or not 0 <= r < pz["regs"]:
                raise ValueError(f"{n}: bad register {r}")
        a, b = R[i], R[j]
        if a is None or b is None:
            raise ValueError(f"{n}: undefined source")
        if op == "+": c = a + b
        elif op == "-":
            if a <= b: raise ValueError(f"{n}: non-positive subtraction")
            c = a - b
        elif op == "*": c = a * b
        else:
            if a % b: raise ValueError(f"{n}: inexact division")
            c = a // b
        if c > lim or c < 1:
            raise ValueError(f"{n}: value {c} out of range")
        R[d] = c
        need.discard(c)
    if need:
        raise ValueError(f"{len(need)} targets not produced")
    return len(prog)


def best_len(pid):
    p = BEST / f"{pid}.json"
    return len(json.loads(p.read_text())) if p.exists() else 10**9


def offer(pz, pid, prog, source=""):
    """Validate prog and store it if it beats the current best. Returns gain (0 if not better or invalid)."""
    try:
        n = replay(pz, prog)
    except ValueError:
        return 0
    old = best_len(pid)
    if n < old:
        (BEST / f"{pid}.json").write_text(json.dumps(prog, separators=(",", ":")))
        with open(ROOT / "best_log.csv", "a") as fh:
            fh.write(f"{pid},{old},{n},{source}\n")
        return (old - n) if old < 10**9 else n
    return 0


def write_submission(path, puzzles):
    total = 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["id", "program"])
        for pid in sorted(puzzles):
            prog = json.loads((BEST / f"{pid}.json").read_text())
            total += replay(puzzles[pid], prog)
            w.writerow([pid, json.dumps(prog, separators=(",", ":"))])
    return total
