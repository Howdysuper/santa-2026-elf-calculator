# santa-2026: The Elf Calculator

Optimization competition (Featured, medals). Started 2026-11-17. Entry/merge deadline 2027-01-21, final 2027-01-28 23:59 UTC.
Goal from the user: top 75 (medal), top 10 if possible.

## Task
- 1,000 scored puzzles (`puzzles.csv`): `starting_values`, `targets` (increasing), `value_limit` (<= 1e18), 48 registers.
- Write a straight-line program per puzzle: `[op, i, j, d]`, op in + - * /, sources must be defined, results positive integers <= value_limit,
  subtraction only if a > b, division exact. Both sources read before the write. Every target must appear in some register at least once.
- Score = total instruction count over all 1,000 programs. Lower is better. No public/private split (the LB is final).
- Any invalid program rejects the whole submission, so validate locally before every submit.
- Limits: 4,096 instructions per program, 128 KiB per program cell.
- `practice_puzzles.csv`: 200 unscored puzzles with `family` (independent, shared, multiplicative, mixed, tiny), `design_tier`, `lower_bound`.

## Submission
CSV `id,program`, program = JSON array of 4-element arrays, written with a CSV writer. All ids scored_0001..scored_1000.

## Landscape (2026-11-18, day 2)
- LB top ~134.1k. Public notebooks: getting started 233k; "Wider Dictionary + Portfolio" 142.9k; public merges ~141.4k.
- Techniques seen in titles: dictionary / beam search over 2-step dictionary, portfolio (best per puzzle across methods), register reuse,
  shared intermediates across targets, w-NAF / addition chains, MILP, peephole passes, graph rewrites.

