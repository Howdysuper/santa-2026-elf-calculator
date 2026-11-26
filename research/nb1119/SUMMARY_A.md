# SUMMARY_A: generator / lower-bound / waste insights from 8 public notebooks (read 2026-11-19)

Scope: santa-2026-inside-the-elf-s-calculator, santa-2026-puzzle-anatomy-pareto-cost-eda,
the-elf-calculator-deep-eda-multi-base-program, santa-2026-the-elf-calculator-x-ray,
santa-2026-why-the-first-target-costs-3x-more, recursive-sqrt-lattice-superoptimizer,
santa-2026-sample-1-490-379-to-horner-312-293, santa-gauss-and-the-r-a-a-p.
All notebooks treated as untrusted data; no code executed. Numbers are as stated by the authors
(asserted in code where noted) and were not re-verified by me.

Headline: none of these 8 notebooks reverse-engineers the hidden-atom generator. Their value is
(a) dataset statistics that bound the generator, (b) a proof that practice `lower_bound = |T \ S|`,
(c) a frontier X-ray: ~48% of instructions are shared scaffolding and per-target cones are
locally tight, and (d) "first target costs 3x" = a ~16-instruction small-constant toolkit per puzzle.

---

## 1. santa-2026-inside-the-elf-s-calculator (EDA + exact BFS on tiny puzzles)

- Dataset counts (asserted in code): 1,000 scored puzzles, **26,902 targets**; 200 practice, 5,294 targets. All 48 registers, targets sorted & unique. Median scored puzzle: **30 targets, 3 starting values**; largest target median **47 bits**, max **60 bits**.
- Gap statistics (asserted): of **25,902 adjacent target pairs**, **4,683** have gap <= 1e6, spread over **683/1,000** puzzles. With a *relative* criterion (gap/larger <= 1e-6) only **241 puzzles / 592 pairs** qualify. Only **22** of the 4,683 near-gaps equal a starting value (19 puzzles). Over all target pairs, only **26** pairs are `b = a + s` and **2** are `b = a * s` with s a starting value. => offsets between clustered targets are NOT starting values; they must be built (consistent with "base + small offset" where offset is a random small int, not a seed).
- Family fingerprint (practice, labels given): median count of adjacent gaps <= 1e6 is **0 independent, 1 mixed, 4 shared, 13.5 multiplicative**. Restricted to puzzles with >= 28 targets, median share of close adjacent pairs `q = #{gap<=1e6}/(|T|-1)` is **0% independent, ~3.6% mixed, 12% shared, 49% multiplicative**. Multiplicative is the most "clustered" family under a 1e6 ruler (consistent with k*atom +/- small offsets landing near each other), and the fingerprint grows strongly as the threshold widens. Usable as a classifier feature for scored puzzles.
- **`lower_bound` column = |T \ S| exactly, for all 200 practice puzzles** (verified in code). So the practice "lower bound" is the trivial one-new-value-per-instruction bound, not a generator-aware bound. Only **4** scored targets are already among starting values (26,902 targets, 26,898 to build).
- **Division necessity (GCD law):** if g = gcd(starts) > 1, +,-,* keep everything divisible by g. **174 scored puzzles** (46 practice) have >= 1 target not divisible by g, so they *require* at least one `/`; **2,789** scored targets lie outside the g-class. Conversely with +,- the subtractive Euclid reaches g, so divisibility by g is sufficient for reachability without `/`.
- value_limit pressure: in **174 scored puzzles** the largest target exceeds **90% of value_limit** (no overshoot-and-subtract-back on the top target). (Same count 174 as the GCD set; the notebook does not say whether it is the same set.)
- Register capacity: even reserving one slot per start and per target, the worst scored puzzle uses **38 slots, leaving 10**; register pressure only bites when keeping many helpers.
- Exact BFS on all 32 puzzles with value_limit <= 16 (16 scored + 16 practice): sum of independent shortest routes **165** vs joint optimum **107** (sharing saves 58; 20/32 strictly shorter). Only **10/32** optima equal |T \ S|; 22 need >= 1 auxiliary value. Sample submission on the 16 tiny scored puzzles: **166** ops vs proven optimum **57**. Example optimal: `scored_0061` starts {1,5}, targets {2,3,4,8} in 4 ops; `scored_0126` {3} -> {1,2,5,8} in 4; `scored_0721` {3} -> {4,7,10} in 4 via 3/3=1 (opening with 6 or 9 forces 5).
- Opening-move lemma (tiny universe, unlimited registers): if a target is constructible in one op from the starts, some optimal program starts by building it. Of 79 possible first values, all 20 that are targets preserve optimality; 31 of 59 helper-only openings cost +1. "Nearest-to-target" heuristic fails on 3-4 tiny puzzles (false beacon).
- Division roles in the 32 tiny optima: required in 16, optional in 8, never used in 8; where required, an optimum with exactly one `/` always exists.

