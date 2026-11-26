"""Write the best store as a submission (every program replayed while writing) and submit it if it beats the last submitted total.
usage: python submit_store.py DESC [--no-submit]      (DESC: short file-name tag, e.g. lns_changed)"""
import subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from elf import load, best_len, write_submission, ROOT

desc = sys.argv[1]; P = load()
total = sum(best_len(p) for p in P)
last_f = ROOT / "work" / "last_submitted.txt"
last = int(last_f.read_text().split()[0]) if last_f.exists() else 10**9
print(f"store {total}, last submitted {last}")
if total >= last:
    print("nothing new to submit"); sys.exit(0)
n = len(list((ROOT / "submissions").glob("*.csv"))) + 1
out = ROOT / "submissions" / f"{n:02d}_{desc}_{total}.csv"
assert write_submission(out, P) == total
print("wrote", out.name)
if "--no-submit" in sys.argv: sys.exit(0)
r = subprocess.run([str(ROOT.parents[1] / ".venv" / "Scripts" / "python"), str(ROOT.parents[1] / "tools" / "kg.py"), "submit", "santa-2026", str(out),
                    "-m", f"{desc.replace('_', ' ')} {time.strftime('%m-%d %H:%M')}"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print((r.stdout or r.stderr).strip().splitlines()[-2:])
if "Public score" in r.stdout or "Successfully" in r.stdout:
    last_f.write_text(f"{total} {out.name}\n")
