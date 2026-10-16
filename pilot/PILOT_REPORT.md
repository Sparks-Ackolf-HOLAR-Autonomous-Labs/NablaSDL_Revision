# DGX pilot report — mat_theory (2026-09-25)

Early piloting results before anything touches CHPC. All runs on the DGX Spark (GB10, aarch64, 20 CPU cores),
CPU only; the resident vLLM server was used for inference only (Pilot C).

## Verdict up front

The whole pipeline works on the DGX: environment, physics engine, symbolic
layer, campaign record + shard operations, and the literature/KG track. Two findings
change the CHPC plan (both cost-savers): Green-Kubo heat flux is off the
table for Tersoff in stock LAMMPS (kappa points use Muller-Plathe reverse
NEMD instead, which is also cheaper), and the DGX alone can carry a
meaningful fraction of the MVP campaign, so CHPC is needed for scale-out
and the pure-element endpoints, not for feasibility.

## Pilot A — Phase A mock pipeline (all six checks pass)

End-to-end campaign on the mock evidence party (`results/pilot_summary.json`):
50-point coverage-designed seed (every x-band x T-band regime twice, k=1 loss
tolerance), 5 Merkle-committed batches, one biased batch (kappa scaled 0.72),
one genuine richer-world regime above 1000 K, plus a null-campaign control.

| Check | Result |
|---|---|
| Biased batch caught and forgotten (batch-coherent offset, z > 3) | pass |
| No extra forgets (exactly one operation fired) | pass |
| Valid anomaly scope-limited, NOT forgotten (validity domain T <= 1000 K) | pass |
| Null campaign: zero shard operations fired | pass |
| Forget verified exact: post-forget law == retrain-from-scratch, coef delta < 1e-9, campaign record chain valid | pass |
| Greedy transversal size == exact brute-force minimum | pass (open flag partially retired) |

The recovered law on clean data is `1/kappa = c0 + c1*T + c2*x(1-x) + c3/T`:
the three dominant physics terms (residual, Umklapp, alloy scattering) are
exactly right; the small linear-in-x Ge term is confused with a 1/T term at
4 percent noise and n=50. That is an identifiability limit worth
carrying into the paper's identifiability discussion, not a bug.

- Symbolic layer: deterministic exhaustive-subset SR with BIC selection
  (exact clean retrain by construction). PySR itself also works on the DGX:
  aarch64 install clean, 40-iteration fit in about 10 s.
- The greedy-vs-exact transversal flag (open flag 3 in
  `04_experimental_design_v2.md`) is retired at pilot scale; re-check once
  hyperedge counts exceed brute-force reach.

## Pilot B — real physics bring-up (LAMMPS/Tersoff on DGX)

pip `lammps` wheel (22 Jul 2025, aarch64) + user-space MPICH runtime
(no sudo needed; recipe in `README.md`). Bundled `SiCGe.tersoff`
(Tersoff, Phys. Rev. B 39, 5566, 1989; corrected 2026-09-29, this line previously named Erhart-Albe 2005, which is a Si-C potential), elements `Si(D)` and `Ge`. From `results/lammps_pilot.json`:

| System | a (pilot) | a (reference) | E_coh (pilot) | E_coh (expt) |
|---|---|---|---|---|
| Si | 5.432 A | 5.431 | -4.630 eV | -4.63 |
| Ge | 5.657 A | 5.658 | -3.851 eV | -3.85 |
| Si0.5Ge0.5 | 5.535 A | 5.545 (Vegard) | -4.258 eV | (slight negative Vegard deviation, expected) |

Phase B gate condition (lattice constants reproduce literature) already met
on the DGX.

**Throughput:** 9.1M atom-steps/s on 8 OpenMP threads (4096-atom Tersoff MD).

**kappa points (Muller-Plathe reverse NEMD):** four runs on the DGX,
collected in `results/gk_kappa_points.json` (7-15 min wall each on
4 threads):

| x_Ge | T (K) | box (cells) | atoms | kappa (W/mK) | dT across half box (K) |
|---|---|---|---|---|---|
| 0.5 | 300 | 4x4x24 | 3072 | 0.744 | 245 |
| 0.5 | 300 | 4x4x48 | 6144 | 0.929 | 340 |
| 0.15 | 300 | 4x4x24 | 3072 | 1.141 | 193 |
| 0.5 | 1100 | 4x4x24 | 3072 | 0.81 | 863 |

Trend checks all point the right way: kappa(x=0.15) > kappa(x=0.5) at
300 K (alloy scattering strongest near mid-composition), kappa nearly flat
from 300 K to 1100 K at x=0.5 (alloy-dominated scattering, weak T
dependence, as in experiment), and kappa grows with box length (long
wavelength phonons re-admitted). Absolute values are far below the ~9 W/mK
experimental bulk figure for Si0.5Ge0.5, as expected at these sizes: a
two-point 1/kappa-vs-1/L extrapolation gives only ~1.2 W/mK, so pilot
boxes are nowhere near size-converged, and the imposed gradients (193-863 K
across half a box) strain linear response, especially the 1100 K point.
Production settings on CHPC therefore need larger cross-sections, several
box lengths for the 1/L extrapolation, a gentler swap rate, and multiple
seeds; the pilot numbers are trend evidence, not fitting evidence.

