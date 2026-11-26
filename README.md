# Santa 2026 - The Elf Calculator

Repository for code, solver experiments, puzzle-generator reverse-engineering, and Kaggle automation for **Santa 2026 - The Elf Calculator** (`1,000` scored puzzles, minimize total straight-line instructions across 48 registers with `+ - * /`).

- **Public GitHub Repo:** `https://github.com/Howdysuper/santa-2026-elf-calculator`
- **Handoff Brief (Markdown):** [`HANDOFF_BRIEF.md`](./HANDOFF_BRIEF.md)
- **Handoff Brief (PDF):** [`HANDOFF_BRIEF.pdf`](./HANDOFF_BRIEF.pdf)
- **Chronological Experiment Log:** [`NOTES.md`](./NOTES.md)
- **Current Store Baseline:** **`128,091`** (`submissions/98_remerge_own_128091.csv`, as of `2026-11-25 17:07 CT`)

## Quickstart (Duet / New Environment)

1. **Reconstruct `best/` (`1,000` replay-validated JSON programs summing to `128,091`):**
   ```bash
   python src/ingest.py submissions/98_remerge_own_128091.csv
   ```
2. **Install Python dependencies:**
   - Core scripts (`elf.py`, `remerge.py`, `ingest.py`, `export.py`, `import_out.py`, `submit_store.py`): standard library + `kaggle` CLI (`tools/kg.py` or `kaggle` on PATH).
   - CP-SAT solver/constructor (`src/cpsat_recomb.py`, `src/layered.py`): `ortools==9.15.6755`, `protobuf==6.33.6`, `absl-py==2.5.1`, `immutabledict==4.3.1`, `numpy`.
   - Note for Linux/cloud Duet containers: `src/remerge.py`, `src/submit_store.py`, and `work/*.ps1` assume the original Windows directory tree (`C:\Users\shaur\Kaggle ML\.venv\Scripts\kaggle`, `tools/kg.py`). Adapt those executable paths before running automated submits/merges in a standalone container.
3. **Compile C++ solvers:**
   - Linux / Kaggle: `g++ -O3 -march=native -std=c++17 -pthread -o work/lns cpp/lns.cpp`
   - Windows (WinLibs GCC): `g++ -O3 -march=native -std=c++17 -static -o work/lns3n.exe cpp/lns.cpp`
4. **Never commit secrets or violate Kaggle privacy rules:**
   - Never commit or print Kaggle API tokens (`~/.kaggle/access_token` / `kaggle.json`).
   - Keep all Kaggle kernels and datasets private (`is_private: true`), and never include the string `"claude"` in anything Kaggle-facing.
   - Switch this GitHub repository to **Private** before pushing any private improvements that materially beat the public Kaggle frontier.
