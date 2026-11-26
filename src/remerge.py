"""Keep up with the public frontier: pull every public Santa 2026 notebook output and program dataset that changed since the last
pull, offer all programs to the best/ store (each one replay-validated), write a submission and submit it if the total dropped.

Downloads are untrusted data: only CSV files are parsed (csv module + json.loads), nothing is executed.

usage: python remerge.py [--no-submit] [--all] [--no-recomb] [--store-only]   (--all re-pulls everything, ignoring the change log)
"""
import argparse, csv, io, json, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from elf import load, offer, best_len, write_submission, ROOT  # noqa: E402

csv.field_size_limit(1 << 30)
KAGGLE = str(ROOT.parents[1] / ".venv" / "Scripts" / "kaggle")
STATE = ROOT / "work" / "remerge_state.json"
PUB = ROOT / "pub3"
ME = "shauryanadagoudra"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")


def kg(*args, timeout=600):
    r = subprocess.run([KAGGLE, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV, timeout=timeout)
    return r.returncode, r.stdout


def listing():
    """{ref: last-changed} for public notebooks of the competition and Santa 2026 program datasets."""
    out = {}
    for sort in ("dateRun", "voteCount", "scoreAscending", "hotness"):
        for page in (1, 2):
            code, txt = kg("kernels", "list", "--competition", "santa-2026", "--sort-by", sort, "--page-size", "100", "-p", str(page), "--csv")
            if code: continue
            for r in csv.DictReader(io.StringIO(txt)):
                if r.get("ref") and not r["ref"].startswith(ME + "/"): out["k:" + r["ref"]] = r.get("lastRunTime", "")
    for q in ("santa 2026", "elf calculator"):
        code, txt = kg("datasets", "list", "-s", q, "--sort-by", "updated", "--csv")
        if code: continue
        for r in csv.DictReader(io.StringIO(txt)):
            t = (r.get("title") or "").lower()
            # 11-20: require a contest-specific title and skip huge datasets (a 15 GB 'Santa Catarina' health dataset slipped in)
            try: size = int(r.get("size") or 0)
            except ValueError: size = 0
            relevant = "santa 2026" in t or "santa-2026" in t or "santa2026" in t or "elf" in t or "santa-2026" in r.get("ref", "")
            if r.get("ref") and not r["ref"].startswith(ME + "/") and relevant and size <= 300_000_000:
                out["d:" + r["ref"]] = r.get("lastUpdated", "")
    return out


def pull(key):
    kind, ref = key.split(":", 1)
    dest = PUB / (kind + "__" + ref.replace("/", "__"))
    dest.mkdir(parents=True, exist_ok=True)
    for f in dest.rglob("*"):
        if f.is_file(): f.unlink()
    if kind == "k": code, _ = kg("kernels", "output", ref, "-p", str(dest), timeout=900)
    else: code, _ = kg("datasets", "download", ref, "-p", str(dest), "--unzip", timeout=900)
    return dest if code == 0 else None


def ingest_dir(P, d):
    gain = 0
    for f in d.rglob("*.csv"):
        if f.stat().st_size < 50_000: continue
        try:
            with open(f, newline="", encoding="utf-8") as fh:
                rd = csv.DictReader(fh)
                if not rd.fieldnames or "id" not in rd.fieldnames or "program" not in rd.fieldnames: continue
                for r in rd:
                    pid = r.get("id")
                    if pid not in P: continue
                    try: prog = json.loads(r["program"])
                    except Exception: continue
                    gain += offer(P[pid], pid, prog, source="pub:" + d.name)
        except Exception as e:
            print("  skip", f.name, e)
    return gain


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--no-submit", action="store_true"); ap.add_argument("--all", action="store_true"); ap.add_argument("--no-recomb", action="store_true")
    ap.add_argument("--store-only", action="store_true", help="update the best store only; no submission file (work/autoloop.sh submits)")
    a = ap.parse_args()
    P = load()
    before = sum(best_len(p) for p in P)
    state = json.loads(STATE.read_text()) if STATE.exists() and not a.all else {}
    now = listing()
    changed = [k for k, v in now.items() if state.get(k) != v]
    print(f"{len(now)} public sources, {len(changed)} new or changed")
    total_gain = 0
    for k in changed:
        d = pull(k)
        if d is None: print("  pull failed", k); continue
        g = ingest_dir(P, d); total_gain += g
        state[k] = now[k]
        if g: print(f"  {k}: -{g}")
    STATE.write_text(json.dumps(state, indent=0))
    # recombine near-best variants from all authors (src/recomb.py): occasionally shorter than any single program
    py = str(ROOT.parents[1] / ".venv" / "Scripts" / "python")
    if not a.no_recomb:
      subprocess.run([py, str(ROOT / "src" / "recomb.py"), "collect"], env=ENV, cwd=ROOT)
      r = subprocess.run([py, str(ROOT / "src" / "recomb.py"), "solve", "--workers", "12", "--tl", "60"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(ENV, REL="0.3"), cwd=ROOT)
      print("recomb:", (r.stdout.strip().splitlines() or ["?"])[-1])
    after = sum(best_len(p) for p in P)
    print(f"store {before} -> {after}")
    if after < before and not a.store_only:
        n = len(list((ROOT / "submissions").glob("*.csv"))) + 1
        out = ROOT / "submissions" / f"{n:02d}_remerge_{after}.csv"
        tot = write_submission(out, P)
        assert tot == after, (tot, after)
        print("wrote", out.name)
        if not a.no_submit:
            r = subprocess.run([str(ROOT.parents[1] / ".venv" / "Scripts" / "python"), str(ROOT.parents[1] / "tools" / "kg.py"), "submit", "santa-2026",
                                str(out), "-m", f"public re-merge {time.strftime('%m-%d')}"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
            print(r.stdout.strip().splitlines()[-2:] if r.stdout else r.stderr[-500:])


if __name__ == "__main__":
    main()
