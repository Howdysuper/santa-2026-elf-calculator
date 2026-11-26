# SUMMARY_B - algorithm extraction from 10 public notebooks (Santa 2026 Elf Calculator)

Source folder: `research/nb1119/`. All notebooks were treated as untrusted data: parsed as JSON, never executed.
Embedded zlib+base85 blobs were decompressed only to read the C++ sources/audit JSON (no code run).
Notation: a program is a DAG of value nodes; "cut" = a set of nodes whose recomputation is attempted; "witness" = a concrete recipe `(op,a,b)` for a value.

---

## 1. elf-calc-paired-helpers-and-target-scheduling (avazaku; starts from IceFire V60)

**Purpose:** post-optimizer over a full baseline submission (IceFire V60). Pure Python + `scipy.optimize.milp`. No score is printed in the saved outputs (outputs stripped), so measured gain unknown from this file; the design is a "paired helper + recipe-selection MILP" peephole.

**Pipeline per puzzle** (`shorten`): run `extended_pool` twice with different params, keep the shortest after exact replay:
- pass A: `max_helpers=500, reverse=False, witness_limit=4, schedule_mode=2`
- pass B: `max_helpers=600, reverse=False, witness_limit=5, schedule_mode=1`
- ProcessPool with 4 workers over all 1000 puzzles.

**Step 1 - recipe graph from trace.** `read_recipes(starts, program)`: replay program, first recipe seen for each non-start value -> `recipes[v]=(op,a,b)` (value-keyed, register-agnostic).

**Step 2 - re-ordering of the primary graph** (`schedule_mode`): compute `depth[v]` and `consumers[v]`; DFS-emit targets in order
- mode 1: targets sorted by `(-depth, -consumers)`; mode 2: by `(consumers, depth)`; operands visited deepest-first. This changes the topological order and therefore which alternative recipes are legal (recipes must only use operands earlier in the order => acyclic).

**Step 3 - alternative-recipe pool ("choices").** Over all values V in the trace (starts + computed), for every unordered pair (a,b): if `a+b`, `|a-b|`, `a*b`, `a/b` (exact) equals an existing node, add that recipe as an alternative. (O(|V|^2), |V| ~ 100-200.)

