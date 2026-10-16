#!/usr/bin/env python3
"""Apply the pre-registered decision rule (shard_action_design.json,
ledger seq 19) to the collected shard-action runs. Refuses to run if the
design no longer matches PREREGISTERED_SHA256 or if the results batch is
not yet committed to the ledger (commit_results.py). Writes decision.json.
1/L is taken as 1/ncz: at fixed composition the box length is
proportional to ncz, so kappa_inf and the T3 residual are unchanged
(this is exactly detector.points_of).
Usage: python3 decide.py
"""
import hashlib
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.abspath(os.path.join(HERE, "..", ".."))
blob = open(os.path.join(HERE, "shard_action_design.json"), "rb").read()
assert hashlib.sha256(blob).hexdigest() == open(
    os.path.join(HERE, "PREREGISTERED_SHA256")).read().strip(), "design changed"
design = json.loads(blob)
led = [json.loads(l) for l in open(os.path.join(MT, "phase_c", "ledger_campaign.jsonl"))]
if not any(e["payload"].get("op_id") == "commit-" + design["action"] for e in led):
    sys.exit("REFUSING: results not committed to the ledger yet")

new = {r["run_id"]: json.load(open(os.path.join(HERE, "results", r["run_id"] + ".json")))
       for r in design["runs"]}
orig = {rid: json.load(open(os.path.join(MT, "phase_c", "production", "results", rid + ".json")))
        for rid in [f"{p}_z{n}" for p in ("C37", "C38") for n in (24, 48, 96)]}


def k(j):
    return j.get("kappa_W_mK_full") or j["kappa_W_mK"]


def fit(series):  # series: {ncz: kappa} -> a, b in 1/kappa = a + b/ncz
    xs = [1.0 / n for n in series]
    ys = [1.0 / v for v in series.values()]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


out = {"series": {}, "tests": {}, "decisions": {}}
ser = {}
for base in ("C37", "C38"):
    ser[f"{base}_orig"] = {n: k(orig[f"{base}_z{n}"]) for n in (24, 48, 96)}
    for rid, r in new.items():
        if rid.startswith(base + "r"):
            ser.setdefault(rid.split("_")[0], {})[r["ncz"]] = k(r)
for tag in ("G90_T866", "G97_T866"):
    ser[tag] = {r["ncz"]: k(r) for rid, r in new.items() if rid.startswith(tag)}
for name, s in ser.items():
    a, b = fit(s)
    out["series"][name] = {"kappa_by_ncz": s, "a": a, "b": b,
                           "kappa_inf": 1 / a if a > 0 else None}

# T1
t1 = {}
for base in ("C37", "C38"):
    o = ser[f"{base}_orig"]
    d = {name: sum(abs(math.log(s[n] / o[n])) for n in (24, 48, 96)) / 3
         for name, s in ser.items() if name.startswith(base + "r")}
    t1[base] = {"replicate_distance": d, "pass": all(v <= 0.10 for v in d.values())}
out["tests"]["T1_reproduce"] = t1
# T2
kinf = lambda n: out["series"][n]["kappa_inf"]
c37 = [kinf(n) for n in out["series"] if n.startswith("C37")]
c37m = sum(c37) / len(c37)
out["tests"]["T2_gradient"] = {"k_x0.900": kinf("G90_T866"), "k_x0.943_mean": c37m,
                              "k_x0.970": kinf("G97_T866"),
                              "pass": kinf("G97_T866") > c37m > kinf("G90_T866")}
# T3
a, b = out["series"]["C37_orig"]["a"], out["series"]["C37_orig"]["b"]
k144 = k(new["C37_z144"])
resid = abs(1 / k144 - (a + b / 144)) / (1 / k144)
out["tests"]["T3_one_over_L"] = {"kappa_ncz144": k144, "predicted_ncz144": 1 / (a + b / 144),
                                "relative_residual": resid, "pass": resid <= 0.10}
T1 = {b_: t1[b_]["pass"] for b_ in t1}
T2 = out["tests"]["T2_gradient"]["pass"]
T3 = out["tests"]["T3_one_over_L"]["pass"]
for base in ("C37", "C38"):
    if not T1[base]:
        op = "replace"
    elif T3 and T2:
        op = "scope-limit + release"
    elif not T3:
        op = "scope-limit (method)"
    else:
        op = "keep quarantine"
    out["decisions"][base] = op
out["pe_eV_per_atom"] = {rid: r.get("pe_eV_per_atom") for rid, r in new.items()}
json.dump(out, open(os.path.join(HERE, "decision.json"), "w"), indent=1, sort_keys=True)
print(json.dumps({"tests": out["tests"], "decisions": out["decisions"]}, indent=1))
