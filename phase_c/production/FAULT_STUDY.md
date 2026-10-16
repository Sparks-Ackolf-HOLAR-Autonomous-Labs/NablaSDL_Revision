# Phase C production fault study (paper 1)

Run 2026-09-28. Everything below ran in this order,
each step on the campaign record (`../ledger_campaign.jsonl`) and pushed
to git before the next:

| seq | entry | what it fixed in place |
|---|---|---|
| 3 | preregistration | production design: the committed coverage seed batch (40 points, sha `20608f42...`) pinned with ncxy = 4 and swapn = 50, plus four physics probes with ground truth written up front (`production_design.json`) |
| 4 | commitment | the blind fault catalog (`fault_catalog/`), written by a separate agent that was barred from all detector code, committed **unread** |
| 5 | commitment | the detector (`detector.py`) frozen, thresholds set on the author's own synthetic null (about 1% per-campaign false fires), and the scoring rule stated in advance |
| 6 | deviation D1 | a crash fix (a subset law extrapolating to a negative resistivity), found on synthetic rows before any real row existed; no rule change |
| 9-13 | batch_result | Merkle roots of the five submission batches, appended before the detector read a single real row |

## The campaign

CHPC array 15878628, notchpeak-guest / owner-guest, 132 Muller-Plathe
rNEMD runs (44 points x ncz 24/48/96, 16 ranks each, 6 to 34 min),
**all COMPLETED with zero requeues** (so the preemption erasure channel
reserved for paper 3 stayed closed this time). grn061 untouched.
Raw outputs: `results/` (json, log, profile per run); detector-facing
table: `results/production_rows.json`.

Structural check of the melt-quench probes (`results/structure_check.json`):
post-quench potential energy -3.89 eV/atom at 300 K against about -4.20
for the crystal, so the quench did amorphize.

## Result 1: the detector on the real, uncontaminated campaign

| What | Ground truth (seq 3) | Detector | Verdict |
|---|---|---|---|
| near-melting probes N0 (x 0.5, 1500 K), N1 (x 0.7, 1450 K) | method off-data, scope-limit | physics-guard scope-limit on all 6 runs | **correct** |
| amorphous probes N2 (x 0.5, 300 K), N3 (x 0.5, 700 K) | other phase, split | nothing | **missed**; they sit in the law as low-kappa alloy points and pull the x = 0.5 prediction down |
| Ge-rich dilute corner C37 (x 0.943, 866 K), C38 (x 0.932, 1180 K) | not a planted fault: the law form (x(1-x) plus x) cannot follow kappa rising toward the Ge endpoint | quarantine, no cause identified | reversible, but the right verb is scope-limit or a richer basis; a real law-form limit surfaced by the data |
| four ordinary runs | nothing wrong | forget as "exact duplicates" | **false fire**: kappa is printed to 3 decimals, so 132 real values collide by chance; the frozen duplicate key (kappa, ncz) was only ever tested on full-precision synthetic floats |

Two findings are worth stating in the paper as findings, not footnotes:

- **Amorphous SiGe under Tersoff is not size-independent.** Both the
  probe truth and the blind catalog (entry M02) assumed an amorphous
  phase shows no 1/L trend. The real runs say otherwise: kappa rises
  from 0.48 to 0.68 W/mK between ncz 24 and 96 at 300 K (b/a about 14,
  against 20 to 30 for the crystalline alloy), consistent with
  propagon transport in amorphous group-IV solids. The size-trend flag
  therefore cannot separate the phases, and nothing in (x, T, L, kappa)
  can: only structural metadata (energy per atom, RDF) exposes it. This
  is the same lesson the literature split taught (a kappa value without
  its microstructure is not a datapoint), now learned from our own
  simulations.
- **Synthetic-null calibration does not transfer.** Thresholds giving
  about 1% false fires on the author's synthetic null gave collateral
  operations in 100% of real NULL trials (table below), from exactly
  two causes that exist only in real data: printed-precision collisions
  and a law-form misfit in the dilute corner.

## Result 2: 750 randomized trials against the blind catalog

Trial seeds are the catalog's own pre-registered seeds (50 per entry,
50 NULL); each trial jitters every row by the catalog's replica scatter
and permutes row order. Scoring view A is the rule stated at seq 5
(detected = some operation touches an affected or added run; hit = every
operation on affected runs is in the right family; harmful = a
removal operation on a valid anomaly). The catalog author's own
acceptable/forbidden operator sets (view B) are in the JSON and agree
with A except where noted.

The first table is the frozen detector exactly as pre-registered. The
second is a clearly **post-hoc** sensitivity variant, disclosed on the
campaign record as deviation D2: the duplicate key becomes the design
coordinates (x, T, ncz, seed), and operations the detector already emits
on the clean campaign are not attributed to the injected fault
("baseline-adjusted"). The severity column is raw detection in both
tables.

