# Pre-registered fault catalog: P2 Si(1-x)Ge(x) Tersoff RNEMD production campaign

Author: blind catalog subagent, 2026-09-28. **Written blind**: no detector
code, detector output, or fault-study result was opened while writing this
catalog. Sources consulted: the shard-operation definitions
(`00_terminology_shard_operations.md`), the evidence-table row format
(`phase_c/evidence_table.json`), the design grid
(`phase_c/seed_batch_design.json`), and the finite-size results in
`chpc/RESULTS.md`, together with general physics and HPC experience.

Machine-readable twin: `fault_catalog.json`. Implementation:
`inject_faults.py` (`inject(rows, entry_id, trial_seed, other_parties=None)`
returns the corrupted rows and a separate ground-truth dict; the rows keep the
production schema exactly, so the detector never sees ground truth).

## Categories

- **Planted error**: something is wrong with the data; the evidence should be
  corrected or removed.
- **Method-off data**: genuine simulation output that lies outside the validity
  of the method, or outside the material/phase the law is meant to describe.
  The right response limits scope or splits the shard; it is neither a
  correction nor plain retention.
- **Valid anomaly**: real physics that the simple alloy law lacks. It must
  **not** be forgotten, quarantined, or corrected away; the right response is
  to retain it (and, ideally, strengthen the law with the missing term).

## Trial protocol

- 50 randomized trials per entry and 50 NULL trials.
- Trial seed = 1000 x entry number + k, k = 0..49 (NULL = 0, P01 = 1, ...,
  V03 = 14). A single integer drives `numpy.random.default_rng(trial_seed)`,
  which makes every random choice in the trial: background jitter, target
  batch or points, magnitude, and final row order.
- Each trial first draws a severity u ~ U(0,1) and maps it monotonically onto
  the entry's magnitude range (subtle near u = 0, gross near u = 1), so
  detection-rate curves can be plotted against u and against the physical
  magnitude recorded in the truth dict.
- Background in every trial, NULL included: kappa of each row multiplied by
  exp(N(0, 0.01)) (replica-level scatter, comparable to measured seed scatter)
  and rows randomly permuted. Edited numbers are rounded to the input precision
  so they do not stand out by digit count; added run_ids copy the textual style
  of existing ids.
- **NULL campaign**: no fault. Expected operator retain (strengthen
  acceptable). One caveat is recorded in every trial: production rows already
  in the real-alloy premelting band (T/T_sol(x) >= 0.85) are listed as
  background method-off rows, for which scope-limit is the expected operator.
- Suggested scoring: localisation (precision and recall of flagged rows against
  the affected and added run_ids), and operator outcome (hit if the detector's
  operator is in the acceptable set, harmful if in the forbidden set, neutral
  otherwise). For valid anomalies the primary metric is the harmful rate; NULL
  trials give the false-alarm rate.

## Entries

