#!/usr/bin/env python3
"""Apply the pre-registered decision rule (acquisition_design.json, ledger
seq 34) to the collected almaBTE x = 0.7 points. Refuses to run if the
design file no longer matches its pre-registered hash. Writes decision.json
and transfer_law_refit.json here; appends the resulting shard operations
to the campaign ledger (idempotent).
Usage: ~/mat_theory_pilot/venv/bin/python decide_acquisition.py
"""
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MT, "pilot", "src"))
sys.path.insert(0, os.path.join(MT, "phase_c", "transfer_law"))
from ledger import Ledger  # noqa: E402

blob = open(os.path.join(HERE, "acquisition_design.json"), "rb").read()
sha = hashlib.sha256(blob).hexdigest()
assert sha == open(os.path.join(HERE, "PREREGISTERED_SHA256")).read().strip(), "design changed after registration"
D = json.loads(blob)
X = D["runs"][0]["x_Ge"]
obs = {}
for T in (300, 700, 1100):
    f = os.path.join(MT, "party4_bte", "results", f"bte_x{X}_T{T}.json")
    obs[T] = json.load(open(f))["kappa_W_mK"]

# D1: which calibration predicted k_obs(1100) better
p = D["predictions"]["1100"]
ko = obs[1100]
es = abs(np.log(ko / p["kappa_BTE_pred_symbolic_transfer"]))
ei = abs(np.log(ko / p["kappa_BTE_pred_interpolated_calibration"]))
undecided = (es < np.log(1.10) and ei < np.log(1.10)) or abs(es - ei) < 0.03
winner = None if undecided else ("symbolic_transfer" if es < ei else "interpolated_calibration")

# sanity gate: neighbouring BTE nodes x=0.5 and x=0.85 at 700-1100 K, times 0.5..2
nb = [json.load(open(os.path.join(MT, "party4_bte", "results", f"bte_x{x}_T{T}.json")))["kappa_W_mK"]
      for x in (0.5, 0.85) for T in (700, 1100)]
gate = 0.5 * min(nb) <= ko <= 2.0 * max(nb)

# D2: refit the transfer law with the new in-domain nodes (same basis and rule)
import transfer_law as tl  # noqa: E402
added = []
for T, k in obs.items():
    if tl.sd.in_domain(X, float(T)):
        tl.sd.BTE[(X, float(T))] = k
        added.append(T)
tl.HERE = HERE
tl.main()
os.replace(os.path.join(HERE, "transfer_law_results.json"), os.path.join(HERE, "transfer_law_refit.json"))
refit = json.load(open(os.path.join(HERE, "transfer_law_refit.json")))
d1100 = refit["decisions"]["1100"]["symbolic_transfer"]
xnew = d1100["argmin_x"]

# D3
pre = {"symbolic_transfer": 0.645, "interpolated_calibration": 0.43}
confirmed = [k for k, v in pre.items() if abs(xnew - v) <= 0.05]
dec = {"design_sha256": sha, "observed_kappa_W_mK": obs,
       "abs_ln_error_1100K": {"symbolic_transfer": round(float(es), 4),
                              "interpolated_calibration": round(float(ei), 4)},
       "D1_winner": winner or "undecided at this resolution",
       "sanity_gate_pass": bool(gate), "nodes_added_T_K": added,
       "D2_refit_selected": refit["selected"],
       "D2_refit_1100K": {k: d1100.get(k) for k in ("argmin_x", "kappa_min", "window")},
       "D3_confirmed": confirmed or "both refuted"}
json.dump(dec, open(os.path.join(HERE, "decision.json"), "w"), indent=1, default=float)
print(json.dumps(dec, indent=1, default=float))
if not gate:
    sys.exit("sanity gate failed: log a deviation and rerun, do not ledger")

# D4
dsha = hashlib.sha256(open(os.path.join(HERE, "decision.json"), "rb").read()).hexdigest()
led = Ledger(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))
common = {"action": D["action"], "decision_file": "phase_c/acquisition_x07/decision.json",
          "decision_sha256": dsha}
ops = []
if winner:
    loser = "interpolated_calibration" if winner == "symbolic_transfer" else "symbolic_transfer"
    ops = [{"op": "strengthen", "op_id": f"acq07-strengthen-{winner}", "target": winner,
            "cause": f"pre-registered D1: |ln err| {dec['abs_ln_error_1100K'][winner]} vs {dec['abs_ln_error_1100K'][loser]}"},
           {"op": "downweight", "op_id": f"acq07-downweight-{loser}", "target": loser,
            "cause": "pre-registered D1 loser; archived, not forgotten"}]
ops.append({"op": "re-anchor", "op_id": "acq07-transfer-law-refit", "target": "transfer_law",
            "nodes_added": [f"x{X}_T{T}" for T in added], "selected_after": refit["selected"]})
for op in ops:
    if any(e["payload"].get("op_id") == op["op_id"] for e in led.entries):
        continue
    e = led.append("shard_operation", dict(op, **common))
    print(op["op"], "-> seq", e["seq"])
assert led.verify_chain()
