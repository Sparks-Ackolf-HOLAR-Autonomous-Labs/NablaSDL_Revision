#!/usr/bin/env python3
"""Phase C production campaign: pin the committed seed batch and add the
material's own off-data probes (paper 1's fault study substrate).

Inputs: ../seed_batch_design.json (committed 2026-09-26; its SHA-256 is
checked here so the production runs are provably the committed coverage
design). The Phase B cross-section and swap-interval series pinned the
two protocol fields left open in the seed design:
ncxy = 4 (6x6 and 8x8 fell inside the seed band) and swapn = 50 (the
Phase B value; gentler swaps moved kappa only 3-5%, and keeping 50
keeps the new party protocol-identical to the CHPC-MD party). The
endpoint field resolves to "excluded" by scope-limit-alloys-2026-09-27.

Physics probes (the testbed's own undesigned off-data, added on
purpose; ground truth written here, BEFORE any outcome):
  - near-melting: the real alloy solidus is roughly 1400 K at x = 0.5 and
    roughly 1330 K at x = 0.7 (Si-Ge lens diagram), while Tersoff-1989
    overestimates melting by about 800 K and keeps the crystal intact.
    The runs execute cleanly and give smooth crystalline kappa for a
    regime where the real material is partially molten: method
    off-data, expected operator scope-limit (T domain).
  - amorphous: melt-quenched a-SiGe at 300 K and 700 K. Real, valid
    physics of a different phase (kappa near-independent of box length,
    no 1/L trend): expected operator split (phase scope), never forget.

Batches: the 40 coverage points are dealt round-robin into five
submission batches PB1..PB5 (8 points each, every batch spans all
composition bands), and the four probes are placed one per batch in
PB1..PB4 so no batch is "the probe batch". Each point runs at ncz
24/48/96 -> 44 points x 3 = 132 runs.

Deterministic; writes production_design.json and points_production.txt
and prints the design SHA-256.
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SEED_DESIGN = os.path.join(HERE, "..", "seed_batch_design.json")
SEED_SHA = "20608f425b5a68eef97d7c1a939f151cdb76b1865f1437dbcea1481ee3b3da7d"
NCXY, SWAPN = 4, 50

PROBES = [
    {"probe": "near-melt", "x": 0.5, "T": 1500, "seed": 2001,
     "deck": "std", "truth": {"category": "method-off-data",
                              "expected_op": "scope-limit",
                              "why": "above the real solidus (~1400 K at "
                                     "x=0.5); Tersoff crystal persists"}},
    {"probe": "near-melt", "x": 0.7, "T": 1450, "seed": 2002,
     "deck": "std", "truth": {"category": "method-off-data",
                              "expected_op": "scope-limit",
                              "why": "above the real solidus (~1330 K at "
                                     "x=0.7); Tersoff crystal persists"}},
    {"probe": "amorphous", "x": 0.5, "T": 300, "seed": 2003,
     "deck": "amorph", "truth": {"category": "valid-anomaly (other phase)",
                                 "expected_op": "split",
                                 "why": "melt-quenched a-SiGe: real "
                                        "physics, different phase"}},
    {"probe": "amorphous", "x": 0.5, "T": 700, "seed": 2004,
     "deck": "amorph", "truth": {"category": "valid-anomaly (other phase)",
                                 "expected_op": "split",
                                 "why": "melt-quenched a-SiGe: real "
                                        "physics, different phase"}},
]


def main():
    blob = open(SEED_DESIGN, "rb").read()
    got = hashlib.sha256(blob).hexdigest()
    assert got == SEED_SHA, f"seed design changed: {got}"
    seed = json.loads(blob)
    points = []
    for i, p in enumerate(seed["points"]):
        points.append({"point_id": f"C{i:02d}", "batch_id": f"PB{i % 5 + 1}",
                       "x": p["x"], "T": p["T"], "seed": p["seed"],
                       "deck": "std", "cell": p["cell"],
                       "replica": p["replica"]})
    for j, pr in enumerate(PROBES):
        points.append({"point_id": f"N{j}", "batch_id": f"PB{j + 1}",
                       "x": pr["x"], "T": pr["T"], "seed": pr["seed"],
                       "deck": pr["deck"]})
    runs = []
    for p in points:
        for ncz in seed["points"][0]["ncz_series"]:
            runs.append({"run_id": f"{p['point_id']}_z{ncz}",
                         "point_id": p["point_id"],
                         "batch_id": p["batch_id"], "x": p["x"],
                         "T": p["T"], "ncz": ncz, "seed": p["seed"],
                         "ncxy": NCXY, "swapn": SWAPN, "deck": p["deck"]})
    design = {
        "campaign": "phase-c-production-2026-09-28",
        "paper": "P1 (fault study substrate + kappa(x,T) alloy law)",
        "seed_design_sha256": SEED_SHA,
        "pinned": {"ncxy": NCXY, "swapn": SWAPN,
                   "endpoints": "excluded (scope-limit-alloys-2026-09-27)"},
        "protocol": {"std": "chpc/in.mp_kappa2 (NPT 50 ps, MP warmup 100 ps, "
                            "production 500 ps, 20 z-bins)",
                     "amorph": "phase_c/production/in.mp_amorph (melt 3500 K "
                               "50 ps, quench to T over 100 ps, NPT 50 ps, "
                               "then the identical MP protocol)"},
        "partition": "notchpeak-guest / owner-guest (grn061 off-limits)",
        "probe_truth": {f"N{j}": pr["truth"] | {"probe": pr["probe"]}
                        for j, pr in enumerate(PROBES)},
        "detector_blindness": "the detector sees run rows (run_id, batch_id, "
                              "x, T, ncz, seed, kappa); probe_truth is read "
                              "only by the scoring step",
        "points": points,
        "runs": runs,
        "n_runs": len(runs),
    }
    out = os.path.join(HERE, "production_design.json")
    b = json.dumps(design, indent=1, sort_keys=True).encode() + b"\n"
    open(out, "wb").write(b)
    with open(os.path.join(HERE, "points_production.txt"), "w") as f:
        for r in runs:
            f.write(f"{r['run_id']} {r['x']} {r['T']} {r['ncz']} {r['seed']} "
                    f"{r['ncxy']} {r['swapn']} {r['deck']}\n")
    print(f"{len(runs)} runs; sha256 {hashlib.sha256(b).hexdigest()}")


if __name__ == "__main__":
    main()
