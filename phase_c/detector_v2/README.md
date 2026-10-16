# Detector v2: structure as a second observable (2026-10-01)

A pre-registered detector version that reads structure, following the
fault study (`../production/FAULT_STUDY.md`) and the bond-angle descriptor
(`../../bond_angles/`).

## Order on the campaign record

| seq | kind | what |
|---|---|---|
| 81 | preregistration | `design_v2.json` (sha `a5ad8487...`) with the hashes of `detector_v2.py`, `fault_study_v2.py`, `build_rows_v2.py`, `md/in.rebuild`, `md/run_rebuild.sh`; 7 predictions and the adopt/reject rule. Only a synthetic-descriptor crash test (`selftest_v2.py`) had run. Pushed before any rebuild. |
| 82 | batch_result | Merkle root of the 44 measured descriptor records, before detector v2 read them |
| 83 | deviation D3 | crash fix: a composition relabel from the implied-x grid could be negative; clipped to [0, 1]. No rule change. |
| 84 | commitment | registered rule met (Pr1-Pr5, Pr7): detector v2 adopted as the entry check for MD parties; Pr6 refuted |

`analyze_v2.py` and `apply_v2_decision.py` were pushed (commit `c7b3b22`)
before the descriptors existed.

## What v2 adds

1. **Phase check.** Bond-angle spread of 10 degrees or more: split.
2. **Label checks from structure.** Every production point was rebuilt on
   the DGX CPU (same cell, seed, deck and preparation; 10 ps NPT; 6
   frames; 20 minutes for all 44). Two numbers per run: the lattice
   constant (a composition gauge, Vegard-like) and the bond-angle spread
   (a thermometer: its square is linear in T for the crystal). Fitted on
   the campaign's own crystalline points, the structure reads composition
   to 0.006 (robust s.d.) and temperature to 10 K. A label that disagrees
   with its own structure by 5.5 s.d. (point) or 4.5 s.d. (batch mean) is
   corrected, with the implied value as the corrected label.
3. Ge-rich domain x <= 0.90 (campaign-record entries 29); premelting guard at 0.85 of the
   solidus; duplicate key on design coordinates (D2). v1 thresholds unchanged.

## Results

Real campaign (out-of-catalog test): the amorphous probes N2, N3 are split
by structure (missed by v1); N0, N1 and premelting point C30 (x 0.63,
1199 K, 0.86 of the solidus) are scope-limited; C36-C38 (x > 0.90) are
scope-limited by the declared domain; and a new statistical scope-limit
appears on C00, C01 (x 0.06 and 0.09 at 304 and 414 K): the dilute,
low-temperature corner where phonon mean free paths outgrow the box, the
regime the blind catalog's M03 entry describes. No forget, quarantine or
correct on any real row (v1 quarantined C37, C38 and forgot four rows).

750 trials against the blind catalog (baseline-adjusted; percent):

| id | entry | v1 frozen det / hit / harm | D2 det / hit / harm | v2 det / hit / harm | v2 collateral |
|---|---|---|---|---|---|
| NULL | null campaign | 0 / 100 / 0 | 0 / 100 / 0 | 0 / 100 / 0 | 0 |
| P01 | biased batch | 86 / 86 / 0 | 80 / 80 / 0 | 82 / 82 / 0 | 0 |
| P02 | unit slip | 100 / 100 / 0 | 100 / 100 / 0 | 100 / 100 / 0 | 0 |
| P03 | composition label swap | 22 / 18 / 0 | 16 / 12 / 0 | 100 / 100 / 0 | 0 |
| P04 | species swap (x to 1-x) | 26 / 26 / 0 | 0 / 0 / 0 | 94 / 64 / 0 | 0 |
| P05 | temperature label offset | 64 / 46 / 0 | 32 / 14 / 0 | 86 / 74 / 0 | 0 |
| P06 | duplicated batch | 96 / 56 / 0 | 90 / 50 / 0 | 92 / 10 / 0 | 0 |
| P07 | unequilibrated long box | 60 / 60 / 0 | 56 / 56 / 0 | 80 / 80 / 0 | 0 |
| P08 | MACE rows under the Tersoff label | 60 / 60 / 0 | 56 / 54 / 0 | 100 / 26 / 0 | 0 |
| M01 | near-solidus premelting | 20 / 0 / 0 | 10 / 0 / 0 | 100 / 100 / 0 | 0 |
| M02 | amorphous contamination | 60 / 0 / 0 | 38 / 0 / 0 | 100 / 100 / 0 | 32 |
| M03 | dilute ballistic regime | 44 / 20 / 0 | 40 / 20 / 0 | 44 / 42 / 0 | 0 |
| V01 | regime-localized scattering (valid) | 76 / 24 / 74 | 46 / 54 / 44 | 0 / 100 / 0 | 0 |
| V02 | high-T scattering channel (valid) | 66 / 34 / 64 | 18 / 82 / 0 | 0 / 100 / 0 | 0 |
| V03 | composition asymmetry (valid) | 98 / 2 / 98 | 0 / 100 / 0 | 4 / 100 / 0 | 0 |

