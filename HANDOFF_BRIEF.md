# HANDOFF BRIEF & CONTINUITY RECORD: Kaggle "Santa 2026 - The Elf Calculator"

**Date of Handoff:** 2026-11-25 ~17:30 CT  
**Repository:** `https://github.com/Howdysuper/santa-2026-elf-calculator`  
**Competition:** [Santa 2026 - The Elf Calculator](https://www.kaggle.com/competitions/santa-2026)  
**Kaggle Account:** `shauryanadagoudra`

---

## 1. Goal

- **Objective:** Minimize the total straight-line instruction count across `1,000` scored puzzles (`scored_0001`..`scored_1000` in `data/puzzles.csv`). Each puzzle gives `starting_values`, ascending `targets`, `value_limit` (`<= 1e18`), and `48` registers (`0..47`). Each instruction `[op, i, j, d]` (`op` in `+ - * /`) reads registers `i, j` before writing `d`, producing positive integers `<= value_limit` (strictly `a > b` for `-`, exact `a % b == 0` for `/`). Limits: `<= 4,096` instructions and `<= 128 KiB` per CSV cell.
- **Scoring & Deadlines:** Score = sum of instruction counts over all `1,000` valid programs (lower is better). No public/private split—leaderboard score is final. Any invalid instruction rejects the entire submission. Started `2026-11-17`; team merge deadline `2027-01-21`; final deadline `2027-01-28 23:59 UTC`; `100` submissions/day allowed.
- **Target Rank:** Top 50, ideally Top 25 (with top-75 medal floor per `NOTES.md`).
- **Dual Strategy:**
  1. **Floor maintenance:** Automatically merge all updated public Kaggle notebooks/datasets and run Kaggle 5-CPU polish/recombination kernels so our score never trails the public frontier.
  2. **Breakthrough R&D:** Build a genuinely different **from-scratch construction engine** capable of beating the public frontier (closing the gap where local search and recombination have saturated).

---

## 2. Current State (as of `2026-11-25 17:07 CT`)

### Store, Submissions, and Leaderboard
- **Verified Local Store (`best/scored_0001.json` .. `best/scored_1000.json`):** `1,000` replay-validated programs summing to **`128,091`**.
- **Latest Submission:** `128091` (`submissions/98_remerge_own_128091.csv`, recorded in `work/last_submitted.txt`), submitted `2026-11-25` after `17:02 CT` hourly merge.
- **Leaderboard Snapshot (`2026-11-25 17:07 CT`):**
  - `#1` Amin Eb: `124,679` (`-3,412` vs us)
  - `#25` Moegi: `127,176` (`-915` vs us)
  - `#50` Takumi Saito: `127,618` (`-473` vs us)
  - `#200` Pirhosseinlou: `128,087` (`-4` vs us)
  - **Us (`shauryanadagoudra`):** `128,091` (>200th, `4` behind `#200`, `1` ahead of best seen public notebook `viktorbarbarich/santa-2026-value-graph-lns-in-c-128-092`).
- **Source Attribution (`best_log.csv`):** Score progressed `141,363` (`11-18`) -> `138,413` (`11-19`) -> `135,758` (`11-20`) -> `132,900` (`11-21`) -> `128,503` (`11-23`) -> `128,091` (`11-25`). Out of `3,000` store updates audited on `2026-11-24`, only `8` instructions came from our own search (`work`: 5, `elf-calc-search-5_1120_0625`: 2, `elf-calc-fresh-3_1123_0238`: 1); the rest came from merging `238` tracked public Kaggle notebooks/datasets (`work/remerge_state.json` caches `670` historical source keys).

### Active Kaggle Kernels & Automation (In Progress)
- **Kaggle Batch CPU (5/5 slots occupied as of `2026-11-25 17:07 CT`):**
  - `shauryanadagoudra/elf-calc-cpsat-0` (v7, pushed `11-25 13:27 CT`, `RUNNING`) — `kaggle/cpsat_run.py` (`STRUCT=1` CP-SAT recombination over half of `cpsat_ids.txt`: `shared`, `multiplicative`, `mixed`, costliest/target first; dataset `shauryanadagoudra/elf-calc-cpsat-inputs`).
  - `shauryanadagoudra/elf-calc-cpsat-1` (v7, pushed `11-25 13:27 CT`, `RUNNING`) — second half of `cpsat_ids.txt`.
  - `shauryanadagoudra/elf-calc-fresh-0` (v12, pushed `11-25 13:33 CT`, `RUNNING`) — `cpp/lns.cpp` (`-O3 -march=native -std=c++17`) on `70` changed/rotating puzzles (`BEAMW=10`; dataset `shauryanadagoudra/elf-calc-search-inputs`).
  - `shauryanadagoudra/elf-calc-fresh-1` (v11, pushed `11-25 13:33 CT`, `RUNNING`) — `cpp/lns.cpp` with `CUTPROB="25", WMAX="5"`.
  - `shauryanadagoudra/elf-calc-fresh-2` (v11, pushed `11-25 13:33 CT`, `RUNNING`) — `cpp/lns.cpp` default (`BEAMW=10`).
  - `elf-calc-fresh-3` and `elf-calc-fresh-4` are idle and blocked from pushing (`Maximum batch CPU session count of 5 reached`).
  - Note: `kaggle/fresh_state/cpsat_nopush.txt` is **not present** (deleted `11-23`), so `work/kcpsat.ps1` actively re-pushes `cpsat-0/1` when slots open.
- **Aside Scheduled Routine:** `eEdqDZS545ieEWcv` ("Santa 2026 merge + Kaggle polish round", `FREQ=HOURLY;INTERVAL=1`) on the Windows host runs `work/oneround.sh` -> `work/kcpsat.ps1` -> `work/kfresh.ps1` -> second `oneround.sh` (if CP-SAT pulled outputs) -> leaderboard check.
- **Local background jobs:** None running on the Windows host (`autoloop.sh` is stopped; Aside exec sessions expire after ~1h). Note: `bash` inside Aside Browser currently fails with `The Windows sandbox component is missing`, which is why this handoff is being moved to Duet.

### Done: Generator Reverse-Engineering (`research/generator/FINDINGS.md`, `scored_family.csv`)
- **`independent` (`248` scored, `max start >= 100`):** Targets are i.i.d. uniform in one decade `[10^(D-1), 10^D)` (`D in {6,9,12,15,18}`). No hidden structure; `~6.92` instr/target (`~47.4k` instr). Exclusive target cones in frontier are almost all `1..7` steps (sum of `cone - 7` over cones `>= 8` across all `1,000` puzzles is only `215`: `96` independent + `119` mixed). Counting/MITM bounds put these near the practical floor.
- **`shared` (`251` scored, `~4.13` instr/target):** `T = k * M + c` where `M` is a degree 1–3 product of `~4–6` hidden `17–21`-bit (sometimes `13–14`-bit) atoms, `k` is smooth (`<= ~2^15`), `|c| <= ~2500`, with clusters sharing `k*M`, nested `m2*(m1*M+c1)+c2`, and affine target links `Tj = p*Ti + r`.
- **`multiplicative` (`287` scored, `~3.42` instr/target):** Products of `2–5` small `8–12`-bit atoms + small offset (invisible to high-bit statistical hub scans).
- **`mixed` (`198` scored, `~6.11` instr/target):** ~Half independent targets in one decade + ~half structured affine chains/clusters.
- **`tiny` (`16` scored):** `57` total instructions.
- **`value_limit`:** `min(~1e18, max_target * U(1, 4))`; carries no hidden structure.

### Done: Solver & Constructor Benchmarks (`NOTES.md`)
- **Local Search / Beam / Re-planning / Helper Search (all saturated at ~0 net over current frontier):**
  - `cpp/lns.cpp` (`work/lns3n.exe`): window LNS (1–4 targets, `<=5` MITM + backward beam) — `0` gains across recent fresh/changed rows (`r5`–`r7` `freshonce`, Kaggle `fresh`).
  - `cpp/beam.cpp`, `cpp/plan.cpp`, `src/hcub.cpp`, `research/konbu_solver.cpp`: from scratch `+10%` to `+35%` worse than frontier; suffix/re-plan passes exhausted.
  - `cpp/pal.cpp` (`work/paln.exe`): `SA`, `LNS`, `KEEP`, `ITEMS`, `INJECT`, `FACTOR` (Pollard-Brent cofactor split of `v - r`) — `0` gains over frontier; `~63 ms/eval` too slow for global palette search.
  - `src/helper_rederive.py`: `0` gains on frontier.
  - `REGS=64` vs `REGS=48` (`lns64` vs `lns3` on 12 register-bound puzzles): `2066 -> 2066` (`0` gains), proving 48 registers is not the bottleneck.
- **Exact MILP & CP-SAT Recombination:**
  - `src/scaf_milp.py` (HiGHS + lazy generalized subtour cuts): on `scored_0938` (`188` nodes, `946` recipes), proved frontier (`103` then, now `99`) within `1` of optimal on its own value neighborhood (`bound 102` in `300s`). HiGHS took `156s–490s` per iteration at `811k` recipes -> abandoned for OR-Tools CP-SAT (`~100x` faster).
  - `src/cpsat_recomb.py` (OR-Tools CP-SAT over `work/var_all.json` [`20,134` variants across `1,003` CSVs as of `11-23`] + `STRUCT=1` candidates + `numpy` `build_recipes` + `LNSMODE=1`):
    - Local `40` most-diverse puzzles (`11-23`, `60s` each) and two `8h` Kaggle runs (`11-20`–`11-21`): `0` net gains after public merges caught up (`v7` currently running).
    - **Decisive Basin Diagnostic (`scored_0938`, public `99` vs own `108`):** Even with every value of the public `99` solution injected into the pool (`INCLUDE_PUB=1`), starting from own `108` yielded `0` gains in `420` LNS iterations and only `106` (`bound 94`) in `400s` full CP-SAT. **Conclusion:** CP-SAT/LNS are local polishers; moving from a suboptimal constant palette to a better global palette requires a true **global constructor**.
- **Active Constructor Prototype — `src/layered.py`:**
  - Builds strictly ordered layers (no acyclicity/ordering variables needed): `L0` (starts + best-program cones of detected atoms, fixed) -> `PAL` (`P1/P2 < 2^13`, 1–2 ops over small `L0`) -> `L2` (atom products) -> `L3` (`X op p` and `L2 +/- L2`) -> `INT`/targets (`1` op from `L3/L2/PAL`/earlier targets, or `<=3`-step chains with constants from `L0`/`P1`, or pair leaves `w = X +/- leaf`; unfit targets fall back to best-program ancestors).
  - **`scored_0938` (public `99`) progression:** `119 OPTIMAL` (`38s`, strict 1-op layers) -> `108 OPTIMAL` (+ bases of bases + target reuse) -> `106 OPTIMAL` (+ 3-step chains + pair leaves) -> **`105 OPTIMAL`** (`216s`, `37.7k` nodes, `107k` recipes, all `L0` values as chain constants). `LCOVER=1` shows only `4` of `99` public values fall outside the layer grammar.
  - **10-Puzzle `shared` Benchmark (`work/p_bench10.txt`, `150s` each, public best -> `layered.py`):**
    - Two atom modes: `ATOMMODE=mul` (operands of big `*` big in best program; catches 13–14-bit atoms like `9398, 5159, 9392` on `scored_0950`) and `ATOMMODE=freq` (mid values `2^14..2^24` used `>=2x`).
    - Best-of-both (`mul` / `freq`) vs public: `0291` `162/156`, `0341` `131/115`, `0950` `114/107`, `0605` `162/159`, `0102` `116/113`, `0226` `134/114`, `0675` `122/114`, `0345` `202/193` (`mul` hits `regfail`), `0746` `122/112`, `0332` `150/136`.
    - Mean gap: **`+9.6` instructions (`~10%` behind public)**, almost all solved to `OPTIMAL` inside the model.
  - **Pooling `layered.py` (`ALTOUT`) + public variants (`work/p_bench11.txt`, `11-24`):** `22` `layered.py` constructions (`mul` + `freq`, `60s`) pooled with public variants in `cpsat_recomb.py` (`REL=1.45`, `120s`) gave **`0` gains on all `11` puzzles** (`10%`-worse constructions do not contribute shorter shared helpers).

---

## 3. Decisions Made (Do Not Revisit)

1. **Stop spending cycles on generic LNS, helper re-derivation, or default CP-SAT recombination alone:** Public notebooks (`viktorbarbarich`, `ishankarnick`, `ozertuu`, `goodpjw2008`, `kmmmvs`, `royalacecat`) run identical rewrite/recombination pipelines with huge compute. Local `freshonce.ps1` and `cpsonce.ps1` were removed from the hourly routine after `>=3` consecutive `0`-gain hours.
2. **Use OR-Tools CP-SAT instead of HiGHS (`scaf_milp.py`):** HiGHS takes `156–490s` per lazy-cut iteration on `811k` recipes; CP-SAT is `~100x` faster.
3. **Do not naively broaden `layered.py` (`LBROAD=1`) or `cpsat_recomb.py` (`STRUCT=2`):** `LBROAD=1` expanded `L3` to `385k–738k` candidates (`339s` Python generation) and worsened `scored_0226` (`134 -> 145`). Keep candidate grammars targeted and move candidate/recipe generation to C++ before scaling node counts.
4. **Do not pursue 64-register-style relaxations or single-target depth-6 search:** `REGS=64` yielded `0` gains; exclusive target cones >7 steps total only `215` instructions across all `1,000` puzzles. Real gains require **global shared-helper/basis co-selection (~48% of budget)**.
5. **Keep `remerge.py` dataset filter:** Only download datasets whose title/ref matches `santa 2026`, `santa-2026`, `santa2026`, or `elf` AND `size <= 300_000_000` (prevents re-downloading an unrelated `15.3 GB` Brazilian health dataset).
6. **Do not launch detached background processes via Windows `Start-Process` / WMI / Task Scheduler / Aside exec:** Aside kills detached children and expires exec sessions after ~1h. Long jobs must run on Kaggle Batch CPUs (`<= 5` concurrent) or in a durable host/Duet environment.

---

## 4. Constraints & Rules

### Kaggle Competition & Secrecy Rules
- **NEVER** include the substring `"claude"` anywhere Kaggle-facing (kernels, dataset titles/descriptions, commit messages, submission messages).
- **NEVER** print, commit, or expose Kaggle credentials (`C:\Users\shaur\.kaggle\access_token` or `kaggle.json`).
- **Keep all Kaggle kernels and datasets private (`is_private: true`):** `elf-calc-cpsat-0/1`, `elf-calc-fresh-0..4`, `elf-calc-cpsat-inputs`, `elf-calc-search-inputs`.
- **GitHub Visibility Warning for Duet:** The repo `https://github.com/Howdysuper/santa-2026-elf-calculator` was created **Public** per explicit user instruction so Duet can access it immediately (and currently holds `128,091`, only `1` instruction below the public `128,092` notebook). **As soon as Duet clones it—and strictly before pushing any original improvements below the public frontier—switch the repository to Private** to comply with Kaggle's rule against publicly sharing private solutions.

### Store & Validation Integrity (`src/elf.py`)
- `best/<id>.json` is the single source of truth. Never overwrite without `elf.replay()` validation and strictly lower `best_len(pid)`.
- Always hold `work/store.lock` (`mkdir work/store.lock` / `work/lock.sh`) during writes to `best/`, `src/export.py`, or `src/submit_store.py`.
- In `work/oneround.sh`, keep `export PATH=/usr/bin:/bin:/mingw64/bin:$PATH` before `work/lock.sh` so `seq` and `grep` resolve in Git Bash.

### Duet Environment Adaptation (Critical for Seamless Switch)
- **Reconstructing `best/` in a fresh Duet clone:** `best/` (`1,000` JSONs) is `.gitignore`d; run `python src/ingest.py submissions/98_remerge_own_128091.csv` to populate `best/` with all `1,000` validated programs (`total = 128091`).
- **Hardcoded Windows paths if Duet runs in Linux/Cloud:**
  - `src/remerge.py` hardcodes `KAGGLE = str(ROOT.parents[1] / ".venv" / "Scripts" / "kaggle")` and `tools/kg.py` (`src/submit_store.py` also calls `tools/kg.py`). If Duet runs outside `C:\Users\shaur\Kaggle ML\competitions\santa-2026`, update those to use `shutil.which("kaggle")` / `kaggle competitions submit`!
  - `work/*.ps1` (`kcpsat.ps1`, `kfresh.ps1`, `kdone.ps1`, `freshonce.ps1`, `cpsonce.ps1`) are PowerShell scripts with hardcoded `C:\Users\shaur\Kaggle ML\...` paths; port to bash/Python if Duet runs on Linux.
- **Windows Host Quirks (if Duet runs locally on Windows):**
  - Unset `PYTHONHOME` and `PYTHONNOUSERSITE` and set `PYTHONIOENCODING=utf-8` before running `.venv` Python or `kaggle.exe` (prevents `_thread.start_joinable_thread` crash).
  - OR-Tools (`ortools==9.15.6755`, `protobuf==6.33.6`) lives in `ortools_lib/` isolated from `.venv`'s `protobuf 7.36.2`; run with `PYTHONPATH=.../ortools_lib`. (Linux `cp313` wheels were also cached locally in `kaggle/cpsat_inputs/wheels/`.)
  - Compile C++ with `g++ -O3 -march=native -std=c++17 -static` (WinLibs GCC); `-static` prevents random Git `libstdc++-6.dll` crashes.
- **Kaggle Resource Limits:** Maximum `5` concurrent batch CPU sessions per account; `100` submissions/day; `~10.5–12h` max CPU kernel wall time.

---

## 5. Open Questions / Gaps

1. **Closing the `~10%` (`+9.6`) gap in `src/layered.py` to beat the public frontier (`~473` steps to `#50`, `~915` to `#25`, `~3,412` to `#1`):**
   - `LCOVER` on `scored_0950` and `scored_0226` identified exact missing idioms:
     - **Independent atom/factor discovery:** `layered.py` currently steals `L0` atom cones from `best/`. We need an independent atom decoder (Pollard-Rho / smooth-divisor / pairwise-GCD + difference-lattice search over `T`) that finds both `17–21`-bit atoms (`shared`) and `8–14`-bit atoms (`0950`, `multiplicative`).
     - **Missing construction rules:** `L3 - L3` (difference of two bases), `L0 - L3`, `T - base`, `T +/- P1`, `INT * L0` chains, and non-atom `L0 * L0` products (`16712 * 1028` in `0226`) without blowing up `L3` to `700k` nodes.
     - **Register-aware scheduling:** `scored_0345` (`ATOMMODE=mul`) hit `regfail` at `est 202` because DFS post-order exceeded `48` live registers; needs Belady eviction / register-pressure-aware ordering (like `avazaku` in `research/nb1119/SUMMARY_B.md`).
2. **State of Kaggle `v7` / `v11–12` kernels (`11-25 13:27–13:33 CT`):** Still running at handoff time; expected to finish ~`23:30 CT` on `2026-11-25`.
3. **Host coordination:** Aside hourly routine `eEdqDZS545ieEWcv` may still run on the user's Windows PC if Aside Browser stays open—coordinate Kaggle batch CPU slots and `best/` writes if both Duet and the Windows routine use the same Kaggle account (`5` CPU limit).

---

## 6. Exact Next Step

### Very First Actions for Duet:
1. **Bootstrap the workspace & verify `128,091` store:**
   ```bash
   git clone https://github.com/Howdysuper/santa-2026-elf-calculator
   cd santa-2026-elf-calculator
   python src/ingest.py submissions/98_remerge_own_128091.csv
   ```
   Confirm `store total 128091`, verify `kaggle` CLI authentication (do **not** commit credentials), and check whether `elf-calc-cpsat-0/1` (v7) and `elf-calc-fresh-0/1/2` (v11–12) have completed so their outputs (`out_*.txt`) can be imported via `src/import_out.py` + `src/submit_store.py`.
2. **Fix path portability (if running in a Linux/cloud Duet container) & run a merge check:**
   Update `KAGGLE` and `tools/kg.py` paths in `src/remerge.py` and `src/submit_store.py` if needed, pull any newly published public kernels/datasets, and submit if `< 128091`.
3. **Execute the core engine breakthrough (`src/layered.py` -> C++):**
   - Run `LCOVER=1` across all 10 puzzles in `work/p_bench10.txt` plus 5 `multiplicative` puzzles from `research/generator/scored_family.csv` to rank the most frequent `OUT` patterns.
   - Add targeted `L3 - L3`, `T - base`, `INT * L0`, and Belady register allocation (`allocate_graph` style) to `src/layered.py`, plus an independent atom/cofactor finder so `layered.py` does not depend on `best/`'s scaffold.
   - Iterate on `work/p_bench10.txt` until `layered.py` **matches or beats** the public best on `>= 2` of the `10` puzzles (currently `0/10`, mean `+9.6`).
   - Once validated, port candidate/recipe generation to C++ (`-O3 -march=native`) and deploy across the `5` private Kaggle CPU kernel slots (`elf-calc-cpsat-0/1`, `elf-calc-fresh-0..2`) with `10–20 min/puzzle` budgets, auto-remerging and submitting gains.
