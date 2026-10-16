#!/usr/bin/env python3
"""Phase C production detector: evidence rows in, shard operations out.

Written and FROZEN (SHA-256 on the campaign ledger) before the blind
fault catalog was opened; thresholds are fixed a priori below and are
not tuned on any catalog entry. The detector sees only run rows

    {run_id, batch_id, x, T, ncz, seed, kappa}

and never the probe truth or injected ground truth.

Pipeline (the six-stage loop of the design doc, specialized to one
campaign party):
  1. per-point 1/L extrapolation: 1/kappa = a + b/ncz over the sizes a
     point has (points with one size are marked `insufficient`);
  2. alloy law: 1/kappa_inf regressed on an exhaustive subset of
     {x(1-x), x, t, x(1-x)t} with t = T/1000 plus intercept, BIC pick;
  3. red flags, each with its own a-priori threshold:
     - DUPLICATE: identical kappa across run_ids (double counting);
     - BATCH: leave-one-batch-out residual offset of a batch
       (robust z >= Z_BATCH);
     - PARTY: whole-campaign anchor check against the previously
       collected CHPC-MD party (ratio outside [1/1.5, 1.5]);
     - SIZE: per-point size-trend slope b/a far from the population
       (robust z >= Z_SIZE) = the point does not behave like a crystal
       with long-wavelength phonons;
     - REGIME: a composition-temperature cell whose residuals are
       coherent across >= 2 batches (z >= Z_REGIME);
     - POINT: single-point residual outlier (robust z >= Z_POINT),
       tested for a label swap within its batch;
     - PHYSICS guard: T at or above the real Si-Ge solidus (a crystalline
       MD point cannot describe a partially molten alloy).
  4. triage into the grammar (two-bar rule):
     - identified cause (duplicate, unit factor, Celsius/Kelvin shift,
       label swap) -> forget (duplicates) or correct;
     - statistical verdict only, batch- or party-coherent -> quarantine;
     - regime-coherent across batches (world richer than the law) ->
       scope-limit, never forget;
     - size-trend outlier (different transport physics) -> split;
     - physics guard -> scope-limit (method validity domain);
     - isolated point outlier without an identified cause -> quarantine.
Returns a list of operations with targets and reasons.

Usage as a library: detect(rows) -> dict. CLI: detector.py rows.json
"""
from __future__ import annotations

import itertools
import json
import math
import sys

import numpy as np

# Thresholds: set on the detector author's own synthetic null (200
# production-shaped campaigns, 3% run noise; selftest_detector.py) to a
# per-campaign false-fire rate near 1%, BEFORE the blind catalog was
# opened. They are frozen with this file's hash on the ledger.
Z_BATCH = 4.5
Z_POINT = 5.5
Z_SIZE = 6.0
Z_REGIME = 4.5
PARTY_RATIO = 1.5
UNIT_FACTORS = {"1000": 1e3, "1/1000": 1e-3, "100": 1e2, "1/100": 1e-2,
                "10": 10.0, "1/10": 0.1,
                "1/units.fs^2 (ASE)": 103.6427, "units.fs^2 (ASE)": 1 / 103.6427,
                "kcal/kJ 4.184": 4.184, "1/4.184": 1 / 4.184}
UNIT_TOL = 0.03
C_TO_K = 273.15
DUP_MODE = "kappa"   # frozen rule; "design" = post-hoc variant D2
# previously collected CHPC-MD 1/L extrapolations (chpc/RESULTS.md)
ANCHORS = [(0.5, 300.0, 1.80), (0.15, 300.0, 1.96), (0.5, 1100.0, 1.52)]
X_EDGES = [0.0, 0.23, 0.41, 0.59, 0.77, 1.0]
T_EDGES = [0.0, 525.0, 750.0, 975.0, 1e9]


def solidus(x: float) -> float:
    """Approximate real Si(1-x)Ge(x) solidus in K (lens diagram, slight
    downward bow): 1687 K (Si) to 1211 K (Ge)."""
    return 1687.0 * (1 - x) + 1211.0 * x - 150.0 * x * (1 - x)


def _robust_z(v, ref):
    ref = np.asarray(ref, float)
    med = np.median(ref)
    mad = 1.4826 * np.median(np.abs(ref - med))
    if mad <= 1e-12:
        mad = np.std(ref) + 1e-12
    return (np.asarray(v, float) - med) / mad