| id | name | category | magnitude (subtle to gross) | expected operator (acceptable) | prior: statistical or physics |
|---|---|---|---|---|---|
| P01 | biased batch | planted-error | one batch x (1+d) or /(1+d), d = 0.03 to 0.80 | quarantine (correct, downweight, forget) | statistical |
| P02 | unit slip | planted-error | one batch x 2, 0.5, 0.01, 100, 1000 | correct (quarantine, forget) | statistical to detect, physics to correct |
| P03 | composition label swap | planted-error | two points trade x labels, target abs(dx) = 0.05 to 0.60 | correct (quarantine, forget) | mostly physics for small dx |
| P04 | species type swap, x to 1-x | planted-error | 1 point near x = 0.5 up to a whole batch far from 0.5 | correct (quarantine, forget) | physics |
| P05 | temperature label offset | planted-error | one batch, abs(dT) = 20 to 300 K; gross case a Celsius slip (-273.15 K) | correct (quarantine, downweight) | physics for subtle, statistical for Celsius |
| P06 | duplicated batch | planted-error | 50 to 100 percent of a batch re-ingested: new ids with hardware jitter, new ids bit-identical, or replayed rows | forget the copies (downweight) | statistical (bookkeeping) |
| P07 | unequilibrated long box | planted-error | largest box of one batch reads low by up to 3 to 40 percent | forget (quarantine, downweight) | both |
| P08 | party mislabel, MACE rows as CHPC-MD-C | planted-error | 1 point to a whole batch at about 0.55x | correct, i.e. re-attribute (split, quarantine, replace) | statistical to detect, cross-party knowledge to attribute |
| M01 | near-solidus premelting regime | method-off-data | new batch of 3 to 8 points at T/T_sol = 0.86 to 0.975 | scope-limit (split, downweight) | physics |
| M02 | amorphous-phase contamination | method-off-data | 1 point to a whole batch; size-independent kappa at 0.5 to 1.5x the mid-size value | split (quarantine, scope-limit) | both |
| M03 | dilute ballistic regime | method-off-data | corner min(x,1-x) < 0.10 to 0.25, T < 500 to 900 K, long-box enhancement 10 to 100 percent | scope-limit (split, downweight) | both |
| V01 | regime-localized extra scattering | valid-anomaly | Gaussian extra resistance, amplitude 3 to 35 percent | retain (strengthen, split, scope-limit) | statistical to see, physics to keep |
| V02 | high-T second scattering channel | valid-anomaly | extra resistance at 1200 K of 5 to 50 percent, onset 600 to 900 K | retain (strengthen, split, scope-limit) | statistical to see, physics to keep |
| V03 | composition asymmetry | valid-anomaly | antisymmetric extra resistance, 3 to 30 percent at the endpoints | retain (strengthen, split) | statistical to see, physics to keep |

Counts: 8 planted errors, 3 method-off entries, 3 valid anomalies (14 total).

### P01 Biased batch (planted error)
*Story.* One committed submission ran with a systematic protocol difference:
a wrong timestep or thermostat coupling in a copied input deck, a different
compiler build on the node, or a swap interval outside the linear-response
window. Every run in that batch then reads high or low by the same factor.
*Transformation.* Pick one batch at random and multiply kappa of all its rows
by f = 1 + d (up) or 1/(1 + d) (down), with the direction 50/50 and
d = 0.03 + 0.77u. *Expected operator.* quarantine (correct, downweight, and
forget acceptable). *Prior.* Statistical: the batch is internally consistent
but offset from neighbouring points in other batches; below about 5 percent it
is near the noise floor.

### P02 Unit slip (planted error)
*Story.* A post-processing script converts the Muller-Plathe exchanged energy
to kappa with a wrong factor: the classic missing 1/2 for a periodic box (heat
flows both ways from the hot slab), the 1/2 applied twice, W/(cm K) instead of
W/(m K), nm^2 instead of Angstrom^2 area, or mW/(m K).
*Transformation.* One batch multiplied by a factor from [2, 0.5, 0.01, 100,
1000], indexed by severity. *Expected operator.* correct. *Prior.* Powers of
ten are trivially visible; the factor-2 cases look like a gross biased batch.
Recovering the exact correction is a physics and bookkeeping insight.

### P03 Composition label swap (planted error)
*Story.* Two lines of the points file are transposed (a spreadsheet sort
applied to one column only), so two points trade Ge-fraction labels while the
kappa values stay with the true structures.
*Transformation.* Two points of the same batch (all box sizes) whose abs(dx)
is close to a target of 0.05 + 0.55u swap x labels. *Expected operator.*
correct. *Prior.* Mostly physics: alloy kappa(x) is flat and roughly symmetric
near x = 0.5, so swaps across the minimum can be nearly invisible to a
statistical model.

### P04 Species type swap, x to 1-x (planted error)
*Story.* The LAMMPS data-file template of one batch maps atom type 1 to Ge
instead of Si (or the mass lines are swapped), so the simulated alloy is
really Si(x)Ge(1-x).
*Transformation.* In one batch, n = round(1 + u(N-1)) points get x replaced by
1-x; low severity chooses the points nearest x = 0.5, high severity the
farthest. *Expected operator.* correct. *Prior.* Physics: SiGe kappa is only
mildly asymmetric in x, and knowing that the Si-rich side conducts better is
what exposes the swap.

