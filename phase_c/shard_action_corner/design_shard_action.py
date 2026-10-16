#!/usr/bin/env python3
"""Design the first real *shard action* of the campaign: acquisition bought
to decide an open quarantine (paper 1's active loop on real physics).

Trigger: the frozen production detector (ledger seq 5 + D1) quarantined
C37 (x 0.943, 866 K) and C38 (x 0.932, 1180 K) as "isolated point outlier,
no cause identified" (FAULT_STUDY.md, Result 1). With one seed per
regime cell, an isolated fault and a genuine dilute-limit rise toward the
Ge endpoint look identical to any statistic. The fault study measured that
limit; this action buys the three measurements that separate the cases.

Writes shard_action_design.json deterministically (run matrix, decision
rule, predictions) and points.txt for the SLURM array. preregister.py
puts its SHA-256 on the ledger before any run is submitted.
"""
import json

runs = []
def add(rid, x, T, ncz, seed, role):
    runs.append({"run_id": rid, "x": x, "T": T, "ncz": ncz, "seed": seed,
                 "ncxy": 4, "swapn": 50, "role": role})

for base, x, T in (("C37", 0.943, 866.0), ("C38", 0.932, 1180.0)):
    for s_off in (1000, 2000):
        seed = int(base[1:]) + 1000 + s_off  # 2037/3037 (C37), 2038/3038 (C38); originals used 1038/1039
        for ncz in (24, 48, 96):
            add(f"{base}r{seed}_z{ncz}", x, T, ncz, seed, "replicate")
for tag, x, seed in (("G90", 0.900, 2101), ("G97", 0.970, 2102)):
    for ncz in (24, 48, 96):
        add(f"{tag}_T866_z{ncz}", x, 866.0, ncz, seed, "gradient")
add("C37_z144", 0.943, 866.0, 144, 1038, "ballistic")

design = {
    "action": "shard-action-ge-corner-2026-09-29",
    "decides": ["quarantine C37_z24/z48/z96", "quarantine C38_z24/z48/z96"],
    "trigger": "frozen detector, production campaign, reason 'isolated point outlier, no cause identified'",
    "protocol": "identical to the production campaign (in.mp_kappa2: Muller-Plathe rNEMD, SiCGe.tersoff, ncxy 4, swap every 50, NPT 50 ps, warm 100 ps, production 500 ps); in.mp_kappa3 adds only a final PE/atom print",
    "compute": "CHPC notchpeak-guest / owner-guest, 16 ranks per run, one array; grn061 untouched",
    "runs": runs,
    "analysis": {
        "kappa_inf": "per (x, T, seed) series: least squares 1/kappa = a + b/L over ncz 24/48/96 (L = box length along z), kappa_inf = 1/a, exactly as detector.points_of",
        "replicate_distance": "per replica series: mean over the three sizes of |ln(k_rep / k_orig)|",
    },
    "tests": {
        "T1_reproduce": "for BOTH C37 and C38: both replica series have replicate_distance <= 0.10 (Phase B seed scatter is 3% at ncz 24; 0.10 allows about 3 sigma)",
        "T2_gradient": "at 866 K: kappa_inf(x 0.970) > kappa_inf(x 0.943, mean of original + replicas) > kappa_inf(x 0.900)",
        "T3_one_over_L": "C37 seed 1038: |1/k(ncz 144) - (a + b/L144)| / (1/k(ncz 144)) <= 0.10 using a, b fitted on ncz 24/48/96 only",
    },
    "decision_rule": [
        {"if": "T1 fails for a point", "op": "replace", "detail": "that point's original rows are forgotten from the law (archived, influence removed) and its replica series take their place; the quarantine on it is closed"},
        {"if": "T1 passes and T2 passes and T3 passes", "op": "scope-limit + release", "detail": "valid anomaly: the rows are real dilute-limit physics the current law form (x(1-x) plus x in resistivity) cannot follow. Quarantine released (rows kept), current law scope-limited to x <= 0.90, and a basis-expansion candidate opened for the Ge-rich dilute limit"},
        {"if": "T1 passes and T3 fails", "op": "scope-limit (method)", "detail": "the 1/L extrapolation is invalid in the Ge-rich corner (ballistic-regime method off-data, blind-catalog class M03); rows kept as lower-bound evidence, law scope-limited to x <= 0.90 with the method reason"},
        {"if": "T1 passes, T3 passes, T2 fails", "op": "keep quarantine", "detail": "inconclusive; recorded, next shard action designed from the result"},
    ],
    "predictions": {
        "stated_before_outcomes": [
            "T1 passes (the production rows are not isolated faults)",
            "T2 passes (kappa rises toward the Ge endpoint, as in BTE-DFT: x 0.85 -> 11.5, x 1 -> 57.1 W/mK at 300 K)",
            "T3 is the uncertain one: C37's b/a is 40, the largest in the campaign, so the ballistic regime is plausible",
        ],
        "status": "predictions are reported pass or fail; the decision rule above is what acts",
    },
    "deviation_policy": "any change to runs, tests, or the rule after the ledger entry is a deviation with its own ledger entry before the affected run; infrastructure failures may be rerun once with the same seed and are logged",
}
json.dump(design, open("shard_action_design.json", "w"), indent=1, sort_keys=True)
with open("points.txt", "w") as f:
    for r in runs:
        f.write(f"{r['run_id']} {r['x']} {r['T']} {r['ncz']} {r['seed']} {r['ncxy']} {r['swapn']}\n")
print(len(runs), "runs")
