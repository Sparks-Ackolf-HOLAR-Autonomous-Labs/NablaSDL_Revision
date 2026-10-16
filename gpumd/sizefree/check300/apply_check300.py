#!/usr/bin/env python3
"""Record the analysis of the 300 K size check on the ledger, then the
shard operation its pre-registered rule selects. Idempotent."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
from ledger import Ledger  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
AN = os.path.join(HERE, "analysis_check300.json")


def main():
    a = json.load(open(AN))
    d = json.load(open(os.path.join(HERE, "check300_design.json")))
    camp = d["campaign"]
    led = Ledger(LEDGER)
    if any(e["payload"].get("op_id") == f"decision-{camp}" for e in led.entries):
        sys.exit("decision already recorded")
    pre = [e["seq"] for e in led.entries if e["kind"] == "preregistration"
           and e["payload"].get("campaign") == camp][0]
    bat = [e["seq"] for e in led.entries if e["kind"] == "batch_result"
           and e["payload"].get("campaign") == camp]
    e1 = led.append("analysis", {
        "op_id": f"analysis-{camp}", "campaign": camp, "prereg_seq": pre,
        "results_file": "gpumd/sizefree/check300/analysis_check300.json",
        "results_sha256": hashlib.sha256(open(AN, "rb").read()).hexdigest(),
        "gates": a["gates"], "rule_with_300K": a.get("rule_with_300K"),
        "decision": a["decision"], "predictions": a["predictions"],
        "statement": "analysis by the script pushed with the pre-registration, "
                     f"after raw outputs were on the ledger (seq {bat})"})
    dec = a["decision"]
    target = "P1 bulk kappa(x, T) law level at 300 K (gpumd/sizefree/corrected_law.json)"
    if dec == "strengthen_seq90":
        op, why = "strengthen", ("300 K size check passes; with 300 K included the "
                                 f"rule gives median rho {a['rule_with_300K']['median_rho']}, "
                                 "within 5% of 1.281; the seq-90 factor now covers 300 K")
    elif dec == "correct_factor":
        op, why = "correct", ("300 K size check passes; with 300 K included the "
                              f"level factor becomes {a['rule_with_300K']['median_rho']}")
    elif dec == "scope_limit_300K":
        op, why = "scope_limit", ("300 K size check fails; the 300 K level stays "
                                  "carried from 700-1100 K HNEMD")
    else:
        op, why = dec.replace("apply_branch_", ""), "branch per seq-85 rule with 300 K included"
    e2 = led.append("shard_operation", {
        "op_id": f"decision-{camp}", "campaign": camp, "op": op, "target": target,
        "decision": f"pre-registered rule (seq {pre}): {why}",
        "evidence": {"analysis_seq": e1["seq"], "batch_seqs": bat,
                     "parent_decision_seq": 90}})
    assert led.verify_chain()
    print("analysis seq", e1["seq"], "decision seq", e2["seq"], op)


if __name__ == "__main__":
    main()