### P05 Temperature label offset (planted error)
*Story.* The T label of one batch is the thermostat set-point from a copied
input deck (or a slab temperature) rather than the mean sample temperature;
in the gross case the labels were written in degrees Celsius.
*Transformation.* One batch: T += dT with abs(dT) = 20 to 300 K and random
sign for u <= 0.9; dT = -273.15 K for u > 0.9. *Expected operator.* correct.
*Prior.* Physics for subtle offsets: alloy scattering is temperature
independent and the Umklapp term grows slowly, so 100 K moves kappa by a few
percent at most. The Celsius slip is statistically obvious (labels below the
300 K design floor).

### P06 Duplicated batch, double counting (planted error)
*Story.* A batch is ingested twice: resubmitted after an apparent failure with
the same seeds and a new batch id (results equal up to hardware
non-determinism), re-ingested with new ids but bit-identical kappa, or
replayed by the ledger with identical rows.
*Transformation.* 50 to 100 percent of one batch appended again in one of
those three modes (subtle to gross). *Expected operator.* forget, applied to
the copies only (downweight acceptable). *Prior.* Statistical (bookkeeping):
identical seeds and near-identical kappa at identical (x, T, ncz), whereas
genuine replicas use different seeds and scatter at about 1 percent.

### P07 Unequilibrated long box (planted error)
*Story.* The walltime limit truncates the longest box of one batch. Thermal
relaxation time grows as L^2, so the ncz = 96 runs are averaged before steady
state and read low, bending the 1/kappa vs 1/L line.
*Transformation.* Largest-box rows of one batch multiplied by
1 - d U(0.7, 1.0), d = 0.03 + 0.37u. *Expected operator.* forget (quarantine
pending re-run, or downweight, acceptable). *Prior.* Both: non-monotone or
concave size series are statistically visible for large d; the L^2 argument
tells a detector where to look.

### P08 Party mislabel, MACE rows under CHPC-MD-C (planted error)
*Story.* Output of the MACE machine-learned potential, run with the identical
Muller-Plathe protocol, is copied into the Tersoff production folder. MACE
reads about 0.55x Tersoff with a mild composition dependence.
*Transformation.* n points of one batch multiplied by
r0 (1 + 0.15(x - 0.5)) exp(N(0, 0.03)), r0 ~ U(0.50, 0.60).
*Expected operator.* correct, meaning re-attribute to the MACE-MD party (split,
quarantine, replace acceptable). *Prior.* Statistically visible as an outlier
group; attributing it to MACE rather than to an arbitrary bias requires the
cross-party ratio.

### M01 Near-solidus premelting regime (method-off data)
*Story.* The Tersoff alloy stays crystalline far above the real melting point,
but real Ge-rich SiGe at 1000 to 1200 K is within 5 to 15 percent of its
solidus (Ge 1211 K, Si 1687 K, lens-shaped diagram), where vacancies,
premelting at defects and anharmonic softening make the real material differ.
The crystalline Tersoff kappa there is internally consistent yet does not
transfer to the real alloy.
*Transformation.* A new batch of 3 to 8 Ge-rich points at
T = h T_sol(x) <= 1200 K with h = 0.86 to 0.975; kappa comes from a smooth
least-squares continuation of the table itself (crystalline Tersoff trend)
plus replica jitter. Pre-existing rows with T/T_sol >= 0.85 are reported as
background method-off rows in every trial. *Expected operator.* scope-limit
(split, downweight acceptable; correct forbidden). *Prior.* Invisible to a
purely statistical detector by construction; physics (the real solidus) is
required.

### M02 Amorphous-phase contamination (method-off data)
*Story.* A melt-quench step left in the structure generator, or a too-fast
anneal, produces amorphous SiGe for some points. Amorphous kappa is carried by
diffusons with nanometre mean free paths, so it is independent of box length
and weakly increasing with T.
*Transformation.* n points of one batch get the same kappa at every box size,
equal to the point's mid-size crystalline value times a level of
(1 +/- 0.5u)(1 + 0.08(T - 300)/900). *Expected operator.* split (quarantine,
scope-limit acceptable). *Prior.* Both: large level offsets are statistical
outliers, while at a level near 1 only the flat size series betrays the phase,
which requires the diffuson-versus-propagon picture.