**Step 4 - forward x backward helper matching (new intermediates).**
- `middle`: all values `forward(a,b)` over pairs of existing values that are NOT already in the graph (cap = max existing value), keeping up to `witness_limit` recipes each.
- For each existing node v and each earlier existing x, enumerate `backward(v,x)` = the helper h such that one op of (h,x) gives v: `v+x (v=h-x)`, `v-x (v=x+h)`, `x-v (v=x-h)`, `v*x (v=h/x)`, `v/x (v=x*h)`, `x/v (v=x/h)`.
- If h is in `middle` (i.e. h = one op of two existing values), h becomes a candidate helper: costs 1 instruction, gives v a new recipe `(op,h,x)`.
- **Helper ranking:** bitmask footprint per node (`footprint[v]` = all instructions in its cone, `private[v]` = instructions used only by v's chain, i.e. operands with a single use). Savings estimate for helper h on node v = popcount(private[v] & ~(footprint[x] | footprint[a] | footprint[b])) - 1. Rank helpers by (total savings, largest saving, #nodes served). Keep top `max_helpers`.
- **Paired helpers:** for the top 64 helpers: (i) a node v may be rebuilt as `op(h1,h2)` of two new helpers (backward(v,h) lands in helper set); (ii) a helper z may be built from another helper h and an existing x (forward(h,x) in helper set). So two fresh intermediates can feed one output ("balanced expressions").

**Step 5 - merged topological order.** Kahn-style: a value becomes ready when any of its recipes has all operands ready; priority = rank in primary trace. Each value then keeps only recipes whose operands precede it.

**Step 6 - exact recipe selection MILP** (`exact_graph`):
- Binary x_v per candidate value (cost 1 each, roots free). Targets fixed to 1.
- Pre-fixing: if all recipes of a fixed node share an operand, that operand is fixed too (propagated top-down) - "fixes most of a generated circuit".
- For each v: operand-sets of its recipes minus fixed nodes. If some recipe needs nothing unfixed -> no constraint. Else `x_v <= sum_r y_r`, where y_r is either the single operand variable or an AND-auxiliary variable `y_r <= x_a, y_r <= x_b` for 2-operand recipes. Dominated 2-operand sets (containing a singleton option) dropped.
- Objective: minimize sum x_v. `node_limit=200, mip_rel_gap=0`. Then pick for each needed v the first recipe whose operands are present.
- This is a set-cover / "Steiner DAG" selection: each intermediate charged once regardless of fan-out.

**Step 7 - register allocation / emission** (`allocate_graph`): emit in schedule order (3 schedule modes x each graph). Recursive emit of operands; free register pool; when no free register, evict the live value whose **next use is farthest** (Belady), roots evicted last (roots can't be recomputed => if needed later, they get priority class 2). Emission fails if a root would need recompute or length exceeds incumbent; fallback to original.

**Limitations:** Python O(V^2) pools; helpers only 1 forward op from existing values (depth-1 helpers; depth-2 only via the pair trick on the top 64); only values <= max existing value; recompute never allowed (evicted non-root values that are needed again cause failure); no new targets ordering beyond 2 heuristics.

**Reimplementation note:** this is very close to our recombination MILP but adds (a) depth-1 *fresh helper* generation by forward-x-backward meet, (b) helper-pair recipes, (c) private-footprint bitmask ranking. If our MILP only uses recipes appearing in variant programs, step 4 is the novel part.

---

## 2. santa-2026-joint-recipes-for-large-puzzles (atakanaldemir, V30 = 138,273)

**Status:** the notebook itself only replays packed programs (base tape + delta tape). The offline search sources (26 files, ~375 KB C++/Py) and an audit JSON are embedded as zlib+b85 blobs; I decompressed and read them. V30 vs V29: **-7 instructions on 6 large puzzles** (0330 125->124, 0377 91->89, 0512 130->129, 0657 98->97, 0674 109->108, 0792 130->129). Gains are now tiny: the engine family is mature/saturated.

**Overall architecture (engine stack, each `#include`s the previous):**
`elf_window` -> `elf_global_schedule` -> `elf_congruence_generated` (beam core) -> `elf_shared_synthesis` -> `elf_target_blocks` -> `elf_block_rebuild` -> `elf_cumulative_sets` -> `elf_product_distance` / `elf_tail_rollout` -> `elf_reverse_bridges`; plus `elf_multiplier_lanes` -> `elf_multiplier_frontier`; and `elf_interface_closure` -> `elf_joint_interfaces` / `elf_interface_relay` / `elf_outside_alias`, with `elf_numeric_splice.h`.
Acceptance rule everywhere: an edit is kept **only if the full 48-register program, re-emitted and replayed, is strictly shorter** ("neutral plateau" moves allowed only in first round of some engines; final portfolio never takes longer).

### 2a. Core per-target beam (`elf_congruence_generated.cpp`, from Tony Li's "register reuse" notebook)
- **Palette** built first: 1 (via s/s if absent), powers 2^k for k in {1..8,10,12,16,20,24,32,40,48}, small odds {3,5,...,31} (11,13,19,23 as 8+3 etc., 2^k-1 as 2^k - 1, others by binary).
- **Dictionary per target:** leaves = palette + starts + up to `N_DONE=52` most recent done targets (largest first) + recent intermediates up to `N_RECENT=56`. Level-1 = all pair ops of leaves (cost 1), level-2 = level-1 x leaves (cost 2). Open-addressed hash index (2^20).
- **Backward beam from the target** (depth <= 20, width w): state = residual value v with cost. Moves, each costing `expr_cost(factor)+expr_cost(atom)`:
  - `v = q*f + r`, `v = (q+1)*f - (f-r)` for dictionary f (quotient q becomes new state, remainder must be in dictionary);
  - `v = a +/- diff` / `diff - v` where diff in dictionary or diff = 2^k * (state) (shifted, trailing zeros >= 4);
  - nearest dictionary neighbours of v in each sorted cost class (+-4 positions) -> residual |v-a|;
  - **congruence buckets (ResidueIndex):** for each factor f in [16,1e9], non-power-of-two, index dictionary values by `value mod f`; for v, look up atoms with residue v mod f (or f - rem) so `(v -/+ atom)/f` is exact -> new state.
  - "approximate quotient": for big q, take nearest dictionary b to q, residual |a*b - v| if a*b in dictionary.
- Rank = `cost + ALPHA*log2(v)`, `ALPHA=0.18`; prune if `cost+3 >= best`; states must strictly decrease in value.
- **Compile:** targets solved sequentially (order tunable), materialized expressions shared via value map; register allocation by next use, evicted values may be rebuilt (recompute allowed).

### 2b. Window peephole (`elf_window.cpp`, args width=10 passes=8; width>=100 enables 3-step)
- `sweep`: for each window [begin,stop) (stop from begin+width downwards) compute the **goals** = live registers at `stop` whose value differs from current regs (<=2) plus targets whose last write is inside the window and not yet covered. Need |goals| <= 2 and < window length.
- Replace window with `one_step` (single op from known values), `two_steps`, `three_steps` (incl. squaring/doubling sole intermediate; two independent intermediates combined), or `two_goals` (2 outputs). Keep the window giving max (length - replacement).
- Also `elide_helpers` (drop dead writes), `reschedule` (randomized topological re-emission with `mt19937`), `rewrite_graph` with `share_helper` (one new shared helper that replaces exclusively-used operands, "charge exactly one new instruction") and `improve(max_helpers)` with bounding of best possible saving before trying 2 new nodes.

### 2c. Shared synthesis from scratch (`elf_shared_synthesis.cpp`; args hubs=10 width=5 leaves=54 pivots=2 order_mode alpha=.18)
- **Hub discovery by inverse arithmetic:** for each target t and candidate hub h, a demand can be met by `q*f`, `q*f+r`, `q*f-r`, `q+r`, `q-r`, `r-q` with offsets cheap from the seed palette.
- **Divisor hubs:** hypothesize a common factor or common arithmetic-progression modulus directly from several target values (gcd / residue agreement), no family labels.
- Factor plans: synthesize small factors first so their DAGs share; buy a hub only if exact program cost per covered goal is low (strict guard). `exact_batches(leaf_budget,width,hub_budget)`.

### 2d. Multi-output blocks (`elf_target_blocks.cpp`; args group=2 jobs=12 breadth=8 depth=4 leaves=64)
- Pick groups of 2+ targets (choose_cuts over disjoint parts of the program, frequency-penalized so one expensive target doesn't dominate). Enumerate complete short scripts for several roots in one search, no preselected hub; track incidental target hits; dedupe states by hash of value set; keep varied equal-cost scripts.
- **Set-state backward search:** state = SET of unresolved values; intermediate values may enter/leave on either output's behalf (no output must finish first). Leave a difficult operand open only if reduction is large or it connects two goals.
- `replace_block` splices the block into the graph cut; `emit_graph` re-emits with randomized trials.

### 2e. Block rebuild / cumulative sets / tail rollout / reverse bridges / product distance
- `elf_block_rebuild`: rebuild complete dependency cuts with **4-8 actual scoring outputs**; old interior is not free (it must be paid by the new block); demands from several outputs vote for a common new hub, charged once.
- `elf_cumulative_sets` (Hcub-inspired): forward speculative work charged against the reduction in *witnessed* route lengths of all still-open targets; every candidate register-replayed; a preparatory investment must buy strictly more witnessed savings than its cost; near-squares handled with integer sqrt witness; sparse starts -> reverse-beam paths to several pivots; early exit when frozen routes can't improve. "Do not precompute a radix palette - speculative constants are mistaken for paid inputs." (a stated negative).
- `elf_tail_rollout`: choose an opening (prefix) by the write count of its **complete regenerated future** (not grafting to the old suffix); old graph only fallback; mild exploration allows a price-neutral preparation followed by an improvement.
- `elf_reverse_bridges`: re-root a bridge at a numerically cheaper descendant: build the descendant first and recover the bridge by legal inversion (e.g. bridge = desc / k or desc - k).
- `elf_product_distance`: nearest known *products* (not nearest quotient) around unequal-cost operands, then exact arithmetic corrections; first try an exact one-instruction relation to newly computed limbs.

### 2f. Multiplier lanes / frontier (`elf_multiplier_lanes.cpp`, `elf_multiplier_frontier.cpp`)
- Rewrite several target chains around **one explicitly paid multiplier m**: per root t, `affine`: t = m*q (+/- r) [or (m*q +/- r)/divisor], with q, r, m taken from an "atlas" of already-available or one-write values (<=4 witnesses each).
- `fold`: if t's base recipe is x op y with f | x and f | y, rewrite t = f * (x/f op y/f).
- `reassociate`: for up to 6 factors, price all binary partitions of a product (divisions can cancel across leaves) so partial products become shared keys.
- **Factor candidates:** values with >=2 refs or <=32, pairwise gcds >=4, x/d and x*d for d in {2,3,4,8,16}; strength = 4*min(uses,12) + 6 (t%f==0 and q known) / +3 (q,r known) / +3 (q+1 and f-r known). At depth>=5 also **latent coefficients** m in [51, limit/3] with feasible q,r witnesses for >=2 roots (cap 42, or 105 at depth>=7).
- Frontier: explore several equal-cost graphs in parallel; index by scaled difference; "coalition" mode retires all direct consumers of one old scaffold value as a bundle (individual changes may cost more than they save while another consumer keeps the scaffold alive) - price each union exactly.

### 2g. Interface engines (V28-V30, latest)
- `elf_interface_closure`: synthesize several mandatory interface values (values consumed outside a region = fixed "contract") while charging extra helper writes once; existing descendants are not free operands; second helper may be paired with the first in the same output.
- `elf_numeric_splice.h` (credited with V30 wins): replace references **by numeric value** so new and outside consumers share a single write (whole-program merge by value).
- `elf_joint_interfaces`, `elf_interface_relay` (shared-interface beam with exact continuation at every state), `elf_outside_alias` (rebuild a blocked outside descendant first).

**Measured (audit JSON, 850 large cases full split, ~130 s per profile):** interface-revisit: 4 wins (-4); numeric-splice: 2 more (-2); dev numeric splice 3 wins. **Negative results (all 0 wins on 40-case dev, baseline 6,834):** joint-interfaces (literal/actual ports; 138k states), interface-relay (output-only continuation and interior packets, 688k completed costs), outside-alias (alias-only 63 aliases, coupled 1,724 aliases/3,182 whole-program checks) - none shortened anything. Text also states joined-boundary, partial-completion and prepaid downstream-value pilots failed.

**Takeaway:** a very deep local-rewrite stack has reached ~0 gain on its own frontier (7 instructions / 1000 puzzles per version). Same wall we hit.

---

## 3. elf-calculator-residual-cut-search (137,720 -> 137,719; 1 instruction on scored_0738)

**Purpose:** portfolio of 4 pinned public banks (Roman v56 137,722; Ozer v74 137,723; Kinda v21 137,738; Asterios ds v48 137,720) + two post-optimizers. Final gain: **-1 (scored_0738)**, from the CP-SAT graph search with all 4 banks pooled (effort 1.5, bridges 160). Includes a useful table of 10 public notebooks and their scores (Nov 20): best public ~137.7k.

**Engine A - "residual cut" C++ search** (per node = root of a cut):
- Graph from trace: first definition of each value. For each non-start node root: `old_cost` = root + all ancestors whose use-count drops to 0 when root is removed (non-target, non-start) = **private cone**. Skip if old_cost < 2 (or < 4 for non-target roots).
- Allowed leaves = all nodes not in the private cone and **not downstream of root** (descendants cannot rebuild it -> acyclicity).
- `Bank` = all pairwise ops of ALL nodes (hash, size ~6n^2); an atom is "supplied" at cost 0 if it is a kept node, cost 1 if it has a recipe from kept nodes.
- Try in order (stop when cost can't beat old_cost):
  1. own value one op from kept (cost 1);
  2. `binary_join`: goal = x op y with x a leaf/usable atom, y found by hash (goal-a, a-goal, a+goal, goal/a, a*goal, a/goal) -> cost 1 + cost(x)+cost(y);
  3. product + offset: `goal = f*q +/- r` / `r - f*q` with f in leaves (+ up to `extra_factors=256` sampled cost-1 atoms), q in usable, r looked up -> cost 2+...;
  4. `deep_join` with `TwoBank` (width W sampled cost-1 atoms x all nodes -> 2-step values): goal = twoStep op atom, or twoStep op twoStep via **two-pointer scans** on sorted keys for sum, difference, product, plus quotient lookups.
- Output (root, gain, patch). Python applies patches in gain order, with `replace_interior` False/True, recomputes live plan, **re-allocates registers** and replays; first improving patch accepted, iterate.
- **"shared" mode** (`shared_cuts`): for every value h one op away from existing nodes (bank atom not in graph): invert each edge recipe of h to find consumers d that could be re-expressed with h (e.g. h=a+b => a = h-b, b = h-a; h=a*b => a=h/b; also d = h+h or h*h). Evaluate rewiring 1 or 2 consumers (pairs) simultaneously with exact use-count cascade: gain = (#nodes whose use count hits 0) - 1. Ancestor matrix prevents cycles. => "one new intermediate serving two different operations".

**Allocator** (`allocate`): list scheduling; ready set; 3 priority modes: (0) original position; (1) prefer nodes that *release* operands (uses==1) and whose own value is dead; (2) mode 1 only when <6 free regs. Free registers via min-heap; dying operand registers are freed before choosing dest (result can overwrite a dying operand). Fail if 48 exhausted.

**Engine B - CP-SAT graph recombination** (`graph_search(effort, bridges)`):
- Pool = values from all bank tapes for the puzzle. choices[v] = every pair identity among pool values that produces v.
- **Bridges:** values NOT in pool produced by >= 2 different pairs of original nodes (`outside[h]` count >= 2); top `bridges` ranked by count become candidate nodes, and each endpoint x of those pairs gets new recipe from (h, other).
- CP-SAT: bool used[v], int depth[v] in [1,base]; one selector per recipe, sum(selectors)=used[v]; chosen => used[operands] and depth[v] > depth[operand] (acyclicity via depth ordering); targets forced; sum(used) <= len(base); minimize sum used. Hints = base solution. `max_deterministic_time=effort` (0.35 default, 1.5 in the winning sweep), 1 worker, seed 43.
- Then live_plan + allocate + replay.

**Limitations/notes:** the only new-value generator is depth-1 bridges (pair ops of existing values seen >=2 times) - same as our recombination MILP plus 1-step helpers. Gain on frontier ~0 (1 instruction).

---

## 4. rudolph-the-red-nosed-register-allocator (alexchilton; merged 138,193; own solver ~163k)

**Purpose:** self-contained C++ beam solver (Tony Li lineage) + EDA + **the most complete list of measured negative results**. Own solver alone is far from frontier; value is in the ablations and the "hidden hub" analysis.

**Solver (backward reduction over 2-step dictionary):**
- Leaves per target: 1, starts, `N_DONE=60` recent targets, `N_RECENT=80` recent intermediates, and **small leaves first**: up to `SMALL_N=40` recent values < 2^`SMALL_BITS=16` (biggest single win: -5.0%). Dictionary = all values reachable in <=2 ops from leaves (+ x+x, x*x for 1-step values), prices 0/1/2; values already held by the program are free leaves.
- Backward beam: `v = c*f +/- r`, `a - c`, `c + a`, factors f from price<=1 part, remainders from all. Rank = spent + `ALPHA(0.18)*log2(residual)`, `WIDTH=20`.
- **Recipe pick by true cost:** keep all finished recipes within `SLACK=2` of best; re-price by number of *distinct* new values (value used twice counted once); choose cheapest (-0.9%).
- **Dictionary growth** when no recipe: add squares of 3 largest, doubles of 3 smallest, retry up to `GROW=4` rounds (single-start puzzles 8,594 -> 7,974; first target is the costly one: 2,107 vs public 827 - public squares early: 4,16,1024,1055744...).
- Target order: `HEAD` = number of first picks chosen as cheapest target, then ascending; portfolio over HEAD in {0,1,2,3,4,6} + leaf variants; "order diversity is a free portfolio" (-3%).
- **Ruin & recreate** (`RR_ROUNDS=2`): delete values only one target needs, rebuild, accept on *compiled length only* (accepting on value count was +60 worse). **Pair ruin** (`PAIR_ROUNDS=2`): rebuild target + the target sharing most of its chain.
- **Allocator:** Belady (farthest next use) eviction with recompute; plus creation-order schedule, free dead starts, write result into dying operand's register. Without these, public programs recompiled 26% longer; with them they recompile to exactly original length.
- Runtime: ~8 h for 1000 puzzles on 4 CPUs for the 7-setting portfolio.

**Measured arms (scored 1000):** v1 177,553 -> small leaves 168,592 -> 6 orders 164,169 -> 163,817 ...; practice 200: 36,574 -> 32,689.

**Key analysis (section 5b):** in cracked puzzles, targets T = q*h + r with hub h ~18 bits (p10-p90 15-20), quotient q 16/23/35 bits, |r| 3/10/14 bits. **Oracle: given the best program's hubs, their solver cuts 16 cracked puzzles 2,900 -> 2,330 (-20%)**. Slack above 1 instr/target grows from ~38/puzzle (24-bit targets) to ~167/puzzle (56-bit); 300 puzzles hold half the slack. 997/1000 shortest programs in public merge came from one notebook (convergence).

**Everything that FAILED (with numbers) - very relevant to us:**
| idea | result |
|---|---|
| polish public merge with ruin&recreate | 141,432 -> 141,431 |
| pair ruin on merge | 14,362 -> 14,362 (100 puzzles) |
| prefix re-solve (keep 30-85% of merged program, re-solve rest) | 141,423 -> 141,420 |
| meet-in-middle `v = A*B +/- C` over dictionary | 141,420 -> 141,418 |
| two-hub link `T = A*x +/- C*y` (ext. Euclid) | 0; recipes exist (3-5 instr) but replaced instrs feed later targets |
| recombine targets across 76 public files | 0 on 50 puzzles: every apparent saving makes a cycle |
| name hidden hubs from targets (divisor near 3+ targets; shared one-step parent), top 6/12 forced as extra targets | cracked 2,900 -> 2,768 (K6) but uncracked 4,718 -> 4,840 (worse): detectors return 6-512 candidates, wrong hubs cost |
| LLL approximate common divisor | not built: r ~10 bits vs h ~18 bits, gap too small; enumerate 18-bit hubs directly |
| remove dead instructions | 0 dead in public programs |
| bases from 2x2 target grids (T1*T4 = T2*T3), 8,655 quadruples in 151 puzzles | 55 puzzles: 10,094 -> 9,973 but merge 8,057; 0 beat merge |
| small-constant toolkit (lock constants < 2^16) | worse: 6,173 -> 6,353..7,129 |
| joint recipe for 2 consecutive targets via one shared y | 32/507 pairs shorter on paper; 0/32 survive splice (replaced instrs make 1-5 values, mean 2.9, read later) |
| product link `v=f*Y+/-c`, rank bonus for start-divisible residuals, more leaves, small leaves to 2^24 | noise or worse |

Stated conclusion: public programs are locally optimal for every neighbourhood tried; the leader (~5-8k below public merge) uses "a different construction, not a better local search". Statistics: first target ~3x cost of later ones; 12% of instructions precede the first target; 27.6% of instructions make small constants < 2^16.

---

## 5. santa-2026-arithmetic-graph-rewrites (bikrambasnet1; 138,485)

**Status:** packaging notebook only; changed rows stored as zlib+b85 JSON; no search code in this version (v1 had it; not downloaded). Text-only algorithm description:
- Starting from konbu17 programs (142,940) -> 138,485 (**-4,455 on 857 puzzles**). v11 = 138,599; final v adds 114 (75 rows from a complete 1,000-puzzle *randomized search + joint recipe selection over alternate programs*, 14 rows from IceFire).
- Moves named: (1) replace a recipe when an existing value or a shorter chain supplies the same result; (2) **inverse chains / re-rooting**: build the downstream value first and recover its predecessor with the inverse op; (3) recipe recombination across source programs sharing intermediates; then 48-register allocation + replay.
- Gains are vs an older weak baseline; nothing beyond what notebooks 2, 3, 6 implement in code.

---

## 6. santa-2026-shared-intermediates-cuda-cofactors (lightningv08 "Luna"; 141,399 -> 141,380 (-19) +11 from merge)

**Purpose:** a GPU (CuPy RawModule + numba) toolkit of cut-rebuild moves applied to a per-ID minimum portfolio. Outputs stripped; text: arithmetic pass saved **19 instructions** over the 141,399 composite seed (earlier Luna V4 gave larger gains on a weaker base). A per-puzzle plan of (cut, hub, method, coefficient) from 50 earlier batches is replayed. CPU pass on all 1,000; CUDA on CPU winners + 120 targeted cases (source disagreement, previous savings, size).

**Common infrastructure:**
- `to_graph` (first definition per value), `schedule(starts,targets,recipes,hints)` = DFS topological order respecting hint order; `allocate` emits in order and **rebuilds spilled values on demand** (seeds always preserved); `allocate_exact` = linear scan where dest may reuse either retiring source; `pressure_order` alternative. `physical_programs` tries several -> keep shortest replayed.
- **Cut jobs** (`branch_cuts`/`cut_jobs`): for each node v, `gone` = v + ancestors whose all references are inside gone (private cone), budget = |gone|; free set = starts + nodes not gone and not descendants of v (bitmask dependency). Only budget >= 2..4.
- `joint_cuts`: owner bitmask per value = which target closures use it; for target pairs (top 28 pairs by number of values owned exactly by that pair) + 12 random triples: removed = values whose owners subset of the group; roots = the group targets.

**Moves / engines (each yields `edits` = {value: recipe}; accepted greedily by gain if re-schedule is acyclic and strictly shorter):**
1. `BridgeSearch` (CUDA, per batch of 24 cuts, leaves <= ~176): build hash of all pair ops of leaves (1-step atoms); `join`: goal = atom op atom; `backward` (budget>=4): goal = (base op leaf) op outer, i.e. 2-level chain with one intermediate; `fork_search` (budget>=5): goal = (base op known) op leaf with 12 extra. Cost packed in high bits, min over all.
2. `residual_witness` (numba CPU): target = approx (atom op atom, where atom = leaf or one-step value; modes +, y-x, *) +/- correction; correction = atom or `inner_finish` (atom op leaf, 6 modes). Keeps nearest corrections per approximation cost in 80 hashed buckets ("running minima across coarse buckets prevent a cluster of near-identical values occupying the shortlist"), then solves best deltas with inner_finish. Budget pruning.
3. `RecipeNetwork` (CUDA): value pool = all values in all seed banks + for every target pair: b-a, gcd(a,b), a/g, b/g. Hyperedges = all pair identities among pool values (`identities` kernel). `grow(free_sets, rounds=9)`: **Bellman-Ford style min-cost relaxation over the hypergraph** for 64 cuts at once (label = cost<<22 | edge id). Decode tree for roots; accept if total new edits < budget. Used for single and joint (pair/triple) cuts.
4. `CofactorSearch` (CUDA): level-1 table (atoms = 1-step of leaves), level-2 table (atom op leaf). `search_radix`: target = x op q with x atom, q from tables (direct sum/diff/product/quotient), or `x*q +/- r`. **`factor_offsets`: for each atom d, factor T-d, T+d, d-T by trial division over primes < 800 (+ composite remaining cofactor), enumerate up to 64 divisors f, q = prod/f; accept if f and q both in tables** => T = f*q +/- d with all three cheap. This replaces the quadratic multiplicand search by divisibility on a puzzle-specific factor base.
   - `shifted`: for budget>=5, for each free x (48 sampled: 8 smallest + stride), mid = T-x, T+x, x-T, T/x, T*x; search mid with budget-1 (one more op layer).
5. `NearestCofactors.nearest_terms` (CUDA): approximate inverse of sum/difference/product by the nearest reproducible coefficient from the sorted 1-step dict (exhaustive) + strided 2-step dict (stride 32), then price residual: T = (x op q) +/- d.
6. `retained_frontiers`: for each cut, also queries where part of the private cone is kept (a sub-DAG `required[x]` of the cone is retained as free, budget reduced) => partial rebuilds.
7. `exchange_search` (numba): **arithmetic hypergraph** = existing values + one-step helpers h (not in graph) that are produced by >= 2 distinct source pairs; each helper's identities are inverted into "consumer" edges that rebuild original nodes from h. For each banned node/pair (forbid computing v or pair (a,b) - forces a structural change), forward-chain from starts (unlock propagation); if goals unreachable, greedily add helpers by score (# blocked original nodes it would unlock), up to cap=12 per forbid; cost = # used witnessed nodes. Up to 3 rounds. "A helper may repair several branches in one change."
8. `reroot_jobs` (depth<=4, cap 360): **rotate a chain**: make a child the pivot (temporarily free), invert recipes along the path (v = child - other, child / other, etc.), price the whole remaining graph with the child as an extra seed; budget = old size - new size; then search the child itself via cofactors (`optimize_reroot`).
9. `guided_*`: per-puzzle planned (root, hub, coefficient, method in {share, pivot}): neighbourhood radius 2 around root and hub; `guided_subgoals` prices explicit affine exteriors value = hub*q +/- rest, value +/- hub, with q in floor-1..floor+2, then solves the interior on GPU; `guided_exchanges` runs `find_exchange` with bans biased to the neighbourhood (8 turns for share, 4 for pivot).

**Limitations:** all moves are cut-local (single cone, pairs/triples of targets) with 1-2 new levels; the hypergraph relaxation in RecipeNetwork prices trees (no sharing credit inside the relaxation); helpers limited to one op from existing values. On a mature base it yields ~19 instructions per 1000 puzzles.

---

## 7. santa-is-not-happy (prvsiyan; public 138,441 portfolio + own lanes; ~137,784 per notebook-3 table)

**Purpose:** merge (Pratham Jain 138,441 frontier + own combined warm start) then a wall-clock campaign (0.1 h, 4 workers) over puzzles sorted by excess instructions per target, running three engines per puzzle: `poolc` (constructor) -> `relink`/`relink2` (Python rewrite) -> `lns` (C++ value-DAG LNS). Outputs stripped, so the gain of this version is not visible.

### 7a. `lns.cpp` - value-DAG LNS (most reusable part)
- **Analysis per iteration:** `ownMask[x]` = bitmask of targets whose ancestry contains x; **dominator tree of the reversed DAG** (virtual root -> first-producer node of each target -> operands); `domSize[v]` = size of v's dominator subtree = exactly the nodes that disappear if v is removed.
- **Neighbourhoods:** (a) single node v: R = dominator subtree of v (need domSize >= 2, or >= 5 in deep phase; equal-cost rounds allow >= 1); (b) **target groups**: for every distinct ownMask m with popcount 2..4, R = all nodes whose ownMask is a subset of m; Q = the targets of m that are themselves only owned within m. Ranked by |R| (or |R|/|Q|) + random jitter, shuffled then stable-sorted.
- **`tryMove`:** budget = |R| - 1 (or |R| when accepting equal); pool = nodes not in R and not descendants of Q; rebuild each q in Q in order with `find(T, maxc)`; newly created values (and the rebuilt q) are added to the pool for subsequent q's (sharing within the move). For |Q|>1 also try reversed order. Build new DAG (dedupe by value, topo sort, cycle check), accept if count < old (or == with probability `eq=0.3` when stalled), then `fixPressure` (topological re-sort by pos; if register pressure > 48 use greedy list scheduling).
- **`find(T, maxc)` (exact shallow synthesis over pool):** F1 = all one-op values over pool (hash). cost 0: T in pool; cost 1: T in F1; cost 2: T = u op x, u in F1, x in pool (via inverses of T w.r.t. x); cost 3a: T = u1 op u2 both in F1; cost 3b: T = (u op y) op x; special w = u+u, u*u. **Depth 4 (`--deep 1`)**: stream F2 = F1 op pool[0..K) (pool sorted by usage) against a hash of needed values: kind0 need = inv(T,u), u in F1 (T = w op u, w in F2); kind1 need = inv(inv(T,x),y) (T = ((w op y) op x)).
- **`helperMove`** (when no cut move works): for each target k with >= 2 privately-owned nodes, for each pool x, invert T w.r.t. x to w1; if w1 in F1 -> candidate helper h=w1 (cost 1); if rsT >= 3, invert again w.r.t. y in first K pool values -> helper h in F1 at cost 2. Group candidates by h; require >= 2 targets, exclude targets that privately own a parent of h; gain = sum(rsT - cost) - 1. Try top 12: remove the private sets of all used targets, insert h + the 1-2 steps per target.
- **Schedule:** phase 0 depth<=3; on stall (>40 equal moves or no move) restore best and go to phase 1 (depth 4, larger neighbourhoods, minRs 5); any strict improvement returns to phase 0. Per puzzle `--time 6` s in the campaign.

### 7b. `poolc.cpp` - "planted-pool recovery" constructor (from scratch)
- Grow a pool K (starts first). F1 = one op over K. Index R1 entries: for every live target t and every k in K, key u with t = u op k (u = t-k, t+k, k-t, t/k, t*k, k/t).
- Each step: if some target is already one op away, take it (free covers). Otherwise **add the hidden value h in F1 \ K that has the most live targets keyed to it** (h would make them one op away) - a "most-covering hub" greedy (with randomized weights W, JIT, PSKIP, EA, EB, HUB; `hits2` counts targets two ops away). If none: **collision hub** (value not in K or F1 that is a virtual parent of >= 2 targets, built recursively by the split encoder), else **two helpers** t = f op g with f,g in F1 (3 ops), else **split encoder**: x = q*B +/- r or B +/- r with B in K or F1 (recursive), halving fallback.
- Smallest live target first; multiple randomized runs (`runs=16` in campaign, 6 s). Emit: prune to ancestors of first producers, schedule each node just before its first user (as late as possible), Belady allocation with rematerialization.
- Designed and validated on a **simulator with planted hidden programs** ("our simulator gives it instances with known hidden programs").

### 7c. `relink.py` / `relink2.py` - hub link rewrites (post-optimizer)
- relink: for each target T and each earlier value P (hub or target), try T = P*m +/- r, (P +/- r)*m, P +/- r, P*m, (P*m +/- r)/q, with constants m, r costing 0 (available), 1 or 2 ops (`const_plan` via cost-1 table); accept if cheaper than T's private ancestry; re-allocate by liveness; iterate to 200.
- relink2: private sets from the **dominator tree**; any node (target or hidden hub) v > 64 whose dominated private ancestry costs more than a derivation from an earlier *linked* big value P (|v - m*P| < 2^20 for m in {floor, floor+1}, or v*q close to multiple of P for q <= 8, or P - v < 2^20, or P/q close to v for q <= 64) is rebuilt; up to 300 iterations; best gain first.

**Limitations:** 4-target cap on group neighbourhoods (64-bit masks), depth <= 4 synthesis, helper moves limited to 1-2 op helpers.

---

## 8. elves-don-t-branch-meet-in-the-middle-greedy (from-scratch numba solver; score not printed)

**Purpose:** a clean from-scratch baseline (35-45 min on 4 CPUs). Far from frontier (no score in saved outputs); useful only as a clean MITM reference.
- **Forward table:** all values reachable from the current pool with cost <= jmax ops, built level by level (level j = pairs (i, j-1-i)); plus 2x and x^2 of the previous level at +1. Budgets: `PAIRBUDGET=3e6` pairs per level, `ENTBUDGET=1.5e6`, hard cap 2.6e6 entries, 2^22 hash.
- **Backward search:** `scan(t,k)`: t = z op w for w in table level i, z from 6 inverse forms; recursively up to k = jmax+2 => exact cheapest expression up to jmax+2 ops (tree cost, not DAG).
- **Greedy:** each round build the cheapest remaining target (iterative deepening over all targets); intermediates join the pool (CAP=100 logical values, LRU eviction non-targets first, biggest first).
- **Big targets:** decompose `t = A*B +/- C` (A, B table values, two-pointer over sorted level, C exact or estimated by `E0 + (log2 C - 20)/RBITS`, E0=4, RBITS=4) or `t = y*x +/- r` / `t = x + B` with recursion on the unresolved part.
- **Registers:** liveness linear scan; if > 48 live, shrink CAP by 15% and retry.
- Its own "ideas to go further": joint search across targets (shared hidden intermediates), final re-solve pass, deeper exact search (6-7 ops) for A*B +/- C.

---

## 9. santa-2026-deterministic-atlas-solver (pablodiegoo; 6,292-line C++20 integrating most public ideas)

**Purpose:** deterministic (SplitMix64 seeded by puzzle_id*1009+trial, no wall-clock cutoffs) solver with two modes. Outputs stripped (no score). Companion dataset "Puzzle Structure Atlas": **49.5% of the 26,898 non-start targets derive from earlier targets via small offsets, exact multiples or shared GCDs**; 242 `independent` puzzles have larger seeds and tighter limits; families shared/independent/mixed/multiplicative/tiny.

**Mode 1 (from scratch):** exact tiny BFS (<=15,000 nodes) -> backward quotient-remainder beam DAG solver (Tony Li style) + cost-aware allocation -> "RealMachineSolver" (register-level MITM, stride 23) fallback -> helper elision, window/cut passes, scaffold exchange.

**Mode 2 (`--optimize` over banks), per puzzle:**
- Select diverse donor contexts: best + up to 3 diverse traces within best+2; up to 4 distinct DAGs.
- Pass 1 lowering: linear-scan zero-spill allocator (retiring sources overwritten immediately); "Mizero-style" cost-aware spill-and-rebuild allocator; live-frontier start-index sweep; **24 random target orderings + 24 jittered pressure schedules**.
- Pass 2a: O(1)-refcount acyclic 1/2-op peephole; 2-helper single-node rewrite v = h1 op h2; 2a-bis shared-helper introduction (1 new helper rewiring 2 active nodes); 2b **Pollard-Rho divisor cuts** (factor T +/- d over starts + small constants <= 32, budget >= 4); Pass 4 root-only Pollard-Rho factor_offsets (<= 48 live values).
- **Pass 2c square-peeling chain resynthesis** (3 rounds): for each node v with private cone budget >= 3: try v (or a value u on a backward chain from v) = r*r with r = isqrt exact, r reachable free/1-op; r = r2*r2; r via one inverse step from free c; two backward steps from r; plus 3-op and bounded 4-op linear chains. Free values sorted by (leaf of the cone, refs).
- Pass 2d dependency reversal (build consumer w directly, recover predecessor u from w in one op).
- Pass 2e cross-trace multi-donor hypergraph recombination + fresh helper promotion.
- Pass 3 helper elision + 1/2-goal 1..3-step sliding windows & single-use expression-tree cuts (chained 3-step with intermediate squaring/doubling).
- **Pass 5 complete fan-out scaffold exchange:** for a cut with K roots (fan-out of one scaffold value), roots directly one op from atoms are "ready"; otherwise for each atom x invert root -> y; group by y into **bundles** (one stem helper y = forward op of atoms, shared by several roots); **exact subset bitmask DP** over 2^K root subsets for the minimum number of bundles + "1-remaining-root 2-step closure"; then forward multi-output beam and bounded set-based backward search over unresolved value sets.
- Pass 4 bounded single-target removal + reverse quotient-remainder search (150 expansions). Final cleanup only if anything improved.

**Limitations:** all moves are the same families as notebooks 2/3/6 (cut-local, 1-2 new levels); deterministic but no score evidence.

---

## 10. santa-2026-icefire-strong-start (romanrozen; V60 used as baseline by notebook 1; ~137,722 at v56)

**Purpose:** best-of over all attached banks + **CP-SAT recombination of equal-length programs** + register re-allocation.
- **Pool:** values of all programs with length == best length (up to `MAX_PROGRAMS=8`), plus starts. Recipes = every pair identity among pool values producing a pool value (+, -, *, /, and 1 = a/a).
- **CP-SAT model:** bool x[v] per non-start value, bool y per recipe, int level[v] in [0, n]; y => x[operands], y => level[v] >= level[u]+1; x[v] => OR(y of v); targets forced. **Objective `1000*sum x + sum penalty`**, penalty 1 per non-original recipe, 3 if the recipe uses an operand that appeared later in the original order (keeps register lifetimes short). Hints = original solution and order. 1 worker, seed 0, `max_deterministic_time=5.0`.
- **Compile:** prune to needed; schedule by original position with optional **pull-JIT** (an operand is pulled to just before its first consumer: prio = min(hint_pos, min(consumer prio) - 0.5)); emit recursively with Belady destination (farthest next use; never evict starts; soft-protect current operands), rebuild evicted values on demand. Try pull False/True; accept only strictly shorter + replay.
- Reports "plans shorter by X values; Y survive register allocation" => **allocation loses some plan gains** (numbers not in saved output).
- **Anatomy:** on large puzzles (>= 28 targets, max >= 1e13) the first 5 targets cost much more than later ones; later targets ~ near the ~5-op ceiling of a random 50-bit target from a well-stocked register file => "the start of a program is where a new idea pays most".

---

## Cross-notebook synthesis: what the public move set is

Every engine above is one of these move types. If our stack has all of them, more of the same will not close the gap:

| move family | where | our coverage (per brief) |
|---|---|---|
| private-cone / dominator cut, rebuild root with <= 2-4 new ops from survivors (no descendants) | 2,3,6,7,9 | yes (LNS drop 1-4 + exact <=5-step MITM) |
| target-group cuts (2-4 targets' joint private sets) | 6 (pairs+12 triples), 7 (ownMask popcount 2-4), 2 (4-8 outputs), 4 (pair ruin) | yes |
| 1-op fresh helper shared by >= 2 consumers (helper produced by >= 2 source pairs = "bridge") | 1,3,6,7,9 | partly? check our LNS can *insert* a helper that serves 2+ targets |
| affine/cofactor forms T = f*q +/- r, T +/- d factored (prime trial division / Pollard-Rho), nearest-product | 2,6,9 | yes (MITM/beam) |
| re-rooting / dependency reversal (build descendant, recover ancestor by inverse op) | 2,5,6,9 | unclear |
| square peeling (u = r^2) | 9 | probably covered by MITM |
| recombination MILP/CP-SAT over pooled equal-length variants (+ bridges) | 1,3,10 | yes |
| windows of 1-2 live outputs, 1-3 steps | 2,9 | yes |
| register re-allocation (Belady + rematerialization, pull-JIT, 24-48 schedules) | all | yes |
| from-scratch backward q/r beam + palette + small-leaves-first | 2,4,8,9 | yes |

All authors report ~0 on the merged frontier: Atakan V30 -7/1000 puzzles, residual-cut -1, Luna -19, Rudolph's whole list of nulls. Rudolph states it outright: public programs are locally optimal for every neighbourhood tried. The leader (~5-8k below public) uses "a different construction". The practice file's `lower_bound` is just the target count (checked: sum lower_bound = sum targets per family), so it reveals nothing about the generator.

## Ideas not yet exploited / combinable (ranked by expected savings)

1. **Hidden-hub recovery as a global reconstruction, scored by real compiled length. Expected: large (several thousand on the ~300 big-slack puzzles).**
   - Evidence: Rudolph's oracle. Given only the best program's hubs (values >= 2^14, read 3+ times), their weak solver cut 16 cracked puzzles from 2,900 to 2,330 (-20%). Hubs are about 18 bits (p10-p90 15-20). Targets fit T = q*h + r with q at 16/23/35 bits and |r| at 3/10/14 bits. Half of the slack sits in 300 puzzles, and slack grows with target size (~38 to ~167 instructions per puzzle).
   - Why the public attempt failed: they forced the top 6/12 candidates *by support count*, and wrong forced hubs cost instructions. Nobody **enumerated all h in [2^14, 2^22] and scored candidate hub *sets* by actually re-solving the puzzle** with the hubs pre-seeded (a cheap greedy/beam solve per candidate, then the full pipeline on the best).
   - A random h hits |T mod h| < 2^10 with probability ~2^-7 per target. With ~30 targets, needing >= 5-6 hits leaves fewer than one false positive over 2M candidates, so detection is statistically cheap. Rudolph dismissed lattice ACD after looking at the per-target gap (r ~10 bits vs h ~18 bits). But multi-sample simultaneous Diophantine approximation with t ~30 needs roughly gamma/t + rho < eta, i.e. 41/30 + 10 < 18, which holds.
   - Also try **nested/mixed-radix hubs** (q_i = q2_i*h2 + r2_i: the per-target quotients may themselves share a second hub) and hubs that are products/near-squares of small values.
   - None of the 10 notebooks covers this move: "choose a hub set, then rebuild every target around it, from scratch."
2. **Prelude / constant-palette co-optimization (multiple-constant-multiplication view). Expected: medium (hundreds to ~1-2k).**
   - The first target costs ~3x a later one, 12% of instructions come before the first target, and 27.6% of instructions build small constants < 2^16 (Rudolph, IceFire anatomy).
   - Every public method builds the prelude greedily, target by target. Locking a toolkit was tried and failed, because single-use constants keep chains short. The untried version: **fix the downstream "consumer demands" (which small constants and factors each later recipe needs), then solve the min-instruction DAG producing that demand set exactly** (Hcub/MCM, or exact ILP over the small-value lattice < 2^20), and splice. Our Hcub prototype is a planner. Point it at the *demand set extracted from the incumbent* instead of the targets.
3. **Non-monotone search: uphill acceptance + large ruin (5-10 targets or a whole hub family) rebuilt by the full solver. Expected: medium.**
   - Every public engine accepts only strictly shorter results. lns.cpp is the one exception: it accepts equal results with p=0.3, and Atakan has an unused "UPHILL_PAIR" flag. Nobody does simulated annealing or ILS over whole-DAG states.
   - Also use plateau walks to **manufacture diverse equal-length variants**. IceFire / residual-cut CP-SAT recombination only gains when the pool holds *different* equal-length DAGs, so our recombination MILP is limited by pool diversity, not by the solver.
4. **Deeper shared helpers: a 2-3-op helper chain feeding >= 3 targets, with savings priced exactly (dominator sets). Expected: small-medium.**
   - Public helpers are one op from existing values (2 ops in lns `helperMove`, which needs >= 2 targets; the paired helpers in notebook 1 apply only to the top 64).
   - Use the depth-4 streaming trick (F2 = F1 op pool[0..K) against a hash of needed inverse values) to find helpers h at depth 2-3 that put >= 3 targets within one op. Price them with dominator subtrees (lns.cpp) rather than footprint bitmasks.
5. **Pricing that is aware of register allocation. Expected: small but cheap.**
   - IceFire reports that CP-SAT plan gains are partly *lost in register allocation*. Atlas tries 24 random target orders + 24 jittered pressure schedules, and Rudolph saw a 26% blow-up with a poor allocator.
   - Check what fraction of our MILP/LNS plan gains die in our allocator, and add pull-JIT, dying-operand register reuse and rematerialization if they are missing.
6. **Cheap ports from these notebooks, in case our stack lacks them:**
   - (a) `factor_offsets`: factor T +/- d (prime trial division < 800 + leftover cofactor), with d an atom, and accept f*q when both are in the 1/2-step tables (Luna). It replaces the quadratic multiplicand search.
   - (b) **bridge values**: non-pool values produced by >= 2 distinct pairs of existing values, added as candidate nodes to the recombination MILP (residual-cut `bridges=160`; Luna exchange hypergraph with forbid-and-repair).
   - (c) **re-rooting**: rotate up to 4 inverse edges so a descendant becomes a free pivot, then rebuild it (Luna `reroot_jobs`, Atlas pass 2d, Atakan reverse bridges).
   - (d) **fan-out scaffold bundle DP**: exact set cover over 2^K roots of one scaffold by one-stem helpers (Atlas pass 5).
   - (e) **interface / numeric splice**: merge equal values across old and new branches by value at whole-program level (Atakan V30, the only V30 winner, -6).
   - Expected total for these: tens of instructions, consistent with what the authors measured.

**Explicit negatives to avoid re-running** (all measured ~0 on merged frontiers): ruin-and-recreate and pair ruin on the merge; prefix re-solve; A*B +/- C meet-in-the-middle; two-hub ext-Euclid links; cross-file target recombination (creates cycles); 2x2 target-grid bases; small-constant toolkit locking; joint 2-target shared-y recipes (0/32 survive splicing); start-divisibility rank bonus; product link f*Y +/- c; joint-interfaces / interface-relay / outside-alias engines (0 wins on 40 dev cases each); hub forcing by support count.
