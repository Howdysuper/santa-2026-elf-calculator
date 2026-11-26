# Elf calculator: structure-aware CP-SAT recombination over a share of the structured puzzles (template; PART/NPARTS/SEED
# are filled in by work/kcpsat.ps1). Inputs: private dataset elf-calc-cpsat-inputs.
import glob, os, subprocess, sys, time, json, shutil
PART, NPARTS = __PART__, __NPARTS__
src = os.path.dirname(glob.glob("/kaggle/input/**/cpsat_recomb.py", recursive=True)[0])
W = "/kaggle/working"
for d in ("src", "data", "best", "work"): os.makedirs(f"{W}/{d}", exist_ok=True)
for f in ("cpsat_recomb.py", "elf.py"): shutil.copy(f"{src}/{f}", f"{W}/src/{f}")
shutil.copy(f"{src}/puzzles.csv", f"{W}/data/puzzles.csv")
shutil.copy(f"{src}/hubs_all.txt", f"{W}/work/hubs_all.txt")
for line in open(f"{src}/programs.txt"):
    x = line.split(); n = int(x[1])
    prog = [[x[2 + 4 * k], int(x[3 + 4 * k]), int(x[4 + 4 * k]), int(x[5 + 4 * k])] for k in range(n)]
    json.dump(prog, open(f"{W}/best/{x[0]}.json", "w"), separators=(",", ":"))
try:
    import ortools  # noqa
except ImportError:
    whl = glob.glob(f"{src}/wheels/*.whl") + glob.glob(f"{src}/*.whl")
    subprocess.run([sys.executable, "-m", "pip", "install", "--no-index", "--no-deps", "--target", f"{W}/ortools_lib", *whl], check=False)
env = dict(os.environ, STRUCT="1", PYTHONPATH=f"{W}/ortools_lib")
ids = [l.strip() for l in open(f"{src}/cpsat_ids.txt") if l.strip()]
mine = [p for i, p in enumerate(ids) if i % NPARTS == PART]
open(f"{W}/ids.txt", "w").write("\n".join(mine) + "\n")
th = os.cpu_count() or 4
sec = max(60, min(300, 10.3 * 3600 / max(1, len(mine)) - 8))
print("puzzles", len(mine), "threads", th, "sec", round(sec), flush=True)
t0 = time.time()
r = subprocess.run([sys.executable, f"{W}/src/cpsat_recomb.py", f"{src}/var_all.json", f"{W}/ids.txt", f"{W}/out_cpsat_lns.txt",
                    str(int(sec)), str(th), "1.3"], env=env, cwd=W)
print("exit", r.returncode, "hours", round((time.time() - t0) / 3600, 2), flush=True)
shutil.rmtree(f"{W}/best", ignore_errors=True); shutil.rmtree(f"{W}/ortools_lib", ignore_errors=True)