# --- stage 1: per-point extrapolation --------------------------------------

def points_of(rows):
    pts = {}
    for r in rows:
        key = (r["batch_id"], round(r["x"], 6), round(r["T"], 3), r["seed"])
        pts.setdefault(key, []).append(r)
    out = []
    for (b, x, T, seed), rs in pts.items():
        sizes = sorted({r["ncz"] for r in rs})
        p = {"batch_id": b, "x": x, "T": T, "seed": seed,
             "run_ids": sorted(r["run_id"] for r in rs), "n_sizes": len(sizes)}
        if len(sizes) < 2 or any(r["kappa"] <= 0 for r in rs):
            p["insufficient"] = True
            out.append(p)
            continue
        inv_l = np.array([1.0 / r["ncz"] for r in rs])
        inv_k = np.array([1.0 / r["kappa"] for r in rs])
        b1, a = np.polyfit(inv_l, inv_k, 1)
        p.update({"a": float(a), "b": float(b1),
                  "kappa_inf": float(1 / a) if a > 0 else float("nan"),
                  "b_over_a": float(b1 / a) if a != 0 else float("nan")})
        out.append(p)
    return out


# --- stage 2: law ----------------------------------------------------------

BASIS = {"x(1-x)": lambda x, t: x * (1 - x), "x": lambda x, t: x,
         "t": lambda x, t: t, "x(1-x)t": lambda x, t: x * (1 - x) * t}


def design(x, t, terms):
    cols = [np.ones_like(x)] + [BASIS[k](x, t) for k in terms]
    return np.column_stack(cols)


def fit_law(pts):
    x = np.array([p["x"] for p in pts])
    t = np.array([p["T"] for p in pts]) / 1000.0
    y = np.array([1.0 / p["kappa_inf"] for p in pts])
    n, best = len(y), None
    for k in range(0, len(BASIS) + 1):
        for terms in itertools.combinations(BASIS, k):
            if n <= len(terms) + 2:
                continue
            A = design(x, t, terms)
            coef, *_ = np.linalg.lstsq(A, y, rcond=None)
            rss = float(np.sum((A @ coef - y) ** 2))
            bic = n * math.log(rss / n + 1e-300) + (len(terms) + 1) * math.log(n)
            if best is None or bic < best["bic"]:
                dof = max(n - len(terms) - 1, 1)
                cov = (rss / dof) * np.linalg.pinv(A.T @ A)
                best = {"terms": list(terms), "coef": coef.tolist(),
                        "bic": bic, "cov": cov.tolist()}
    return best


def pred_log_sd(law, x, T):
    """Standard deviation of log(kappa) predicted by the law at (x, T),
    from the OLS coefficient covariance (delta method)."""
    a = design(np.atleast_1d(float(x)), np.atleast_1d(T / 1000.0),
               law["terms"])[0]
    r = float(a @ np.array(law["coef"]))
    var_r = float(a @ np.array(law["cov"]) @ a)
    return math.sqrt(max(var_r, 0.0)) / abs(r)


def predict(law, x, T):
    x = np.atleast_1d(np.asarray(x, float))
    t = np.atleast_1d(np.asarray(T, float)) / 1000.0
    r = design(x, t, law["terms"]) @ np.array(law["coef"])
    # deviation D1 (ledger): a law fitted on a subset can extrapolate to
    # a non-positive thermal resistivity; floor it (kappa <= 1000 W/mK)
    # so the point reads as a gross residual instead of crashing
    return 1.0 / np.maximum(r, 1e-3)


def _good(pts):
    return [p for p in pts if not p.get("insufficient")
            and np.isfinite(p.get("kappa_inf", np.nan)) and p["kappa_inf"] > 0]


def residuals(law, pts):
    return np.array([math.log(p["kappa_inf"]) -
                     math.log(float(predict(law, p["x"], p["T"])[0]))
                     for p in pts])


def regime(x, T):
    xi = max(i for i, e in enumerate(X_EDGES[:-1]) if x >= e)
    ti = max(i for i, e in enumerate(T_EDGES[:-1]) if T >= e)
    return f"x{xi}T{ti}"


# --- stage 3 + 4 -----------------------------------------------------------

