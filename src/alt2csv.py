"""Convert solver variant files (lines: id n op a b d ...) into CSVs under work/alt/ that src/recomb.py collect picks up.
Keeps at most --cap distinct programs per puzzle (shortest first).
usage: python alt2csv.py FILE.txt [...] [--cap 60]"""
import argparse, csv, json
from pathlib import Path

ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--cap", type=int, default=60)
a = ap.parse_args()
out = Path(__file__).resolve().parents[1] / "work" / "alt"; out.mkdir(parents=True, exist_ok=True)
for f in a.files:
    by = {}
    for line in open(f):
        p = line.split()
        if len(p) < 2: continue
        n = int(p[1])
        if len(p) != 2 + 4 * n: continue
        prog = [[p[2 + 4 * k], int(p[3 + 4 * k]), int(p[4 + 4 * k]), int(p[5 + 4 * k])] for k in range(n)]
        by.setdefault(p[0], set()).add(json.dumps(prog, separators=(",", ":")))
    rows = [(pid, s) for pid, ss in by.items() for s in sorted(ss, key=len)[: a.cap]]
    dst = out / (Path(f).stem + ".csv")
    with open(dst, "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["id", "program"]); w.writerows(rows)
    print(f"{f}: {len(rows)} programs for {len(by)} puzzles -> {dst.name}")
