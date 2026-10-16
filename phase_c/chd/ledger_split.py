#!/usr/bin/env python3
"""Ledger the CHD stage-0 literature split as ONE shard operation.

Appends a single entry of kind "shard_operation", op "split", to
../ledger_campaign.jsonl (hash-chained, pilot/src/ledger.py), built from
split_decision.json, stage0_results.json and calibration.json. Row
membership per scope is committed as a Merkle root over the rows'
leaf hashes (ledger.leaf_hash of the raw extracted point; row ids are
stored too, so ledger.merkle_proof can prove membership later), plus
the distinct snippet_hash values for human lookup.

Idempotent: if an entry with the same op_id already exists, it does
nothing. Refuses to run if split_decision.json says "no split" or if the
existing chain does not verify.

Usage:
  python3 ledger_split.py --dry-run    print the payload, append nothing
  python3 ledger_split.py              append
Pure stdlib (no jax needed).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PHASE_C = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PHASE_C, "..", "pilot", "src"))
from ledger import Ledger, merkle_root  # noqa: E402
from stage0_data import SAMPLE_GROUP, literature_rows  # noqa: E402

LEDGER = os.path.join(PHASE_C, "ledger_campaign.jsonl")
OP_ID = "split-literature-microstructure-2026-09-28"


def _load(name):
    return json.load(open(os.path.join(HERE, name)))


def build_payload():
    dec = _load("split_decision.json")
    res = _load("stage0_results.json")
    cal = _load("calibration.json")
    if dec["decision"] != "split":
        raise SystemExit(f"split_decision.json says {dec['decision']!r}: "
                         "nothing to ledger")
    P = res["partitions"][dec["primary_partition"]]
    lit = literature_rows()
    by_id = {r["row_id"]: r for r in lit}
    all_ids = [r["row_id"] for r in lit]

    scopes = {}
    for sname, s in dec["scopes"].items():
        ids = s["row_ids"]
        scopes[sname] = {
            "group": s["group"],
            "n_rows": len(ids),
            "n_rows_with_x_T": s["n_rows_fit_table"],
            "merkle_root": merkle_root(ids),
            "row_ids": ids,
            "snippet_hashes": sorted({by_id[i]["snippet_hash"] for i in ids}),
            "claim_status": s["law"],
        }
    cvs = dec["cv_summary"]
    ch = cal["chosen_setting"]
    rates = cal["chosen_rates"]
    fitc = res["chd_literature_fit_table"]["xT+sample+method+junk"]
    xc = res["chd_literature_x_table"]["x+sample+method+junk"]
    fb = res["fallback_anova"]
    payload = {
        "op": "split",
        "op_id": OP_ID,
        "target": {
            "party": "literature",
            "scope_before": "literature-bulk (single pooled scope, "
                            "assemble_evidence.py)",
            "n_rows": len(all_ids),
            "merkle_root_all_rows": merkle_root(all_ids),
            "row_rule": "extracted_points.json rows with an all-digit corpusId",
        },
        "partition": {
            "name": dec["primary_partition"],
            "field": "system (LLM-extracted sample class)",
            "grouping": SAMPLE_GROUP,
            "grouping_note": "pre-declared physics merge: boundary-scattering "
                             "samples (nanowire, nanostructured, film, "
                             "superlattice) form reduced-dim",
        },
        "scopes": scopes,
        "evidence": {
            "chd": {
                "package": "ComputationalHypergraphDiscovery 2.1.0 (Bourdais et al., "
                           "PNAS 121, 2024, doi 10.1073/pnas.2403449121)",
                "calibrated_setting": ch["setting"],
                "calibration": {
                    "score": ch["score"], "max_fp_rate": ch["max_fp_rate"],
                    "class_hit_rate_B42": rates["B42"]["hit_rate"]["cls"],
                    "class_hit_rate_B17real": rates["B17real"]["hit_rate"]["cls"],
                    "junk_fp_rate_B42": rates["B42"]["fp_rate"],
                    "null_fp_rate_N17": rates["N17"]["fp_rate"],
                    "null_fp_rate_N42": rates["N42"]["fp_rate"],
                    "limitation": "calibrated setting recovers the dominant "
                                  "monotone driver only (x never recovered)",
                },
                "ancestors_ln_kappa_fit_table": fitc["calibrated"]["ancestors"],
                "ancestors_ln_kappa_x_table": xc["calibrated"]["ancestors"],
                "C1_table_used": P["C1_table_used"],
                "noise_ratio_ln_kappa": {
                    "fit_table_given_x_T": res["chd_literature_fit_table"]["xT"]
                    ["noise_given_all"]["min_noise"],
                    "x_table_given_x": res["chd_literature_x_table"]["x"]
                    ["noise_given_all"]["min_noise"],
                    "x_table_given_x_sample": res["chd_literature_x_table"]
                    ["x+sample"]["noise_given_all"]["min_noise"],
                    "md_contrast_given_x_T_L": res["chd_md_contrast"]["xTL"]
                    ["noise_given_all"]["min_noise"],
                    "note": "n/(n+s), min over kernels; 1 = unexplained"},
            },
            "cv_medape_pct": cvs,
            "fallback_anova_x_table_sample_group": {
                k: fb["x_table"]["sample_group"][k] for k in ("eta2", "F", "p")},
            "rule": dec["rule"],
            "refs": ["phase_c/chd/STAGE0_RESULTS.md",
                     "phase_c/chd/stage0_results.json",
                     "phase_c/chd/split_decision.json",
                     "phase_c/chd/calibration.json"],
        },
        "decision": {
            "by": "agent, CHD stage-0 per operator go (issue 55, 2026-09-28)",
            "where": "issue 55, 2026-09-28",
        },
        "reversal_condition": (
            "merge back into one literature scope if the per-scope laws are "
            "statistically indistinguishable: once reduced-dim (or amorphous) "
            f"reaches >= 12 rows with x and T, refit per scope; if a pooled law "
            "over the merged scopes has CV MedAPE within 10 points of the "
            "per-scope laws on the same rows AND the class indicator drops out "
            "of the calibrated CHD ancestor set of ln kappa, reverse the split"),
        "unaffected": "no rows are forgotten or edited; MD, BTE-DFT, MACE-MD "
                      "and DB-CITRINE parties are untouched",
    }
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    led = Ledger(LEDGER)
    present = any(e.get("payload", {}).get("op_id") == OP_ID
                  for e in led.entries)
    payload = build_payload()
    if a.dry_run:
        print(json.dumps({"kind": "shard_operation", "payload": payload},
                         indent=1))
        print(f"# dry run: ledger has {len(led.entries)} entries, chain "
              f"verifies={led.verify_chain()}, op_id already present="
              f"{present}; nothing appended", file=sys.stderr)
        return
    if present:
        print(f"no-op: {OP_ID} already in {LEDGER}")
        return
    if not led.verify_chain():
        raise SystemExit("ledger chain does not verify; refusing to append")
    e = led.append("shard_operation", payload)
    print(f"appended seq {e['seq']} {e['entry_hash']} ({OP_ID})")


if __name__ == "__main__":
    main()