def detect(rows: list[dict]) -> dict:
    ops, flags = [], []
    rows = [dict(r) for r in rows]

    # physics guard first (a declared validity domain, not a statistic)
    melt = [r for r in rows if r["T"] >= solidus(r["x"])]
    if melt:
        ops.append({"op": "scope-limit", "layer": "physics",
                    "target_runs": sorted(r["run_id"] for r in melt),
                    "reason": "T at or above the real solidus: crystalline "
                              "Tersoff MD outside its physical validity"})
    live = [r for r in rows if r["T"] < solidus(r["x"])]

    # DUPLICATE (identified cause: double counting). DUP_MODE "kappa" is
    # the frozen rule (ledger seq 5); "design" is post-hoc sensitivity
    # variant D2 (ledger): a duplicate is a second run_id with the same
    # design coordinates (x, T, ncz, seed), because genuine replicas use
    # different seeds, while kappa printed to 3 decimals collides by
    # chance across 132 real runs.
    seen, dup = {}, []
    for r in sorted(live, key=lambda r: r["run_id"]):
        key = ((round(r["kappa"], 9), r["ncz"]) if DUP_MODE == "kappa" else
               (round(r["x"], 6), round(r["T"], 3), r["ncz"], r["seed"]))
        if key in seen and seen[key]["run_id"] != r["run_id"]:
            dup.append(r["run_id"])
        else:
            seen[key] = r
    if dup:
        ops.append({"op": "forget", "layer": "statistical",
                    "target_runs": sorted(dup),
                    "reason": "exact duplicate of an earlier run "
                              "(double counting)"})
        live = [r for r in live if r["run_id"] not in set(dup)]

    pts = points_of(live)
    good = _good(pts)
    if len(good) < 8:
        return {"ops": ops, "flags": ["too few extrapolable points"],
                "law": None}

    # SIZE: points whose size trend is unlike a crystal
    ba = np.array([p["b_over_a"] for p in good])
    zs = _robust_z(ba, ba)
    size_out = [p for p, z in zip(good, zs) if abs(z) >= Z_SIZE]
    for p in size_out:
        ops.append({"op": "split", "layer": "statistical",
                    "target_runs": p["run_ids"],
                    "reason": f"size trend b/a={p['b_over_a']:.3g} is a "
                              "population outlier: different transport "
                              "physics (phase or structure), separate scope"})
    good = [p for p in good if p not in size_out]

    law = fit_law(good)

    # PARTY anchor check
    ratios = [float(predict(law, x, T)[0]) / k for x, T, k in ANCHORS]
    gm = float(np.exp(np.mean(np.log(ratios))))
    if not (1 / PARTY_RATIO <= gm <= PARTY_RATIO):
        cause = _unit_cause(gm)
        allruns = sorted(r["run_id"] for r in live)
        ops.append({"op": "correct" if cause else "quarantine",
                    "layer": "statistical", "target_runs": allruns,
                    "reason": f"whole-campaign offset vs prior CHPC-MD "
                              f"anchors, ratio {gm:.3g}"
                              + (f", matches unit factor {cause}" if cause
                                 else "")})
        return {"ops": ops, "flags": flags, "law": law}

    # BATCH: leave-one-batch-out offsets, peeled one batch at a time
    # (the most extreme batch first) so a gross batch cannot contaminate
    # the reference fit used to test the others
    bad_batches = set()
    while True:
        cand = []
        for b in sorted({p["batch_id"] for p in good} - bad_batches):
            inb = [p for p in good if p["batch_id"] == b]
            rest = [p for p in good if p["batch_id"] != b
                    and p["batch_id"] not in bad_batches]
            if len(inb) < 2 or len(rest) < 8:
                continue
            lw = fit_law(rest)
            rr = residuals(lw, rest)
            sig = 1.4826 * np.median(np.abs(rr - np.median(rr))) + 1e-9
            rb = residuals(lw, inb)
            z = float(np.mean(rb) / (sig / math.sqrt(len(rb))))
            same = float(np.mean(np.sign(rb) == np.sign(np.mean(rb))))
            if abs(z) >= Z_BATCH and same >= 0.75:
                cand.append((abs(z), z, b, lw, inb, rb))
        if not cand:
            break
        _, z, b, lw, inb, rb = max(cand, key=lambda c: c[0])
        bad_batches.add(b)
        factor = float(np.exp(np.mean(rb)))
        cause = _unit_cause(factor)
        if cause is None:
            cause = _celsius_cause(lw, inb)
        runs = sorted(r for q in pts if q["batch_id"] == b
                      for r in q["run_ids"])
        ops.append({"op": "correct" if cause else "quarantine",
                    "layer": "statistical", "target_batch": b,
                    "target_runs": runs,
                    "reason": f"batch-coherent offset z={z:.1f}, factor "
                              f"{factor:.3g}" + (f"; cause: {cause}"
                                                 if cause else
                                                 "; no cause identified "
                                                 "(two-bar rule: suspend, "
                                                 "do not delete)")})
    good = [p for p in good if p["batch_id"] not in bad_batches]
    law = fit_law(good)
    res = residuals(law, good)

    # REGIME: residual coherence per (x, T) cell across >= 2 batches
    sig = 1.4826 * np.median(np.abs(res - np.median(res))) + 1e-9
    cells = {}
    for p, e in zip(good, res):
        cells.setdefault(regime(p["x"], p["T"]), []).append((p, e))
    regime_hit = set()
    for c, lst in cells.items():
        es = np.array([e for _, e in lst])
        nb = len({p["batch_id"] for p, _ in lst})
        if len(es) < 2 or nb < 2:
            continue
        # leave-cell-out refit so the anomaly cannot absorb itself
        others = [p for p in good if regime(p["x"], p["T"]) != c]
        lw = fit_law(others)
        ec = residuals(lw, [p for p, _ in lst])
        sd_pred = float(np.mean([pred_log_sd(lw, p["x"], p["T"])
                                 for p, _ in lst]))
        z = float(np.mean(ec) / math.sqrt(sig ** 2 / len(ec) + sd_pred ** 2))
        if abs(z) >= Z_REGIME and np.all(np.sign(ec) == np.sign(np.mean(ec))):
            regime_hit.add(c)
            ops.append({"op": "scope-limit", "layer": "statistical",
                        "target_regime": c,
                        "target_runs": sorted(r for p, _ in lst
                                              for r in p["run_ids"]),
                        "reason": f"regime-coherent deviation z={z:.1f} "
                                  f"across {nb} batches: world richer than "
                                  "the law; keep data, narrow the claim"})

    # POINT outliers (outside flagged regimes)
    zp = _robust_z(res, res)
    outl = [(p, z) for p, z in zip(good, zp) if abs(z) >= Z_POINT
            and regime(p["x"], p["T"]) not in regime_hit]
    handled = set()
    for p, z in outl:
        if id(p) in handled:
            continue
        swap = _label_swap(law, p, good, sig)
        if swap is not None:
            q, what = swap
            handled.update({id(p), id(q)})
            ops.append({"op": "correct", "layer": "statistical",
                        "target_runs": sorted(p["run_ids"] + q["run_ids"]),
                        "reason": f"{what} label swap between two points of "
                                  f"batch {p['batch_id']} explains both "
                                  "outliers"})
        else:
            handled.add(id(p))
            ops.append({"op": "quarantine", "layer": "statistical",
                        "target_runs": p["run_ids"],
                        "reason": f"isolated point outlier z={z:.1f}, no "
                                  "cause identified"})
    return {"ops": ops, "flags": flags, "law": law,
            "n_points": len(pts), "n_good": len(good)}