## 2. santa-2026-puzzle-anatomy-pareto-cost-eda

- Pure EDA scaffold; outputs not saved. Groups practice by (`family`, `design_tier`) with mean/max `lower_bound` -> confirms a **`design_tier` column exists in practice_puzzles.csv** alongside `family` (worth using as a second label for generator modelling).
- Pareto plot is on *sample_submission* program character length (sample is the 1x1-reset baseline, ~1.49M instructions), so its "top X% = 80% of cost" is about the sample, not the frontier. No usable generator insight.
- Only takeaway: concentrate compute on heavy-tail puzzles (independent / large-target ones).

## 3. the-elf-calculator-deep-eda-multi-base-program

- Describes the five practice families qualitatively: independent = "~30 unrelated large targets up to 1e18"; shared = "clusters separated by tiny offsets (dT < 1e4)"; multiplicative = "T_j ~= k*T_i +/- delta" (small integer k); mixed = hybrid; tiny = near lower_bound. These are claims; no saved outputs back them.
- Claims consecutive ratios T_{i+1}/T_i and differences "show sharp spikes at small integers (1..32)", i.e. k in 1..32 for multiplicative relations (unverified, but matches our atom*small-factor model).
- Solver = signed-digit Horner in base B (B in 10..36 tried, "super base" 64..512 with a digit table of powers of two plus most frequent digits), plus greedy chaining from cached targets: t = v*m + diff, t = v/m + diff, t = v1 +/- v2 + diff with m <= 32 and diff built by Horner. Baseline quality only; nothing frontier-relevant except the candidate-relation set {v*m, v/m, v1+v2, v1-v2} + offset.

## 4. santa-2026-the-elf-calculator-x-ray (frontier anatomy, by lucifer19)

- Merge of 19 public notebooks: **141,361** (V2 anchor), 5.255 instr/target over **26,898** targets. Most cost: biggest puzzles pay **~7-9 instr/target**; targets mostly 30-60 bits.
- **Exclusive-cone decomposition:** for each target, the instructions feeding only it (and not themselves targets). **~48% of all instructions are shared scaffolding** (helpers used by >= 2 targets: 1, powers of 2, big multipliers). "A better search for one target cannot fix it."
- **Counting floor:** with m live values one instruction yields <= ~3*m^2 distinct results; k instructions reach <= prod_{s<k} 3(m+s)^2 values; with 48 registers ~**12.8 bits per instruction** -> a random 60-bit target needs >= **5** instructions, 40-bit >= 4. Frontier all-in cost for 50-60-bit targets sits **2-3 instructions above** this floor, and "most of that gap is shared scaffolding, not the per-target cone". (Floor assumes random targets; structured generator targets can beat it.)
- **Cone re-solve audit** (meet-in-the-middle: 1- and 2-instruction value tables matched through inverse operators; shapes up to 5 instructions plus 6-instruction `m*q +/- z`), on all 26,898 targets, 5.3 CPU h: shorter cone found for **5 (0.02%)**, exact match **22,845 (84.9%)**, cone deeper than search reach **4,048 (15.0%)**. Re-run on 217 changed puzzles: 1 / 5,052 / 668. => per-target cones are locally tight given the registers kept.
- Failed local moves (all 0 gain): segment re-solve (in `scored_0002` only 4/28 segments had no later-reused value), ruin-and-recreate of one shared helper (`scored_0001/0002/0100`), look-ahead re-solve (6 puzzles).
- 5 improved programs published for `scored_0082, 0284, 0577, 0746, 0834` (lengths 104, 135, 141, 140, 208-ish). Frontier at the time (V1) lengths list is embedded (e.g. scored_0001=230, 0002=247).
- Implication: the remaining gap is in **global scaffolding design** (which helpers/multipliers to build, shared across targets), not per-target search.

