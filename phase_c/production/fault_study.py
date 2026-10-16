#!/usr/bin/env python3
"""Phase C production fault study (paper 1): frozen detector (ledger
seq 5) versus the blind fault catalog (ledger seq 4) on the real
production campaign rows (ledger seq 3), 50 randomized trials per
catalog entry plus 50 NULL trials, using the catalog's own pre-registered
trial seeds.

Scoring, two views reported side by side:
  A. the rule stated in advance on the ledger (seq 5): operator
     families {remove-influence: forget/quarantine, correct, scope:
     scope-limit/split, keep: no operation};
  B. the blind catalog author's own acceptable / forbidden operator sets
     per entry (no operation on the affected runs counts as `retain`).
Per trial:
  detected  = some operation targets an affected or added run;
  outcome   = hit (all operations on affected runs acceptable, or no
              operation when retain is expected), harmful (any forbidden
              operation on affected runs), miss (no operation on affected
              runs when an operation was expected), partial otherwise;
  collateral = operations whose targets avoid the affected/added runs
              and are not expected fires (probe runs of ledger seq 3,
              physics-guard rows at or above the solidus, and the
              catalog's background premelting rows).
Usage: python3 fault_study.py rows.json [n_trials] [D2]
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "fault_catalog"))

import detector  # noqa: E402
import inject_faults as IF  # noqa: E402

FAMILY = {"forget": "remove-influence", "quarantine": "remove-influence",
          "correct": "correct", "scope-limit": "scope", "split": "scope",
          "retain": "keep"}
EXPECTED_FAMILY = {  # rule A, from the ledger seq 5 statement
    "planted-error": {"remove-influence", "correct"},
    "method-off-data": {"scope"},
    "valid-anomaly": {"keep", "scope"},
    "null": {"keep"},
}


def _probe_runs(rows):
    return {r["run_id"] for r in rows if r["run_id"].startswith("N")}


def _sig(o):
    return (o["op"], tuple(sorted(o["target_runs"])))


def score(res, truth, rows, baseline=frozenset()):
    """baseline: operation signatures the detector emits on the clean
    campaign itself; in the baseline-adjusted view (suffix _adj) those
    are not attributed to the injected fault."""
    hit_set = set(truth["affected_run_ids"]) | set(truth["added_run_ids"])
    expected_bg = (_probe_runs(rows) |
                   set(truth.get("background_method_off_run_ids", [])) |
                   {r["run_id"] for r in rows
                    if r["T"] >= detector.solidus(r["x"])})
    on, coll = [], []
    for o in res["ops"]:
        tg = set(o["target_runs"])
        if tg & hit_set:
            on.append(o["op"])
        elif not tg <= expected_bg:
            coll.append(o["op"])
    cat = truth["category"]
    # view A
    fams = {FAMILY[o] for o in on} or {"keep"}
    exp = EXPECTED_FAMILY[cat]
    if cat == "valid-anomaly" and "remove-influence" in fams | (
            {"correct"} if "correct" in fams else set()):
        a = "harmful"
    elif fams <= exp:
        a = "hit"
    elif fams & exp:
        a = "partial"
    else:
        a = "miss" if fams == {"keep"} else "wrong-op"
    # view B
    ops_b = set(on) or {"retain"}
    acc = set(truth["acceptable_operators"])
    forb = set(truth["forbidden_operators"])
    if ops_b & forb:
        b = "harmful" if cat in ("valid-anomaly", "null") else (
            "miss" if ops_b == {"retain"} else "forbidden-op")
    elif ops_b <= acc:
        b = "hit"
    elif ops_b == {"retain"}:
        b = "miss"
    else:
        b = "partial"
    out = {"detected": bool(on), "ops_on_affected": sorted(set(on)),
            "outcome_A": a, "outcome_B": b, "collateral": sorted(coll),
            "severity_u": truth.get("severity_u")}
    if baseline:
        adj = score({"ops": [o for o in res["ops"]
                             if _sig(o) not in baseline]}, truth, rows)
        for k in ("detected", "outcome_A", "outcome_B", "collateral"):
            out[k + "_adj"] = adj[k]
    return out


def main():
    rows = json.load(open(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    if len(sys.argv) > 3 and sys.argv[3] == "D2":
        detector.DUP_MODE = "design"
    clean = detector.detect(rows)
    baseline = frozenset(_sig(o) for o in clean["ops"])
    out = {"detector_variant": detector.DUP_MODE, "clean_campaign": clean,
           "entries": {}}
    for eid in ["NULL"] + IF.entries():
        trials = []
        for ts in IF.trial_seeds(eid, n):
            rows_t, truth = IF.inject(rows, eid, ts)
            res = detector.detect(rows_t)
            s = score(res, truth, rows_t, baseline)
            s["trial_seed"] = ts
            s["magnitude"] = truth.get("magnitude")
            trials.append(s)
        cat = truth["category"]
        summ = {"category": cat,
                "expected": truth["expected_operator"],
                "detected_rate": sum(t["detected"] for t in trials) / n,
                "A": dict(Counter(t["outcome_A"] for t in trials)),
                "B": dict(Counter(t["outcome_B"] for t in trials)),
                "trials_with_collateral":
                    sum(bool(t["collateral"]) for t in trials),
                "detected_rate_adj": sum(t["detected_adj"] for t in trials) / n,
                "A_adj": dict(Counter(t["outcome_A_adj"] for t in trials)),
                "B_adj": dict(Counter(t["outcome_B_adj"] for t in trials)),
                "trials_with_collateral_adj":
                    sum(bool(t["collateral_adj"]) for t in trials),
                "ops_seen": dict(Counter(o for t in trials
                                         for o in t["ops_on_affected"]))}
        # detection vs severity (quartiles of u)
        byq = defaultdict(list)
        for t in trials:
            if t["severity_u"] is not None:
                byq[min(int(t["severity_u"] * 4), 3)].append(t["detected"])
        summ["detected_by_severity_quartile"] = {
            f"Q{q + 1}": round(sum(v) / len(v), 2) for q, v in sorted(byq.items())}
        out["entries"][eid] = {"summary": summ, "trials": trials}
        print(eid, json.dumps(summ))
    dst = os.path.join(HERE, "fault_study_results_%s.json" % (
        "frozen" if detector.DUP_MODE == "kappa" else "D2"))
    json.dump(out, open(dst, "w"), indent=1, default=str)
    print("->", dst)


if __name__ == "__main__":
    main()
