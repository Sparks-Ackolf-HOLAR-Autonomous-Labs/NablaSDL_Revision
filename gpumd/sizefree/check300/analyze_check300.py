#!/usr/bin/env python3
"""Analyse the 300 K size check exactly as pre-registered in
check300_design.json. Reads only the committed copies under raw/ (stage
C300 must be on the ledger) and the parent campaign's committed analysis
(analysis_sizefree.json, ledger seq 89). Writes analysis_check300.json.
Written and pushed before any run output existed."""
import json
import math
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "production"))
sys.path.insert(0, os.path.join(HERE, ".."))
from analyze_campaign import run_stats  # noqa: E402
from analyze_sizefree import est, agree  # noqa: E402

LEDGER = os.path.join(MT, "phase_c", "ledger_campaign.jsonl")
DESIGN = json.load(open(os.path.join(HERE, "check300_design.json")))
PARENT = json.load(open(os.path.join(HERE, "..", "analysis_sizefree.json")))
SEQ90_FACTOR = 1.281


def committed():
    for l in open(LEDGER):
        e = json.loads(l)
        if (e["kind"] == "batch_result" and
                e["payload"].get("campaign") == DESIGN["campaign"]):
            return True
    return False


def rule(points, ok300):
    """seq-85 decision rule, unchanged (analyze_sizefree.main)."""
    use = [p for p in points if p["in_law_domain"] and (p["T"] != 300 or ok300)]
    rhos = [p["rho"] for p in use]
    med = st.median(rhos)
    cv = st.stdev(rhos) / st.mean(rhos)
    if 0.85 <= med <= 1.15 and all(abs(r - 1) <= 0.25 for r in rhos):
        b = "strengthen"
    elif med > 1.15:
        b = "correct_level" if cv <= 0.15 else "replace_level"
    elif med < 0.85:
        b = "downweight"
    else:
        b = "no_rule_matched"
    return {"n_points": len(use), "median_rho": round(med, 4),
            "cv_rho": round(cv, 4), "branch": b}


def main():
    if not committed():
        sys.exit("REFUSING: stage C300 not on the ledger")
    runs = [dict(r, **run_stats(os.path.join(HERE, "raw", r["run_id"]), r))
            for r in DESIGN["runs"]]
    gates, vals = {}, {}
    for x in (0.15, 0.85):
        size2 = est([r for r in runs if r["x_ge"] == x])
        ref = PARENT["checks"][f"values_x{x}"]
        lin, base = ref["lin"], ref["base"]
        gates[f"G_size2_x{x}"] = bool(size2 and lin and base and agree(size2, lin)
                                      and agree(size2, base))
        vals[f"x{x}"] = {"size2_16x8x8_fe1e-4": size2, "ref_8x8x8_fe1e-4": lin,
                         "base_8x8x8_fe2e-4": base}
    ok = all(gates.values())
    out = {"campaign": DESIGN["campaign"],
           "runs": [{k: r[k] for k in ("run_id", "kappa", "sem", "drift_z",
                                       "mean_T", "gates", "pass")} for r in runs],
           "gates": gates, "values": vals, "pass": ok}
    if ok:
        d = rule(PARENT["points"], True)
        out["rule_with_300K"] = d
        if d["branch"] == "correct_level":
            if abs(d["median_rho"] / SEQ90_FACTOR - 1) <= 0.05:
                out["decision"] = "strengthen_seq90"
            else:
                out["decision"] = "correct_factor"
        else:
            out["decision"] = "apply_branch_" + d["branch"]
    else:
        out["decision"] = "scope_limit_300K"
    pr = {"PrC1": all(r["gates"]["R4_physical"] for r in runs),
          "PrC2": ok}
    if ok:
        d = out["rule_with_300K"]
        pr["PrC3"] = (d["branch"] == "correct_level" and 1.2 <= d["median_rho"] <= 1.4)
    else:
        pr["PrC3"] = None
    out["predictions"] = pr
    json.dump(out, open(os.path.join(HERE, "analysis_check300.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in ("gates", "pass", "decision", "predictions")}
                     | {"rule": out.get("rule_with_300K")}, indent=1))


if __name__ == "__main__":
    main()