## Experiment log
| # | date | change | score | notes |
|---|------|--------|-------|-------|
| 1 | 11-18 | merge of 34 public notebook outputs, best valid program per puzzle (src/ingest.py, best/ store) | 141,363 | would rank ~89/549 on day 2 (top-75 line 141,353, top-10 136,124, #1 131,697) |
| 2 | 11-18 | cone re-solve: drop a target's private instructions, exact MITM search (<=5 steps) from the live registers | 0 gain | public solvers already do this; shared intermediates (~55% of instructions) and pool choice are where slack is |
| 3 | 11-18 | submitted 01_public_merge.csv | **141,362 LB** | rank 129/599; top-75 line 141,324, top-10 135,996, #1 131,697. User allows free submits on this comp. |
| 4 | 11-18 | re-merge: 7 public datasets + re-pulled 40 notebook outputs (pub2/); asteriospanoras best_programs gave -23 | **141,339 LB** | 02_remerge_141339.csv |
| 5 | 11-18 | src/remerge.py (changed public sources only) | **141,309 LB** | 03_remerge_141309.csv |
| 6 | 11-18 | recombination of near-best variants from different authors (src/recomb.py, exact MILP + pressure-aware scheduler): scored_0269 276->274, scored_0446 246->244; + beam-planner variants: scored_0008 119->118 | **141,305 LB** | rank 106/654; #100 141,297, #75 141,064 |
| 7 | 11-19 | daily re-merge: ozertuu portfolio -178, bikram graph rewrites -45, hanif -1, recomb -1 | **141,079 LB** | 05_remerge_141079.csv; ~rank 105/781 |
| 8 | 11-19 | recomb with 5,150 beam-planner variants (320 puzzles, killed the rest of the 6 h run): 3 gains of 1 | **141,076 LB** | 06_recomb_beamvar.csv; ~1% of puzzles gain |
| 9 | 11-19 | beam.cpp ORIG=1 KMIN=0 (re-plan from the program's opening, original derivations offered at every target): scored_0583 35->34, 0137 56->55, 0473 28->26, 0478 84->83 (partial full pass, 30 s/puzzle) | **141,071 LB** | 07_replan_opening.csv; gains are on small/mid puzzles, near the start |
| 10 | 11-19 | Kaggle LNS kernels elf-calc-search-0..3 (lns.cpp, 250 puzzles each, ~550 s/puzzle, 4 CPUs): 17+16+5+18 = 56 gains | **141,015 LB** | 08_kaggle_lns_141015.csv. Long runs work where 30-90 s tests on 8 puzzles found 0: keep Kaggle busy with long LNS |
| 11 | 11-19 | re-planner (KMIN=0 KMAX=0.4, 120 s base) on the 431 puzzles with <= 130 instructions: 8 found, 7 new after the LNS gains | **141,008 LB** | 09_replan_small_141008.csv |
| 12 | 11-19 | mid-size re-plan pass (372 puzzles, 131-200 instr, 2 h local): 1 gain; Kaggle variants-0 out: 2 gains | 141,005 store | beam re-planning is exhausted on mid puzzles |
| 13 | 11-19 | re-merge after the public jump: kindasomethin 138,441 portfolio -2,590 (438 puzzles, 72 of them -10 to -46; base = Bikram V13 Arithmetic Graph Rewrites 138,485), ozertuu -1 | **138,413 LB** | 10_remerge_138413.csv, ~rank 99/1106. Kaggle dataset updated; local LNS on the 438 changed puzzles + recomb running |
| 14 | 11-19 | recomb (REL=0.3, 32,462 variants incl. the new public lineage) over all 1,000 puzzles on the 138,413 store | 0 gain | 1,434 s; local LNS on the 438 changed puzzles: 0 gains in the first hour; second local LNS started on the 562 unchanged |
| 15 | 11-19 12:30 | first round of work/autoloop.sh: public re-merge -70 (atakanaldemir joint recipes -53, ozertuu -10, asteriospanoras -7) + own LNS on changed puzzles -2 | **138,341 LB** | 11_remerge_own_138341.csv, rank 114/1189 (bronze line ~119). Unchanged-puzzle LNS stopped after 1 h with 0 gains; its 6 threads now run a reversed-order pass over the changed puzzles |
| 16 | 11-19 14:29-16:32 | autoloop rounds: public re-merges -143 and -72 plus own LNS -2 (two loop copies ran, see findings) | **138,040 LB** | 13-15_remerge_own_*.csv. Forward LNS pass over the 438 changed puzzles done: 54,125 -> 54,112 (-13 in 5.5 h, 6 threads) |
| 17 | 11-19 17:05 | manual round: royalacecat residual cut search -34, icefire -2, own LNS -2 | **138,002 LB** | 16_remerge_own_138002.csv; rank ~150/1,381, bronze line 138,023, #75 137,011, #100 137,810 |
| 18 | 11-19 18:32-20:39 | autoloop rounds 3-4: public -225 (ozertuu starter -84, others), Kaggle replan/search0 outputs -4 | **137,691 LB** | 17-18_remerge_own_*.csv; rank 165/1,500, bronze line 137,609, silver 136,453, #1 128,831. LNS on the 211 newest public rows (default settings, 400 s): 0 gains in 4 h |

## Findings
- Current best spends 5.26 instructions per target, ~7.0 bits of target per instruction. Rough capacity with 48 registers is ~9 bits/instr.
- Only 6 of 141,363 instructions recompute a value: registers barely bind in current solutions.
- Value coverage by number of new steps from a 48-value pool: 1 step ~2^12, 2 ~2^20, 3 ~2^26, 4 ~2^34, 5 ~2^41, 6 ~2^47.
  A fresh 45-50 bit target needs ~6 steps, so gains come from building intermediates that several targets share.
- Build every tool with `g++ -O2 -static ...`: without -static the exe loads Git's /mingw64/bin/libstdc++-6.dll in any shell
  that lacks the WinLibs PATH and crashes at random (cost an hour of 'heisenbug' hunting).
- GCC (WinLibs) is installed: `PATH=$(ls -d /c/Users/shaur/AppData/Local/Microsoft/WinGet/Packages/BrechtSanders.WinLibs*/mingw64/bin):$PATH`.
- Leaderboard 11-18 night: #1 sekai013 131,697; Tony Li (author of the public beam solver) #3 133,732; ~70 teams beat the public merge.
  They build their own programs; local search around public programs is not how they win.
- Public best = mostly konbu17's dataset (methods: graph recombination 438 puzzles, wide planning + re-allocation 247, suffix re-solve 237;
  ~1100 CPU-hours). asteriospanoras' public experiment log (pub2/ds/...experiments.csv) found the same dead ends as us.
- Two puzzle regimes. Structured puzzles (shared/mixed/multiplicative families): targets = hidden ~20-bit values multiplied together
  (squares, products) +/- small offsets, e.g. scored_0011: T0+2421 = X^2, T4-28 = X*Y, T5+1343 = Y^2. Independent puzzles: 60-bit
  targets with no shared factor, 8.5-8.9 instructions per target (73 puzzles >= 7.5/target hold 18.2k instructions; 216 puzzles
  >= 6.5/target hold 48.3k). Counting bound for a 60-bit target from 48 live values is ~6 steps, so the independent ones have the most slack.
- First 3 targets of each puzzle take 21% of all instructions (bootstrapping from tiny starts).

## 11-19 findings
- **Automation (from 11-19 12:20 UTC, 24 h):** `bash work/autoloop.sh ROUNDS INTERVAL` runs every 2 h: `src/remerge.py --no-submit --no-recomb
  --store-only` (public outputs that changed, CSV only, replay-validated), `src/import_out.py work/out_*lns.txt work/kaggle_out/*/out_*.txt`,
  then `src/submit_store.py remerge_own` (submits only if below work/last_submitted.txt). It is the only writer of best/, so nothing races.
  Santa allows 100 submissions a day. LB 12:40: 1,189 teams, #1 130,700, #10 133,862, #75 137,937, #100 138,267, #112 138,338.
- TaskStop left the old `bash work/autosubmit.sh` and `bash work/autoloop.sh` running (Git Bash grandchildren), so two loops submitted
  until 17:00; killed by PID. Since then work/lock.sh guards store writes (autoloop + kaggle/watch_big.sh).
- TPU many-core search: kaggle/lns_big (elf-calc-search-big, `--accelerator TpuV5E8`, 96 CPUs / 330 GB per Kaggle docs, 9 h limit) pushed
  12:59 UTC, still QUEUED at 17:05 (batch TPU queue; 1 batch TPU session per user). kaggle/watch_big.sh N chains N more sessions.
- Kaggle CLI returned "Authentication required" for ~1 h around 13:00 UTC, then worked again without a new sign-in.
- Local LNS on the 211 puzzles changed between the 138,413 and 138,040 exports: work/p_changed4.txt, 400 s, 6 threads (~4 h): 0 gains.
  Cut settings (CUTPROB=25 WMAX=5) on the same rows: 1 gain in 2 h. Default and cut passes find mostly the same puzzles.
- Kaggle CPU kernels from 18:00: elf-calc-search-1..4 (quarters, 550 s, default) and -5 (531 rows changed on 11-19, cut settings,
  ~290 s); kaggle/watch_pull.sh pulls each to work/kaggle_out/<slug>_<time>/ when done.

## Engine research (11-19 evening)
- Cost law of the frontier: ~7 bits of target per instruction across sizes (23-bit targets at 3.0/target, 50-bit at 7.0, 59-bit at
  8.6). Independent 60-bit rows build each new target as an earlier big value +/- a difference that costs 5-13 instructions.
  Rough counting (MITM over 1-2-step dictionaries from a 48-value pool) puts these near the practical bound: little slack there.
- Structured rows (3-6 per target, ~90k instructions) hide ~6 atoms of 19-21 bits; targets = atom products * small +/- small offset.
  The frontier already spends ~44 instructions on atoms/constants and then ~2.4 per target (scored_0280: 119 for 31 targets).
  The remaining slack is global: which helpers (shared products, offsets) to build so that more targets cost 1-2.
- Bikram's later notebook versions (v2-v13) contain only packaged programs; the rebuild code is not public. arsen123's source
  bundle is post-processing (value deletion, joint cuts, MILP) with single-digit gains per run, like ours.
- Forum pointer (topic 760300): Hcub (Voronenko & Pueschel 2007, multiple constant multiplication) picks each new intermediate by
  its benefit to all remaining targets (A-distance estimates), not target by target. Candidate design for our own planner on the
  structured rows: candidates = one-step values of the pool; score = sum over targets of distance reduction (exact 0/1/2 by
  dictionary lookups, estimate beyond); randomized/beam; finish with recomb + LNS.
- **hcub v0 built** (src/hcub.cpp -> work/hcub.exe, driver src/hcub_run.py [--dry] IDS; env PREFIX=first|k, HSEC, NOISE, FAR).
  Keeps the frontier's scaffold (everything before its first target), then re-plans all targets: emits any target one step away,
  else builds the one-step value with the largest total cost reduction over remaining targets. Cost shapes: t = y op p (2),
  t = x*y +/- o with y = round(t/x) and x, y, o built or one step away (2-5), chains through one or two new values (3); far targets
  get a sub-target (|t - v| or t / p). Pruned, scheduled with recomb.order_and_allocate, replayed.
  Result 11-19: scored_0280 124 vs frontier 119; 6 random structured rows +4% to +10% (117->125, 98->107, 33->37, 117->122,
  98->108, one run over the cap). ~5 s per run (std hash maps), so restarts barely explore. Scores are mostly 1.0: the
  planner works target by target and rarely finds shared helpers.
  Next: open-addressing hash + incremental D1 (10x faster), beam/rollout over the pick instead of greedy, credit helpers that
  serve several targets' x*y+o shapes, scaffold choices other than the frontier prefix (e.g. its atoms only).
- hcub as a large-window re-planner (PREFIX=0.6 / 0.8 of the frontier program, 6 structured rows): never shorter, ties at best
  (0.8: 117=117, 98=98, 119=119; others +1..+4). The frontier's tails are locally optimal against this move set.
- hcub v1 (open-addressing maps, beam W, K expansions, x*y+o scan over built x only): scored_0280 greedy 129-136 (order-sensitive),
  W=16 133 in 28 s, vs frontier 119. Still ~2 s per greedy run. The cost model is ~10% behind the public engines; beam does not
  close it. Gap to top 50 (11-19 23:00): 135,670 vs our 137,691 = -2,021 (1.5%), out of reach for polish and for this planner.
- LB 11-19 04:50 UTC: 781 teams, #1 131,049, #10 134,357, #50 139,407, #75 140,667, #100 141,036; 223 teams below our 141,305.
  Best public portfolio is now 141,132 (ozertuu), so the frontier moves ~100-200 a day: run src/remerge.py at least daily.
- Instruction mix of the best programs: 26.9k produce targets, 37.9k small values (<= 16 bits), 47.8k mid (17-32 bits), 28.7k big.
  56k instructions are exclusive to one target (max 9); 85k are shared by two or more target cones.
- Small-constant Steiner idea (rebuild the <= 2^16 part of a program more cheaply): the trivial bound leaves 978 slack at 12 bits,
  3.7k at 16 bits, but an exact search found no shorter small-part for any tested puzzle (fully small puzzles are already optimal).
- Recomb with "bridges" (new one-step values x = a op b with c = x op y, a, b, c, y known; BRIDGE=1, BMIN filter): 1k-50k new
  values per puzzle, the MILP relaxation is weak (LP bound 36 vs 51 on scored_0005) and HiGHS cannot even recover the best in 120 s.
  highspy warm start (HIGHS=1) is buggy: it reports an objective 5 below the warm start but returns the warm start itself. Off by default.
- Public engine (konbu/Tony, research/konbu_solver.cpp) from scratch is ~35% worse than the frontier (scored_0129: 358 vs 268 at
  width 30). The frontier is the product of heavy crowd post-processing; local moves (our LNS, beam re-plans, bridges) find ~0.
- Independent puzzles: no pairwise relations between targets (checked q*Ti + r, gcd). Pure search problem; expression trees over a
  48-value pool carry ~7.6 bits per instruction, so a 60-bit target needs ~7.2 instructions at best vs ~8.4 in the frontier.
- beam.cpp ORIG=1 (11-19): the planner also offers the given program's own derivation of each target (its cone, stopping at values
  the state can still use), so runs stay near-best (+0..+4) and can detour. KMIN=0 lets it re-plan from the very first target.
  50 puzzles x 40 s: 1 gain (scored_0583 35->34, keep 0). ORIGP (withhold the original with probability p) to force detours.
  As an improver with KMIN=0.15: 0 gains on 50 puzzles (145k runs).
  ORIGP 0.05-0.3 with W 4-12: 0 gains on 49 puzzles. ROLL=1 (score each child by the exact final length when the rest follows
  the original derivations, a pilot/rollout beam): 0 gains on 50 puzzles (54k runs). Only KMIN=0 (re-plan from the first target)
  found anything. Bug fixed 11-19: MinGW rename() does not overwrite, so out files stopped updating after the first dump
  (beam/lns/plan now remove() first; Kaggle/Linux was fine).
