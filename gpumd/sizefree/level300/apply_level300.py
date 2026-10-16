#!/usr/bin/env python3
"""Record the analysis of the 300 K level campaign on the ledger, then the
shard operation its pre-registered rule selects. Run only once
analysis_level300.json carries a final branch (fail after L1, or a/b/c
after L2). Idempotent."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
AN = os.path.join(HERE, "analysis_level300.json")
OPS = {"fail": ("scope_limit", "300 K level stays carried from 700-1100 K HNEMD; boxes to 48 cells or Fe down to 2.5e-5 did not give a converged linear point"),
       "a_strengthen": ("strengthen", "size-free 300 K level agrees with the carried factor; the 'carried' label is lifted"),
       "b_correct_T_dependent_level": ("correct", "the law takes a temperature-dependent level: median rho300 at 300 K, 1.281 at 700-1100 K, linear in between"),
       "c_downweight_shape_300K": ("downweight", "the law's composition shape at 300 K disagrees with size-free HNEMD")}


def main():
    a = json.load(open(AN))
    br = a.get("decision_branch")
    if br not in OPS:
        sys.exit(f"no final branch yet ({br}); run L2 first")
    camp = json.load(open(os.path.join(HERE, "level300_design.json")))["campaign"]
    led = Ledger(LEDGER)
    if any(e["payload"].get("op_id") == f"decision-{camp}" for e in led.entries):
        sys.exit("decision already recorded")
    pre = [e["seq"] for e in led.entries if e["kind"] == "preregistration"
           and e["payload"].get("campaign") == camp][0]
    bat = [e["seq"] for e in led.entries if e["kind"] == "batch_result"
           and e["payload"].get("campaign") == camp]
    e1 = led.append("analysis", {
        "op_id": f"analysis-{camp}", "campaign": camp, "prereg_seq": pre,
        "results_file": "gpumd/sizefree/level300/analysis_level300.json",
        "results_sha256": hashlib.sha256(open(AN, "rb").read()).hexdigest(),
        "G_lin": a["G_lin"], "G_conv": a["G_conv"], "Lstar": a["Lstar"],
        "median_rho300": a.get("median_rho300"), "cv_rho300": a.get("cv_rho300"),
        "branch": br, "predictions": a["predictions"],
        "statement": f"analysis by the script pushed with the pre-registration, after raw outputs were on the ledger (seq {bat})"})
    op, why = OPS[br]
    e2 = led.append("shard_operation", {
        "op_id": f"decision-{camp}", "campaign": camp, "op": op,
        "target": "P1 bulk kappa(x, T) law level at 300 K (gpumd/sizefree/corrected_law.json)",
        "decision": f"pre-registered rule (seq {pre}): {why}",
        "evidence": {"analysis_seq": e1["seq"], "batch_seqs": bat, "parent_decision_seq": 98}})
    assert led.verify_chain()
    print("analysis seq", e1["seq"], "decision seq", e2["seq"], op)


if __name__ == "__main__":
    main()
