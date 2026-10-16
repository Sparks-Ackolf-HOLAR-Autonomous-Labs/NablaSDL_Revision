# CHD (Computational Hypergraph Discovery) before the symbolic regression

Question considered (2026-09-26): should CHD
(https://arxiv.org/abs/2311.17007) run before the symbolic regression?

## The paper, verified

Bourdais, Batlle, Yang, Baptista, Rouquette, Owhadi, *Codiscovering
graphical structure and functional relationships within data: A Gaussian
Process framework for connecting the dots*, **PNAS 121 (2024)**, DOI
[10.1073/pnas.2403449121](https://doi.org/10.1073/pnas.2403449121),
arXiv 2311.17007, Semantic Scholar CorpusId 271644249. Open source:
`pip install ComputationalHypergraphDiscovery` (v2.1.0, jax-based).

What it does: for a set of observed variables, it decides — via GP
regression with kernel-mode/ANOVA decomposition and a noise-vs-signal
ratio — which variables are functions of which others, and returns that
dependency structure as a hypergraph (a node's ancestors form a
hyperedge). Polynomial cost, no sparsity or DAG assumptions, no
controlled interventions needed. It discovers **structure among
variables**; it does not produce closed-form laws.

## Verdict: yes, as a Phase C stage-0, with specific jobs

CHD and our SR are complementary, not competing: CHD answers "which
variables does kappa actually depend on, per evidence group", SR answers
"what is the functional form". Right now our pipeline *assumes* the
answer to the first question (r = f(x, T, L) with a hand-fixed basis).
Three concrete jobs, in value order:

1. **Missing-variable detection on the literature party.** The
   cross-engine finding (`../sr_compare/COMPARISON.md`): every engine fails on the raw
   literature party (87-100% CV MedAPE) because kappa at equal (x, T)
   spans two orders of magnitude across bulk/film/nano samples. CHD run
   per candidate variable set can quantify that (x, T) leave kappa
   mostly unexplained (high noise ratio) and, once microstructure
   proxies are extracted from the papers (film thickness, grain size,
   sample class), confirm which of them carry the signal. That turns
   the planned literature scope-**split** from a judgment call into a
   measured decision — and the split threshold arriving from data is
   exactly the stage-1/stage-4 coupling the design doc wants.
2. **Basis-input audit for HG-SR/PySR.** Run CHD on (x, T, L, seed,
   gradient, kappa) for the MD parties: it should find kappa depends on
   (x, T, L) and NOT on seed or imposed gradient. "Seed shows up as an
   ancestor" would be a red flag on the protocol itself — a cheap
   automated anomaly detector in front of every SR refit.
3. **Structure disagreement as a shard signal.** Run CHD per party:
   parties disagreeing about the *structure* (literature kappa depends
   on a microstructure variable, MD kappa cannot) is precisely the
   scope-limit trigger, discovered rather than asserted.

Placement: after evidence assembly, before basis construction — a
stage-0 "which variables, per party" pass whose output (per-party
ancestor sets + noise ratios) is committed alongside the evidence table
and re-run on every shard operation that changes rows.

## Smoke test on the DGX (2026-09-26, native py312 udocker container)

v2.1.0 installs and runs on aarch64 (jax CPU): 60 synthetic points with
r = 0.1 + 2x(1−x) + 1e-4·T + noise, variables (x, T, junk, r). Runtime
under a second per node. Found `x -> r` (true); with all defaults it
also drew spurious edges (`junk -> x`, `x -> T`, and missed the weak T
signal). So: mechanically viable today, but the noise-ratio threshold
and kernel choice must be tuned on planted cases before any conclusion
is trusted, and our smallest tables (17-24 rows) are near its lower
edge. Budget a planted-fault calibration exactly like the one the shard
machinery got (fault catalog, null campaign).

## Literature check (did anyone do this already?)

Originally run 2026-09-26 on the public Semantic Scholar API;
**re-run 2026-09-27 through Asta** (`asta_search_results/q20-q24_*_asta.json`; full
write-up in `../../07_asta_lit_recheck.md`). The verdict survived and
sharpened:

- All 11 citations of the CHD paper (q20, confirmed by Asta) are
  methods/applied-math follow-ups (kernel ROM, functional PDEs, digital
  twins, Koopman, algorithm discovery). **None** apply CHD to materials
  data, none put it in front of a symbolic-regression pipeline, and
  none couple structure discovery to provenance or belief revision.
  Also cite the CHD precursor: Owhadi, *Computational graph
  completion*, Res. Math. Sci. 2021 (DOI 10.1007/s40687-022-00320-8) —
  per q22 it is essentially the only other paper in the line.
- The structure-discovery-before-equation-discovery coupling has real
  prior art to cite: the survey **Camps-Valls et al., "Discovering
  causal relations and equations from data", Physics Reports 2023**,
  and — found only by the real-Asta pass — **Jia et al., "Governing
  equation discovery based on causal graph for nonlinear dynamic
  systems", Mach. Learn.: Sci. Technol. 2023** (DOI
  10.1088/2632-2153/acffa4), which feeds discovered causal structure
  into equation discovery directly (dynamic-systems benchmarks, single
  evidence source, no provenance/revision). The 2026 "Probabilistic
  Symbolic Regression with Causal Discovery" preprint is **downgraded**:
  it is a Zenodo-only deposit (DOI 10.5281/zenodo.22334876), absent
  from the Semantic Scholar corpus, zero citations — a completeness
  citation, not a threat.

So the defensible claim is scoped: not "structure discovery before SR"
(taken, most concretely by Jia et al. 2023), but "per-party structure
discovery on a provenance hypergraph, with cross-party structure
disagreement as a shard-operation trigger". Cite: the CHD paper, Owhadi
2021, Camps-Valls 2023, Jia 2023, and the Zenodo preprint for
completeness.
