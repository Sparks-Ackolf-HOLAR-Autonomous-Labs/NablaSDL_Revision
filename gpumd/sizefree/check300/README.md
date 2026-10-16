# 300 K size check at half driving force (follow-up to campaign-record entries 85-90)

Registered at campaign record seq 91 (`check300_design.json`, `PREREGISTERED_SHA256`),
pushed with all scripts before any run directory existed.

Why: the seq-85 size check failed at x = 0.85 because two of three 16x8x8 runs at
Fe = 2e-4 ran away, so all 300 K points were excluded from the law-level
decision (seq 90, factor 1.281). Here: 16x8x8 at Fe = 1e-4, four seeds at
x = 0.15 and 0.85, compared with the committed 8x8x8 points at Fe = 1e-4 and
2e-4. Rule in `check300_design.json`.

Placement: seeds 57001-2 on grn061 (granite sparks-gpu-grn, no sparks job on
the node at submission), seeds 57003-4 on notchpeak-gpu-guest. Three guest
tasks first landed on TITAN V GPUs (sm_70, not in the GPUMD build) and exited
via the guard with no output; resubmitted unchanged on A40s (16053456). The
x = 0.85 grn061 tasks were moved to guest A40s (16053475) to halve the wall
time; placement only.

Commit and analysis order:
1. finished run directories are copied from CHPC to a local staging folder
2. `python3 commit_check300.py C300` (refuses unfinished runs)
3. commit + push, then `python3 analyze_check300.py`
4. `python3 apply_check300.py`

## Result (collected 2026-10-04)

All 8 runs exit 0. Raw on the campaign record (seq 96) before analysis (seq 97);
registered decision `scope_limit` (seq 98).

| x | 16x8x8, Fe 1e-4 (passing runs) | 8x8x8, Fe 1e-4 | 8x8x8, Fe 2e-4 | G_size2 |
|---|---|---|---|---|
| 0.15 | 3.23 +/- 0.22 (2 of 4) | 1.95 +/- 0.22 | 2.52 +/- 0.35 | fail |
| 0.85 | 7.31 +/- 0.30 (3 of 4) | 5.72 +/- 0.53 | 5.57 +/- 0.71 | pass |

- Halving the driving force did not stop the runaway in the doubled box:
  3 of 8 runs reached 520 to 4540 W/mK (gates R3/R4). PrC1 fails.
- At x = 0.15 the passing doubled-box runs read 66% above the 8x8x8 value at
  the same driving force: at 300 K the 8x8x8 HNEMD value is not box-size
  free. PrC2 fails; PrC3 not evaluated.
- Decision (registered fail branch): the 300 K level of the law stays carried
  from the 700-1100 K factor (1.281) and is scope-labelled as such.

Post hoc, not registered: both compositions read higher in the longer box
(x = 0.15 by 66%, x = 0.85 by 28%), so the 300 K level from 8x8x8 boxes is
more likely low than high; long-wavelength phonons still matter at 300 K in
these alloys. Settling it needs boxes beyond 16x8x8 with a driving force low
enough to stay linear, which is a new design.