#### Frozen detector (campaign record seq 5 + D1), pre-stated scoring A, raw

| id | entry | category | detected % | hit % | harmful % | miss % | other % | trials with collateral % | detection by severity Q1/Q2/Q3/Q4 |
|---|---|---|---|---|---|---|---|---|---|
| NULL | null campaign (no fault) | null | 0 | 100 | 0 | 0 | 0 | 100 | n/a |
| P01 | biased batch | planted-error | 92 | 52 | 0 | 8 | 40 | 86 | 0.71/1.00/1.00/1.00 |
| P02 | unit slip | planted-error | 100 | 64 | 0 | 0 | 36 | 80 | 1.00/1.00/1.00/1.00 |
| P03 | composition label swap | planted-error | 28 | 18 | 0 | 72 | 10 | 94 | 0.11/0.36/0.50/0.18 |
| P04 | species type swap (x -> 1-x) | planted-error | 40 | 18 | 0 | 60 | 22 | 88 | 0.47/0.60/0.17/0.25 |
| P05 | temperature label offset | planted-error | 78 | 48 | 0 | 22 | 30 | 74 | 0.73/0.67/0.92/0.79 |
| P06 | duplicated batch (double counting) | planted-error | 96 | 56 | 0 | 4 | 40 | 86 | 1.00/1.00/1.00/0.88 |
| P07 | unequilibrated long box | planted-error | 88 | 52 | 0 | 12 | 36 | 94 | 0.75/0.83/0.94/1.00 |
| P08 | party mislabel (MACE rows under CHPC-MD-C) | planted-error | 68 | 54 | 0 | 32 | 14 | 94 | 0.33/0.91/0.88/1.00 |
| M01 | near-solidus (premelting) regime | method-off-data | 20 | 0 | 0 | 80 | 20 | 100 | 0.11/0.08/0.31/0.27 |
| M02 | amorphous-phase contamination | method-off-data | 72 | 12 | 0 | 28 | 60 | 88 | 0.45/0.54/0.93/0.92 |
| M03 | dilute ballistic regime (1/L extrapolation invalid) | method-off-data | 44 | 20 | 0 | 56 | 24 | 98 | 0.00/0.20/0.64/1.00 |
| V01 | regime-localized extra scattering | valid-anomaly | 76 | 24 | 74 | 0 | 2 | 94 | 0.65/1.00/0.73/0.85 |
| V02 | high-T second scattering channel | valid-anomaly | 100 | 8 | 90 | 0 | 2 | 54 | 1.00/1.00/1.00/1.00 |
| V03 | composition asymmetry | valid-anomaly | 100 | 0 | 100 | 0 | 0 | 2 | 1.00/1.00/1.00/1.00 |

#### Post-hoc variant D2 (design-coordinate duplicate key), baseline-adjusted (clean-campaign fires not attributed)

| id | entry | category | detected % | hit % | harmful % | miss % | other % | trials with collateral % | detection by severity Q1/Q2/Q3/Q4 |
|---|---|---|---|---|---|---|---|---|---|
| NULL | null campaign (no fault) | null | 0 | 100 | 0 | 0 | 0 | 4 | n/a |
| P01 | biased batch | planted-error | 80 | 80 | 0 | 20 | 0 | 6 | 0.71/1.00/1.00/1.00 |
| P02 | unit slip | planted-error | 100 | 100 | 0 | 0 | 0 | 2 | 1.00/1.00/1.00/1.00 |
| P03 | composition label swap | planted-error | 16 | 12 | 0 | 84 | 4 | 8 | 0.22/0.29/0.40/0.12 |
| P04 | species type swap (x -> 1-x) | planted-error | 0 | 0 | 0 | 100 | 0 | 4 | 0.40/0.33/0.00/0.00 |
| P05 | temperature label offset | planted-error | 32 | 14 | 0 | 68 | 18 | 14 | 0.73/0.25/0.69/0.79 |
| P06 | duplicated batch (double counting) | planted-error | 90 | 50 | 0 | 10 | 40 | 12 | 1.00/1.00/0.93/0.75 |
| P07 | unequilibrated long box | planted-error | 56 | 56 | 0 | 44 | 0 | 4 | 0.75/0.83/0.94/1.00 |
| P08 | party mislabel (MACE rows under CHPC-MD-C) | planted-error | 56 | 54 | 0 | 44 | 2 | 10 | 0.33/0.82/0.88/1.00 |
| M01 | near-solidus (premelting) regime | method-off-data | 10 | 0 | 0 | 90 | 10 | 82 | 0.00/0.00/0.15/0.20 |
| M02 | amorphous-phase contamination | method-off-data | 38 | 0 | 0 | 62 | 38 | 10 | 0.09/0.23/0.93/0.83 |
| M03 | dilute ballistic regime (1/L extrapolation invalid) | method-off-data | 40 | 20 | 0 | 60 | 20 | 70 | 0.00/0.00/0.64/1.00 |
| V01 | regime-localized extra scattering | valid-anomaly | 46 | 54 | 44 | 0 | 2 | 60 | 0.53/0.80/0.33/0.46 |
| V02 | high-T second scattering channel | valid-anomaly | 18 | 82 | 0 | 0 | 18 | 0 | 1.00/1.00/1.00/1.00 |
| V03 | composition asymmetry | valid-anomaly | 0 | 100 | 0 | 0 | 0 | 0 | 1.00/1.00/1.00/1.00 |

