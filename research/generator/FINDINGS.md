# Generator reverse-engineering (research/generator/)

Scripts here: overview.py (per-puzzle sizes), limratio.py, indep.py, mixsplit.py, hubs.py (statistical hub scan),
smooth.py (smooth-offset factorization, too noisy - kept as negative result), show.py/hubres.py/fac.py (inspection).

## 1. value_limit
- limit / max(target) in [1.0, 4.0] for every non-tiny family (median: indep 1.37, mixed 2.20, shared 2.19, mult 2.53),
  with a cap just below 1e18 (59.79 bits). Looks like L = min(~1e18, maxT * U(1,4)). Carries no hidden-value info.

## 2. Independent (45 practice; scored = max start >= 100, 242 puzzles)
- Targets are i.i.d. uniform in one decade [10^(D-1), 10^D): hard tier D in {12, 15, 18} (28-32 targets),
  medium D in {6, 9, 12}. Pooled KS test vs uniform-in-decade over 45 practice puzzles: D=0.018, p=0.76.
  All 242 scored independent puzzles: 100% of targets inside their decade; decades (6:8, 9:12, 12:88, 15:74, 18:60).
- Starts: 1-8 random integers in ~[18, 1973] (structured families: starts <= 34).
- Nothing to decode: no hidden values. Generator-aware cost = current search problem.

## 3. Mixed (48 practice)
- Every mixed puzzle = ~half "independent" targets (14-18 of 28-32, uniform in one decade 10^(D-1)..10^D, D in 12/15/18;
  medium tier: D=6/9) + ~13-16 structured targets below (and occasionally 1 above) that decade.
- The structured part behaves like the shared family (affine chains, clusters); see section 5.

## 4. Family classifier (classify.py -> scored_family.csv)
- Rules: independent = max start >= 100 (or span < 3.4 bits); mixed = >= 38% of targets in one decade 10^(d-1)..10^d
  (d in 6/9/12/15/18) with >= 25% below it; else multiplicative if median target < 2^27.5, else shared.
- Practice accuracy 92.5% (indep 45/45, mult 40/40, mixed 43/48, shared 41/51 - small shared puzzles look multiplicative).
- Scored (predicted): independent 248 puzzles 47,434 instr 6.92/target; mixed 198, 35,203, 6.11/t;
  multiplicative 287, 22,839, 3.42/t; shared 251, 31,226, 4.13/t; tiny 16, 57.

## 5. Shared structure (manual decode, practice_0015 and scored_0938)
- practice_0015 (starts 16,30): hidden atoms A=13051 (=31*421), B=7507, C=163451 (=79*2069), D=142409 (=17*8377), 509...
  T13 = 248000*A*B - 2, T14 = 248000*A*B + 151 (same base, two offsets), T18 = 560000*A*B + 1, T5 = 1600*A^2 - 140,
  T22 = 162880*A*D exact, T19 = T22/4 + 244320. Multipliers are smooth-ish numbers built from the starts
  (248000 = 2^6 5^3 31, 560000 = 2^7 5^4 7, 1600 = 40^2).
- scored_0938 (starts 5,13,24,29,30): atoms X=124780, Y=618523, Z=717923(?), W=54432; ALL 32 targets fit k*M + c with
  M = product of 2 atoms (one deg-3), k in {1,4,5,8,9,16,18,24,29,30,120,145,195,240,243,484,486,1216,29160,...}
  (products of start-derived small numbers), |c| <= 2411; clusters share (M,k) with several offsets
  (X*Y + {152, 481}, X*W + {-95, 5, 121}, 29*Y*W + {-1153, 7}).
- Generator hypothesis (shared): ~4-6 hidden atoms of 17-21 bits; each target = k * (atom monomial, deg 1-3, mostly 2)
  + c, k a small smooth multiplier (<= ~2^15, sometimes up to 2^20), |c| <= ~2500; ~15-25% of targets are in clusters
  sharing k*M; some nested m2*(m1*M + c1) + c2 / target-to-target affine links (T25 = 5*T24 + 150).
- Atoms are NOT short formulas of the starts: an exhaustive tree search (treesize.py, <= 5 ops) reaches 0 extra targets
  vs random controls of equal size; atoms look like random 17-21 bit integers (several are prime).

## 6. Multiplicative structure
- No shared large factors between targets (pairwise gcd after removing primes <= 13: 0-4 pairs per puzzle),
  almost no pairwise affine relations (pairs.py: 0-4 linked targets per puzzle vs 10-28 in shared).
- Targets are smoother than random (largest prime factor <= t^0.33: 10.7% vs 4.2% control; shared 12.4% vs 4.2%).
- Frontier example scored_0022: hidden atoms are SMALL (805, 146, 1174, 2349, 3590, 3718; 8-12 bits); targets =
  products of 2-5 such atoms + small offset (T6 = 3590^2 - 2340, T8 = 3590*3718 + 25, T30 = 3590*3718*2344*146*587).
  Atoms this small are invisible to the hub scan (random residue hits), so multiplicative is the hardest to decode.

## 7. Decoder validation (decoder.py, scored_decode.py, clean_stats.py, fp_check.py)
- decoder.decode(pz, atoms) explains a target as L1 k*M+c (|c|<=4096), L2 m2*(m1*M+c1)+c2, or AFF t = m*u+c
  (u = earlier target, |c|<=2^16, >=12 bits significance). Atoms come from hubs.hubs() (statistical hub scan) and/or
  decoder.prog_atoms() (values 2^12..2^26 of best/<id>.json that leave a residue < 2^12 on >= 3 targets).
- FALSE POSITIVES: on 40 scored independent puzzles with frontier atoms, 33% of targets were "explained"
  (L2 19%, L1 with a single atom 14%). Frontier programs build values next to targets, so deg-1 and L2 matches are
  noise. Only L1 with deg>=2 monomials and AFF links are clean (independent: 0.7%).
- Clean explained fraction (scored, frontier atoms): shared 29.9% (2,256/7,553; deg2 1,564, deg3 54, AFF 638;
  181 targets in clusters sharing k*M), mixed 7.4% (mostly AFF chains: 344), multiplicative 4.0%, independent 0.7%.
  Shared k: p10/p50/p90 = 4 / 70 / 31,296; |c| p50/p90/p99 = 145 / 2,016 / 3,839.
- Hub scan on practice (slow: ~40 s/puzzle on this loaded machine; the background run over 46 practice puzzles died
  with the shell job, so these are spot checks only): practice_0015 shared 18/31, practice_0004 shared 15/29,
  practice_0005 independent 0/32 (no hub above surprise 8), practice_0001 multiplicative 7/30, practice_0003 mixed 2/31.

## 8. Cost estimate vs frontier
- estimate_len2 (atoms ceil(bits/7)+1, monomials deg-1, one op per distinct k*M, +1 per offset, 0.5-1 per distinct
  small constant, unexplained bits/7+1) vs best/ sums, all scored puzzles of the class:
  shared 36,841-41,254 vs 30,737 frontier; mixed 39,451-42,211 vs 35,181; multiplicative 30,218-31,659 vs 22,722.
  Only 5 / 14 / 3 puzzles get a lower estimate (total gain on paper: 114). Conclusion: a naive "decode then build" comes out
  15-30% WORSE than the frontier. The frontier already builds the atoms and shares multipliers and offsets better than
  per-target k/c. Decoded structure alone does not explain the leaders' ~6% edge. If there is a lever, it is choosing
  the small-constant pool (the k's and c's) jointly; the decoder exposes the per-target k and c lists but does not optimise them.
