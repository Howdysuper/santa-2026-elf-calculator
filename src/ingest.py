"""Offer every program in one or more submission CSVs to the best store. usage: python ingest.py FILE.csv [...]"""
import csv, json, sys
from elf import load, offer, best_len
csv.field_size_limit(10**9)
P = load()
for f in sys.argv[1:]:
    gain = bad = 0
    with open(f, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("id") not in P: continue
            try: prog = json.loads(r["program"])
            except Exception: bad += 1; continue
            g = offer(P[r["id"]], r["id"], prog, source=f.replace("\\", "/").split("/")[-2] if "/" in f.replace("\\", "/") else f)
            gain += g
    print(f"{f}: improved by {gain}; store total {sum(best_len(p) for p in P)}")
