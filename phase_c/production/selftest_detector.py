#!/usr/bin/env python3
"""Detector self-test on a synthetic production-shaped table (the
detector author's own sanity cases, written before the blind catalog was
opened: null, the pilot's classic 0.72 biased batch, a x100 unit slip,
a duplicated run). Not part of the scored fault study."""
import json
import os

import numpy as np

from detector import detect

HERE = os.path.dirname(os.path.abspath(__file__))


def synth(seed=0):
    d = json.load(open(os.path.join(HERE, "production_design.json")))
    rng = np.random.default_rng(seed)
    rows = []
    for r in d["runs"]:
        if r["deck"] != "std" or r["T"] >= 1300:
            continue
        x, T, L = r["x"], r["T"], r["ncz"] * 5.5
        inv = 0.091 + (2.045 + 431.6 / L) * x * (1 - x) + 0.02 * T / 1000
        k = (1 / inv) * (1 + 0.03 * rng.standard_normal())
        rows.append({"run_id": r["run_id"], "batch_id": r["batch_id"],
                     "x": x, "T": T, "ncz": r["ncz"], "seed": r["seed"],
                     "kappa": float(k)})
    return rows


def ops(res):
    return [(o["op"], o.get("target_batch"), len(o["target_runs"]))
            for o in res["ops"]]


if __name__ == "__main__":
    out = {}
    for s in range(30):
        out[f"null_{s}"] = ops(detect(synth(s)))
    rows = synth(1)
    out["bias072_PB3"] = ops(detect([dict(r, kappa=r["kappa"] * 0.72)
                                     if r["batch_id"] == "PB3" else r
                                     for r in rows]))
    out["unit100_PB2"] = ops(detect([dict(r, kappa=r["kappa"] * 100)
                                     if r["batch_id"] == "PB2" else r
                                     for r in rows]))
    out["dup"] = ops(detect(rows + [dict(rows[5], run_id="DUP_z24",
                                         batch_id="PB5")]))
    print(json.dumps(out, indent=1))
