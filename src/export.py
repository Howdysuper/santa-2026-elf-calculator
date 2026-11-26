"""Write solver inputs: OUTDIR/puzzles.txt and OUTDIR/programs.txt (from the best store). usage: python export.py OUTDIR"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, BEST
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
P = load()
with open(out / "puzzles.txt", "w") as f:
    for pid, p in sorted(P.items()):
        f.write(" ".join(map(str, [pid, p["limit"], len(p["starts"]), len(p["targets"]), *p["starts"], *p["targets"]])) + "\n")
tot = 0
with open(out / "programs.txt", "w") as f:
    for pid in sorted(P):
        prog = json.loads((BEST / f"{pid}.json").read_text()); tot += len(prog)
        f.write(f"{pid} {len(prog)} " + " ".join(f"{o} {a} {b} {d}" for o, a, b, d in prog) + "\n")
print("exported", len(P), "puzzles, total", tot)
