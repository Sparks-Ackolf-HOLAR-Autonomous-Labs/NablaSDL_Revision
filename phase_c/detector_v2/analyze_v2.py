#!/usr/bin/env python3
"""Evaluate the registered predictions (design_v2.json) on
fault_study_results_v2.json and write results_v2.json. Run after
build_rows_v2.py (descriptors on the ledger) and fault_study_v2.py."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "fault_study_results_v2.json")))
E = {k: v["summary"] for k, v in R["entries"].items()}
n = 50
clean = R["clean_campaign"]["ops"]


def runs(pref, op=None):
    return {r for o in clean if op is None or o["op"] == op for r in o["target_runs"] if r.split("_")[0] in pref}


probes_split = {r.split("_")[0] for o in clean if o["op"] == "split" for r in o["target_runs"]}
scoped = {r.split("_")[0] for o in clean if o["op"] == "scope-limit" for r in o["target_runs"]}
other_bad = sorted({r for o in clean if o["op"] in ("forget", "quarantine", "correct")
                    for r in o["target_runs"]})
P = {}
P["Pr1"] = {"pass": {"N2", "N3"} <= probes_split and {"N0", "N1", "C37", "C38"} <= scoped
            and not other_bad and probes_split <= {"N2", "N3"},
            "split_points": sorted(probes_split), "scoped_points": sorted(scoped),
            "removal_or_correct_on_runs": other_bad}
m02 = E["M02"]
P["Pr2"] = {"pass": m02["detected_rate_adj"] >= 0.90 and m02["A_adj"].get("hit", 0) / n >= 0.80,
            "detected_adj": m02["detected_rate_adj"], "hit_adj": m02["A_adj"].get("hit", 0) / n}
P["Pr3"] = {"pass": E["M01"]["detected_rate_adj"] >= 0.90, "detected_adj": E["M01"]["detected_rate_adj"]}
P["Pr4"] = {"pass": E["P04"]["detected_rate_adj"] >= 0.70 and E["P05"]["detected_rate_adj"] >= 0.70
            and E["P03"]["detected_rate_adj"] >= 0.50,
            **{k: E[k]["detected_rate_adj"] for k in ("P03", "P04", "P05")}}
P["Pr5"] = {"pass": E["NULL"]["A"].get("hit", 0) == n and E["NULL"]["trials_with_collateral_adj"] / n <= 0.10,
            "hit": E["NULL"]["A"].get("hit", 0) / n, "collateral_adj": E["NULL"]["trials_with_collateral_adj"] / n}
P["Pr6"] = {"pass": E["V01"]["A_adj"].get("harmful", 0) / n >= 0.30,
            "harmful_adj": E["V01"]["A_adj"].get("harmful", 0) / n}
d2 = {"P01": 0.80, "P02": 1.00, "P06": 0.90}
P["Pr7"] = {"pass": all(E[k]["detected_rate_adj"] >= v - 0.10 for k, v in d2.items()),
            **{k: E[k]["detected_rate_adj"] for k in d2}}
gate = all(P[k]["pass"] for k in ("Pr1", "Pr2", "Pr3", "Pr4", "Pr5", "Pr7"))
table = {k: {"detected_adj": round(v["detected_rate_adj"], 2),
             "hit_adj": round(v["A_adj"].get("hit", 0) / n, 2),
             "harmful_adj": round(v["A_adj"].get("harmful", 0) / n, 2),
             "collateral_adj": round(v["trials_with_collateral_adj"] / n, 2),
             "detected_raw": round(v["detected_rate"], 2),
             "hit_raw": round(v["A"].get("hit", 0) / n, 2),
             "harmful_raw": round(v["A"].get("harmful", 0) / n, 2)} for k, v in E.items()}
out = {"predictions": P, "adopt": gate, "table": table, "clean_campaign_ops": clean}
json.dump(out, open(os.path.join(HERE, "results_v2.json"), "w"), indent=1, default=str)
for k, v in P.items():
    print(k, v)
print("ADOPT" if gate else "REJECT")