## What the study says (for the paper and for the next detector)

1. **Gross bookkeeping and protocol errors are caught.** Biased batches
   (71% detection in the subtlest quartile, 100% above), unit slips
   (100% detected, but the cause is named, i.e. `correct`, in only 7 of
   50 D2 trials: the Muller-Plathe factor-2 slips the blind author
   drew are not in the detector's unit table, and batch residual
   scatter pushes the estimated power-of-ten factors outside the 3%
   tolerance, so the detector falls back to quarantine), duplicated batches
   (90 to 96%), unequilibrated long boxes (56 to 88%).
2. **Label errors that physics would expose are mostly invisible to
   statistics.** Composition swaps (12 to 28%), x to 1-x species swaps
   (0% baseline-adjusted), temperature offsets short of a Celsius slip
   (the alloy law is nearly flat in T). The blind author predicted
   exactly this ("physics" prior); the fix is physics-aware checks, not
   tighter thresholds.
3. **Method off-data below the melting line is missed.** The physics
   guard fires only at or above the solidus, which caught both real
   near-melting probes, but premelting rows at T/T_sol 0.86 to 0.975
   (M01) pass through (10 to 20%). The blind catalog treats
   T/T_sol >= 0.85 as outside Tersoff's trustworthy range; the detector
   drew the line at 1.0. Moving the guard is a one-line, physics-motivated
   change that belongs in the next pre-registered version, not in this
   one.
4. **Valid anomalies are the hard case, and they are exactly where the
   active loop has to earn its keep.** Under the frozen rule the
   detector harmed 74 to 100% of valid-anomaly trials, most of it
   inherited from the two baseline causes above. With those removed
   (D2, adjusted) broad anomalies are handled well (high-T channel 82%
   hit, composition asymmetry 100% hit), but a regime-localized extra
   scattering (V01) is still quarantined in 44% of trials. With two
   replicas per regime cell, a real localized anomaly and an isolated
   fault look the same to any statistic. Quarantine (reversible, rows
   kept) is the correct interim state under the two-bar rule; what
   separates the two is a new measurement at that regime, which is the
   shard action the active loop exists to buy. The fault study
   therefore measures the limit of detection-without-acquisition and
   motivates the acquisition step with a number.
5. **The NULL campaign is clean only after D2.** 4% of NULL trials
   carry any collateral operation under D2 adjusted, against 100% under
   the frozen detector on real rows.

## The alloy law this campaign supports (preliminary)

The detector's own fit (which still contains the undetected amorphous
probes) selects r = 1/kappa = 0.172 + 2.887 x(1-x) - 0.288 x, with no
temperature term by BIC. Excluding the four probes (truth-informed,
reported for reference only): r = 0.008 + 3.453 x(1-x) - 0.334 x +
0.354 t - 1.541 x(1-x) t (t = T/1000 K), giving kappa_inf = 1.44 W/mK at
x = 0.5 / 300 K. That sits below the Phase B value of 1.80 because the
production size series stops at ncz 96 (Phase B went to 144): the 1/L
extrapolation from shorter boxes under-reads, a documented method
bias to carry on the scope label, not to average away. Restricting to
0.1 <= x <= 0.9 gives a T-independent law (kappa_inf 1.48 at x = 0.5).
P1's final law needs the Ge-rich corner handled (scope-limit at
x > 0.9, or a basis term for the dilute limit) and the amorphous rows
split out; both are now ledger-ready operations.

## Reproduce

    python3 design_production.py && python3 preregister_production.py   # design + seq 3
    sbatch --array=0-131 sbatch_production.sh                         # on CHPC
    python3 build_rows.py                                              # rows + seq 9-13 (run outputs in results/)
    python3 detector.py results/production_rows.json                   # real campaign
    python3 fault_study.py results/production_rows.json 50             # frozen
    python3 fault_study.py results/production_rows.json 50 D2          # post-hoc variant
    python3 make_tables.py > tables.md

(numpy required: `~/mat_theory_pilot/venv/bin/python` on the DGX.)
