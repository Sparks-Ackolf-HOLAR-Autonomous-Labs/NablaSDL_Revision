#!/usr/bin/env python3
"""Execute the Phase B endpoint decision, part B: scope-limit the MD
theory to alloys, as a ledgered shard operation.

Per 00_terminology_shard_operations.md and shard_ops.py, scope-limit is
a ledger operation: no rows change and no refit runs; the ledger records
a restriction on where the fitted law may claim validity, and fit_party.py
applies every active restriction to the claims it writes.

This is the campaign ledger's first entry beyond the pilot demos, so the
script also opens phase_c/ledger_campaign.jsonl. The operation is
reversible by design: when a validated endpoint method (GPUMD, Option A
of chpc/ENDPOINT_DECISION.md) lands converged x=0/x=1 kappa, a `restore`
entry lifts the restriction without rewriting history.

Idempotent: re-running while the restriction is active is a no-op.
Usage: python3 scope_limit_alloys.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pilot", "src"))

from ledger import Ledger  # noqa: E402

LEDGER = os.path.join(HERE, "ledger_campaign.jsonl")

OP_ID = "scope-limit-alloys-2026-09-27"

PAYLOAD = {
    "op": "scope-limit",
    "op_id": OP_ID,
    "target": {
        "claims": "symbolic laws fitted on scope tersoff-md-extrapolated "
                  "(parties DGX-MD/CHPC-MD, pooled party MD-extrapolated), "
                  "current and future",
        "unaffected": "literature-party claims; pure-element rows remain in "
                      "the evidence table as anchor evidence with their own "
                      "scope labels (nothing is forgotten)",
    },
    "restriction": {
        "x": [0.05, 0.95],
        "statement": "the Tersoff-MD theory is about alloy-scattering-"
                     "dominated transport; pure-element limits are outside "
                     "its validity domain",
    },
    "evidence": {
        "refs": ["chpc/RESULTS.md (Phase B endpoint verdict)",
                 "chpc/ENDPOINT_DECISION.md"],
        "facts": [
            "pure Si rNEMD kappa still near-linear in box length at 18432 "
            "atoms (9.8 -> 34.7 W/mK), 1/L fit intercept negative",
            "pure Ge nominal extrapolation 238 W/mK vs ~60 experimental: "
            "not credible, series still ballistic",
            "Green-Kubo unavailable in LAMMPS for tersoff and sw (no valid "
            "many-body heat flux, verified through LAMMPS 7 Feb 2024)",
        ],
    },
    "decision": {
        "by": "operator (kinstonwithoutg)",
        "where": "issue 55, 2026-09-27",
        "pick": "B then A (scope-limit now; GPUMD endpoints as the next "
                "compute block)",
    },
    "reversal_condition": "restore when GPUMD (Option A) delivers validated, "
                          "size-converged Tersoff kappa at x=0 and x=1; see "
                          "gpumd/BRINGUP.md",
}


def active_scope_limits(path=LEDGER):
    """Scope-limit restrictions not yet lifted by a restore entry."""
    if not os.path.exists(path):
        return []
    entries = [json.loads(line) for line in open(path)]
    active = {}
    for e in entries:
        p = e.get("payload", {})
        if e.get("kind") != "shard_operation":
            continue
        if p.get("op") == "scope-limit":
            active[p.get("op_id")] = p
        elif p.get("op") == "restore" and p.get("restores") in active:
            del active[p["restores"]]
    return list(active.values())


def main():
    if any(p.get("op_id") == OP_ID for p in active_scope_limits()):
        print(f"scope-limit {OP_ID} already active; no-op")
        return
    led = Ledger(LEDGER)
    entry = led.append("shard_operation", PAYLOAD)
    assert led.verify_chain(), "ledger chain verification failed"
    print(f"ledgered scope-limit as seq {entry['seq']} "
          f"(hash {entry['entry_hash'][:12]}...), chain verified")
    print(f"active restrictions: "
          f"{[p['restriction']['x'] for p in active_scope_limits()]}")


if __name__ == "__main__":
    main()
