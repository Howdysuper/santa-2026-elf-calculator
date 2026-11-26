"""Build kernel folders kaggle/replan_K for K in range(N): each runs the beam planner (cpp/beam.cpp with ORIG=1, so runs stay near
the given program and detour) as an improver on its share of puzzles; strict improvements go to /kaggle/working/out_K.txt.
usage: python make_replan_kernel.py N SECS_PER_PUZZLE SEED "ENV=VAL ENV=VAL ..." [--alt]
  --alt also saves every run's program to alt_K.txt (variants for src/recomb.py)"""
import json, sys
from pathlib import Path
N, SECS, SEED, ENVS = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
ALT = "--alt" in sys.argv
env = dict(kv.split("=", 1) for kv in ENVS.split())
here = Path(__file__).parent
for k in range(N):
    d = here / f"replan_{k}"; d.mkdir(exist_ok=True)
    extra = dict(env)
    if ALT: extra["ALTOUT"] = f"/kaggle/working/alt_{k}.txt"
    (d / "run.py").write_text(f'''# Elf calculator: beam re-planning around the best known programs (part {k} of {N}).
import glob, os, subprocess, time
src = glob.glob("/kaggle/input/**/beam.cpp", recursive=True)[0]
base = os.path.dirname(src)
W = "/kaggle/working"
subprocess.run(["g++", "-O2", "-std=c++17", "-pthread", "-o", W + "/beam", src], check=True)
lines = open(base + "/puzzles.txt").read().splitlines()
mine = [l for i, l in enumerate(lines) if i % {N} == {k}]
open(W + "/p.txt", "w").write(chr(10).join(mine) + chr(10))
th = os.cpu_count() or 4
print("puzzles", len(mine), "threads", th, flush=True)
t0 = time.time()
r = subprocess.run([W + "/beam", W + "/p.txt", base + "/programs.txt", W + "/out_{k}.txt", "{SECS}", str(th), "{SEED + k}"],
                   env=dict(os.environ, **{json.dumps(extra)}))
print("exit", r.returncode, "hours", round((time.time() - t0) / 3600, 2), flush=True)
''')
    meta = {"id": f"shauryanadagoudra/elf-calc-replan-{k}", "title": f"elf calc replan {k}", "code_file": "run.py",
            "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": ["shauryanadagoudra/elf-calc-search-inputs"],
            "competition_sources": [], "kernel_sources": [], "model_sources": []}
    (d / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
print("built", N, "env", extra)
