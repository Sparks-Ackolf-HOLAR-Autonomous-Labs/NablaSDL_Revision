#!/usr/bin/env python3
"""Write gk300_design.json: equilibrium Green-Kubo (GPUMD compute_hac) for
the 300 K law level that three driven-heat-current registrations left
carried from 700-1100 K (ledger 91/96-98, 99-102). Run 2026-10-07.
No driving force, so the
nonlinear runaway of long HNEMD cells cannot occur.
Stage K1: box convergence at x = 0.15 and 0.85 (8^3, 12^3, 16^3 cells) and a
method check against size-free HNEMD at x = 0.5, 700 K. Stage K2: the four
inner compositions at the box K1 selects, by a rule fixed here."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
parent = json.load(open(os.path.join(HERE, "..", "sizefree_design.json")))
a0 = {(r["x_ge"], r["T_K"]): r["a0_A"] for r in parent["runs"]}
pot = parent["runs"][0]["potential"]
NS = 10.0


def row(x, T, n, seed, check, stage, k2_box=None):
    r = {"T_K": T, "a0_A": a0[(x, T)], "cells": [n, n, n], "check": check,
         "config_seed": seed, "in_law_domain": True, "n_atoms": 8 * n ** 3,
         "potential": pot, "production_ns": NS, "estimator": "EMD Green-Kubo",
         "hac": {"sample_interval_steps": 10, "Nc": 10000, "output_interval": 10},
         "run_id": f"GK_x{x:g}_T{T}_{n}c_s{seed}", "seed": seed,
         "stage": stage, "system": "SiGe", "x_ge": x}
    if k2_box:
        r["k2_box"] = k2_box
    return r


runs = []
for x in (0.15, 0.85):
    for n, seeds in ((8, 6), (12, 6), (16, 4)):
        for s in range(seeds):
            runs.append(row(x, 300, n, 59001 + s, "size", "K1"))
for s in range(6):
    runs.append(row(0.5, 700, 8, 59101 + s, "method", "K1"))
for box in (8, 12):
    for x in (0.2, 0.3, 0.5, 0.7):
        for s in range(6):
            runs.append(row(x, 300, box, 59201 + s, "main", f"K2-box{box}", box))

design = {
    "campaign": "gpumd-gk300-level-2026-10-07",
    "paper": "P1 (law level at 300 K); P2 (a third follow-up purchase on a gap two registered rules left open, with a change of estimator fixed before the data)",
    "parent": "gpumd-sizefree-check300-2026-10-04 (ledger 91, 96-98) and gpumd-sizefree-level300-2026-10-04 (ledger 99-102): both scope_limit, 300 K level carried from 700-1100 K",
    "why": "ledger 101: in Tersoff SiGe at 300 K the longest HNEMD cells (48x8x8) ran away or failed the drift gate, so no box length could be selected. The reading recorded there was that long-wavelength modes respond nonlinearly to the driving force. Equilibrium Green-Kubo measures the same conductivity from heat-current fluctuations with no driving force.",
    "question": "What is the box-converged equilibrium Green-Kubo 300 K conductivity of Tersoff-1989 SiGe across x = 0.15-0.85, and does its level agree with the factor 1.281 carried from 700-1100 K?",
    "law": "kappa_law(x, T) = 1 / (0.2092492 + 1.9190900 x - 2.2443438 x^2 + 8.352241e-5 T) (phase_c/final_law/final_law.json)",
    "level_factor_carried": 1.281,
    "hnemd_reference_700K": {"x": 0.5, "T": 700, "kappa": 1.8656, "se": 0.1381, "source": "gpumd/sizefree/analysis_sizefree.json (ledger 87-90), 8x8x8, size-free HNEMD"},
    "protocol": {
        "engine": "GPUMD (CHPC build, gpumd_v2/GPUMD), equilibrium MD, compute_hac",
        "run_in": "npt_ber 100 ps, nvt_nhc 50 ps, then nve with compute_hac 10 10000 10 for 10 ns, dump_thermo 10000, time step 1 fs (HAC sampled every 10 fs to 100 ps correlation time)",
        "kappa_run": "hac.out running conductivity columns: kx = kxi + kxo, ky = kyi + kyo, kz; kappa_run(t) = (kx + ky + kz) / 3",
        "readout": "kappa_run = mean of kappa_run(t) over the window 50-100 ps",
        "placement": "execution detail: grn061 (granite sparks-gpu-grn, H100) when no sparks-partition job runs there, otherwise notchpeak-gpu-guest A40 (--gres=gpu:a40:1); moving between them needs only a placement note",
        "preemption": "requeue, restart from scratch with the same seed (declared, not a deviation)",
        "stage_order": ["K1", "K2-box<box*> (only the box K1 selects is built and run)"],
    },
    "run_gates": "R1: exit 0 and hac.out has 1000 rows; R2: mean NVE temperature within 3% of target (all thermo.out rows; dump_thermo covers only the NVE production); R3: 0 < kappa_run < 2000 W/mK",
    "point_rule": "an (x, T, box) point needs >= 3 passing runs (>= 2 for 16^3); estimate = seed mean of kappa_run, SE = seed standard deviation / sqrt(n)",
    "agreement": "two estimates agree when |a-b| <= 2*sqrt(sa^2+sb^2) + 0.10*(a+b)/2",
    "gates": {
        "G_plat": "for every K1 point, the seed-mean running conductivity averaged over 75-100 ps agrees with that over 50-75 ps (same agreement rule, SE from seeds)",
        "G_meth": "the GK point at x = 0.5, 700 K, 8^3 agrees with the size-free HNEMD reference (1.8656 +/- 0.1381 W/mK)",
        "G_conv": "at x = 0.15 and 0.85, the 12^3 point agrees with the 16^3 point",
        "box_star": "if G_plat, G_meth and G_conv pass: box* = 8 if the 8^3 point also agrees with the 16^3 point at both x, else box* = 12. If any gate fails: no box*, K2 is not run",
    },
    "decision_rule": {
        "fail": "any gate fails: the 300 K level stays carried from 700-1100 K; the K1 values are recorded as evidence about the equilibrium estimator; no factor change",
        "pass": "rho300(x) = kappa_GK(x, 300 K at box*) / kappa_law(x, 300) over x = 0.15, 0.2, 0.3, 0.5, 0.7, 0.85 (each needs a qualifying point; if fewer than 5 qualify, branch fail). Let m = median rho300, cv = stdev/mean. (a) cv <= 0.15 and |m/1.281 - 1| <= 0.10: strengthen the ledger-90 level correction at 300 K and lift the 'carried' label. (b) cv <= 0.15 and |m/1.281 - 1| > 0.10: correct, a temperature-dependent level: factor m at 300 K and 1.281 at 700-1100 K, linear in T between 300 and 700 K, scope label 'level from equilibrium GK at 300 K and HNEMD at 700-1100 K, shape from rNEMD'. (c) cv > 0.15: downweight the law's composition shape at 300 K (scope label 'composition shape at 300 K disagrees with equilibrium GK'); no refit in this registration",
        "not_affected": "the 700-1100 K level (1.281), the law's composition shape outside 300 K, all SiGeC and SiC claims",
    },
    "predictions": {
        "PrK1": "G_meth passes: GK and HNEMD agree at x = 0.5, 700 K",
        "PrK2": "G_plat and G_conv pass, with box* = 12",
        "PrK3": "kappa_GK(x = 0.15, 300 K, box*) >= 4.60 W/mK (the largest HNEMD value recorded at ledger 101, which was still rising with box length)",
        "PrK4": "branch (b) with m > 1.281",
    },
    "cost_estimate": "scaled from ledger-100 timing (15 min per 8192 atoms x 5 ns on H100): 8^3 runs about 15 min, 12^3 about 50 min, 16^3 about 2 h on H100, roughly twice on A40. K1 (38 runs) about 22 H100-hours; K2 (24 runs) 6 (box 8) or 20 (box 12) H100-hours",
    "n_runs_K1": sum(r["stage"] == "K1" for r in runs),
    "n_runs_K2_per_box": 24,
    "runs": runs,
}
json.dump(design, open(os.path.join(HERE, "gk300_design.json"), "w"), indent=1, sort_keys=True)
print(len(runs), "rows;", design["n_runs_K1"], "in K1")
