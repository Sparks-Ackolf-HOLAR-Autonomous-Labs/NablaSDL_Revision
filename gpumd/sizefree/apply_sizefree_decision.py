#!/usr/bin/env python3
"""Apply the pre-registered decision rule (ledger seq 85) to the committed
size-free analysis: record the analysis on the ledger, then the shard
operation the rule selects. Writes corrected_law.json. Idempotent."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
AN = os.path.join(HERE, "analysis_sizefree.json")


def main():
    a = json.load(open(AN))
    design = json.load(open(os.path.join(HERE, "sizefree_design.json")))
    led = Ledger(LEDGER)
    camp = design["campaign"]
    if any(e["payload"].get("op_id") == f"decision-{camp}" for e in led.entries):
        sys.exit("decision already recorded")
    assert a["decision_branch"] == "correct_level", a["decision_branch"]
    s = hashlib.sha256(open(AN, "rb").read()).hexdigest()
    used = [p for p in a["points"] if p["in_law_domain"] and
            (p["T"] != 300 or a["300K_used_in_decision"])]
    e1 = led.append("analysis", {
        "op_id": f"analysis-{camp}", "campaign": camp, "prereg_seq": 85,
        "results_file": "gpumd/sizefree/analysis_sizefree.json",
        "results_sha256": s, "checks": {k: v for k, v in a["checks"].items()
                                        if k.startswith("G_")},
        "300K_used_in_decision": a["300K_used_in_decision"],
        "n_decision_points": a["n_decision_points"],
        "median_rho": a["median_rho"], "cv_rho": a["cv_rho"],
        "predictions": a["predictions"],
        "statement": "analysis run by the script committed with the "
                     "pre-registration, after raw outputs were on the ledger "
                     "(seq 87-88)"})
    f = a["median_rho"]
    law = design["law_under_test"]
    corrected = {
        "campaign": camp, "ledger_analysis_seq": e1["seq"],
        "level_factor": f,
        "form": f"kappa(x, T) = {f} / (0.2092492 + 1.9190900 x - 2.2443438 x^2"
                " + 8.352241e-5 T)",
        "parent_law": law,
        "scope_label": "level from HNEMD, shape from rNEMD",
        "domain": "x in [0.05, 0.90], 300 K <= T <= 0.85 T_solidus, "
                  "crystalline Tersoff-1989 SiGe",
        "decision_points": [{k: p[k] for k in ("x", "T", "kappa", "se",
                                              "law", "rho")} for p in used]}
    json.dump(corrected, open(os.path.join(HERE, "corrected_law.json"), "w"),
              indent=1)
    e2 = led.append("shard_operation", {
        "op_id": f"decision-{camp}", "campaign": camp, "op": "correct",
        "target": "P1 bulk kappa(x, T) law level (phase_c/final_law)",
        "cause": "identified: the rNEMD 1/L extrapolation underestimates the "
                 "infinite-box level; size-free HNEMD reads above the law at "
                 "every in-domain point used",
        "decision": f"pre-registered branch correct_level: median rho {f} > "
                    f"1.15, CV {a['cv_rho']} <= 0.15; law shape kept, level "
                    f"multiplied by {f}",
        "evidence": {"analysis_seq": e1["seq"], "batch_seqs": [87, 88],
                     "corrected_law_file": "gpumd/sizefree/corrected_law.json"},
        "effect": "every claim resting on the absolute Tersoff law level "
                  "(Tersoff-vs-BTE bias factors, law-vs-experiment ratios) "
                  "is re-read with the corrected level; composition and "
                  "temperature shape claims are unchanged"})
    assert led.verify_chain()
    print("analysis seq", e1["seq"], "decision seq", e2["seq"])


if __name__ == "__main__":
    main()
