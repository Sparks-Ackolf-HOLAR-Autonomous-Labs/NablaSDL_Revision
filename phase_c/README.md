# Phase C — seed campaign + symbolic party set-up

Set up 2026-09-26, covering the parts of Phase C that do not depend on
Phase B. Phase C is the MVP
experiment from `../04_experimental_design_v2.md`: coverage-designed
seed batch, per-party symbolic fits with passports, injected fault +
valid anomaly routed by the EES loop, verification against clean
retrains.

## Dependency split (why this can be set up now)

**Independent of the Phase B follow-ups (done here):**
- the coverage-designed seed batch geometry over (x, T) with k-loss
  tolerance, committed with a SHA-256 pre-registration hash (N3);
- the evidence assembly from the three-party hypergraph with per-party
  scope labels;
- the symbolic-party fitting pipeline (minisr now, PySR drop-in on the
  same claim format) with the two passports.

**Pinned by the Phase B follow-up series before the campaign was
submitted (deliberately left as `PENDING` in the seed design; `ncxy` and `swapn`
are pinned in `production/design_production.py`, the endpoints by
`scope_limit_alloys.py`):**
- production cross-section (`ncxy`): follow-up cross-section series;
- production swap interval (`swapn`): follow-up gentle-swap series;
- endpoint strategy (x = 0, 1): GK/SW feasibility runs decide between a
  second-potential endpoint party and scope-limiting to alloys.

## Files

| File | Purpose |
|---|---|
| `design_seed_batch.py` | deterministic coverage design: 5 x-bands times 4 T-bands, 2 replicas per cell (k=1 loss tolerance), 3 sizes per point for 1/L; emits `seed_batch_design.json` and prints its SHA-256 commitment |
| `seed_batch_design.json` | the committed batch design (regenerate bit-for-bit with the script) |
| `assemble_evidence.py` | three-party evidence table from `../pilot/kg/extracted_points.json`: per-party scope labels, seed-averaged MD rows, 1/L-extrapolated rows where a size series exists |
| `fit_party.py` | one symbolic loop per party: Pareto front, BIC selection, support-region and ensemble passports, validity domain; writes `claims_<party>.json` |
| `evidence_table.json`, `claims_*.json` | current outputs on today's evidence (preliminary: the MD party is not yet fittable, see below) |
| `sr_compare/` | multi-engine SR comparison (PySR, SISSO, AI Feynman, QLattice/Feyn — the latter now runs on the DGX via the amd64-emulated container, `../containers/`) + **HG-SR**, the new hypergraph-provenance engine; see `sr_compare/COMPARISON.md`. Shard operations beyond forget: `sr_compare/shard_ops.py` + `sr_compare/HGSR_SHARD_OPS.md` |
| `chd/` | CHD (Computational Hypergraph Discovery, PNAS 2024) as a proposed stage-0 per-party structure-discovery pass; see `chd/ASSESSMENT.md` |

## Status of the preliminary fit

The literature party (67 points) is fittable now and exercises the whole
pipeline. The MD party has only three 1/L-extrapolated (x, T) points, so
a symbolic fit on it is refused by design (underdetermined); filling
that grid is exactly what the seed campaign is for. Fault injection,
EES routing, and verification already run end-to-end in
`../pilot/src/` (all six Phase A checks passed) and are reused, not
duplicated, here.
