# CHD stage-0: the literature scope-split (2026-09-28)

Stage-0 applies Computational Hypergraph Discovery (CHD; Bourdais et al.,
PNAS 121, 2024; `ComputationalHypergraphDiscovery` 2.1.0, jax on CPU) to
the literature party. The question is which variables ln kappa depends
on. The answer then decides, by a rule stated before the real data were
touched, whether the pooled literature party is split into
microstructure scopes. Plan and literature context: `ASSESSMENT.md`.

## 1. Calibration first (`calibrate_chd.py` -> `calibration.json`)

The 2026-09-26 smoke test showed CHD's default settings drawing
spurious edges, so no real-data result was used until the settings had
been calibrated on planted cases. The synthetic tables reuse the real
designs: the 17 real (x, T) points, the real class vector (2 of the 17
rows are reduced-dimension samples), the 42 real rows that have x, and
the 29 real CHPC-MD (x, T, L, seed) points. The planted noise equals
the real pooled within-cell scatter of ln kappa, **s = 0.94** (a factor
of 2.6; 11 degrees of freedom), and is also run at s/2. The planted
class effect is a factor of 10. There were 8 cases (x/T-only, class,
junk variable, pure null, MD with a junk seed), 8 seeds per case, and
12 settings (3 kernel sets times 4 mode choosers), all deterministic.

The pre-stated selection rule was: every false-positive (FP) test must
have an FP rate of at most 1/8, and among the settings that pass, the
one with the best mean hit rate wins.

| Setting | x hit | class hit (B42 / B17real / B17bal) | L hit (MD) | FP: C17 junk / N17 null / B42 junk / N42 null / MD seed |
|---|---|---|---|---|
| library default (lin+quad+gauss, max-increment) | 0.13-1.0 | 0.38 / 0.88 / 0.50 | 0.0 | 0.25 / 0.25 / 0 / 0.125 / 0 |
| best score (lin+quad, threshold 0.8) | 1.0 | 1.0 / 0.88 / 0.63 | 0.0 | 0 / **0.25** / 0 / 0 / 0 |
| **chosen: linear kernel, max-increment** | **0.0** | **1.0 / 1.0 / 0.38** | **1.0** | **0 / 0 / 0 / 0 / 0** |

- **Only one setting passes, and only as a dominant-driver detector.**
  The linear kernel with max-increment pruning drew no false edge in 40
  FP-test runs (the same held at half noise). It found the planted class
  variable in every seed on both real designs, and it found L in every
  MD seed. It **never** recovered x, because the planted x(1-x) alloy
  term is not monotone and max-increment pruning keeps only the single
  strongest driver. CHD is therefore trusted here to say *whether a
  class indicator is the dominant driver of ln kappa*, and not to return
  the full ancestor set.
- **The library defaults fail calibration.** They drew false edges on
  junk in 2 of 8 seeds and on pure noise in 2 of 8 seeds at n = 17.
  The best-scoring setting recovers the full planted structure but still
  finds "ancestors" in pure noise in 2 of 8 seeds at n = 17. It is
  reported below as a sensitivity check only.
- **Noise-ratio ablation is not a usable criterion at this size.** With
  the non-linear kernels, removing a planted class variable changed the
  noise ratio by less than removing junk did (class hit rate 0 at the
  junk-calibrated threshold).

## 2. Rows (nothing imputed)

The 67 literature rows are the rows with an all-digit corpusId, the same
rule `assemble_evidence.py` uses. Of these, 25 lack x and are dropped
everywhere. A further 25 have x but no T, so they are dropped from the
fit table. That leaves:

- **fit table**, rows with x, T and kappa: **17** (15 bulk, 2
  reduced-dim; by method, 8 measurement, 6 simulation, 3 unclear);
- **x-table**, rows with x and kappa, where T is not a variable: **42**
  (33 bulk, 3 reduced-dim, 5 amorphous, 1 unclassified).

The class groups were declared before any fitting and were merged by
physics: nanowire, nanostructured, film and superlattice are all
"reduced-dim" samples dominated by boundary scattering.

## 3. What CHD found (`stage0_results.json`)

**(x, T) leave the literature ln kappa mostly unexplained.** The CHD
noise ratio n/(n+s) of ln kappa given (x, T) is 0.68 on the fit table,
and given x alone it is 0.90 on the x-table. For contrast, the MD party
gives **0.15** given (x, T, L). Under the calibrated setting, (x, T)
alone yield no detectable ancestor of ln kappa at n = 17. The classical
fallback agrees. An OLS fit of ln kappa on (1, x, x(1-x), T) leaves a
residual scatter of 1.0 in ln units (a factor of 2.7) on the fit table.
On the x-table, R² is 0.35 and the residual scatter is 1.8.

**Sample class is the dominant driver.** With the full variable set
{x, T, sample class, method class, junk control}, the calibrated CHD
returns:

- fit table: ln kappa <- {reduced-dim};
- x-table: ln kappa <- {reduced-dim, amorphous}.

**The method class is never selected**, and the junk control is never
selected by the calibrated setting. The uncalibrated settings did pick
up the junk control on the real data: the library default on the fit
table returned {T, junk, rdim, sim}, and the sensitivity setting on the
x-table returned junk among five ancestors. This is the real-data
counterpart of the calibration's false-positive finding.

The fallback ANOVA of the x-table residuals points the same way:

- **sample group: eta² = 0.32, F = 8.9, p = 7e-4.** The mean residual is
  -2.45 ln for amorphous rows (a factor of 12 low) and -0.91 ln for
  reduced-dim rows;