def _unit_cause(factor):
    for name, f in UNIT_FACTORS.items():
        if abs(factor / f - 1) <= UNIT_TOL:
            return f"unit factor {name}"
    return None


def _celsius_cause(law, inb):
    """Does relabeling the batch's T by +-273.15 K explain it?"""
    base = np.mean(np.abs(residuals(law, inb)))
    for s in (+C_TO_K, -C_TO_K):
        moved = [dict(p, T=p["T"] + s) for p in inb]
        if any(q["T"] <= 0 for q in moved):
            continue
        if np.mean(np.abs(residuals(law, moved))) < 0.25 * base:
            return f"temperature labels shifted by {s:+.2f} K (C/K)"
    return None


def _label_swap(law, p, good, sig):
    for q in good:
        if q is p or q["batch_id"] != p["batch_id"]:
            continue
        for what in ("x", "T"):
            a = dict(p, **{what: q[what]})
            b = dict(q, **{what: p[what]})
            before = np.abs(residuals(law, [p, q]))
            after = np.abs(residuals(law, [a, b]))
            if after.max() < 2.0 * sig and before.max() >= Z_POINT * sig * 0.9:
                return q, what
    return None


if __name__ == "__main__":
    rows = json.load(open(sys.argv[1]))
    print(json.dumps(detect(rows), indent=1, default=str))
