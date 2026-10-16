# Phase B CHPC campaign results (array 15844481, notchpeak-guest)

Collected 2026-09-26. All 19 array tasks COMPLETED with exit 0, elapsed
6 to 39 minutes each on 16 MPI ranks, zero preemptions despite running
on the preemptible guest partition. Raw points: `results/*.json`
(kappa, box, gradients, provenance) plus `results/*.profile`
(temperature profiles). Regenerate the tables below with
`python3 summarize.py`.

## Points

| x_Ge | T (K) | ncz | Lz (A) | atoms | seed | kappa (W/mK) |
|---|---|---|---|---|---|---|
| 0.0 | 300 | 48 | 261.23 | 6144 | 101 | 9.78 |
| 0.0 | 300 | 96 | 522.56 | 12288 | 101 | 23.302 |
| 0.0 | 300 | 144 | 783.54 | 18432 | 101 | 34.694 |
| 0.15 | 300 | 24 | 131.33 | 3072 | 101 | 1.188 |
| 0.15 | 300 | 48 | 262.83 | 6144 | 101 | 1.5 |
| 0.15 | 300 | 96 | 525.37 | 12288 | 101 | 1.67 |
| 0.5 | 300 | 24 | 133.41 | 3072 | 101 | 0.696 |
| 0.5 | 300 | 24 | 133.39 | 3072 | 202 | 0.733 |
| 0.5 | 300 | 24 | 133.26 | 3072 | 303 | 0.693 |
| 0.5 | 300 | 24 | 133.37 | 3072 | 404 | 0.736 |
| 0.5 | 300 | 48 | 266.61 | 6144 | 101 | 0.917 |
| 0.5 | 300 | 96 | 532.61 | 12288 | 101 | 1.21 |
| 0.5 | 300 | 144 | 799.63 | 18432 | 101 | 1.626 |
| 0.5 | 1100 | 24 | 133.81 | 3072 | 101 | 0.791 |
| 0.5 | 1100 | 48 | 268.22 | 6144 | 101 | 0.977 |
| 0.5 | 1100 | 96 | 535.55 | 12288 | 101 | 1.284 |
| 1.0 | 300 | 48 | 271.99 | 6144 | 101 | 8.745 |
| 1.0 | 300 | 96 | 544.28 | 12288 | 101 | 17.125 |
| 1.0 | 300 | 144 | 816.37 | 18432 | 101 | 24.156 |

## Derived quantities

- Seed statistics (x=0.5, 300 K, ncz=24, 4 seeds):
  kappa = 0.714 +/- 0.023 W/mK (3.2% relative). Single-seed points are
  therefore good to a few percent at this size.
- 1/L extrapolations (linear fit of 1/kappa vs 1/Lz, seed-averaged per
  length):
  - x=0.5, 300 K (4 lengths): kappa_inf = 1.78 W/mK
  - x=0.15, 300 K (3 lengths): kappa_inf = 1.96 W/mK
  - x=0.5, 1100 K (3 lengths): kappa_inf = 1.52 W/mK
  - x=0.0 (pure Si): intercept <= 0, no extrapolation possible
  - x=1.0 (pure Ge): nominal 238 W/mK, not credible (see below)

## Reading the numbers

**Alloys converge; the trends are physical.** Alloy-scattering-limited
mean free paths are short, so the three alloy series flatten with size
and extrapolate stably. Composition ordering is right (x=0.15 above
x=0.5) and the temperature dependence at x=0.5 is weak and slightly
decreasing (1.78 at 300 K to 1.52 at 1100 K), the signature of
alloy-dominated scattering that real SiGe shows.

**Cross-machine reproducibility passes.** Where the DGX pilot ran the
same (x, T, ncz), CHPC agrees within seed scatter: x=0.5/300 K/z24 DGX
0.744 vs CHPC 0.696-0.736; z48 DGX 0.929 vs 0.917; x=0.15/z24 DGX
1.141 vs 1.188; 1100 K/z24 DGX 0.81 vs 0.791. Two independent machines,
same potential and protocol, consistent numbers: this is the two-party
agreement check the shard machinery wants.

