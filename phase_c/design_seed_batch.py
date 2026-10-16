#!/usr/bin/env python3
"""Phase C seed-batch design: coverage over (x, T) with k-loss tolerance.

Deterministic (fixed RNG seed), so the committed JSON regenerates
bit-for-bit; its SHA-256 is the pre-registration commitment (design
element 2 + N3 of 04_experimental_design_v2.md).

Design: 5 composition bands x 4 temperature bands (every pairwise
band-band interaction covered, the strength-2 guarantee, which for two
factors is the full band grid), 2 replicas per cell with distinct MD
seeds, points jittered within their cell so band edges are not
systematically sampled. k = 1 erasure tolerance: any single run per
cell can fail (preemption, non-equilibration) and every cell is still
covered. Each (x, T, seed) point runs at three sizes (ncz 24/48/96)
for the 1/L extrapolation, matching Phase B protocol.

Alloy campaign only: x in [0.05, 0.95]. The pure endpoints are excluded
on purpose; their method was decided separately by the Phase B
endpoint study (GK/SW second party vs scope-limit). Cross-section and
swap interval were left open at design time, awaiting the Phase B
cross-section and swap-interval series, and were pinned later in
phase_c/production/design_production.py.

Usage: python3 design_seed_batch.py   (writes seed_batch_design.json)
"""
import hashlib
import json
import os
import random

X_BANDS = [(0.05, 0.23), (0.23, 0.41), (0.41, 0.59), (0.59, 0.77), (0.77, 0.95)]
T_BANDS = [(300, 525), (525, 750), (750, 975), (975, 1200)]
REPLICAS = 2          # k=1 loss tolerance per cell
NCZ_SERIES = [24, 48, 96]
RNG_SEED = 20260926


def main():
    rng = random.Random(RNG_SEED)
    points = []
    seed_counter = 1000
    for xi, (xlo, xhi) in enumerate(X_BANDS):
        for ti, (tlo, thi) in enumerate(T_BANDS):
            for rep in range(REPLICAS):
                x = round(rng.uniform(xlo, xhi), 3)
                T = round(rng.uniform(tlo, thi))
                seed_counter += 1
                points.append({
                    "cell": [xi, ti], "replica": rep,
                    "x": x, "T": T, "seed": seed_counter,
                    "ncz_series": NCZ_SERIES,
                })
    design = {
        "design": "5x4 band grid, strength-2 coverage, 2 replicas (k=1)",
        "x_bands": X_BANDS, "T_bands": T_BANDS,
        "rng_seed": RNG_SEED,
        "n_points": len(points),
        "n_runs": len(points) * len(NCZ_SERIES),
        "protocol": {
            "method": "Muller-Plathe rNEMD, in.mp_kappa2",
            "ncxy": "PENDING (Phase B follow-up: cross-section series)",
            "swapn": "PENDING (Phase B follow-up: gentle-swap series)",
            "endpoints": "PENDING (Phase B follow-up: GK/SW feasibility)",
        },
        "points": points,
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "seed_batch_design.json")
    blob = json.dumps(design, indent=2, sort_keys=True)
    with open(out, "w") as f:
        f.write(blob + "\n")
    print(f"{len(points)} points, {design['n_runs']} runs -> {out}")
    print("commitment sha256:",
          hashlib.sha256((blob + "\n").encode()).hexdigest())


if __name__ == "__main__":
    main()
