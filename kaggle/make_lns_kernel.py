"""Build kernel folders kaggle/lns_K for K in range(N): each improves its share of puzzles with lns for ~11 h.
usage: python make_lns_kernel.py N SECS_PER_PUZZLE SEED"""
import json, sys
from pathlib import Path
N, SECS, SEED = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
here = Path(__file__).parent
for k in range(N):
    d = here / f"lns_{k}"; d.mkdir(exist_ok=True)
    (d / "run.py").write_text(f'''# Elf calculator: long local search over existing programs (part {k} of {N}).
import glob, os, subprocess, time
src = glob.glob("/kaggle/input/**/lns.cpp", recursive=True)[0]
base = os.path.dirname(src)
W = "/kaggle/working"
subprocess.run(["g++", "-O2", "-std=c++17", "-pthread", "-o", W + "/lns", src], check=True)
lines = open(base + "/puzzles.txt").read().splitlines()
mine = [l for i, l in enumerate(lines) if i % {N} == {k}]
open(W + "/p.txt", "w").write(chr(10).join(mine) + chr(10))
th = os.cpu_count() or 4
print("puzzles", len(mine), "threads", th, flush=True)
t0 = time.time()
r = subprocess.run([W + "/lns", W + "/p.txt", base + "/programs.txt", W + "/out_{k}.txt", "{SECS}", str(th), "{SEED + k}"],
                   env=dict(os.environ, BEAMW="10"))
print("exit", r.returncode, "hours", round((time.time() - t0) / 3600, 2), flush=True)
''')
    meta = {"id": f"shauryanadagoudra/elf-calc-search-{k}", "title": f"elf calc search {k}", "code_file": "run.py",
            "language": "python", "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
            "enable_internet": False, "dataset_sources": ["shauryanadagoudra/elf-calc-search-inputs"],
            "competition_sources": [], "kernel_sources": [], "model_sources": []}
    (d / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
print("built", N)
