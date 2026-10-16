#!/usr/bin/env python3
"""Outcome-matrix tables for FAULT_STUDY.md from the two result files.
Usage: python3 make_tables.py > tables.md"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
cat = json.load(open(os.path.join(HERE, "fault_catalog", "fault_catalog.json")))
names = {e["id"]: e["name"] for e in cat["entries"]}
names["NULL"] = "null campaign (no fault)"


def pct(d, k, n=50):
    return f"{100 * d.get(k, 0) / n:.0f}"


for v, adj in (("frozen", ""), ("D2", "_adj")):
    d = json.load(open(os.path.join(HERE, f"fault_study_results_{v}.json")))
    title = ("Frozen detector (ledger seq 5 + D1), pre-stated scoring A, raw"
             if v == "frozen" else
             "Post-hoc variant D2 (design-coordinate duplicate key), "
             "baseline-adjusted (clean-campaign fires not attributed)")
    print(f"\n#### {title}\n")
    print("| id | entry | category | detected % | hit % | harmful % | miss % "
          "| other % | trials with collateral % | detection by severity Q1/Q2/Q3/Q4 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for eid, x in d["entries"].items():
        s = x["summary"]
        A = s["A" + adj]
        other = 50 - A.get("hit", 0) - A.get("harmful", 0) - A.get("miss", 0)
        q = s["detected_by_severity_quartile"]
        qs = "/".join(f"{q[k]:.2f}" for k in ("Q1", "Q2", "Q3", "Q4") if k in q) or "n/a"
        print(f"| {eid} | {names[eid]} | {s['category']} | "
              f"{100 * s['detected_rate' + adj]:.0f} | {pct(A, 'hit')} | "
              f"{pct(A, 'harmful')} | {pct(A, 'miss')} | {100 * other / 50:.0f} | "
              f"{100 * s['trials_with_collateral' + adj] / 50:.0f} | {qs} |")