- Kaggle replan kernels (kaggle/make_replan_kernel.py -> elf-calc-replan-K, 4 x 250 puzzles, 550 s, KMIN=0 KMAX=0.5 W=4 ORIG=1)
  are pushed automatically as the old LNS kernels finish.
- Practice puzzles' lower_bound = number of targets (useless). Families: independent targets all ~same bit size; shared/mixed have hidden
  ~20-bit atoms (targets = m * monomial(atoms) + o, nested affine chains); the public programs already build the atoms.

- LB 11-19 10:33 UTC: 1,106 teams (bronze top 10% = 110, silver top 5% = 55); #1 130,806, #10 133,882, #50 137,528, #75 138,188,
  #100 138,423, #200 138,549. A public portfolio at ~138.4k appeared ~06:40 (kindasomethin "Exact Portfolio Frontier [138441]",
  muchat007, ozertuu 138,867): the public frontier jumped ~2.6k in one morning, so we fell to ~370th. Re-merge every few hours.
- Public notebooks read 11-19: IceFire Strong Start (merge + CP-SAT recombination + register re-allocation: same idea as recomb.py),
  rishabhbafna DAG synthesis (merge, 141,302), Mamarin "first target costs 3x" (the first target carries ~16 helpers, 3/4 small constants).
- Where Kaggle LNS gains land: 11 of 17 (search_0) on puzzles <= 56 instructions; small puzzles (<= 18 targets, 150 puzzles, 5k instr)
  are less polished than the large ones.

- The new public programs are different constructions, not polish: scored_0789 166 -> 122 keeps only 24 of ~140 non-target
  values, builds a 45-instruction scaffold before its first target (old: 25) and then ~2.4 instructions per target.
  Bikram V13 describes randomized whole-puzzle rebuilds, "build the downstream value first and recover its predecessor with
  an inverse op", and joint recipe selection (MILP) over alternate programs.
