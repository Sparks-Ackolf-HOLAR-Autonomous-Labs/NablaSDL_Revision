# Independent second extractor for the literature party (2026-09-29)

This folder asks whether the stage-0 sample-class scope split
(`../STAGE0_RESULTS.md`, `../split_decision.json`) depends on who read the
papers. The literature party (67 rows of `pilot/kg/extracted_points.json`
with an all-digit corpusId) was machine-read from 20 Asta snippets by a
first extractor, a local Qwen3.6-35B served by vLLM. Its `system` label
fed `SAMPLE_GROUP` in `../stage0_data.py`, and so fed the split.

## 1. Method

**Second extractor.** A Claude model (Anthropic, claude-opus-5-5), which
is a different model family from the first extractor. It worked blind to
the first extractor's labels.

**Blinding protocol.** The snippets were re-located by recomputing
`snippet_hash = sha256(text)[:16]` exactly as in `pilot/kg/extract_kg.py`;
all 20 hashes resolved. The labeling view was a dump that showed, for
each snippet, the paper title, the snippet text, and, for each row, only
its index, `x_ge`, `T_K` and `kappa_W_mK`, used solely to locate the
datapoint in the text. The first extractor's `system` and `method`
fields were left out of the dump. The labels were written and saved
(`make_labels.py` -> `labels_second.json`) before any first-extractor
label, `stage0_results.json`, or `split_decision.json` was opened. One
caveat applies: the task brief named the seven class names and said the
split was bulk-scope driven. It gave no per-row labels.

**Label schema, per row.** The fields are:

- `sample_class`, one of {bulk, film, nanowire, nanostructured,
  superlattice, amorphous, other};
- `method`, one of {experiment, MD, BTE/DFT, model-fit, unclear};
- `confidence`;
- a verbatim `evidence_quote` of at most 25 words (the script asserts
  that it is a substring of the snippet);
- `thickness_nm`, `diameter_nm`, `grain_size_nm` and `prep_route` where
  stated;
- `value_in_snippet`, with `value_note`: verbatim, derived (arithmetic on
  snippet numbers), or absent;
- `material`, the chemistry of the quoted value.

The labels describe the sample form. Epitaxial-layer "microwires" were
labeled film, and metastable Si polymorphs were labeled other. Where a
value is a fixed bulk input to a fitted model, the method is model-fit.

**Agreement statistics** (`agreement.py` -> `agreement.json`). The
script reports raw agreement and Cohen's kappa for:

- the 7-way class;
- the 4-group `SAMPLE_GROUP` mapping (bulk / reduced-dim / amorphous /
  unclassified);
- the 5-way method;
- the 3-way `METHOD_GROUP`.

Each is computed on three row sets: all 67 rows, the 42-row x-table
(rows with x and kappa; used for criterion C1), and the 17-row fit table
(rows with x, T and kappa; used for criterion C2).

**Split sensitivity** (`sensitivity.py` -> `sensitivity.json`). This
script imports `stage0_literature.py` unchanged. It re-applies its C1
test (calibrated CHD, lin|maxinc, full variable set, with the same
table-choice rule) and its `evaluate_partition` C2 test to five
variants:

- **A**: the first extractor's labels. This reproduces
  `split_decision.json` exactly.
- **B**: the second extractor's sample group.
- **B_m**: the second extractor's sample group and method group.
- **C**: only the rows where both extractors agree on the group.
- **D**: the second extractor's labels, keeping only rows whose value is
  verbatim in the snippet, whose chemistry is SiGe-family, and whose
  x_ge is not misattributed.

CHD is cheap here, about 1 s per variant, so C1 was re-run in every
variant. Total runtime was under 10 s on 4 threads.

## 2. Agreement

