#!/usr/bin/env python3
"""Planted-case calibration of CHD BEFORE it is trusted on real data.

Why: the 2026-09-26 smoke test (ASSESSMENT.md) showed CHD with library
defaults drawing spurious edges on a 60-row synthetic table. Our real
literature table is smaller (17 fit-usable rows) and much noisier, so
the settings are tuned here on synthetic tables that copy the real
design (the real (x, T) points, the real class vector, the real noise
level) with a KNOWN ancestor set, and the hit / false-positive rates
are recorded in calibration.json.

Planted cases (target is always ln kappa, "logk"):
  A17      logk = f(x,T) + e                vars x,T         truth {x,T}
  B17real  logk = f(x,T) + D*cls + e         vars x,T,cls     truth {x,T,cls}
           cls = the REAL reduced-dim indicator of the 17 rows (2 of 17)
  B17bal   same, cls on 5 of 17 rows (what a better-balanced corpus gives)
  C17      logk = f(x,T) + e                vars x,T,junk    truth {x,T}; junk = FP
  N17      logk = e (pure null)             vars x,T,junk    any ancestor = FP
  B42      logk = f(x,300) + D*cls + e       vars x,cls,junk  truth {x,cls}; junk = FP
           (all 42 literature rows with x and kappa, T ignored: real x and class vectors)
  N42      logk = e                         vars x,cls,junk  any ancestor = FP
  MD29     logk = ln kappa_MD(x,T,L) + e_md  vars x,T,L,seed  truth {x,L}; seed = FP
           (the real 29 CHPC-MD design: x, T, L, seed)
f(x,T): Matthiessen resistivity 1/kappa = (T/300)(0.0065 + 0.011x) +
0.7x(1-x) (Si 154, Ge 57, Si0.8Ge0.2 8 W/mK at 300 K); class effect
D = ln(1/10) (reduced-dim samples 10x lower, as in the real x=0.2 rows:
1.1-1.2 vs 9 W/mK); e ~ N(0, s) with s = the REAL pooled within-cell
standard deviation of ln kappa (0.94, computed below) and s/2; MD noise
s_md = 0.05 (real seed-to-seed scatter is 0.03) and 0.025.

Settings grid: kernel set {lin+quad+gauss (default), lin+quad, lin} x
mode chooser {max-increment (default), threshold 0.4/0.6/0.8};
kernel chooser = library default (min noise below the Z-test band).

Pre-stated selection rule (fixed before looking at results):
  feasible = every FP test at the realistic noise level has FP rate
             <= 1/8 (at most one seed in eight);
  score    = mean hit rate over the scored true ancestors
             (x in A17, B17bal, C17, B42; cls in B17bal, B42; x and L
             in MD29) at the realistic noise level;
  choose   = the feasible setting with the highest score; ties broken
             by grid order (defaults first). If no setting is feasible,
             CHD FAILS calibration and stage 0 must use the fallback
             criterion (ANOVA on log-kappa residuals), and says so.
B17real is reported, not scored: it measures whether the real 17-row
design can reveal a class effect at all.

A second, CHD-core criterion is calibrated alongside ("ablation
noise"): delta(v) = noise ratio of logk given S minus v, minus the
noise ratio given S (min over the setting's kernels). Its threshold is
the largest delta any junk variable produced across all seeds, so it
has 0 in-sample false positives by construction; its class hit rate is
reported.

Deterministic: numpy seeds 0..7, CHD jax key 0. Runtime about 5 min
on 8 CPU workers. Usage: ~/venvs/chd/bin/python calibrate_chd.py
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from stage0_data import literature_rows, md_rows  # noqa: E402

SEEDS = list(range(8))
D_CLASS = float(np.log(0.1))
S_MD = 0.05
FP_MAX = 1.0 / 8.0
WORKERS = 8


def f_bulk(x, T):
    r = (T / 300.0) * (0.0065 + 0.011 * x) + 0.7 * x * (1 - x)
    return -np.log(r)


def f_md(x, T, L):
    r = 0.0065 * (T / 300.0) * (1 + 1.7 * x) + 1.2 * x * (1 - x) + 26.0 / L
    return -np.log(r)


def real_designs():
    lit = literature_rows()
    fit = [r for r in lit if r["x"] is not None and r["T"] is not None
           and r["kappa"]]
    xonly = [r for r in lit if r["x"] is not None and r["T"] is None
             and r["kappa"]]
    xall = [r for r in lit if r["x"] is not None and r["kappa"]]
    # pooled within-cell sd of ln kappa (cells = x, T, sample group)
    cells = {}
    for r in fit:
        cells.setdefault((r["x"], r["T"], r["sample_group"]), []).append(
            np.log(r["kappa"]))
    ss = sum(float(np.sum((np.array(v) - np.mean(v)) ** 2))
             for v in cells.values() if len(v) > 1)
    dof = sum(len(v) - 1 for v in cells.values() if len(v) > 1)
    s_real = float(np.sqrt(ss / dof))
    md, _ = md_rows()
    md = [r for r in md if r["party"] == "CHPC-MD"]
    return {
        "x17": np.array([r["x"] for r in fit], float),
        "T17": np.array([r["T"] for r in fit], float),
        "cls17": np.array([r["sample_group"] != "bulk" for r in fit], float),
        "x42": np.array([r["x"] for r in xall], float),
        "cls42": np.array([r["sample_group"] != "bulk" for r in xall], float),
        "md": {k: np.array([r[k] for r in md], float)
               for k in ("x", "T", "L", "seed")},
        "s_real": s_real, "s_real_dof": dof,
        "n": {"fit17": len(fit), "xonly_noT": len(xonly), "x42": len(xall),
              "md29": len(md)},
    }


def make_case(case, seed, noise_scale, D):
    rng = np.random.default_rng(1000 * seed + {"A17": 1, "B17real": 2,
                                               "B17bal": 3, "C17": 4,
                                               "N17": 5, "B42": 6, "N42": 7,
                                               "MD29": 8}[case])
    s = D["s_real"] * noise_scale
    if case in ("A17", "B17real", "B17bal", "C17", "N17"):
        x, T = D["x17"], D["T17"]
        n = len(x)
        e = rng.normal(0, s, n)
        if case == "A17":
            return np.column_stack([x, T, f_bulk(x, T) + e]), ["x", "T", "logk"], \
                {"true": ["x", "T"], "fp": []}
        if case in ("B17real", "B17bal"):
            if case == "B17real":
                cls = D["cls17"]
            else:
                cls = np.zeros(n)
                cls[rng.choice(n, 5, replace=False)] = 1.0
            y = f_bulk(x, T) + D_CLASS * cls + e
            return np.column_stack([x, T, cls, y]), ["x", "T", "cls", "logk"], \
                {"true": ["x", "T", "cls"], "fp": []}
        junk = rng.normal(size=n)
        y = (f_bulk(x, T) + e) if case == "C17" else e
        return np.column_stack([x, T, junk, y]), ["x", "T", "junk", "logk"], \
            {"true": ["x", "T"] if case == "C17" else [],
             "fp": ["junk"] if case == "C17" else ["x", "T", "junk"]}
    if case in ("B42", "N42"):
        x, cls = D["x42"], D["cls42"]
        n = len(x)
        e = rng.normal(0, s, n)
        junk = rng.normal(size=n)
        y = (f_bulk(x, 300.0) + D_CLASS * cls + e) if case == "B42" else e
        return np.column_stack([x, cls, junk, y]), ["x", "cls", "junk", "logk"], \
            {"true": ["x", "cls"] if case == "B42" else [],
             "fp": ["junk"] if case == "B42" else ["x", "cls", "junk"]}
    if case == "MD29":
        m = D["md"]
        n = len(m["x"])
        y = f_md(m["x"], m["T"], m["L"]) + rng.normal(0, S_MD * noise_scale, n)
        return np.column_stack([m["x"], m["T"], m["L"], m["seed"], y]), \
            ["x", "T", "L", "seed", "logk"], {"true": ["x", "L"], "fp": ["seed"]}
    raise ValueError(case)


CASES = ["A17", "B17real", "B17bal", "C17", "N17", "B42", "N42", "MD29"]
NOISE_SCALES = [1.0, 0.5]
KSUB = {"lin+quad+gauss": ["linear", "quadratic", "gaussian"],
        "lin+quad": ["linear", "quadratic"], "lin": ["linear"]}


def _work(job):
    import chd_common as C
    case, seed, ns, D = job
    X, names, truth = make_case(case, seed, ns, D)
    out = {"case": case, "seed": seed, "noise_scale": ns, "truth": truth,
           "runs": {}, "ablation": {}}
    for s in C.all_settings():
        r = C.run_chd(X, names, "logk", s)
        out["runs"][C.setting_name(s)] = r["ancestors"]
    # ablation noise: full candidate set vs each variable removed
    cands = [n for n in names if n != "logk"]
    full = C.noise_given(X, names, "logk", cands)
    for v in cands:
        red = C.noise_given(X, names, "logk", [c for c in cands if c != v])
        out["ablation"][v] = {
            ks: (min(red["per_kernel"][k]["noise"] for k in kk)
                 - min(full["per_kernel"][k]["noise"] for k in kk))
            for ks, kk in KSUB.items()}
    return out


def summarize(results, D):
    import chd_common as C
    settings = [C.setting_name(s) for s in C.all_settings()]
    table = {}
    for ns in NOISE_SCALES:
        for sname in settings:
            row = {}
            for case in CASES:
                rs = [r for r in results if r["case"] == case
                      and r["noise_scale"] == ns]
                truth = rs[0]["truth"]
                hits = {v: float(np.mean([v in r["runs"][sname] for r in rs]))
                        for v in truth["true"]}
                fp = (float(np.mean([any(v in r["runs"][sname]
                                         for v in truth["fp"]) for r in rs]))
                      if truth["fp"] else None)
                row[case] = {"hit_rate": hits, "fp_rate": fp}
            table[f"{ns}|{sname}"] = row
    scored = [("A17", "x"), ("B17bal", "x"), ("C17", "x"), ("B42", "x"),
              ("B17bal", "cls"), ("B42", "cls"), ("MD29", "x"), ("MD29", "L")]
    fp_tests = ["C17", "N17", "B42", "N42", "MD29"]
    ranking = []
    for sname in settings:
        row = table[f"1.0|{sname}"]
        score = float(np.mean([row[c]["hit_rate"][v] for c, v in scored]))
        fpmax = max(row[c]["fp_rate"] for c in fp_tests)
        ranking.append({"setting": sname, "score": score, "max_fp_rate": fpmax,
                        "feasible": fpmax <= FP_MAX + 1e-12})
    feas = [r for r in ranking if r["feasible"]]
    chosen = max(feas, key=lambda r: r["score"]) if feas else None
    # ablation-noise criterion, per kernel set, realistic noise
    abl = {}
    for ks in KSUB:
        junk_d = [r["ablation"][v][ks] for r in results
                  if r["noise_scale"] == 1.0
                  for v in r["truth"]["fp"] if v in r["ablation"]]
        thr = float(max(junk_d))
        hit = {}
        for case in ("B17real", "B17bal", "B42"):
            ds = [r["ablation"]["cls"][ks] for r in results
                  if r["case"] == case and r["noise_scale"] == 1.0]
            hit[case] = {"cls_hit_rate": float(np.mean([d > thr for d in ds])),
                         "cls_delta_median": float(np.median(ds))}
        abl[ks] = {"threshold_delta": thr,
                   "junk_delta_quantiles": [float(q) for q in np.quantile(
                       junk_d, [0.5, 0.9, 1.0])],
                   "n_junk_deltas": len(junk_d), "class": hit}
    return table, ranking, chosen, abl


def main():
    D = real_designs()
    jobs = [(c, s, ns, D) for ns in NOISE_SCALES for c in CASES for s in SEEDS]
    t0 = time.time()
    os.environ["XLA_FLAGS"] = ("--xla_cpu_multi_thread_eigen=false "
                               "intra_op_parallelism_threads=1")
    ctx = mp.get_context("spawn")
    with ctx.Pool(WORKERS) as pool:
        results = pool.map(_work, jobs, chunksize=2)
    table, ranking, chosen, abl = summarize(results, D)
    import chd_common as C
    out = {
        "what": "planted-case calibration of CHD (ComputationalHypergraphDiscovery "
                f"{C.CHD_VERSION}) on synthetic tables copying the real stage-0 designs",
        "real_design": {"n": D["n"], "noise_sd_ln_kappa": D["s_real"],
                        "noise_sd_dof": D["s_real_dof"],
                        "class_effect_ln": D_CLASS,
                        "n_reduced_dim_in_fit17": int(D["cls17"].sum()),
                        "n_nonbulk_in_x42": int(D["cls42"].sum()),
                        "md_noise_sd_ln": S_MD},
        "seeds": SEEDS, "noise_scales": NOISE_SCALES,
        "selection_rule": {
            "feasible": f"FP rate <= {FP_MAX} on every FP test "
                        "(C17 junk, N17 any, B42 junk, N42 any, MD29 seed) at realistic noise",
            "score": "mean hit rate over x in A17/B17bal/C17/B42, cls in B17bal/B42, "
                     "x and L in MD29 at realistic noise",
            "tie_break": "grid order (defaults first)"},
        "ranking": ranking,
        "chosen_setting": chosen,
        "calibration_passed": chosen is not None,
        "chosen_rates": (table[f"1.0|{chosen['setting']}"] if chosen else None),
        "chosen_rates_half_noise": (table[f"0.5|{chosen['setting']}"]
                                    if chosen else None),
        "default_setting_rates": table["1.0|lin+quad+gauss|maxinc"],
        "ablation_noise_criterion": abl,
        "full_table": table,
        "runtime_s": round(time.time() - t0, 1),
    }
    with open(os.path.join(HERE, "calibration.json"), "w") as f:
        json.dump(out, f, indent=1)
    for r in sorted(ranking, key=lambda r: -r["score"]):
        print(f"{r['setting']:28s} score {r['score']:.3f} maxFP "
              f"{r['max_fp_rate']:.3f} feasible={r['feasible']}")
    print("chosen:", chosen)
    print("ablation:", json.dumps({k: {"thr": v["threshold_delta"],
                                       **{c: v['class'][c]['cls_hit_rate']
                                          for c in v['class']}}
                                   for k, v in abl.items()}))
    print(f"runtime {out['runtime_s']} s -> calibration.json")


if __name__ == "__main__":
    main()
