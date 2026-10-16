#!/usr/bin/env python3
"""Write check300_design.json: the 300 K size check left open by the
size-free campaign (ledger 85-90). Box doubled AND driving force halved
(lesson of the seq-85 size check), four seeds per composition."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
parent = json.load(open(os.path.join(HERE, "..", "sizefree_design.json")))
a0 = {r["x_ge"]: r["a0_A"] for r in parent["runs"]}
pot = parent["runs"][0]["potential"]
runs = []
for x in (0.15, 0.85):
    for s in (57001, 57002, 57003, 57004):
        runs.append({"Fe_per_A": 1e-4, "T_K": 300, "a0_A": a0[x], "cells": [16, 8, 8],
                     "check": "size_halfFe", "config_seed": s, "in_law_domain": True,
                     "n_atoms": 8192, "potential": pot, "production_ns": 5.0,
                     "run_id": f"SiGe_x{x:g}_T300_fe1e-4_16x8x8_s{s}", "seed": s,
                     "stage": "C300", "system": "SiGe", "x_ge": x})
d = {
 "campaign": "gpumd-sizefree-check300-2026-10-04",
 "parent": "gpumd-sizefree-kappa-2026-10-02 (ledger seq 85, decision seq 90)",
 "question": "Is the 300 K size-free HNEMD level free of box-size effects, so the 300 K points can join the law-level decision?",
 "why": "seq-85 check G_size failed at x = 0.85 because two of three 16x8x8 runs at Fe = 2e-4 ran away (nonlinear response); the 8x8x8 runs at Fe = 1e-4 showed no runaway. Here the box is doubled and Fe halved, with four seeds.",
 "runs": runs, "n_runs": len(runs),
 "protocol": parent["protocol"] | {"placement": "execution detail: grn061 (granite sparks-gpu-grn) when no sparks job runs there, otherwise notchpeak-gpu-guest; moving between them needs only a placement note"},
 "run_gates": parent["run_gates"], "point_rule": parent["point_rule"],
 "agreement": parent["agreement"],
 "reference": "8x8x8 at Fe = 1e-4 (seq-85 linearity runs, 3 seeds, committed at seq 87) and the 8x8x8 Fe = 2e-4 base point",
 "gate": "G_size2(x): the 16x8x8 Fe = 1e-4 point (>= 2 passing runs) agrees with BOTH the 8x8x8 Fe = 1e-4 point and the 8x8x8 Fe = 2e-4 base point, for x = 0.15 and x = 0.85",
 "decision_rule": {
  "pass": "G_size2 passes at both x: re-apply the seq-85 rule (analyze_sizefree.py logic, unchanged) with the 300 K points included. If the branch is still correct_level and the new median rho is within 5% of 1.281: strengthen the seq-90 correction and drop the '300 K excluded' note. If still correct_level but more than 5% away: correct the level factor to the new median. Any other branch: apply that branch as defined at seq 85.",
  "fail": "G_size2 fails at either x: 300 K stays excluded; the 300 K law level is scope-labelled 'level carried from 700-1100 K HNEMD' (scope_limit entry); no factor change."
 },
 "predictions": {
  "PrC1": "no 16x8x8 Fe = 1e-4 run fails gate R4 (kappa < 2000 W/mK): no runaway at half the driving force",
  "PrC2": "G_size2 passes at both compositions",
  "PrC3": "with 300 K included, median rho stays in [1.2, 1.4] and CV <= 0.15 (branch correct_level)"
 },
 "paper": "P1 (law level at 300 K); P2 (a follow-up purchase that closes a gap a pre-registered rule left open)"
}
json.dump(d, open(os.path.join(HERE, "check300_design.json"), "w"), indent=1, sort_keys=True)
print(len(runs), "runs")