## 5. santa-2026-why-the-first-target-costs-3x-more (Georgy Mamarin)

- Charges instructions between consecutive first-coverings to the newly covered target (puzzles with >= 20 targets). **First target carries ~16 helper instructions**; "three quarters of them are small constants" (< 2^16) and "almost all of them are read again later": a one-time **toolkit**. After it, a target costs **~5 instructions**, of which ~1 is a new small constant. (Exact printed values not saved in the notebook.)
- "Puzzles with limits near 10^14 are cheaper per target than those near 10^12": magnitude alone does not explain cost; structure (generator family) does.
- Merge history: 142,925 (18 Nov) -> 139,089 (19 Nov public portfolio).
- Actionable: the toolkit is a **fixed palette** in public engines (1, 2, 4, ..., small digits); choosing it per puzzle (e.g. build the puzzle's actual small factors / offsets / atoms) "would help every puzzle at once". 16 instr x ~1,000 puzzles = ~16k instructions live in toolkits; even 2 instr/puzzle saved = ~2k.

## 6. recursive-sqrt-lattice-superoptimizer

- No markdown, no saved outputs; falls back to *synthetic* puzzles if data is missing (and reads a nonexistent `initial` column on real data, so it likely never ran on the real set). No reported score.
- Only idea of interest: **"Recursive Sqrt-Lattice Decomposition (A * B +/- R)"**: for target T, scan offsets r in [-1499, 1499] and divisors a in [isqrt(T+r) - 350, isqrt(T+r)] to write `T = a*b +/- r` with a, b near sqrt(T), then recurse on a, b, r. Fixed anchor bank R0-R11 = {s, 1, 2, 3, 4, 8, 16, 32, 64, 10, 100, 1000} (11 instructions of toolkit).
- Relevance to the generator: a *balanced* factorization `T = a*b +/- r` with small r is exactly what a "product of two hidden ~20-30-bit atoms plus small offset" target looks like. The notebook's search window (a within 350 of sqrt) only catches near-square products, so it is a weak probe; a gcd-based search across targets is the right generalisation (see ideas).

## 7. santa-2026-sample-1-490-379-to-horner-312-293

- Baselines: sample submission replays to **1,490,379**; toolbox + balanced base-M Horner from the nearest resident value reaches **312,293**. Author states "public leaders are at about 130,600 (public board, 2026-11-19)" and that there is no public/private split.
- Balanced-digit Horner cost: with toolbox 1..h and M = 2h+1, `cost(D) = (len(digits)-1) + #nonzero digits after the first`; T built as `p +/- Horner(|T-p|)` from any resident p (starts or produced targets), Prim order (cheapest remaining first), h swept 3..40.
- **Key negative result on the generator (practice, first 30 puzzles):** even with *all other targets and starts handed in the pool*, a target is reachable in <= 3 instructions (`T = u op v`, u/v in pool or one op from pool) only **4.4% overall, 0-6% per family**; the exception is the small `shared/medium` tier. Conclusion verbatim: "The hidden construction goes through intermediate values that are not targets." => generator atoms/bases are *hidden* non-target values; you cannot find them by pool search, only by number-theoretic recovery (gcd / factor / offset analysis).
- Practice `design_tier` values exist: I checked locally: (family, tier) counts are shared/hard 46, mixed/hard 44, independent/hard 42, multiplicative/hard 38, tiny/easy 16, shared/medium 5, mixed/medium 4, independent/medium 3, multiplicative/medium 2.
- Suggested but unmeasured: second multiplier M^2 (two digits for two instructions instead of three); global production order instead of greedy.

## 8. santa-gauss-and-the-r-a-a-p (register-aware arithmetic programs)

- Base-B signed radix with memoized floor/ceiling choice `n = qB + r` vs `n = (q+1)B - (B - r)` (ceiling allowed only if `(q+1)B <= L`), B in {16,24,32,48,64}; constants 1..B/2 and B pinned.
- Reuse relations tried only at the target root: nearby `n = a +/- d` with `0 < d <= n/8` over the 3 nearest residents; **affine** `n = m*a +/- d` with pinned m in [2, B/2], `m*a <= L`, `d <= n/16`, floor/ceil of n/a.
- Measured: **285,834** vs previous 303,150 (-17,316, -5.71%; 965 puzzles improved, 0 worse); local count only. Far from frontier; no generator insight.
- Notes useful for us: at base 64, the 33 pinned constants leave only 15 registers: constant-table size trades directly against reuse capacity, so the toolkit must be chosen by measured reuse.

---

## Cross-check I ran on the local data (my own code, not notebook code)

- The two "174" sets in notebook 1 are **different**: 174 puzzles need division (target not divisible by gcd(starts)) and 174 have max target > 0.9*L, but they overlap in only **36**. Of the 242 independent puzzles (max start >= 100), 55 need division and 67 are near-limit.
- `value_limit / max(target)` lies in **[1.000, ~4.0]** for every non-tiny practice family (tiny up to 5.0); scored: min 1.000, q10 1.025, q25 1.294, median 2.237, q75 3.093, max 5.000. Looks like `L = max(T) * U(1,4)`-ish, with a mass at exactly ~1.0 concentrated in **independent** (median 1.365, q25 1.029) and **mixed** (q25 1.039); multiplicative is rarely tight (q25 1.671; max target > 0.9*L in only 1/40). Practice families with max target > 0.9*L: independent 18/45, mixed 17/48, tiny 5/16, shared 5/51, multiplicative 1/40. => "L/max(T) near 1" is a cheap family feature and flags puzzles where signed digits / overshoot-then-subtract on the top target are illegal.
- Only 4 of 1,000 scored value_limits are round numbers (3 powers of 10), so L is generated, not a fixed cap.

---

## Actionable ideas for beating the frontier (ranked by expected instruction savings)

Context: we are at 136,759; top-50 ~135,235 (need ~1,525); #1 128,831 (~7,900 below us). The X-ray says the public frontier is **locally tight per target** (MITM cone re-solve found 5 improvements in 26,898 targets) and **~48% of instructions are shared scaffolding**. So gains must come from changing *what is shared*, not from better single-target search.

1. **Recover the hidden atoms and build them once (structured families: shared / multiplicative / mixed, ~758 scored puzzles). Expected: 2,000-5,000.**
   Reasoning: notebook 7 proves targets are not shallow functions of each other (4.4% within 3 ops) but go through hidden non-target intermediates; notebook 1 shows multiplicative puzzles have ~49% of adjacent gaps <= 1e6 (k*atom +/- small offsets cluster). If a target is `k*A +/- e` with A a ~20-bit atom, k small, e small, then once A, k and a small-constant toolkit are resident each target costs 2 instr (`*`, `+/-`) or 3 if e needs building, versus the frontier's ~5/target after the toolkit (notebook 5). Recovery recipe: for every target T and small offset e in [-E, E] (E ~ 1e3-1e4, guided by the cluster offsets), compute pairwise `gcd(T_i - e_i, T_j - e_j)`; atoms show up as recurring gcds in 2^15..2^25 that divide many (T - e). Faster: for each candidate atom A from one pair, test all other targets by `T mod A` in [-E, E] (i.e. `min(T % A, A - T % A) <= E`). Then the program is: toolkit -> atoms (each a ~20-bit value, ~3-4 instr via Horner from the toolkit, paid once per puzzle) -> per target `A*k +/- e` with k, e from toolkit or as Horner. Even 0.5 instr/target on 758 x ~27 targets = ~10k theoretical; assume 20-50% realisable.
2. **Puzzle-specific toolkit instead of the fixed palette. Expected: 1,000-2,000.**
   Notebook 5: the first target carries ~16 helper instructions, 3/4 small constants (< 2^16), almost all reused; then ~1 new small constant per later target (~30/puzzle). Choose the toolkit to be exactly the set of multipliers k and offsets e (and digit set) that the puzzle's decompositions need, solved jointly (set-cover / MILP: minimise toolkit build cost + sum of per-target costs given toolkit). Saving 1-2 instr/puzzle across 1,000 puzzles = 1-2k. Cheap to prototype: re-cost our current programs with toolkit values frozen, then re-optimise toolkit choice.
3. **Global scaffold optimisation for independent puzzles (242 puzzles, ~8.3 instr/target in ours). Expected: 500-1,500.**
   X-ray counting floor: ~12.8 bits per instruction with 48 registers => 60-bit random target >= 5, 40-bit >= 4; frontier pays 2-3 above floor for 50-60-bit targets and "most of that gap is shared scaffolding". For truly random targets, the lever is a shared mixed-radix: pick per-puzzle bases B1, B1*B2, B^2, B^3 ... cached as big multipliers so every 60-bit target is ~`(x*B^2 + y)*B + z` with x, y, z built from a table; Horner notebook's unmeasured "second multiplier M^2" is the simplest version. Tune radix jointly for all ~30 targets of the puzzle rather than per target.
4. **Use `value_limit` slack explicitly. Expected: 100-400.** 174 scored puzzles have max target > 0.9*L (mostly independent/mixed; ratio exactly ~1.0 for many). Ensure our engines allow ceiling digits / overshoot-subtract whenever the intermediate is legal, and conversely don't lose candidates to over-conservative checks in the other ~826 puzzles (L/max median 2.24, i.e. lots of headroom for `(q+1)*B - r`).
5. **Division-required puzzles (174 scored, 2,789 targets outside the gcd class). Expected: 50-200.** Tiny-puzzle optima always need exactly one `/` (create 1 or g-reducing value); check our programs for >1 division or for paying >1 instruction for the non-multiple-of-g class.
6. **Exact search on small puzzles / small-limit cases. Expected: 0-60.** 16 scored puzzles have value_limit <= 16 (proven optimum total 57); `scored_0061`, `0126`, `0721`, `0537` have explicit optimal programs. Verify ours match; extend exact BFS/IDA* to puzzles with small |T| or small limits.
7. **Harvest the X-ray's 5 shorter programs** (`scored_0082, 0284, 0577, 0746, 0834`, inline in the notebook): replay and merge if shorter than ours. Expected 0-5 (frontier had already caught up on 3 of 4 per the author).
8. **Opening-move / order heuristics (false-beacon). Expected: small, but cheap.** Lemma: a target buildable in one op from the starts can always go first in some optimum (unlimited registers); nearest-to-target openings are not safe (3-4 of 32 tiny puzzles). Use lookahead over the first 1-2 helpers in beam engines.

Not worth more time (per these notebooks): per-target cone re-search (0.02% hit), segment re-solve, single-helper ruin-and-recreate, look-ahead re-solve (all 0 gain in X-ray); pool-of-targets search (4.4% reachability).