### M03 Dilute ballistic regime (method-off data)
*Story.* Near the pure endpoints and at low T, phonon mean free paths exceed
the longest box, so 1/kappa is no longer linear in 1/L and the three-size
extrapolation method leaves its validity range, although each run is fine.
*Transformation.* For points with min(x, 1-x) < x_c and T < T_c, kappa is
multiplied by 1 + a w s^2 (w tapers to zero at the regime edges, s is the
normalized box length), with x_c = 0.10 to 0.25, T_c = 500 to 900 K,
a = 0.1 to 1.0. *Expected operator.* scope-limit (split, downweight
acceptable; forget and correct forbidden). *Prior.* Both: size-series
curvature is visible, but limiting the method's scope instead of dropping the
runs needs the mean-free-path argument.

### V01 Regime-localized extra scattering (valid anomaly)
*Story.* At intermediate composition and moderate T, partially relaxed local
bond-length mismatch (Si-Si, Si-Ge and Ge-Ge bonds of different length)
creates strain-field scattering beyond pure mass disorder, a term the simple
alloy law lacks.
*Transformation.* Every row of every batch gains intrinsic resistance
1/kappa += A exp(-(x-x0)^2/(2 sx^2) - (T-T0)^2/(2 sT^2)) / kappa_ref, with
kappa_ref the point's largest-box value, so the 1/L slope is preserved and
the effect is batch independent. A = 0.03 to 0.35, x0 = 0.3 to 0.7,
T0 = 300 to 800 K. *Expected operator.* retain (strengthen, split,
scope-limit acceptable; forget, quarantine, correct, replace forbidden).
*Prior.* The deviation is statistically visible for A above about 0.1; keeping
it requires recognizing that it is smooth, spans batches, and respects size
scaling.

### V02 High-T second scattering channel (valid anomaly)
*Story.* At high T, four-phonon scattering grows roughly as T^2 on top of
three-phonon Umklapp, so a law with only a linear-in-T intrinsic resistance
underpredicts the high-T drop.
*Transformation.* Every row: 1/kappa += c ((T - T_on)+ / (1200 - T_on))^2 /
kappa_ref, c = 0.05 to 0.50, T_on = 600 to 900 K. *Expected operator.* retain
(strengthen, split, scope-limit acceptable). *Prior.* Visible as a high-T
residual; it is confounded with M01 and P05 in the hot Ge-rich corner, and
separating them needs physics (all compositions affected, size scaling
preserved).

### V03 Composition asymmetry (valid anomaly)
*Story.* Mass-disorder scattering is not symmetric in x: Ge impurities in a
light, stiff Si host and Si impurities in a heavy, soft Ge host scatter
differently, and the host conductivities differ, so kappa(x) is skewed (lower
on the Ge-rich side) while an x(1-x) law is symmetric.
*Transformation.* Every row: 1/kappa += a (2x - 1) / kappa_ref, a = 0.03 to
0.30. *Expected operator.* retain (strengthen, split acceptable; scope-limit
forbidden because the effect is global). *Prior.* Structured residuals across
all batches; the risk is a detector blaming the Ge-rich batches. Physics says
the skew is real.

## Strengths and limitations

- Strength: every entry is defined by a row-level transformation on the frozen
  production table, deterministic from one integer seed, with severity spanning
  subtle to gross.
- Strength: valid anomalies act through an intrinsic thermal resistance that
  preserves the 1/L size scaling, which is how real extra scattering behaves,
  so they are not a disguised batch artefact.
- Limitation: magnitudes and the solidus table are physics-informed estimates
  (solidus about +/-30 K), not measured values for this campaign.
- Limitation: M01 kappa values are a smooth continuation fitted to the table,
  not new MD runs; they emulate crystalline Tersoff by assumption.
- Limitation: V02 and M01 overlap in the hot Ge-rich corner, and P05 can mimic
  either there; scoring should report these entries separately.