| Row set | Label | n | Raw agreement | Cohen's kappa |
|---|---|---|---|---|
| all 67 | sample class, 7-way | 67 | 0.731 | 0.623 |
| all 67 | sample group, 4-way (split mapping) | 67 | 0.821 | 0.718 |
| all 67 | method, 5-way | 67 | 0.836 | 0.763 |
| all 67 | method group, 3-way | 67 | 0.925 | 0.862 |
| x-table (C1) | sample class, 7-way | 42 | 0.833 | 0.600 |
| x-table (C1) | sample group, 4-way | 42 | 0.857 | 0.653 |
| x-table (C1) | method, 5-way | 42 | 0.929 | 0.899 |
| fit table (C2) | sample class, 7-way | 17 | 0.941 | 0.730 |
| fit table (C2) | sample group, 4-way | 17 | 1.000 | 1.000 |
| fit table (C2) | method, 5-way | 17 | 1.000 | 1.000 |

**Class-level agreement is substantial; the group merge absorbs most of
the disagreement.** Of the 67 rows, 25 disagree on class or method: 18
on the 7-way class, 11 on method, 12 on the 4-way group, and 5 on the
method group. Six of the 18 class disagreements stay inside
reduced-dim: nanowire or nanostructured versus film for GeSn epilayer
microwires and one MIC-grown nanostructured SiGe film. Those six do
not change the split's group.

**The 12 group-level disagreements**, each row with its first label ->
second label and a short piece of evidence:

| Rows | First -> second | Evidence (second extractor) |
|---|---|---|
| 17-20 | bulk -> reduced-dim (nanostructured) | Ni/B co-doped SiGe; "scattering ... by ... nano to micro grain boundaries"; title says "nanostructuring" |
| 25 | reduced-dim (nanostructured) -> amorphous | "na-SiGe", an amorphous heterogeneous nanocomposite (MD) |
| 13, 14 | unclassified -> bulk | GeSn bulk-alloy theory value; polycrystalline Ge0.93Sn0.07 |
| 16, 29, 30 | unclassified -> reduced-dim (film) | suspended or unsuspended GeSn epilayer microwires |
| 50, 51 | bulk -> unclassified (other) | metastable Si-XII / Si-III polymorphs from dynamic decompression |

In the confusion matrix, rows are the first extractor and columns the
second. Every one of these 12 rows lacks x or T, so none enters the fit
table. Six of them enter the x-table (13, 17-20, 25).

**Method disagreements** fall into three groups:

- The first extractor called three MD rows "experiment" (a-Si, a-Ge and
  na-SiGe from Green-Kubo simulations, rows 23-25).
- It called three Raman-plus-thermal-model rows (45-47) "model-fit".
- It called two Raman rows on Si polymorphs (50, 51) "model-fit".

The full list, with both labels and the verbatim quotes, is in
`agreement.json` under `disagreements`.

## 3. Values not found in the snippet, and misattributions

**9 of 67 reported kappa values do not appear in the snippet text.**

- **7 are derived arithmetic.** The first extractor computed them
  instead of copying:
  - rows 8 and 9 (a-SiGe, 2.2 - 0.6 and 2.2 - 0.6 - 0.55);
  - rows 40 and 41 (1.06 +/- 0.16 split into 1.22 and 0.9, with the
    central 1.06 never extracted);
  - rows 53-55 (51 W/mK x 1.8, / 2, / 5, from "overshoot by about 80%"
    and "a factor of 2 and 5").
- **2 are absent.** Rows 29 and 30 (20.8 and 15.6 W/mK, GeSn) appear
  nowhere. The snippet gives a truncated ".1±2.8" and "18.2±2.6" for
  those samples, so these two are the only candidate hallucinations.
  Neither has x_ge, so neither enters any table.

**Further integrity problems, found while locating values.**

- **Rows 33 and 34** (fit table): x_ge is misattributed. The quoted "~20
  to ~9" W/mK is a range for bulk SiGe alloys, not pure Si (row 33,
  x_ge = 0). The "~9" belongs to 20% Ge, not to pure Ge (row 34,
  x_ge = 1).
- **Rows 17-20** (x-table): x is a Ni/B co-dopant level, not a Ge
  fraction.
- **15 rows are not SiGe-family chemistry.** 13 are GeSn, 1 is SiSn and
  1 is BiSbTe. Row 2 is pure Sn with x_ge = 0. Five of these (rows 2, 3,
  4, 5 and 13) enter the C1 x-table. None enters the fit table.

In total, 5 of the 17 fit-table rows are suspect: 53, 54 and 55
(derived) and 33 and 34 (misattributed). All five are in the bulk scope.

