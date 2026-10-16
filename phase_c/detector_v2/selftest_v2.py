#!/usr/bin/env python3
"""Crash test of detector v2 and its harness on SYNTHETIC descriptors
(Vegard lattice + linear expansion, harmonic angle spread; amorphous probes
at 17 deg). Run before registration; no real descriptor is used."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(HERE, "..", "production", "results", "production_rows.json")))
rng = np.random.default_rng(1)
pts = {}
for r in rows:
    pts.setdefault(r["run_id"].split("_")[0], (r["x"], r["T"]))
syn = {}
for pid, (x, T) in pts.items():
    a = 5.432 + 0.2247 * x + 0.004 * x * x + 2.6e-5 * (T - 300) + rng.normal(0, 0.0015)
    sd = 17.0 if pid in ("N2", "N3") else float(np.sqrt(0.0281 * T + 0.6 * x * (1 - x)) + rng.normal(0, 0.05))
    syn[pid] = (a ** 3 / 8, sd)
out = [dict(r, vol_atom=syn[r["run_id"].split("_")[0]][0], angle_sd=syn[r["run_id"].split("_")[0]][1]) for r in rows]
p = os.path.join(HERE, "selftest_rows_synthetic.json")
json.dump(out, open(p, "w"))
sys.argv = ["x", p, sys.argv[1] if len(sys.argv) > 1 else "3"]
sys.path.insert(0, HERE)
import fault_study_v2 as F
F.main()
