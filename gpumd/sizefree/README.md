# Box-size-free Tersoff kappa across composition and temperature (GPUMD HNEMD)

Run 2026-10-02 on CHPC: grn061 (granite `sparks-gpu-grn`), or guest
partitions when many jobs were queued.

**Question.** P1's kappa(x, T) law is a two-stage rNEMD fit; its
infinite-box level comes from a 1/L extrapolation over 130-800 A boxes.
The single size-free HNEMD value so far (x = 0.5, 300 K, 2.23 W/mK,
campaign record seq 8) is 41% above the law (1.58). Is the law level a lower bound
everywhere, and how large is the Tersoff alloy bias against BTE-DFT
across x and T?

**Design** (`sizefree_design.json`, sha256 `c8ac408d...05cb`, campaign record seq
85, pushed in `9287612` before any run directory existed, together with
`commit_sizefree.py` and `analyze_sizefree.py`):

- x in {0.15, 0.2, 0.3, 0.5, 0.7, 0.85} x T in {300, 700, 1100} K, three
  alloy configurations each, 8x8x8 cells (4096 atoms), Fe = 2e-4 1/A,
  5 ns production (protocol of `gpumd/production`);
- checks at 300 K, x = 0.15 and 0.85: linearity (Fe = 1e-4) and size
  (16x8x8);
- decision rule on rho = kappa_HNEMD / kappa_law: strengthen / correct
  the level / replace the level by an HG-SR v2 refit / downweight;
- predictions Pr1-Pr7 (in the design file).

**Execution.**

| stage | runs | where | job |
|---|---|---|---|
| H1-300K (main + checks) | 30 | tasks 0-14 on granite `sparks-gpu-grn`, grn061 (H100 NVL), one at a time (grn061 had no sparks job at submission, only another user's guest job); tasks 15-29 moved, still pending, to notchpeak-gpu-guest to halve the wall time | 2099531, 16005930 |
| H2-highT | 36 | notchpeak-gpu-guest: task 5 in 16005841; the other 35 resubmitted as 16005929 after broken GPUs (campaign record seq 86) | 16005841, 16005929 |

Speed on the H100: about 15 min per 5 ns run (about 4 h for its 15 runs).

**Commit and analysis order.**

1. finished run directories are copied from CHPC to a local staging folder (`~/mat_theory_sizefree_stage/`, not the repo)
2. `python3 commit_sizefree.py H1-300K` and `... H2-highT` once each stage is finished (raw copied into `raw/`, hashed onto the campaign record before analysis)
3. commit + push, then `python3 analyze_sizefree.py`
4. campaign-record entry for the decision branch.

## Results (collected 2026-10-04)

All 66 runs finished (exit 0): 15 on grn061 (H100 NVL), 51 on notchpeak
guest GPUs (A6000, A40, A5500, L40S, A800, RTX 6000 Ada). Raw outputs
hashed onto the campaign record before analysis (seq 87 H1-300K, seq 88
H2-highT); analysis `analysis_sizefree.json` recorded at seq 89; decision
at seq 90 (`apply_sizefree_decision.py`, `corrected_law.json`).

**Checks.** Linearity passed at x = 0.15 and 0.85. The size check passed
at x = 0.15 but failed at x = 0.85: two of the six 16x8x8 runs ran away
(kappa 4449 and 2775 W/mK, the same nonlinear-runaway failure seen in
the GPUMD bring-up, `../BRINGUP.md`), leaving one passing run at x = 0.85. By the registered rule
the 300 K points are reported but excluded from the decision.

**Run gates.** 11 of 66 runs fail R3 (positive drift z >= 3); x = 0.7,
700 K is left with one passing run and has no point estimate.

| x | 300 K | 700 K | 1100 K |
|---|---|---|---|
| 0.15 | 2.52 +/- 0.35 (rho 1.19) | 2.23 +/- 0.14 (1.12) | 2.28 +/- 0.13 (1.23) |
| 0.2 | 2.22 +/- 0.17 (1.17) | 2.35 +/- 0.12 (1.32) | 2.49 +/- 0.29 (1.48) |
| 0.3 | 2.08 +/- 0.11 (1.26) | 1.77 +/- 0.12 (1.13) | 1.80 +/- 0.13 (1.21) |
| 0.5 | 2.14 +/- 0.08 (1.35) | 1.87 +/- 0.14 (1.24) | 2.13 +/- 0.14 (1.49) |
| 0.7 | 3.51 +/- 0.60 (1.68) | (one passing run) | 2.88 +/- 0.15 (1.57) |
| 0.85 | 5.57 +/- 0.71 (1.36) | 5.61 +/- 0.26 (1.56) | 4.89 +/- 0.20 (out of domain) |

kappa in W/mK (seed mean +/- SE); rho = kappa_HNEMD / kappa_law.

**Decision (pre-registered, seq 90): correct the level.** Ten in-domain
high-T points, median rho 1.281, CV 0.130 (<= 0.15). The law's shape is
kept and its level multiplied by 1.281: kappa(0.5, 300 K) = 2.02 W/mK.
Scope label: "level from HNEMD, shape from rNEMD".

**Predictions.** Pr1 (rho at 0.5/300 K in [1.2, 1.6]: 1.35), Pr2, Pr3
(minimum at x = 0.3 to 0.5 at every T), Pr5 (BTE/HNEMD at 0.5/300 K =
3.04), Pr6 hold. Pr4 fails (at x = 0.2 kappa(1100 K) > kappa(300 K):
Tersoff alloy kappa is flatter in T than predicted). Pr7 fails (size
check at x = 0.85, runaway runs).

**Tersoff vs BTE-DFT, size-free.** BTE / HNEMD = 3.0-3.3 at 300 K
(x <= 0.5), 2.0-2.5 at 1100 K; median 2.5 over 13 in-domain points.
The alloy bias shrinks with temperature. Against the corrected law the
P1 factors become median 2.6 (range 1.7-3.2) vs BTE and 1.6 vs the
experimental compilation.

**Open.** The 300 K level rests on the high-T correction; a 300 K size
check at Fe = 1e-4 (no runaway in the 8x8x8 linearity runs) would close
it. Possible follow-up, not registered.
