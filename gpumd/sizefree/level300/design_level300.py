#!/usr/bin/env python3
"""Write level300_design.json: the 300 K law-level campaign that the
check at ledger 91-98 left open (run 2026-10-04). Longer boxes,
lower driving force and more seeds together (lesson of the ledger 91-98
check).
Stage L1 settles box length and linearity at x = 0.15 and 0.85; stage L2
measures the four inner compositions at the box length L1 selects, by a
rule fixed here before any run exists."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
parent = json.load(open(os.path.join(HERE, "..", "sizefree_design.json")))
a0 = {r["x_ge"]: r["a0_A"] for r in parent["runs"] if r["T_K"] == 300}
pot = parent["runs"][0]["potential"]
FE, FE_LIN = 5e-5, 2.5e-5


def row(x, nx, fe, seed, check, stage, l2_box=None):
    n = 8 * nx * 8 * 8
    r = {"Fe_per_A": fe, "T_K": 300, "a0_A": a0[x], "cells": [nx, 8, 8],
         "check": check, "config_seed": seed, "in_law_domain": True,
         "n_atoms": n, "potential": pot, "production_ns": 5.0,
         "run_id": f"SiGe_x{x:g}_T300_fe{fe:g}_{nx}x8x8_s{seed}", "seed": seed,
         "stage": stage, "system": "SiGe", "x_ge": x}
    if l2_box:
        r["l2_box"] = l2_box
    return r


runs = []
for x in (0.15, 0.85):
    for nx, seeds in ((16, 4), (32, 4), (48, 3)):
        for s in range(seeds):
            runs.append(row(x, nx, FE, 58001 + s, "size", "L1"))
    for s in range(3):
        runs.append(row(x, 32, FE_LIN, 58101 + s, "linearity", "L1"))
for box in (16, 32):
    for x in (0.2, 0.3, 0.5, 0.7):
        for s in range(3):
            runs.append(row(x, box, FE, 58201 + s, "main", f"L2-box{box}", box))

d = {
 "campaign": "gpumd-sizefree-level300-2026-10-04",
 "parent": "gpumd-sizefree-kappa-2026-10-02 (ledger 85-90) and gpumd-sizefree-check300-2026-10-04 (ledger 91, 96-98: scope_limit)",
 "question": "What is the box-size-free, linear-response 300 K HNEMD level of Tersoff-1989 SiGe across x = 0.15-0.85, and does it agree with the level factor 1.281 carried from 700-1100 K?",
 "why": "ledger 98 kept the 300 K level carried from 700-1100 K because 16x8x8 at Fe = 1e-4 read 66% above 8x8x8 at x = 0.15 and 3 of 8 runs grew exponentially (onset 1-3 ns). Here the driving force is halved again (5e-5, linearity at 2.5e-5) and the box is extended to 32 and 48 cells along the driving direction.",
 "runs": runs,
 "n_runs": len(runs),
 "n_runs_L1": sum(r["stage"] == "L1" for r in runs),
 "n_runs_L2_per_box": 12,
 "protocol": parent["protocol"] | {
   "placement": "execution detail: grn061 (granite sparks-gpu-grn) when no sparks-partition job runs there, otherwise notchpeak-gpu-guest A40 (--gres=gpu:a40:1); moving between them needs only a placement note",
   "stage_order": ["L1", "L2-box<Lstar> (only the box L1 selects is built and run)"]},
 "run_gates": parent["run_gates"], "point_rule": parent["point_rule"],
 "agreement": parent["agreement"],
 "level_factor_carried": 1.281,
 "law": "kappa_law(x, T) = 1 / (0.2092492 + 1.9190900 x - 2.2443438 x^2 + 8.352241e-5 T) (phase_c/final_law/final_law.json)",
 "gates": {
   "G_lin": "at x = 0.15 and 0.85, the 32x8x8 point at Fe = 2.5e-5 agrees with the 32x8x8 point at Fe = 5e-5",
   "G_conv": "at x = 0.15 and 0.85, the 32x8x8 point agrees with the 48x8x8 point",
   "Lstar": "if G_lin and G_conv pass: Lstar = 16 if the 16x8x8 point also agrees with the 48x8x8 point at both x, else Lstar = 32. If either gate fails: no Lstar, L2 is not run"
 },
 "decision_rule": {
   "fail": "G_lin or G_conv fails: the 300 K level stays carried from 700-1100 K (ledger 98 label kept); the L1 values are recorded as evidence that 300 K needs boxes beyond 48 cells or a different estimator; no factor change",
   "pass": "rho300(x) = kappa(x, 300 K at Lstar) / kappa_law(x, 300) over x = 0.15, 0.2, 0.3, 0.5, 0.7, 0.85 (each needs >= 2 passing runs; if fewer than 5 points qualify, branch fail). Let m = median rho300, cv = stdev/mean. (a) cv <= 0.15 and |m/1.281 - 1| <= 0.10: strengthen the ledger-90 level correction at 300 K and lift the 'carried' label. (b) cv <= 0.15 and |m/1.281 - 1| > 0.10: correct, a temperature-dependent level: the corrected law takes factor m at 300 K and 1.281 at 700-1100 K, linear in T between 300 and 700 K, scope label 'level from HNEMD at each T, shape from rNEMD'. (c) cv > 0.15: downweight the law's composition shape at 300 K (scope label 'composition shape at 300 K disagrees with size-free HNEMD'); no refit in this registration"
 },
 "predictions": {
   "PrL1": "no run at Fe <= 5e-5 fails gates R3 or R4 (no runaway)",
   "PrL2": "at both x the point means rise with box length, 16 < 48 (the 32 point within agreement of either neighbour allowed)",
   "PrL3": "G_lin and G_conv pass, with Lstar = 32",
   "PrL4": "branch (b) with m > 1.281: the 300 K level sits above the factor carried from 700-1100 K"
 },
 "cost_estimate": "L1 28 runs, about 25 A40-hours (15 min per 8192 atoms x 5 ns on H100, 28 min on A40); L2 12 runs, about 11 A40-hours at Lstar = 32 (6 at Lstar = 16)",
 "paper": "P1 (law level at 300 K); P2 (a second follow-up purchase on a gap a registered rule left open, with a box length chosen by a rule fixed before the data)"
}
json.dump(d, open(os.path.join(HERE, "level300_design.json"), "w"), indent=1, sort_keys=True)
print(len(runs), "runs in design;", d["n_runs_L1"], "in L1")
