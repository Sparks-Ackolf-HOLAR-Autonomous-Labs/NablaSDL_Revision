# P1 head-to-head: pooled symbolic regression and multi-fidelity Bayesian optimisation against the shard-operation pipeline

Run 2026-09-30. Protocol `h2h_design.json` registered on the campaign record
(seq 63) before any baseline was fitted and before the held-out
first-principles grid existed. One change recorded (seq 66: the pipeline's
calibration interpolated in temperature so it can be scored at the
experimental temperatures). The 42 held-out almaBTE outputs (14 new
compositions x 3 temperatures, CHPC guest array 15922753) were hashed onto
the campaign record (seq 67) before `head_to_head.py` read them. Numbers:
`h2h_results.json`.

## The question

A group running an autonomous SiGe campaign holds evidence from seven
sources: machine-read literature, a curated database, two Tersoff MD
parties, a MACE MD party and almaBTE first-principles points. As first
ingested, this evidence contains three faults nobody planted: literature
rows for other materials (GeSn, Sn, BiSbTe), MACE values inflated 104x by a
unit slip, and pure-Si/Ge Tersoff points that never reach bulk behaviour.
Two standard ways to learn kappa(x, T) from it are compared with the
pipeline:

- **Pooled symbolic regression** (PySR 2.5): every row in one table.
- **Multi-fidelity Gaussian process** (linear autoregressive co-kriging):
  Tersoff MD, then MACE MD, then almaBTE as the target fidelity. This is
  the model inside multi-fidelity Bayesian optimisation. A variant adds
  literature plus database as a fourth, "experimental" level.
- **Symbolic regression on almaBTE only** (21 points): a careful group that
  already knows which source to trust.

Truth comes from sources no method was fitted on: 32 experimental bulk rows
from Starrydata (digitized, x <= 0.4) and the 14 new almaBTE compositions.

## Results

| Method | Error vs experimental bulk | Error vs held-out almaBTE | 1100 K pick (truth x = 0.40) | kappa rises or falls with T | Answers outside the validity range |
|---|---|---|---|---|---|
| Pipeline | 13% | 2% (5 points refused) | 0.45 (+0.5%) | falls (correct) | 0 |
| Multi-fidelity GP, as ingested | 13% | 7.5% | 0.50 (+2.3%) | falls | 6 |
| Multi-fidelity GP, after the pipeline's corrections | 8.5% | 8.2% | 0.40 (0%) | falls | 6 |
| Multi-fidelity GP with literature as top level | 56% | 62% | 0.55 (+2.4%) | falls | 6 |
| Pooled symbolic regression, as ingested | 70% | 76% | 0.50 (+2.3%) | no T dependence | 6 |
| Pooled symbolic regression, after corrections | 71% | 75% | 0.50 (+2.3%) | no T dependence | 6 |
| Symbolic regression on almaBTE only | 6.2% | 7.4% | 0.45 (+0.5%) | falls | 6 |

Percentages in the pick column are the extra kappa of the chosen
composition over the true minimum at 1100 K. "Errors" are median absolute
percentage errors. The experimental rows are total kappa of doped samples
(the electronic part adds up to about 1 W/mK), a floor shared by all
methods.

**Faults flagged** (a fault counts as flagged if a 3-MAD residual screen
marks at least half of its rows; the pipeline's flags are campaign-record entries):

| Fault | Pipeline | Pooled SR | Multi-fidelity GP |
|---|---|---|---|
| Other-material literature rows | yes (seq 20, named cause) | 1 of 3 usable rows | not in its data |
| MACE unit slip (x104) | yes (seq 1, named cause) | yes, 2 of 2 as outliers, no cause | no: absorbed into the level correlation |
| Ballistic pure-element MD rows | yes (seq 0, scope-limited) | 1 of 3 | no (0 of 6) |

**Acquisition replay** (find the 1100 K minimum by buying almaBTE points,
starting from the 18 points of party 4a; one point costs 28 CPU-minutes):

| Strategy | Points bought | Pick after buying | Stops by itself |
|---|---|---|---|
| Pipeline (what the campaign did) | 1 (x = 0.7) | 0.505, i.e. 0.50 on the grid (+2.3%) | yes, by the registered rule |
| Multi-fidelity BO, as ingested | 10 (budget) | wanders between 0.40 and 0.65; 0.40 after the 10th | no: the expected-improvement stop never fires |
| Multi-fidelity BO, corrected MACE rows | 10 (budget) | 0.40 before buying anything; later drifts to 0.50 | no |
| Random buying | median 8 to reach within 0.05 | | |

## Predictions (registered)

- H1 pooled SR error at least twice the pipeline's: **holds** (70% vs 13%).
- H2 pooled SR gets the temperature trend wrong: **holds** (it returns a
  law with no temperature term).
- H3 neither baseline flags the unit slip: **fails**. The pooled fit's
  residual screen flags both MACE rows (they sit 4.6 in ln kappa off);
  it cannot say why. The multi-fidelity GP does not flag them.
- H4 the multi-fidelity GP matches the pipeline's 1100 K pick within 0.05:
  **holds** (0.50 vs 0.45), with 3.7x the pipeline's error on the held-out
  first-principles grid.
- H5 multi-fidelity BO needs more than one purchase to get within 0.05 of
  the truth: **fails**. It gets there after one purchase, but does not
  stop and moves off again.

## What this says for materials discovery

1. **The composition decision is easy; the numbers around it are not.**
   The 1100 K bowl is flat: every x from 0.30 to 0.60 is within 8% of the
   minimum. Every method except the experimental-target GP picks within
   2.4% of the best kappa. A designer is misled not by the pick but by
   the level (pooled SR is 4x too low) and by the temperature trend
   (pooled SR has none), which set the zT estimate and the leg design.
2. **Pooling does not fix itself with cleaning.** Removing the three
   faults changes pooled SR by one percentage point. The 226 Tersoff rows
   carry a factor-3 alloy bias and outvote everything else. Cleaning
   matters only for a method that also knows which source sets the scale.
3. **A multi-fidelity GP is a strong baseline, and the pipeline does not
   beat it on accuracy against experiment.** Anchored on almaBTE, it
   matches the pipeline on the experimental rows (13%) and beats it after
   the pipeline's corrections are applied to its input (8.5%). Symbolic
   regression on almaBTE alone does best (6.2%). On the held-out
   first-principles grid the pipeline is best (2%), partly because it
   refuses the five points outside its validity range.
4. **What only the pipeline produces.** (a) The knowledge that almaBTE,
   not Tersoff or the literature, should set the scale: the baselines that
   do well are given this as an input; the pipeline measured it (the
   3.3x Tersoff alloy bias, the 36% of literature rows needing correction).
   (b) Refusal: 0 answers outside the validated range against 6 for every
   baseline, including kappa at x = 0.95 and 1100 K, above 0.85 of the
   solidus. (c) Named causes: the GP silently turned a 104x unit error
   into a correlation parameter (0.86 instead of 1.92), and still
   predicted well, so no downstream check would have noticed.
   (d) A stopping decision: multi-fidelity BO bought ten first-principles
   points (280 CPU-minutes) and was still moving; the pipeline bought one
   because its registered question was which of two calibrations to
   trust, not where the minimum is.
5. **Limit of this comparison.** The pipeline's answer was built over many
   iterations with human review of every operation; the baselines ran once,
   untuned. On a well-charted system with one good first-principles source,
   that source alone gets most of the way. The pipeline's value should be
   larger where no single source covers the question (the SiGeC grain-size
   and SiC-size axes, which almaBTE cannot represent alone); that is not
   tested here.
