#!/usr/bin/env python3
"""Pre-registered design: box-size-free Tersoff kappa across composition
and temperature (GPUMD HNEMD), run 2026-10-02.

Why: P1's kappa(x, T) law is a two-stage Muller-Plathe rNEMD fit whose
infinite-box level rests on a 1/L extrapolation over 130-800 A boxes.
The one box-size-free Tersoff value so far (HNEMD, x = 0.5, 300 K,
2.23 +/- 0.22 W/mK, ledger seq 8) sits 41% above the law (1.58), so the
law's level may be a lower bound (HGSR_FULL_V2.md, reading 3). HNEMD in
a periodic 8x8x8 alloy cell has no imposed length scale, so it measures
the bulk level directly. This campaign buys that evidence on a grid.

Grid: x in {0.15, 0.2, 0.3, 0.5, 0.7, 0.85} (five BTE-DFT compositions
plus the SiGeC recipe host x = 0.3) x T in {300, 700, 1100} K, three
alloy configurations (config seed = velocity seed) each, Fe = 2e-4 1/A
(validated for the alloy at seq 8), 5 ns production. Checks: linearity
(Fe = 1e-4) and size (16x8x8) at the two highest-kappa 300 K points.
Protocol = gpumd/production run.in (NPT 100 ps, NVT 50 ps, HNEMD).

Deterministic: writes sizefree_design.json byte-identically; its SHA-256
goes on the ledger (preregister_sizefree.py) and is pushed to git before
make_runs_sizefree.py builds any run directory.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "sizefree_design.json")
CHPC_ROOT = "/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_sizefree"
POT = ("/uufs/chpc.utah.edu/common/home/u1496771/mat_theory/gpumd_v2/"
       "GPUMD/potentials/tersoff/SiGe_Tersoff_1989.txt")
XS = [0.15, 0.2, 0.3, 0.5, 0.7, 0.85]
TS = [300, 700, 1100]
FE = 2e-4
FE_LIN = 1e-4
SEEDS = [57001, 57002, 57003]
PROD_NS = 5.0


def a0(x):
    return round(5.432 + (5.657 - 5.432) * x, 4)   # Tersoff Vegard start; NPT relaxes


def solidus(x):   # phase_c/production/detector.py, same function
    return 1687.0 * (1 - x) + 1211.0 * x - 150.0 * x * (1 - x)


def row(stage, x, T, fe, seed, cells, check):
    size = "x".join(map(str, cells))
    rid = f"SiGe_x{x}_T{T}_fe{fe:.0e}_{size}_s{seed}".replace("e-0", "e-")
    return {"run_id": rid, "stage": stage, "check": check, "system": "SiGe",
            "x_ge": x, "T_K": T, "Fe_per_A": fe, "seed": seed,
            "config_seed": seed, "cells": cells,
            "n_atoms": 8 * cells[0] * cells[1] * cells[2], "a0_A": a0(x),
            "potential": POT, "production_ns": PROD_NS,
            "in_law_domain": bool(0.05 <= x <= 0.9 and T <= 0.85 * solidus(x))}


def build():
    runs = []
    for T in TS:
        stage = "H1-300K" if T == 300 else "H2-highT"
        for x in XS:
            for s in SEEDS:
                runs.append(row(stage, x, T, FE, s, [8, 8, 8], "main"))
    for x in (0.15, 0.85):
        for s in SEEDS:
            runs.append(row("H1-300K", x, 300, FE_LIN, s, [8, 8, 8], "linearity"))
            runs.append(row("H1-300K", x, 300, FE, s, [16, 8, 8], "size"))
    return runs


def main():
    runs = build()
    design = {
        "campaign": "gpumd-sizefree-kappa-2026-10-02",
        "paper": "P1 (law level); P2 (pre-registered evidence purchase)",
        "question": "Is the rNEMD two-stage law's infinite-box level right, "
                    "and how large is the Tersoff alloy bias vs BTE-DFT across x and T?",
        "n_runs": len(runs),
        "protocol": {
            "engine": "GPUMD (CHPC build, gpumd_v2/GPUMD), HNEMD, driving along x, kappa = kx_in + kx_out",
            "run_in": "gpumd/production/make_runs.py run_in(): npt_ber 100 ps, nvt_nhc 50 ps, nvt_nhc + compute_hnemd 1000 Fe 0 0, dump_thermo 10000",
            "time_step_fs": 1,
            "stage_order": ["H1-300K", "H2-highT"],
            "placement": "execution detail, not design: H1 on granite sparks-gpu-grn (grn061, H100 NVL) per operator 2026-10-02; H2 on notchpeak-gpu-guest; any stage may move between these without a deviation entry beyond a placement note",
            "preemption": "requeue, restart from scratch with the same seed (declared, not a deviation)",
        },
        "run_gates": "per run R1-R4 of gpumd/production/analyze_campaign.run_stats (exit + >=90% lines, |T-T0|<=2%, drift z<3, 0<kappa<2000)",
        "point_rule": "a (x, T) point needs >= 2 passing main runs; estimate = seed mean, SE = max(seed SE, pooled within-run SEM / n)",
        "agreement": "two estimates agree when |a-b| <= 2*sqrt(sa^2+sb^2) + 0.10*(a+b)/2",
        "checks": {
            "G_lin": "Fe 1e-4 agrees with Fe 2e-4 at x = 0.15 and 0.85, 300 K",
            "G_size": "16x8x8 agrees with 8x8x8 at x = 0.15 and 0.85, 300 K",
            "on_failure": "if either check fails, all 300 K points are reported but excluded from the decision (decision on 700/1100 K only); if both 300 K checks fail AND fewer than 6 in-domain high-T points remain, no decision is taken and the law is left as is",
        },
        "law_under_test": {
            "source": "phase_c/final_law/final_law.json (bulk_law_terms)",
            "form": "kappa_law(x, T) = 1 / (0.2092492 + 1.9190900 x - 2.2443438 x^2 + 8.352241e-5 T)",
        },
        "decision_rule": {
            "rho": "rho(x, T) = kappa_HNEMD / kappa_law over in-domain points that pass the checks",
            "strengthen": "median rho in [0.85, 1.15] and every |rho - 1| <= 0.25: law level confirmed",
            "correct_level": "median rho > 1.15 and CV(rho) <= 0.15: the law's shape is kept and its level is multiplied by median rho (ledger correct operation, scope label 'level from HNEMD, shape from rNEMD')",
            "replace_level": "median rho > 1.15 and CV(rho) > 0.15: the bulk law is refit on the size-free points with HG-SR v2 (adopted settings: noise weights, beam 200, shape filter on x in [0.05, 0.9], T in [300, 1100] K; generated basis on features x, T; leave-one-(x, T)-point-out selection); the rNEMD law is kept as a downweighted shape witness",
            "downweight": "median rho < 0.85: the law level is downweighted and flagged, no refit",
        },
        "predictions": {
            "Pr1": "rho(0.5, 300 K) in [1.2, 1.6] (seq-8 value gives 1.41)",
            "Pr2": "median rho > 1.15 (the law is a lower bound across its domain)",
            "Pr3": "at every T, the HNEMD kappa minimum over the grid sits at x in {0.3, 0.5, 0.7}",
            "Pr4": "at every x, kappa_HNEMD(1100 K) < kappa_HNEMD(300 K), and the drop at x = 0.5 is <= 30%",
            "Pr5": "BTE-DFT / HNEMD at x = 0.5, 300 K in [2.4, 3.4]",
            "Pr6": "G_lin passes at both compositions",
            "Pr7": "G_size passes at both compositions",
        },
        "bte_reference": "party4_bte/results/bte_x{x}_T{T}.json (x = 0.3 has none; reported without a ratio)",
        "runs": runs,
    }
    with open(OUT, "w") as f:
        json.dump(design, f, indent=1, sort_keys=True)
        f.write("\n")
    print(len(runs), "runs ->", OUT)


if __name__ == "__main__":
    main()
