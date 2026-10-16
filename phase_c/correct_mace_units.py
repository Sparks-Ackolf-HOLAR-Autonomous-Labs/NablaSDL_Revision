#!/usr/bin/env python3
"""Ledger the party 4b unit correction as a `correct` shard operation.

The first MACE-MD campaign (party 4b, DGX, 2026-09-27) produced kappa
values inflated by exactly 1/units.fs^2 = 103.6427: the final unit
conversion in mp_rnemd_ase.py divided by ase.units.fs where converting
a per-ASE-time rate to per-fs requires multiplying. The slip was caught
by a cross-party consistency check at collection time (39.5 W/mK in a
strongly size-suppressed 13 nm box would exceed the BTE-DFT *bulk*
value of 6.49 W/mK, which is physically impossible), diagnosed to one
line, and verified by recovering physically sensible per-swap
transferred energies (0.06-0.09 eV) from the raw outputs.

Per 00_terminology_shard_operations.md, `correct` replaces a value
whose error has an identified cause while archiving the original:
the raw files stay unmodified under party4_mace/raw/, the corrected
copies (the ones the evidence hypergraph ingests) live under
party4_mace/results/, and this entry binds the two together with the
cause on record.

Idempotent: re-running while the correction is already ledgered is a
no-op. Usage: python3 correct_mace_units.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pilot", "src"))

from ledger import Ledger  # noqa: E402

LEDGER = os.path.join(HERE, "ledger_campaign.jsonl")

OP_ID = "correct-mace-units-2026-09-27"

PAYLOAD = {
    "op": "correct",
    "op_id": OP_ID,
    "target": {
        "party": "MACE-MD (party 4b)",
        "datapoints": [
            {"tag": "mace_x0.5_T300_z24_s101",
             "raw_kappa_W_mK": 39.5444, "corrected_kappa_W_mK": 0.3815},
            {"tag": "mace_x0.15_T300_z24_s101",
             "raw_kappa_W_mK": 71.4753, "corrected_kappa_W_mK": 0.6896},
        ],
        "archived_raw": "party4_mace/raw/ (unmodified, never edited)",
        "corrected": "party4_mace/results/ (hypergraph ingestion copies)",
    },
    "cause": {
        "identified": True,
        "statement": "unit-conversion slip in mp_rnemd_ase.py: per-ASE-time "
                     "-> per-fs conversion divided by ase.units.fs instead "
                     "of multiplying, inflating kappa by exactly "
                     "1/units.fs^2 = 103.6427",
        "fix": "one-line change in mp_rnemd_ase.py (repo and DGX copies), "
               "committed alongside this entry",
    },
    "evidence": {
        "detection": "cross-party consistency check at collection: raw "
                     "39.5 W/mK at x=0.5 in a size-suppressed 4x4x24 box "
                     "exceeds the BTE-DFT bulk value 6.49 W/mK, which is "
                     "physically impossible",
        "verification": [
            "inflation factor matches 1/units.fs^2 to 4 decimal places",
            "per-swap transferred energies recovered from raw outputs are "
            "0.0621 and 0.0860 eV, physically sensible atom kinetic "
            "energies, so bookkeeping upstream of the conversion is sound",
            "corrected values (0.38, 0.69 W/mK) sit below the Tersoff "
            "values at the identical box and protocol (0.74, 1.14), "
            "consistent with MLIP force-noise underestimation of kappa "
            "(Wu et al., J. Chem. Phys. 2024, DOI 10.1063/5.0213811)",
        ],
    },
    "decision": {
        "by": "agent, at collection time (session 33)",
        "where": "issue 55, 2026-09-27 follow-up on party 4b",
        "second_bar": "cause identified in code, so the correct operation "
                      "(not quarantine) applies under the two-bar rule",
    },
}


def already_ledgered(path=LEDGER):
    if not os.path.exists(path):
        return False
    for line in open(path):
        e = json.loads(line)
        if e.get("kind") == "shard_operation" and \
                e.get("payload", {}).get("op_id") == OP_ID:
            return True
    return False


def main():
    if already_ledgered():
        print(f"correct {OP_ID} already ledgered; no-op")
        return
    led = Ledger(LEDGER)
    entry = led.append("shard_operation", PAYLOAD)
    assert led.verify_chain(), "ledger chain verification failed"
    print(f"ledgered correct as seq {entry['seq']} "
          f"(hash {entry['entry_hash'][:12]}...), chain verified")


if __name__ == "__main__":
    main()
