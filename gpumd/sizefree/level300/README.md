# 300 K law level, size-free (follow-up to campaign-record entries 91, 96-98)

Registered at campaign record seq 99 (`level300_design.json`, `PREREGISTERED_SHA256`),
pushed with all scripts (build, commit, analysis, decision) before any run
directory existed. Run 2026-10-04.

Why: the 300 K check (campaign-record entries 98) failed because 16x8x8 at Fe = 1e-4 read 66%
above 8x8x8 at x = 0.15 and 3 of 8 runs grew exponentially (onset 1-3 ns of
5 ns). Here the box grows to 32 and 48 cells along the driving direction, the
force halves again (5e-5, linearity check at 2.5e-5), and seeds increase.

Stages
- **L1** (28 runs): x = 0.15 and 0.85; 16/32/48 x 8 x 8 at Fe = 5e-5
  (4/4/3 seeds) and 32x8x8 at Fe = 2.5e-5 (3 seeds). Gates G_lin and G_conv
  pick the box length Lstar by the registered rule.
- **L2-box<Lstar>** (12 runs): x = 0.2, 0.3, 0.5, 0.7 at Lstar, 3 seeds.
  `make_runs_level300.py` refuses to build any L2 stage other than the one
  the committed L1 analysis selected.

Decision rule (in the design): fail keeps the 300 K level carried from
700-1100 K; on pass, rho300 = kappa / law at six compositions gives
(a) strengthen, (b) a temperature-dependent level, or (c) downweight the
300 K composition shape.

Workflow (CHPC side root `~/mat_theory/gpumd_level300`)
1. `python3 make_runs_level300.py L1 --out DIR [--placement grn|guest]`, rsync to CHPC, `sbatch`
2. copy the finished runs from CHPC, then `python3 commit_level300.py L1`, commit + push
3. `python3 analyze_level300.py` (writes Lstar), commit + push
4. if Lstar: build/run/commit `L2-box<Lstar>` the same way, then re-run the analysis
5. `python3 apply_level300.py` records the analysis and the shard operation

## Execution log (2026-10-04)

- First submission 16054620 (all 28 on notchpeak guest A40s) cancelled while
  still pending: 731 guest GPU jobs queued and CHPC downtime starts
  2026-10-05 07:00 UTC. Placement only.
- L1 split: 12 runs (48x8x8 and the Fe = 2.5e-5 linearity runs) on grn061
  (granite 2111456; only a non-sparks guest job was on the node), 16 on guest
  A40s (16054626). Both failed in the job script before GPUMD started: the
  builder copied the array template from `check300` as source text and kept
  its escaped line continuation (`\\`), a bash syntax error. Fixed in
  `make_runs_level300.py` (build script only; design, runs and analysis
  unchanged); each run's `attempts` file records the failed start.
- Resubmitted: grn061 granite 2111476 (12 runs, one at a time) and the other
  16 on grn061 as granite 2111484 (dependency afterany:2111476) instead of
  the guest queue, so L1 ends before the downtime (about 13 h of H100 time,
  ending near 2026-10-05 00:30 UTC). Placement only.

## Result (2026-10-06)

- All 28 L1 runs finished on grn061 on 2026-10-04 (about 15 min each on the
  H100, before the CHPC downtime); committed at campaign record seq 100 before
  analysis.
- `analyze_level300.py` (seq 101): G_lin passes (x = 0.15: 4.60 vs 4.94 W/mK;
  x = 0.85: 9.05 vs 10.15 at Fe = 5e-5 vs 2.5e-5). G_conv cannot pass: at
  48x8x8, 2 of 3 runs ran away at x = 0.15 and 3 of 3 failed the drift gate
  at x = 0.85, so neither composition has the two passing runs a point needs.
  x = 0.15 still rises from 16 to 32 cells (2.60 to 4.60). No Lstar, so L2 was
  never built. PrL1-PrL3 all fail.
- `apply_level300.py` (seq 102): branch "fail", scope_limit; the 300 K level
  stays carried from 700-1100 K. P1 and P2 updated; verifier 52/52.
- Reading: in Tersoff SiGe at 300 K the longest cells admit long-wavelength
  modes that respond nonlinearly to the HNEMD driving force. Settling the
  room-temperature level needs an estimator that does not drive the heat
  current (equilibrium Green-Kubo in GPUMD, or spectral decomposition); not
  registered here.