- beam.cpp from scratch (KMIN=0 KMAX=0 ORIG=0) on the 138.4k frontier: >= 18% worse (only 2 of 5 puzzles even got within +30%).
  Our constructive planners are far from the public engines; our edge is local search + recombination on top of the frontier.

- LB 11-19 ~11:00 UTC: 1,126 teams; we are #101 at 138,413. #75 138,167, #100 138,411, #110 138,434, #150 138,451: ranks 100-150
  are within 40 instructions, so every own gain moves several places.

- Helper re-derivation (src/helper_rederive.py: replace a non-target value's private cone by a 0-3 instruction derivation from
  the registers live at its first use, re-allocate, replay): 0 gains on the 138.4k frontier (a quick scan claiming 553 was an
  off-by-one in counting 3-instruction derivations). The frontier is locally optimal for helper moves too.

- recomb.py FULL=1 NORANK=1 (- and / links, recipes in any order, lazy cycle cuts): breaks down. On 6 puzzles the cut loop
  degenerates (selects ~all 200-300 values or times out); default settings solve the same puzzles in < 1 s at the current length.
  Inverse-order rewrites need a proper acyclicity model (order variables), not cycle cuts. Off by default.

## Solver work (2026-11-18)
- `cpp/lns.cpp`: local search on stored programs. Move = drop 1-4 targets (adjacent or scattered) and every instruction only they need,
  re-solve them from the registers at a (random, possibly later) insertion point with an exact <=5-step MITM search, falling back to
  the public backward beam search (target = child*factor +/- atom over a 0/1/2-step dictionary, Tony Li / konbu17, Apache 2.0)
  for deeper derivations; re-allocate registers (overwrite the oldest dead register), re-validate; accept shorter, or equal 1 in 4.
- Stats on single-target moves: the shortest re-derivation always equals the current cost; public programs are locally optimal for
  single-target re-solves. 30 s x 8 puzzles: no gains. Running long on Kaggle CPUs (4 private kernels elf-calc-search-0..3,
  250 puzzles each, ~550 s per puzzle, inputs in private dataset elf-calc-search-inputs).
- `cpp/build.cpp`: greedy "cheapest next target" constructor: far worse (380 vs 230 on scored_0001). Shelved.
- More dead ends on 8 test puzzles (20-40 s each, 0 gain every time): pool = all earlier values (MAXPOOL), helper cut (a value plus
  every node depending on it, CUTPROB), windows up to 12 targets (WMAX), annealing (SLACK/TEMP/DRIFT). The public programs are a deep
  local optimum for re-solve moves.