## 4. Sensitivity of the split decision

| Variant | Fit rows (bulk / red.-dim) | C1 (table, calibrated ancestors) | Bulk hgsr own vs pooled CV MedAPE | Bulk minisr-pooled own vs pooled | C2 | Adopted |
|---|---|---|---|---|---|---|
| A first extractor | 17 (15 / 2) | pass (x-table: amorph, rdim) | 67.0% vs 100.0% | 60.9% vs 100.0% | pass | yes |
| B second, sample group | 17 (15 / 2) | pass (x-table: amorph, rdim) | 67.0% vs 100.0% | 60.9% vs 100.0% | pass | yes |
| B_m second, sample and method | 17 (15 / 2) | pass (x-table: amorph, rdim) | 67.0% vs 100.0% | 60.9% vs 100.0% | pass | yes |
| C both agree on group | 17 (15 / 2); x-table 36 | pass (x-table: amorph) | 67.0% vs 100.0% | 60.9% vs 100.0% | pass | yes |
| D second, verbatim SiGe values only | 12 (10 / 2); x-table 24 | pass (x-table: amorph, rdim) | refused (10 < 12) | refused | fail | no |

**The C2 test is identical in variants A to C by construction.** The
two extractors assign identical groups to all 17 fit-table rows, and the
CV numbers reproduce `split_decision.json` to the digit.

**C1 also survives the relabeling.** The amorphous indicator is a
calibrated-CHD ancestor of ln kappa in every variant, including the
36-row agreement-only x-table. The reduced-dim indicator drops out only
in variant C.

**Variant D fails C2 on row count, not on fit.** Dropping the five
suspect bulk rows leaves 10 bulk rows. That is below `MIN_POINTS` = 12,
so the pre-stated rule refuses a bulk law, and C2 fails because no scope
is fittable.

**The C2 gain is measured against a degenerate baseline.** The pooled
law's 100.0% CV MedAPE comes from 8 of 17 invalid, non-positive
predictions. The 33 to 39 point gains are therefore gains over a pooled
law that fails, not over a working one, and the bulk-scope law's own CV
MedAPE of 61 to 67% is poor in absolute terms.

## 5. Verdict for the paper

- **The labeling survives.** An independent extractor from a different
  model family agrees with the split's 4-group labels at kappa = 0.72 on
  all 67 rows and at kappa = 1.00 on the 17 rows that decide C2. Both C1
  and C2 hold under the second extractor's labels and under
  agreement-only rows, so the sample-class split is not an artifact of
  the Qwen extractor's labeling. The 7-way class kappa (0.62) is
  noticeably lower. The paper should therefore claim agreement at the
  merged-group level only, where the pre-declared merge (made by
  physics, before results) is what makes the labeling robust.
- **The values are the weak point.** The second pass finds that 9 of 67
  values are not in the snippet (7 derived arithmetic, 2 absent). It
  also finds misattributed compositions in 6 rows and 15 non-SiGe rows
  in the "SiGe" party. Five of the 15 bulk rows that carry C2 are
  derived or misattributed. With only verbatim, correctly attributed
  SiGe-family values, the bulk scope falls to 10 rows, the pre-stated
  rule refuses it a law, and the split would not be adopted.
- **Recommended statement.** "The scope split is robust to an
  independent re-labeling (group-level Cohen's kappa 0.72 overall, 1.00
  on the decision rows), but its C2 evidence rests on 15 bulk rows, 5 of
  which a second extractor flags as derived or misattributed. Without
  them the bulk scope falls below the minimum size for a law." A
  value-level audit of the literature party, not a label audit, is the
  limiting step.

## Files

- `make_labels.py`: the second extractor's hand labels. It verifies each
  quote verbatim against its snippet and writes `labels_second.json`.
- `labels_second.json`: 67 rows of second-extractor labels.
- `agreement.py` -> `agreement.json`: kappa, confusion matrices,
  disagreements, values not found in the snippet, and non-SiGe rows.
- `sensitivity.py` -> `sensitivity.json`: C1 and C2 under variants A to
  D (run with `~/venvs/chd/bin/python`).