These four points joined the evidence hypergraph as the simulation party
(`kg/`, party id `DGX-MD`): they populate regimes x2T0 and x2T4
(mid-composition at 300 K and at >= 1100 K) where the literature party has
zero datapoints, confirming the coverage-complementarity finding below on
real data. Method finding that changes the plan:

1. **Green-Kubo with Tersoff is not available in stock LAMMPS**: mainline
   `pair tersoff` does not implement `compute centroid/stress/atom`
   (many-body pair styles are CENTROID_NOTAVAIL), and plain `stress/atom`
   heat flux is quantitatively unreliable for many-body potentials. The
   first detached GK attempt died on exactly this. Muller-Plathe
   (`fix thermal/conductivity`) needs no heat-flux compute at all, works
   with OpenMP threading, and imposes/measures the flux directly; the
   trade-off is finite-size gradient effects, handled by running two box
   lengths. (GPUMD or a patched many-body flux would be the GK route if
   ever needed; that is a fenced extension, not MVP work.)
2. Cost per MP kappa point at pilot size: minutes, not hours (3072 atoms x
   650k steps at 4 threads is about 10-15 min). A 50-point campaign is a
   DGX afternoon at pilot fidelity; CHPC (grn061 first, free guest
   partitions as fallback) buys parallel width, bigger boxes for the
   size-converged production numbers, and the pure-element endpoints
   (long phonon mean free paths need the largest boxes).

## Pilot C — Asta literature data, local-LLM extraction, evidence hypergraph

- 4 Asta searches (`kg/asta/q20-q23`): 57 unique full-text snippets on SiGe
  thermal conductivity (composition + temperature dependence, GK/MD methods).
- Extraction by the DGX's resident vLLM (Qwen3.6-35B-A3B, localhost): strict
  JSON schema, 67 kappa datapoints, 0 call failures, every datapoint carrying
  provenance (corpusId, snippet hash, query file). Spot checks are physically
  sensible: pure Si 130-160 W/mK at 300 K, 51 at 700 K, 36 at 900 K
  (Glassbrenner-Slack values are 148 / ~50 / ~40).
- Known extraction impurity, flagged for shard review rather than silently
  cleaned: a few ~1 W/mK points at x = 0.02-0.04 are labeled bulk/experiment
  but almost certainly come from nanostructured-Si passages. This is exactly
  the valid-but-different / mislabeled-evidence case the shard operations
  exist for, so it stays in the graph with a flag.
- Hypergraph (`kg/kg_hypergraph.json`, `.graphml`, `.png`): 40 vertices
  (17 papers, 11 regimes, 5 methods, 7 system types), 67 datapoint
  hyperedges, per design element 3. Rebuilt after the kappa runs landed:
  43 vertices, 71 hyperedges with the `DGX-MD` simulation party joined
  (`extract_kg.py --reuse` rebuilds without re-querying the vLLM).
- Figure correction (2026-09-26): the first `.png` drew the bipartite star
  expansion (grey datapoint nodes with plain pairwise edges), which is not a
  hypergraph picture. `kg/render_hypergraph.py` now draws each hyperedge as
  a shaded region enclosing its {paper, regime, method, system} members
  (identical member sets merged, outline width = datapoint count, regions
  colored by evidence party); `extract_kg.py` calls it on every rebuild. The
  `.graphml` bipartite expansion is unchanged as the algorithmic form.
- **Coverage finding:** literature evidence piles up at x near 0 and
  room/unknown temperature; mid-composition and high-temperature regimes
  (x in 0.4-0.8 with T above 700 K) are nearly empty. The transversal
  targeter run on this graph would send the first shard-action batches to
  exactly the regimes the MVP campaign plans to probe: the literature party
  and the simulation party are complementary, not redundant.

## What this changes for the CHPC plan

1. Phase B's bring-up gate is effectively pre-cleared: the same potential
   file, input deck, and validation script transfer as-is (module lammps on
   CHPC instead of the pip wheel).
2. kappa submission scripts use Muller-Plathe rNEMD, not Green-Kubo
   (no valid many-body heat flux in stock LAMMPS for Tersoff); production
   runs need the finite-size study (multiple box lengths, 1/L extrapolation).
3. The MVP campaign splits naturally: DGX runs alloy compositions
   continuously (free, interactive, already working); CHPC guest/grn061
   adds parallel width and the expensive pure-element endpoints.
4. The literature hypergraph becomes the second evidence party from day one;
   its regime-coverage gaps feed the transversal targeter directly.

## Limits

- The mock pipeline is one seeded realization per campaign arm; false-fire
  rates need the repeated-trials study (Phase C controls), not a single null run.
- MP kappa pilot points are single-seed, two box lengths only: good for
  order-of-magnitude and trend checks, not size-converged values (that part
  is CHPC work by design).
- The extraction pass used one model and one prompt; no inter-extractor
  agreement measured yet. Worth a second extractor pass (different model or
  prompt) before literature points are used as fitting evidence.