- method group: eta² = 0.09, p = 0.17.

**MD contrast (the protocol audit).** The calibrated CHD on the 29
CHPC-MD rows returns ln kappa <- {L}, and the sensitivity setting
returns {x}. **The seed is never an ancestor** in any variable set or
any setting. With the seed as the only candidate, the noise ratio is
0.97 to 0.98, above the Z-test band (Z_low = 0.95), so the seed is
indistinguishable from noise. The cross-section and swap interval are
not selected either. This is the expected structure, (x, L) and not
seed, and neither setting returns both x and L. Four DGX-MD rows were
dropped because their labels carry no seed or size.

**Structure disagreement between parties.** The two parties disagree on
structure. Literature ln kappa depends on a microstructure variable
that MD cannot express, while MD depends on (x, L). That disagreement
is the shard trigger `ASSESSMENT.md` proposed.

## 4. Split decision (`split_decision.json`)

The rule was stated in the header of `stage0_literature.py` before the
run. A partition is adopted only if both conditions hold:

- **C1:** its indicator is a calibrated CHD ancestor of ln kappa. The
  fit table is used unless it has fewer than 3 rows in the class; then
  the x-table is used.
- **C2:** every scope with at least 12 rows beats the pooled law's
  5-fold CV MedAPE on the same rows by 10 points or more, for both
  hgsr and minisr-pooled.

| Partition | C1 | C2 | Adopted |
|---|---|---|---|
| sample class (bulk / reduced-dim / amorphous / unclassified) | yes (x-table; the fit table also returns rdim) | yes | **yes** |
| method class (simulation / measurement / unclear) | no | no (no scope reaches 12 rows) | no |

**Decision: split the literature party by sample class** into four
scopes (all 67 rows re-tagged; nothing forgotten):

| Scope | Rows (all) | Rows with x, T | Law |
|---|---|---|---|
| literature-bulk | 35 | 15 | fitted |
| literature-reduced-dim | 19 | 2 | refused (below 12): scope-limited, no claim |
| literature-amorphous | 7 | 0 | refused: scope-limited, no claim |
| literature-unclassified | 6 | 0 | refused: scope-limited, no claim |

## 5. Per-scope laws vs the pooled failure (5-fold CV, kappa)

The pooled baseline reproduces `../sr_compare/COMPARISON.md` exactly.
Both engines select r = 3.846 x - 3.782 x² on all 17 rows. At x = 0 this
predicts r = 0, which is not a physical prediction and is scored 100%
wrong: **CV MedAPE 100%** (RMSE 123.5 and 122.3 W/mK).

| Engine | bulk-scope law (r = 1/kappa, 15 rows) | Own-scope CV MedAPE | Pooled law, same rows |
|---|---|---|---|
| minisr-pooled | r = 0.5898 x - 0.5407 x² + 4.924e-5 T | **60.9%** (RMSE 107.0) | 100% |
| hgsr (balanced) | r = 0.0513 (constant) | **67.0%** (RMSE 109.8) | 100% |

**The split removes the pooled failure mode but does not yet give a
usable bulk law.** The CV gain is 33 to 39 points, and the minisr bulk
law has the right physics signs: an alloy-scattering bowing term, and a
resistivity that rises with T. But 61% MedAPE is not a predictive law.
The reason shows in the data. At (x = 0, 300 K), the 7 "bulk" rows
span 20 to 393 W/mK: MD values from finite cells, experiments, and a
reference value probably taken from a thin film but labelled bulk by
the extractor.

## 6. Caveats (strengths and limitations)

- **Small n per class.** Only 2 reduced-dim rows have both x and T. C1
  therefore rests on the 42-row x-table, and every non-bulk scope is
  scope-limited with no claim until it reaches 12 fit-usable rows.
- **Extraction noise.** Class, method, x and T were read from paper
  snippets by an LLM. Mislabels, such as the 20 W/mK "bulk" Si row,
  enter as unmodelled scatter, and the within-cell scatter (s = 0.94)
  includes them.
- **Dependence, not causation.** CHD finds functional dependence in
  observational data. "Sample class explains ln kappa" is consistent
  with boundary and disorder scattering, but it is also consistent with
  a corpus correlation, for example if nano papers report lower-T
  measurements.
- **The calibrated detector is conservative.** It sees the dominant
  monotone driver only. A weaker secondary driver, such as the method
  class inside bulk, would be missed even if real.
- **Strength.** The decision is reproducible bit-for-bit: two full runs
  gave identical JSON outputs, and the rule was fixed before the data
  were touched. Two independent criteria (calibrated CHD and ANOVA)
  agree on sample class and reject method class.

**Next step for materials scientists.** Extract explicit microstructure
proxies from the papers (film thickness, wire diameter, grain size,
sample-preparation route), then re-run stage 0 with these variables.
Inside the bulk scope, method and finite-size provenance are the
leading suspects for the remaining scatter.

## Reproduce

```bash
python3 -m venv ~/venvs/chd
~/venvs/chd/bin/pip install ComputationalHypergraphDiscovery jax tqdm networkx matplotlib scipy
cd phase_c/chd                                # from the project root
~/venvs/chd/bin/python calibrate_chd.py       # about 8 min, 8 CPU workers -> calibration.json
~/venvs/chd/bin/python stage0_literature.py   # about 1 min -> stage0_results.json, split_decision.json
python3 ledger_split.py --dry-run             # prints the shard_operation payload; appends nothing
```

`ledger_split.py` without `--dry-run` appends the op
`split-literature-microstructure-2026-09-28` to `../ledger_campaign.jsonl`.
The append is idempotent.