| Prediction | Registered | Result |
|---|---|---|
| Pr1 real campaign | N2, N3 split; N0, N1, C37, C38 scope-limited; no removal or correction elsewhere | pass (extra scope-limits on C00, C01, C30, C36, none of them removals) |
| Pr2 amorphous | detected >= 90%, hit >= 80% | pass: 100 / 100 |
| Pr3 premelting | detected >= 90% | pass: 100 |
| Pr4 label faults | P04 >= 70, P05 >= 70, P03 >= 50 | pass: 94, 86, 100 |
| Pr5 null | hit 100%, collateral <= 10% | pass: 100, 0 |
| Pr6 valid-anomaly limit kept | V01 harmful >= 30% | **refuted**: 0% |
| Pr7 no regression | P01, P02, P06 detection within 10 points of D2 | pass: 82, 100, 92 |

## Reading

- **Label errors are a structure problem, not a statistics problem.**
  Composition swaps went from 16-22% to 100% detected, species swaps from
  0-26% to 94%, temperature offsets from 32-64% to 86%: the run's own
  structure contradicts its label. MACE rows filed under the Tersoff label
  are detected in every trial because MACE's PBE lattice is 0.6-1.4% larger;
  v2 names the symptom (composition label contradicted) rather than the
  cause (wrong party), so only 26% are scored as hits.
- **Pr6 was refuted, and the reason matters.** The earlier "hard limit"
  (a localized valid anomaly quarantined in 44% of D2 trials) was mostly
  caused by the undetected amorphous probes: rerunning D2 on the V01 trials
  with only N2 and N3 removed gives 0 harmful in 50 (`posthoc_v01.py`,
  post-hoc, not registered); removing only the Ge-rich and premelting rows
  leaves 8 harmful. One undetected row of another phase, sitting inside
  the anomaly's regime, turned a valid anomaly into an apparent outlier.
  The logical limit stands (two replicas cannot separate a localized
  anomaly from an isolated fault), but on this campaign it did not fire
  once the entry checks were right.
- **Regressions and costs.** Duplicated-batch hit fell from 50% to 10%:
  the duplicates are still forgotten in 60% of trials, but copies of rows
  that v2 scope-limits for domain or premelting also get those operations,
  which the scoring counts as partial. M02 trials carry 32% collateral (a
  statistical scope-limit elsewhere after the amorphous rows leave). The
  dilute ballistic regime (M03) stays at 44%.
- **Not a blind test.** The catalog has been open since the v1 fault study (2026-09-28); the
  out-of-catalog evidence is the real campaign. The structure attached to
  injected rows follows a stated rule (`fault_study_v2.py`), and the
  premelting rows added by M01 get descriptors from the same kind of fit
  the detector uses, which favours detection of that entry.

## Reproduce

    ./md/run_rebuild.sh                                   # DGX CPU, ~20 min
    ~/venvs/mace/bin/python build_rows_v2.py              # descriptors + campaign-record entries 82
    ~/mat_theory_pilot/venv/bin/python fault_study_v2.py rows_v2.json 50
    ~/mat_theory_pilot/venv/bin/python analyze_v2.py && python3 apply_v2_decision.py
    ~/venvs/mace/bin/python make_v2_figure.py
