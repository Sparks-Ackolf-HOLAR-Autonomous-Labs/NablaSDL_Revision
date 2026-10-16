#!/usr/bin/env python3
"""First autonomous acquisition (A2 seed, 2026-09-29).

Question: at 1100 K the two reasonable Tersoff->BTE-DFT calibrations
(symbolic transfer law vs per-regime interpolation) put the kappa-minimising
composition 0.2 apart, and no first-principles node exists above x = 0.5
inside the validity domain. One almaBTE point at x = 0.7 decides which
calibration to trust there. This script freezes, BEFORE any run exists:
the run spec, both calibrations' predictions at x = 0.7, and the decision
rule. preregister.py then hashes it onto the campaign ledger.
Usage: ~/mat_theory_pilot/venv/bin/python design_acquisition.py
"""
import json
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PC, "transfer_law"))
_SD = os.path.join(PC, "screening_demo", "screening_demo.py")
sd = types.ModuleType("sd")
sd.__file__ = _SD
exec(compile(open(_SD).read().split("# " + "-" * 64 + " run -----")[0], _SD, "exec"), sd.__dict__)

tl = json.load(open(os.path.join(PC, "transfer_law", "transfer_law_results.json")))
names = tl["selected"]["terms"][1:]
coef = np.array(tl["selected"]["coefs"])
B = {"x": lambda x, t: x, "x^2": lambda x, t: x ** 2, "x(1-x)": lambda x, t: x * (1 - x),
     "t": lambda x, t: t, "x t": lambda x, t: x * t, "t^2": lambda x, t: t ** 2}


def r_sym(x, T):
    t = T / 1000.0
    return float(np.exp(coef[0] + sum(c * B[n](x, t) for n, c in zip(names, coef[1:]))))


X, T_DEC = 0.7, 1100.0
preds = {}
for T in (300.0, 700.0, 1100.0):
    k_law = float(sd.law_kappa(sd.LAW_TERMS, X, T)[0])
    preds[str(int(T))] = {
        "in_validity_domain": bool(sd.in_domain(X, T)),
        "kappa_tersoff_law": round(k_law, 4),
        "kappa_BTE_pred_symbolic_transfer": round(k_law * r_sym(X, T), 4),
        "kappa_BTE_pred_interpolated_calibration": round(float(sd.scope_kappa(sd.LAW_TERMS, X, T)[0]), 4),
    }
p = preds["1100"]
ks, ki = p["kappa_BTE_pred_symbolic_transfer"], p["kappa_BTE_pred_interpolated_calibration"]
design = {
    "action": "acq-x0.7-T1100-2026-09-29",
    "decides": "which Tersoff->BTE-DFT calibration governs the Ge-rich side at 1100 K "
               "(symbolic transfer law argmin x=0.645 vs interpolated calibration argmin x=0.43)",
    "why_this_point": "transfer_law/README.md: no BTE node above x=0.5 inside the domain at 1100 K; "
                      "largest calibration disagreement per unit cost (about one guest CPU-hour)",
    "runs": [{"tool": "almabte/1.3.2", "method": "VCA + mass disorder, full iterative BTE",
              "x_Ge": X, "grid": 24, "T_K": [300, 700, 1100],
              "protocol": "party4_bte/run_bte_point.sh unchanged (same as the 18 party-4a points)",
              "partition": "notchpeak-guest / owner-guest (grn061 off-limits)"}],
    "predictions": preds,
    "decision_rule": {
        "primary_T_K": 1100,
        "D1_winner": "the calibration with smaller |ln(k_obs/k_pred)| at 1100 K wins; "
                     "if both are within 10% of k_obs, or their |ln| errors differ by < 0.03, "
                     "the verdict is 'undecided at this resolution'",
        "D2_refit": "append all in-domain x=0.7 nodes to the BTE node set, rerun transfer_law.py "
                    "(same basis, same selection rule, no other change) and report the new 1100 K "
                    "argmin x and 5% window",
        "D3_screening_verdict": "if the refit 1100 K argmin lies within 0.05 of one calibration's "
                                "pre-acquisition argmin (0.645 symbolic, 0.43 interpolated), that "
                                "answer is confirmed; otherwise both are refuted and the new argmin "
                                "is reported with the window",
        "D4_ledger": "the outcome is ledgered as a shard operation: 'strengthen' on the winning "
                     "calibration, 'downweight' on the loser (never forget; both remain archived)",
        "sanity_gate": "reject and rerun (logged deviation) only if k_obs(1100) lies outside the "
                       "bracket of the neighbouring BTE nodes' physical range (x=0.5 and x=0.85 "
                       "values at 700-1100 K, times 0.5 to 2)",
    },
    "prediction_gap_1100K_pct": round(100 * abs(ks - ki) / min(ks, ki), 1),
}
json.dump(design, open(os.path.join(HERE, "acquisition_design.json"), "w"), indent=1, sort_keys=True)
print(json.dumps(preds, indent=1)); print("gap %", design["prediction_gap_1100K_pct"])