**Pure endpoints are ballistic at every size we ran.** Si and Ge kappa
still grow almost linearly with Lz at 18432 atoms (Si: 9.8 -> 23.3 ->
34.7 W/mK), meaning transport is dominated by phonons whose mean free
paths exceed the box. The Si fit gives a non-physical negative
intercept; the Ge fit's intercept is so close to zero that the nominal
238 W/mK (vs roughly 60 W/mK experimental) is meaningless. Verdict:
endpoint points are lower-bound/trend evidence only. Production
endpoints need micron-scale boxes (not affordable this way) or a
different method entirely (homogeneous Green-Kubo with a potential that
supports a valid heat flux, or BTE). This is a known limitation of
direct-method NEMD, now measured on our own system.

**Known caveats carried by every alloy point (method off-data, on
purpose).** (1) The imposed gradient is still steep: about 400 K across
half a box even at ncz=144, straining linear response at nominal
300 K. (2) The cross-section is fixed at 4x4 cells (about 22 A); no
cross-section convergence has been probed. (3) Tersoff systematically
suppresses alloy kappa: extrapolated 1.78 W/mK vs roughly 8-9 W/mK
experimental for bulk Si0.5Ge0.5. These are exactly the
empirical-potential and protocol limitations the design treats as a
distinct evidence party to be scope-limited, not averaged in.

## Status in the evidence hypergraph

All 19 points joined `pilot/kg/` as party `CHPC-MD` (90 datapoints
total: 67 literature, 4 DGX-MD, 19 CHPC-MD). The CHPC party is the only
one covering the pure-endpoint regimes (x0T0, x4T0) with MD evidence.

## What Phase B still owes

1. Cross-section convergence (4x4 -> 6x6 -> 8x8) at one alloy point.
2. Gentler swap rate at one point to quantify the steep-gradient bias.
3. Seeds at the larger sizes (only ncz=24 has them now).
4. An endpoint strategy decision: bigger boxes are hopeless for pure
   Si/Ge with this method; pick homogeneous GK (different potential) or
   scope-limit the theory to alloy compositions.
5. Then Phase C: the symbolic-regression party fits kappa(x, T) on the
   combined hypergraph evidence with per-party scope labels.

## Follow-up campaign (array 15854537, collected 2026-09-27)

All 10 follow-up tasks COMPLETED, exit 0, 10 to 39 minutes each, zero
preemptions. These answer the three method questions RESULTS.md left
open. Regenerate with `python3 summarize.py` (protocol variants appear
in their own table).

**1. Cross-section convergence: 4x4 is adequate.** At ncz=24, 6x6 gives
0.730 and 8x8 gives 0.719 W/mK, inside the 4x4 seed band
(0.714 +/- 0.023). At ncz=48, 6x6 gives 0.94 vs the 4x4 seed mean
0.928 +/- 0.012 (+1.3%). No systematic drift with cross-section at
these alloy compositions; the fixed 4x4 cross-section is not biasing
the campaign beyond the seed scatter.

**2. Swap rate: steep gradients inflate kappa by only 3-5%.** At
ncz=48, swap every 100 steps gives 0.898 and every 200 gives 0.881,
vs 0.928 +/- 0.012 at the production rate (every 50). Gentler driving
lowers kappa slightly and monotonically, so the production numbers
carry a small (~3-5%) nonlinear-response inflation, much smaller than
the ~7x finite-size suppression. Not worth re-running the campaign;
recorded as a known method bias on every production point.

**3. Large-size seed scatter shrinks with size.** New seeds at
ncz=48/96/144 give seed-averaged points 0.928 +/- 0.012,
1.209 +/- 0.006, 1.640 +/- 0.020 W/mK. Updated seed-averaged 1/L
extrapolation at x=0.5, 300 K over 4 lengths: **kappa_inf = 1.80
W/mK** (was 1.78 single-seed). Single-seed points at ncz>=48 are good
to about 1-2%.

**GK/SW endpoint feasibility (array 15854538): negative, definitive.**
`compute heat/flux` is CENTROID_NOTAVAIL for `pair sw` exactly as for
`tersoff`, verified through LAMMPS 7 Feb 2024. Green-Kubo in LAMMPS is
out for this system; the endpoint decision remains GPUMD-on-DGX vs
scope-limiting the theory to alloys.

**Endpoint decision (2026-09-27): B then A** (`ENDPOINT_DECISION.md`).
The scope-limit was executed the same day as the campaign record's
first shard operation, restricting Tersoff-MD claims to x in
[0.05, 0.95] (`phase_c/ledger_campaign.jsonl`, applied by
`fit_party.py`); GPUMD bring-up on the DGX starts as the next compute
block (`../gpumd/BRINGUP.md`), and when validated endpoints land a
`restore` entry lifts the restriction.