- `src/recomb.py`: union of ~18 valid variants per puzzle (work/variants.json) + all +/* links, exact MILP (scipy HiGHS) for the fewest
  values covering the targets, acyclic by ranking values in best-program order. Optimal = current best on small puzzles, too slow on
  large ones (>120 s). konbu17 already recombined these variants. Shelved.
- `cpp/plan.cpp`: from-scratch planner (ascending targets, exact <=5 MITM over the last POOLCAP values, beam fallback). From scratch:
  10-30% worse and fails on some deep first targets (no palette). Suffix test (KEEP=k keeps the best program up to its k-th target,
  re-plans the rest): KEEP=15 gives 246/230, 258/247, 224/213, 218/213, 51/51, 145/143, 171/167, 119/119 -> within 0-7%.
  Pool size matters a lot: POOLCAP=64 gives 290/230, 312/247, 271/213 (vs 300 above). But a 300-value pool makes the two-step table
  ~5e8 entries (~250 s per puzzle), so the beam planner needs a faster full-pool search first (e.g. F2 only over the most useful values,
  or a hashed F1 over all values with backward pool steps). plan.exe segfaults with >1 thread on deep targets (thread stack in the
  beam fallback): run 1 thread per process or create threads with large stacks.
- `cpp/beam.cpp` (built 11-18): register-exact beam suffix planner. Exact occupancy (<= 48 live) decides which old values may be
  reused; full-pool exact search <= 3 steps with up to MAXSOL alternatives, <= 5 steps over the SMALL most recent values, deep beam
  fallback; children scored by length + LAMBDA * estimated cost of the next R targets; W states kept. On 7 puzzles (45 s each,
  cut at 40-60% of targets): best 1,455 vs 1,332 (+9%); DROP=0, SMALL=100, LAMBDA=0 change little; 10-45 s per run. Shelved for now:
  needs a much stronger per-target search before a beam can pay off.
- Medal maths: 250-999 teams -> bronze top 100, silver top 50; 1000+ teams -> bronze top 10%, silver top 5%, gold top 10 + 0.2%.
  Santa usually ends with 1,500+ teams, so staying at the public frontier (src/remerge.py, run daily) is the floor; own gains on top.
- WORKING PIPELINE (11-18): (1) generate diverse near-best variants: beam.cpp with ALTOUT (every run's program, <= 80 per puzzle),
  lns.cpp with MAXALT/ALTOUT (equal-length plateau variants: almost identical, little use); (2) src/alt2csv.py -> work/alt/*.csv;
  (3) src/recomb.py collect + solve (REL=0.3: variants up to 30% longer than the best take part; values ranked in best-program
  order keep the MILP acyclic; ~1-60 s per puzzle). Recombining near-best programs by different authors finds 1-2 instruction gains.
  remerge.py now runs recomb after every pull. Kaggle: max 5 batch CPU sessions at once.
- Old next-step idea (kept for reference): a beam ("wide") suffix planner: several alternative derivations per target (shuffled pools, length+1 options), keep the W best
  partial programs, many cut points and orders; run on Kaggle CPUs. Then a stronger engine for independent 60-bit puzzles
  (exact 6-step shapes such as t = X*Y +/- p with X, Y two steps from the pool). Re-merge public outputs daily.


## Aside session 11-19 evening (handover from Claude Code)
- LB 00:30 UTC 11-20: #1 128,831, #10 131,968, #25 133,716, #50 134,899, #75 135,684, #100 136,137, #200 136,680; we are ~200th
  at 136,759. Public frontier: royalacecat "Public Frontier 136207" (00:03 UTC); goodpjw2008 "DAG LNS + Depth-5 Search" 136,240.
- Research digests: research/nb1119/SUMMARY_A.md (EDA notebooks) and SUMMARY_B.md (method notebooks). Every public method is a
  local rewrite stuck near 0 on the merged frontier; Rudolph: public programs locally optimal, leader uses "a different construction";
  telling a weak solver the best program's hubs cut it 20%. Independent puzzles = max start >= 100 (242 scored).
- Cost structure of the 136,759 store: independent 242 puzzles 47,268 instr (6.94/target); structured 758 puzzles 89,491 (4.46).
  Scaffold (before first target) 20,472 instr, of which 17,697 values are used later (pure scaffold intermediates only ~2.8k).
  Frontier cost per puzzle is predictable from simple features (GBM on nt/bits/link: R2 0.984, MAE 5.4): quality is uniform.
- Peak live registers >= 44 in ~400 puzzles (166 hit 48): registers bind in ~40% of puzzles.
- Independent targets: segment cost avg 7.82 at 55-60 bits; counting/MITM argument: an isolated 59-bit target needs ~8 from a
  48-value pool (F4 x F3 meet); so independent rows look near the practical floor; slack is in structured rows.
- Mixed family: small targets form affine chains (T' = m*T + o, m 2-16, o 2^9-2^16, sometimes (9T+o)/2); large (>2^52) look random.
- cpp/pal.cpp (new): keeps all frontier values as an ordered list, re-derives each with exact <=3-instruction search (F1 hash,
  t0 op y, t0 op t1, chain), register-allocates every eval; moves: remove helper / insert inverse-op helper; modes greedy, SA
  (SA=1), ruin&repair LNS (LNS=1, penalty mode). Result on 0011/0280/0789/0075: 0 gains in 60-90 s each (10k-40k evals).
  The frontier is locally optimal for single and multi helper add/remove too. LNS mode is very slow on 200+ instr programs.
- Process gotcha (Aside): Start-Process children launched from a tool call get killed; use Bash with yield_ms (persistent exec
  session) for long jobs. Claude Code session still active in parallel (it started lns3 small5cut2 at 17:52 local).

- 11-19 ~20:00 local: autoloop round submitted 136,103 (ozertuu starter notebook -1,962 on 577 rows; shared family took
  1,568 of it, 52 rows dropped by >= 10: e.g. scored_0814 160 -> 124, 0162 180 -> 141). The new construction = decode the hidden
  atoms (17-21 bit), build them first in a 45-50 instruction scaffold, then ~2-3 instructions per target.
- Generator facts (research/generator/FINDINGS.md, classifier research/generator/scored_family.csv): independent targets are
  i.i.d. uniform in one decade (nothing to decode); mixed = ~half independent + structured chains; shared = k*M + c with
  M = product of 1-3 hidden 17-21-bit atoms, k smooth <= ~2^15, |c| <= ~2500; multiplicative = products of 2-5 small atoms
  (8-12 bit) + small offset. Predicted family totals: indep 248 / 47.4k, mixed 198 / 35.2k, mult 287 / 22.8k, shared 251 / 31.2k.
- LNS with 64 registers vs 48 on 12 register-bound puzzles: 0 gains both -> registers are not what blocks local search.
- konbu public beam with the atoms injected as early targets: 0814 217 -> 203 (frontier 124). Useless as a constructor.
- pal.cpp v2: depth 4/5 derivations (F2c = F1 op S over the first 40 kept values), ITEMS mode (explicit ordered helper list,
  targets appended ascending), KEEP mode, greedy repair with structured candidates (k = round(v/M), |c|) and factor candidates
  for deep items. Rebuild tests: frontier atoms+cones+shared products -> 0938 104 (=), 0011 108 (+1). Atoms + products only
  (palette rebuilt by pal) -> 0938 119, 0011 125 (+15%): the frontier palettes are much better than greedy helper insertion.
- cpp/hubs.cpp: atom scan h in [2^13, 2^23), count targets with |T mod h| <= 2600, z-score; finds the real atoms on
  0938/0814/0162. work/hubs_all.txt = top 12 per puzzle. Only ~81 shared puzzles have z >= 8 hubs; 53 structured puzzles
  have >= 2 strong hubs that the frontier program does not build (work/p_missing_hubs.txt, 6,547 instr) -> pal ITEMS run.
- Automation: work/freshloop.ps1 (LNS on rows changed by each merge, persistent exec session), work/kfresh.ps1 (pull finished
  Kaggle kernels, push elf-calc-fresh-K on fresh rows when CPU slots free), work/oneround.sh (one merge round).
  Aside routine eEdqDZS545ieEWcv runs oneround (if no autoloop alive) + kfresh every 2 h and reports rank.
- pal ITEMS (decoded hubs + their products, palette rebuilt) on the 53 "missing hub" puzzles: every one infeasible (only ~50%
  of targets fit k*M + c with the decoded hubs). pal INJECT (frontier values + decoded hubs/products before the first target,
  ruin&repair LNS 150 s): 0 gains on 46 of 53 (e.g. 0136 98 -> best 106, 0082 96 -> 100). Those puzzles already carry
  efficient structure; the costliest "shared" rows (0764, 0375, 0466, 0345 at 6.2-6.5/target) are really mixed/random.
- ozertuu starter notebook (source of the -1,962 drop) only replays the dataset ozertuu/santa-2026-verified-programs; its
  engine text: "Deep Cone Pollard-Rho & Joint Scaffold Optimizer": Pollard-rho cofactor decomposition of T +/- r, large D2 MITM
  (2^21-2^22 flat hash), congruence backward beam search, Belady register scheduling. Code (opt_deep_cone.cpp) not public.
  Idea to port: factor T - r (r from the pool / F1) fully and try every divisor split a*b with a, b cheap (D2 lookups) ->
  derivations a*b + r up to depth 6 that our <= 5 MITM and dictionary beam miss.
- 21:00 local: merge round submitted 135,917 (public frontier royalacecat 135,936). LB #1 128,831, #50 134,582, #100 135,767,
  #200 136,057. Built work/lns3n.exe and work/paln.exe with -O3 -march=native; kernels (kfresh) now compile -O3 -march=native.
- Aside exec sessions expire after ~1 h and kill their children (freshloop died, Start-Process/WMI/Task Scheduler launches are
  killed or blocked by the sandbox). Long compute must run in Kaggle kernels; local polish = work/freshonce.ps1 (40 min,
  pending queue in work/fresh/pending.txt), run by the 2-hourly routine.
- pal FACTOR mode (Pollard-rho split of v - r into a*b, a,b in S/F1/F2c, depth <= 6): 0 gains on 24 random puzzles x 60 s.
- Top-down constructor (work/decode2.py: every needed k and |c| + atoms + products as ITEMS, pal prunes): 0938 124 -> 117
  (frontier 103); 0011/0814/0162 infeasible (targets outside k*M + c). Palette search in pal is ~63 ms/eval: too slow for SA.
- src/scaf_milp.py (joint scaffold MILP): nodes = starts + targets + all frontier values + atoms + atom products + top-3
  (k, c, k*M) per target; recipes = every one-instruction pair; HiGHS + lazy generalized subtour cuts. scored_0938: 188 nodes,
  946 recipes; bound rises 71 -> 102 in 27 iterations / 300 s; frontier 103. => within its own value neighbourhood (plus the
  structural candidates) the frontier is optimal to within 1. Big gains need NEW candidate values (other atoms / palettes /
  other lineages), not better selection. Useful as a lower-bound probe: run on puzzles to locate real slack.
- Next engine steps: (1) MILP universe = union of all public variants for the puzzle (pub3 lineages) + structural candidates
  (exact cross-lineage recombination with SEC cuts instead of rank ordering); (2) richer palette candidates (1-op closure of
  small values, filtered by usefulness) with a faster solver path; (3) C++ port of the recipe enumeration.
- Kaggle search-1/3/4 (750 rows, 9.6 h x 4 CPUs each, on the 138,040 dataset): -3/-2/-2 inside the kernels and 0 rows
  shorter than the current store. Generic LNS on stale rows is near-worthless; slots now run fresh-row polish (elf-calc-fresh-K).
- Scaffold MILP + 10 public variants of scored_0938 (281 nodes): bound 96 after 420 s, still rising (frontier 103).
- Workflow fixes 11-19 22:15: (1) removed work/supervisor.ps1 + chain_autoloop.ps1/.pid (never ran; Windows/sandbox blocked
  them; no scheduled task exists). Replacement work/ensure_autoloop.sh = check-then-start (re-checks right before starting;
  refuses if any autoloop.sh runs; --wait starts the next loop when the current one ends). Must be launched from a shell whose
  processes survive (Claude Code / user terminal): nohup bash work/ensure_autoloop.sh --wait > work/ensure_autoloop.log 2>&1 &
  (2) kfresh.ps1 and freshonce.ps1 now TAKE work/store.lock (mkdir) during the store export and release it in finally.
  (3) kfresh.ps1 waits until `kaggle datasets status` = ready AND the dataset lastUpdated >= upload time before pushing
  (max 15 min, else skips pushing that round; snapshot only advances after a push). (4) single downloader: kfresh pulls only
  its own elf-calc-fresh-* kernels; kdone.ps1 reuses watch_pull's work/kaggle_out/<slug>_* folders and downloads only if none
  exist; duplicate _1120_0402 folders removed. Live test: kfresh waited ~1 min for ready, pushed elf-calc-fresh-3, lock released.
- Kaggle search-2 (250 rows): 0 rows shorter than the store (4 of 5 batch kernels: 0). search-5 (cut settings, newer rows)
  still running at 22:21; work/kdone.ps1 (hourly routine step 0) processes the batch when it ends.
- Structure-only MILP (no frontier values except cones of 5 unfit targets; closure = 2 ops from starts, 290 values;
  atom factor candidates): 2,204 nodes / 811k recipes; first HiGHS solve 156 s (obj 72), second 490 s (89): far too slow.
- Counting with tree-shaped derivations: |values within 2 steps| ~ 2^26 (F1 x F1), so isolated 60-bit targets could need ~7.
  BUT exclusive cones in the frontier (instructions used only by one target): independent 50-60 bit targets have cones
  1..7 (only 94 of ~1,800 at 8); sum of (cone - 7) over cones >= 8 is 96 (independent) + 119 (mixed) + 0 elsewhere.
  => per-target re-derivation cannot gain much: targets lean on SHARED helpers (~48% of instructions). Any big gain must
  come from a better shared-helper design (which helpers / basis values exist), not from deeper per-target search.
- OR-Tools CP-SAT installed offline (wheels downloaded via the browser into tools_wheels/, installed with uv --target into
  ortools_lib/ because ortools needs protobuf < 6.34 and the venv has 7.36). Use: PYTHONPATH=<santa-2026>/ortools_lib.
- src/cpsat_recomb.py: CP-SAT exact recombination. Nodes = all values of the best program + every public variant <= 1.3x
  (work/var_all.json, built by work/collect_all.py: 219 CSVs, 9,383 variants, 9.4/puzzle) [+ STRUCT=1 structural candidates:
  atoms (frontier mid values used >= 2x + hubs z >= 8), products, k, |c|, k*M]. Recipes = every one-op pair; bool x/y + int
  levels with OnlyEnforceIf for acyclicity; hint = best program (x, y and levels, repair_hint); depth-first scheduling over
  several target orders + linear-scan allocation (<= 48 live), replay-validated; gains -> work/out_cpsat_lns.txt (auto-imported).
  Results: 0814 OPTIMAL 122 (=), 0938 OPTIMAL 103 (=), 0162 OPTIMAL 138 (best 139: -1, valid), 0011 feasible 106 bound 99.
  0938 with 4 extra pal constructions (116-121, different helper sets): 103, bound 102 -> no gain.
  40-puzzle random sample at 60 s (first ~17 done): 0 gains; bounds weak on 800-1300-node models (FEASIBLE, not proven).
  CP-SAT is ~100x faster than the HiGHS lazy-cut MILP. Public variants are already recombined by public CP-SAT notebooks.
- STRUCT=1 CP-SAT on 16 random shared/multiplicative puzzles (90 s, 8 workers): 1 gain (scored_0326 130 -> 129, valid).
  ~5-7% of structured puzzles gain 1 at this budget; bounds still weak on 600-1000-node models.
- Merge round 23:0x submitted 135,828 (includes CP-SAT 0162 -1). Hourly routine confirmed running (kdone WAITING 23:03).
- Kaggle CP-SAT kernels: kaggle/cpsat_run.py template + work/kcpsat.ps1 (private dataset shauryanadagoudra/elf-calc-cpsat-inputs:
  cpsat_recomb.py, elf.py, puzzles.csv, programs.txt export, var_all.json, hubs_all.txt, cpsat_ids.txt (shared, multiplicative,
  mixed; costliest per target first), Linux cp313 ortools wheels as fallback). Slugs elf-calc-cpsat-0/1 split the ids;
  ~10.3 h budget, 60-300 s per puzzle. First push refused (5 batch sessions busy: Claude Code also runs
  revised-better-elf-calc-search-5, which my slot counter does not track). Retried hourly by the routine (step 2, before kfresh).
- kfresh fixes: an unclear status of a kernel we pushed counts as busy; snapshot advances only after a successful push.
- 11-20 01:03 search batch done (kdone): 1,531 programs compared, 2 shorter (search-5: 0590 116->115, 0908 31->30) ->
  submitted 135,826. 01:16 merge (royalacecat 135,817) -> 135,758, rank 161 (#25 133,061, #50 134,185, #200 135,782).
  All Kaggle pushes refused: 5 batch sessions = my fresh-0/1/2 + Claude Code's revised-better-elf-calc-search-1/2.
- work/cpsonce.ps1 (local CP-SAT STRUCT batch over kaggle/cpsat_inputs/cpsat_ids.txt with a rotating pointer) replaced
  freshonce (0 gains on its last rows) as routine step 3. Batch #0-29 (costliest "structured", mostly random-like): 1 gain
  (0714 144 -> 143). cpsat_recomb STRUCT candidates widened: nested k*(M + c1) + c2 and target links Tj = p*Ti + r.
- 11-20 ~03:00-06:20: PC/Aside apparently asleep (no routine runs). Old merge loop (PID 43020) ended. 06:26 a merge round
  (started by Claude Code) took a new ozertuu release (-1.27k, e.g. 0985 134 -> 112) plus our CP-SAT gains -> submitted
  134,481, rank 147 (#1 128,330, #25 132,569, #50 133,452, #75 134,011, #100 134,318). No merge loop alive afterwards:
  the hourly routine's step 1 (oneround when no autoloop) covers it while Aside runs.
- STRUCT=2 (wider candidates) test on batch-2 puzzles that failed at level 1: 0 gains in the 10 that finished (bigger models,
  same 90 s). Keep STRUCT=1 (+ nested + target links) as production; more time per puzzle is the better lever.
- 06:28 elf-calc-cpsat-0/1 pushed (all 5 slots were free) on the fresh store; RUNNING after 5+ min (setup OK).
- 11-20 evening: hourly routine trimmed to merge + Kaggle steps (~3-7 min/round). Two 8 h Kaggle CP-SAT STRUCT runs: 3 and
  0 programs shorter at run start, 0 net after the public moved -> pushes paused (kaggle/fresh_state/cpsat_nopush.txt).
  Merge-only progress: 134,481 -> 132,913 (goodpjw2008 LNS+CP-SAT recombine notebook -870). remerge.py dataset filter:
  contest-specific title and <= 300 MB (a 15.3 GB 'Santa Catarina' dataset was downloaded once; deleted).
- FROM-SCRATCH CONSTRUCTOR track (cpsat_recomb.py modes): SCRATCH=1 (structural candidates + 2-op closure of starts + atom
  factor candidates + best-program cones of unfit targets, no hint): 0938 1,671 nodes / 418k recipes, UNKNOWN in 240 s;
  0011 2,088 / 644k UNKNOWN. NOFRONT=1 + STRUCT=1 (pool = only our own pal constructions + structural candidates, hint =
  shortest own): 0938 4 constructions 116 -> CP-SAT 108 OPTIMAL in 77 s; 16 constructions -> 108 (bound 100, 240 s).
  Public best for 0938 is now 99 -> own constructor gap 15% -> 9%. Next: iterate construct -> CP-SAT -> perturb (pal LNS
  seeded from the CP-SAT result) and measure on a 30-puzzle benchmark before any Kaggle scale-up.
- Constructor iteration on 0938: pal LNS seeded from the CP-SAT 108 program -> stays 108 (local optimum). Ruin & rebuild
  (drop random 30% of the 76 helpers via KEEP, pal repair + LNS 40 s, 12 seeds, work/ruin.py) -> 11 variants 113-125.
  CP-SAT NOFRONT over 28 own programs (108 + 16 constructions + 11 rebuilds): 108, bound 91 (240 s, FEASIBLE).
  => construct -> recombine plateaus at 108 vs public 99 (+9%). The missing piece is the palette/scaffold design itself,
  not recombination: our constructions never contain the cheap shared helpers the public scaffold uses.
- 0938 public (99) vs own (108) anatomy (work/cmp0938.py, work/bases0938.py): public has 16 big helpers reused >= 2x (ours 8)
  and 20 small constants (ours 34). Bases = products of atoms (124780*618523, 124780*717923, 618523*717923, squares) and
  near-copies (M - 5, M - 24); targets hang off them via a SHARED small palette (152 used 5x, 5, 120, 121, 123, 243, 484, 486)
  and big-with-big ops (617434399520 - 77179299935; 444051887724 + 444051887729; 140130435723 doubled).
  Our decode2 picks each target's exact k and c separately -> many single-use constants.
- MITM palette-chain candidates (cpsat_recomb MITM=1): palette = 2-op closure of starts (MITM_SM), pass 1 counts distinct
  targets each palette value serves in <= 3-step chains (target op s op s2 <- M op s3), keep top MITM_K; pass 2 adds chain
  nodes; + big-with-big links between bases (B1 +/- B2 = target or target +/- palette). Results on 0938 (pool: own only):
  base x base closure: 9 GB, killed. base x starts, K=30: 1,152 nodes / 70k recipes, 108, bound 77 (300 s) - palette chosen
  is tiny values (2, 3, 4, 8: they divide anything) not the public's mid values. Oracle (public palette): 824 nodes / 21k
  recipes, 108, bound 83 (300 s). Running: oracle + big-with-big, 1,500 s, 12 workers.
- Oracle + big-with-big (844 nodes / 21.6k recipes, 1,500 s, 12 workers): 0938 108 -> 107 (bound 85).
- COVERCHECK (cpsat_recomb NOFRONT + COVERCHECK=1: lists public-program values missing from the candidate set):
  3-step chains + big-with-big: 10 of 99 missing (243*M, 120*M - 9 (4-step chains), atom + 29, base - base stepping stones).
  + depth-4 chains restricted to the palette (meet in the middle: forward (M op p) op p2, backward (t op p) op p2)
  + near-atoms (atom +/- palette) + Bs over all big nodes: 5 of 99 missing (all second-order big-with-big:
  179164863885 = B + (B+5) with B+5 a target; 540255099585 = 8M - (M - 5); 1612483774965/973; 4123307471641).
  Candidate set 3,534 nodes. Running: 1,500 s solve on it. Solver scaling is now the bottleneck.
- 3,534-node candidate set (covers 94 of the public program's 99 values): 266k recipes, ~11-12 GB RAM, 1,705 s ->
  108 (bound 69). The full-model CP-SAT cannot use a rich candidate set: more candidates = worse result.
  NEXT: solver-side change, not candidate-side: CP-SAT LNS over the candidate set (fix most of the current program,
  free one target cluster / one base and its consumers at a time, small sub-models solve in seconds), and C++ recipe
  building (Python recipe enumeration alone takes ~10 min at 3.5k nodes).
- 11-21 early: numpy recipe builder (build_recipes: 266k recipes in seconds instead of ~10 min) + CP-SAT LNS mode
  (LNSMODE=1: free k targets or 1-2 shared bases with all downstream targets + their exclusive cones + depth-2 backward
  recipe closure, fixed rest; LNS_K/LNS_D/LNS_CAP/LNS_T/LNS_ZMAX). 0938 from own 108 with the 3,534-node candidate set:
  target nbhds 70 it 0 gains (600 s); base nbhds 47 it 0 gains (900 s).
- DECISIVE DIAGNOSTIC (INCLUDE_PUB=1: pool = own programs + the public 99 program's values, start = own 108):
  my LNS 420 it -> 108 (0 gains); full-model CP-SAT 400 s -> 106 (bound 94). Even with every value of the 99 solution in
  the pool, solver search from our 108 cannot find it: 108 is a deep basin (the palette constants every target depends on
  must change together). => CP-SAT/LNS are polishers, not constructors. The constructor itself must produce near-public
  scaffolds (palette + bases) directly. Candidate next design: layered facility-location model (palette layer, products,
  bases = M op p, targets = base op p / base op base) with no acyclicity constraints, then CP-SAT polish with hint.
- 11-23 16:00 status: 128,503 rank 183 (public best notebook 128,504). Ranks 100-200 within 128,470-128,504: each own
  instruction ~3-5 ranks. Local CP-SAT recomb (STRUCT, 40 most diverse puzzles): 0. Unlisted notebooks (orel1986 lns,
  devraai, hosseinbadrnezhad): 0. fresh LNS r8 + pal FACTOR on changed rows: 0 so far. oneround.sh PATH fix (seq/grep).
- LAYERED CONSTRUCTOR (src/layered.py): L0 = starts + best-program cones of the atoms (fixed); palette P1/P2 (< 2^13, one
  op of small L0 values / P1 x S0); L2 = atom products; L3 = X op p (X in atoms/L2, p in palette) + L2 +/- L2; targets
  ranked by first cover in the best program, built by 1 op from L3/L2/palette/earlier targets, or chains of <= 3 steps
  with constants from L0 (S0s) and P1, leaves = bases / earlier targets / pairs (w = X +/- leaf). Backward generation
  from targets, pruned to target-reachable, fixpoint-filtered to buildable. CP-SAT with no ordering constraints (layers).
  0938 (public 99): strict 1-op layers 119 OPTIMAL (38 s); + bases of bases + target reuse 108 OPTIMAL; + 3-step chains
  + pairs 106 OPTIMAL; + all L0 values as chain constants 105 OPTIMAL (216 s, 37.7k nodes, 107k recipes).
  LCOVER=1 prints the best program's values by layer and those outside (now 4: L3 - L3, chains off 120*L3, T - P1).
  Running: benchmark on 10 random shared puzzles (150 s each).
- layered.py fixes: atoms capped to the 8 most reused (AMAX), targets with no surviving recipe fall back to best-program
  ancestors, targets already in L0 excluded (caused INFEASIBLE).
  Benchmark, 10 random shared puzzles (150 s, public best -> layered): 0291 156->170, 0341 115->131, 0950 107->128,
  0605 159->162, 0102 113->116 (FEASIBLE, bound 95), 0226 114->134, 0675 114->122, 0345 193->202, 0746 112->123,
  0332 136->150. Mean gap +12 (~10%); 0938 +6. Most OPTIMAL within the model -> the structure patterns, not the solver,
  limit it. Next: LCOVER on the worst (0950 +21, 0226 +20) to find missing patterns; better atom detection than
  "frontier mid values used >= 2".
- LCOVER 0950: atoms are 13-14 bit (9398, 5159, 9392; products 9398^2, 5159^2, 5159*9398), the >= 2^14 detector missed
  them (30 public values outside layers). ATOMMODE=mul (default; atoms = operands of big x big '*' in the best program;
  ATOMMODE=freq = old). Benchmark mul vs freq: 0291 162/170, 0341 142/131, 0950 114/128, 0605 165/162, 0102 118/116,
  0226 149/134, 0675 125/122, 0345 regfail(202)/202, 0746 122/123, 0332 151/150. Best-of-both mean gap +9.6 (was +12),
  still behind public on all 10.
- LCOVER 0226 (freq): products of OTHER L0 values (16712*1028, 14398*4228), T - base, INT*L0 chains, L0 - L3.
  LBROAD=1 (L2 = products of the 30 most used L0 values >= 2^9; base constants = S0+P1 when > 60 products): 0226 145
  (FEASIBLE, bound 140) vs 134 freq; generation 339 s. Bigger model = worse: dead end as is.
  Status: layered constructor ~10% behind public on shared puzzles; patterns differ per puzzle; Python generation slow.
- 11-24 morning: layered.py ALTOUT (dump every constructed program). 22 constructions (mul + freq atom modes, 60 s) on
  the 11 benchmark puzzles pooled with public variants (work/var_bench11.json) -> cpsat_recomb STRUCT=1 REL 1.45, 120 s,
  hint = public best: 0 gains on all 11 (bounds 76-141, all FEASIBLE). Constructor programs add no useful values to
  recombination at ~10% worse quality.
