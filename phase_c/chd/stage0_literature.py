#!/usr/bin/env python3
"""CHD stage-0 on the literature party: the measured scope-split decision.

PRE-STATED SPLIT RULE (fixed before running on real data; do not edit
after seeing results without ledgering the change):

Candidate partitions of the literature party (groupings pre-declared in
stage0_data.py, merged by physics, not by outcome):
  P_sample  bulk | reduced-dim (nanowire, nanostructured, film,
            superlattice) | amorphous | unclassified ("other")
  P_method  simulation (MD, BTE/DFT) | measurement (experiment,
            model-fit) | unclear
A partition is ADOPTED as a scope split iff BOTH hold:
  C1 (structure) its indicator variable is in CHD's ancestor set of
     ln kappa under the CALIBRATED setting (calibration.json,
     chosen_setting) on the full variable set {x, T, sample, method,
     junk} of the fit table (rows with x, T, kappa); where the fit table
     has fewer than 3 rows in the non-reference class, the x-table
     (rows with x, kappa; T not a variable) is used instead;
  C2 (fit)  on the fit table, every scope with >= MIN_POINTS (12) rows
     gets its own law, and its 5-fold CV MedAPE on kappa is at least
     10 percentage points below the pooled law's CV MedAPE on the SAME
     rows, for BOTH project engines (hgsr balanced, minisr-pooled);
     scopes below MIN_POINTS are split off but refused a law (the
     fit_party.py rule), and at least one scope must be fittable.
If both partitions pass, the one with the larger mean CV gain is the
primary split; the other is recorded as a candidate secondary split.
If neither passes, the decision is "no split" (stated as such).

Reported alongside (not part of the rule, for transparency):
  - CHD under the library default setting and the best-scoring
    sensitivity setting (lin+quad|thr0.8: full-structure recovery on the
    planted cases but 2/8 false positives on the pure-null 17-row case);
  - CHD noise ratios n/(n+s) of ln kappa given {x,T}, {x,T,class},
    {x,T,method}, ... with the Z-test band (noise above Z_low means the
    variables explain nothing distinguishable from noise);
  - the classical fallback: OLS of ln kappa on (1, x, x(1-x), T/1000),
    then one-way ANOVA of the residuals by sample and method group.
MD contrast: CHD on the CHPC-MD finite-size rows (x, T, L, seed,
cross-section, swap interval); expected ln kappa <- (x, L) (T weakly),
NOT seed.

Rows: nothing is imputed; a row enters a table only if it has every
variable of that table. Counts are written to stage0_results.json.

Usage: ~/venvs/chd/bin/python stage0_literature.py   (after calibrate_chd.py)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "sr_compare"))
import chd_common as C  # noqa: E402
from stage0_data import literature_rows, md_rows  # noqa: E402
import hgsr  # noqa: E402
from datasets import regime  # noqa: E402

MIN_POINTS = 12
CV_GAIN_PTS = 10.0
K = 5
JUNK_SEED = 12345
SENSITIVITY_SETTING = ("lin+quad", "thr0.8")


# ---------------------------------------------------------------- SR/CV
def errors(t, p):
    t, p = np.asarray(t, float), np.asarray(p, float)
    ok = np.isfinite(p) & (p > 0)
    p = np.where(ok, p, 0.0)       # non-finite or negative kappa is just wrong
    ape = np.abs(p - t) / t
    return {"medape_pct": float(100 * np.median(ape)),
            "rmse_kappa": float(np.sqrt(np.mean((p - t) ** 2))),
            "n_invalid_pred": int((~ok).sum()), "n": int(len(t))}


def folds(n, k=K):
    return [list(range(i, n, k)) for i in range(min(k, n))]


def cv_predictions(rows, pooled):
    """Round-robin 5-fold CV exactly as sr_compare/run_compare.py."""
    pred = np.full(len(rows), np.nan)
    for hold in folds(len(rows)):
        hs = set(hold)
        train = [r for i, r in enumerate(rows) if i not in hs]
        m = hgsr.fit(train, ["x", "T"], pooled=pooled)
        pred[hold] = hgsr.predict(m, [rows[i] for i in hold])
    return pred


def as_fit_rows(rs):
    return [{"x": float(r["x"]), "T": float(r["T"]), "L": 0.0,
             "kappa": float(r["kappa"]), "party": "literature",
             "regime": regime(float(r["x"]), float(r["T"])),
             "source": r["corpusId"], "row_id": r["row_id"]} for r in rs]


def describe(m):
    s = m["selected"]
    return "kappa = 1/r, r = " + " + ".join(
        f"{c:.4g}*{n}" for n, c in zip(s["names"], s["coefs"]))


# ---------------------------------------------------------------- tables
def encode(rows, with_T):
    """Numeric table for CHD. Indicators: rdim (reduced-dim), amorph,
    sim (simulation method); junk = seeded N(0,1) negative control."""
    rng = np.random.default_rng(JUNK_SEED)
    cols = {"x": [float(r["x"]) for r in rows]}
    if with_T:
        cols["T"] = [float(r["T"]) for r in rows]
    cols["rdim"] = [float(r["sample_group"] == "reduced-dim") for r in rows]
    cols["amorph"] = [float(r["sample_group"] == "amorphous") for r in rows]
    cols["sim"] = [float(r["method_group"] == "simulation") for r in rows]
    cols["junk"] = list(rng.normal(size=len(rows)))
    cols["logk"] = [float(np.log(r["kappa"])) for r in rows]
    names = list(cols)
    return np.column_stack([cols[n] for n in names]), names


def chd_block(X, names, varsets, calibrated):
    out = {}
    for label, vs in varsets.items():
        idx = [names.index(v) for v in vs + ["logk"]]
        Xs, ns = X[:, idx], vs + ["logk"]
        res = {"variables": vs}
        for tag, st in (("calibrated", calibrated),
                        ("sensitivity", SENSITIVITY_SETTING),
                        ("library_default", C.DEFAULT_SETTING)):
            r = C.run_chd(Xs, ns, "logk", st)
            res[tag] = {"setting": C.setting_name(st),
                        "ancestors": r["ancestors"], "kernel": r["kernel"],
                        "noise_after_pruning": r["noise_after_pruning"],
                        "pruning_path": r["pruning_path"],
                        "dropped_constant": r["dropped_constant"]}
        res["noise_given_all"] = C.noise_given(Xs, ns, "logk", vs)
        out[label] = res
    return out


def anova_fallback(rows, with_T=True):
    """OLS ln kappa ~ 1 + x + x(1-x) (+ T/1000), then one-way ANOVA of
    the residuals by sample and by method group (scipy f_oneway)."""
    from scipy.stats import f_oneway
    x = np.array([r["x"] for r in rows], float)
    y = np.log([r["kappa"] for r in rows])
    cols, lab = [np.ones_like(x), x, x * (1 - x)], ["1", "x", "x(1-x)"]
    if with_T:
        cols.append(np.array([r["T"] for r in rows], float) / 1000.0)
        lab.append("T/1000")
    M = np.column_stack(cols)
    b, *_ = np.linalg.lstsq(M, y, rcond=None)
    res = y - M @ b
    r2 = 1 - np.sum(res ** 2) / np.sum((y - y.mean()) ** 2)
    out = {"ols_ln_kappa": {"terms": lab, "coefs": dict(zip(
        lab, [float(v) for v in b])), "n": len(rows),
        "R2": float(r2), "residual_sd_ln": float(res.std(ddof=len(lab)))}}
    for key in ("sample_group", "method_group"):
        groups = {}
        for r, e in zip(rows, res):
            groups.setdefault(r[key], []).append(float(e))
        g = [v for v in groups.values() if len(v) >= 2]
        ss_tot = float(np.sum((res - res.mean()) ** 2))
        ss_b = float(sum(len(v) * (np.mean(v) - res.mean()) ** 2
                         for v in groups.values()))
        F, p = (f_oneway(*g) if len(g) >= 2 else (np.nan, np.nan))
        out[key] = {"group_sizes": {k: len(v) for k, v in groups.items()},
                    "group_mean_residual_ln": {k: float(np.mean(v))
                                               for k, v in groups.items()},
                    "eta2": ss_b / ss_tot if ss_tot > 0 else None,
                    "F": None if not np.isfinite(F) else float(F),
                    "p": None if not np.isfinite(p) else float(p),
                    "groups_in_test": [k for k, v in groups.items()
                                       if len(v) >= 2]}
    return out


def evaluate_partition(fit_rows_raw, key):
    """C2: per-scope laws vs pooled law, CV MedAPE on the same rows."""
    rows = as_fit_rows(fit_rows_raw)
    kappa = np.array([r["kappa"] for r in rows])
    engines = {"hgsr": False, "minisr-pooled": True}
    pooled = {e: cv_predictions(rows, p) for e, p in engines.items()}
    scopes = {}
    for g in sorted({r[key] for r in fit_rows_raw}):
        ix = [i for i, r in enumerate(fit_rows_raw) if r[key] == g]
        sc = {"n_rows": len(ix), "row_ids": [rows[i]["row_id"] for i in ix]}
        if len(ix) < MIN_POINTS:
            sc["law"] = f"REFUSED: {len(ix)} < MIN_POINTS={MIN_POINTS}"
            sc["pooled_cv_on_these_rows"] = {
                e: errors(kappa[ix], pooled[e][ix]) for e in engines}
            scopes[g] = sc
            continue
        sub = [rows[i] for i in ix]
        sc["engines"] = {}
        for e, p in engines.items():
            full = hgsr.fit(sub, ["x", "T"], pooled=p)
            own = cv_predictions(sub, p)
            sc["engines"][e] = {
                "law": describe(full),
                "complexity": full["selected"]["complexity"],
                "in_sample": errors(kappa[ix], hgsr.predict(full, sub)),
                "cv_own_scope": errors(kappa[ix], own),
                "cv_pooled_law_same_rows": errors(kappa[ix], pooled[e][ix]),
            }
            sc["engines"][e]["cv_gain_pts"] = (
                sc["engines"][e]["cv_pooled_law_same_rows"]["medape_pct"]
                - sc["engines"][e]["cv_own_scope"]["medape_pct"])
        scopes[g] = sc
    fittable = [g for g, s in scopes.items() if "engines" in s]
    c2 = bool(fittable) and all(
        scopes[g]["engines"][e]["cv_gain_pts"] >= CV_GAIN_PTS
        for g in fittable for e in engines)
    gains = [scopes[g]["engines"][e]["cv_gain_pts"]
             for g in fittable for e in engines]
    return {"scopes": scopes, "fittable_scopes": fittable,
            "pooled_cv_all_rows": {e: errors(kappa, pooled[e])
                                   for e in engines},
            "pooled_full_fit": {e: describe(hgsr.fit(rows, ["x", "T"],
                                                     pooled=p))
                                for e, p in engines.items()},
            "C2_pass": c2,
            "mean_cv_gain_pts": float(np.mean(gains)) if gains else None}


def main():
    cal = json.load(open(os.path.join(HERE, "calibration.json")))
    if cal["chosen_setting"] is None:
        raise SystemExit("CHD failed calibration: use the ANOVA fallback only")
    calibrated = tuple(cal["chosen_setting"]["setting"].split("|"))

    lit = literature_rows()
    fit = [r for r in lit if r["x"] is not None and r["T"] is not None
           and r["kappa"]]
    xtab = [r for r in lit if r["x"] is not None and r["kappa"]]
    counts = {
        "literature_rows_total": len(lit),
        "with_kappa": sum(1 for r in lit if r["kappa"]),
        "fit_table_x_T_kappa": len(fit),
        "x_table_x_kappa": len(xtab),
        "missing_T_dropped_from_fit_table": sum(
            1 for r in lit if r["x"] is not None and r["kappa"] and r["T"] is None),
        "missing_x_dropped_everywhere": sum(1 for r in lit if r["x"] is None),
        "fit_table_by_sample_group": _count(fit, "sample_group"),
        "fit_table_by_method_group": _count(fit, "method_group"),
        "x_table_by_sample_group": _count(xtab, "sample_group"),
        "x_table_by_method_group": _count(xtab, "method_group"),
        "all_by_system": _count(lit, "system"),
    }

    # ---- CHD on the literature tables
    Xf, nf = encode(fit, with_T=True)
    Xx, nx_ = encode(xtab, with_T=False)
    vs_fit = {"xT": ["x", "T"], "xT+sample": ["x", "T", "rdim", "amorph"],
              "xT+method": ["x", "T", "sim"],
              "xT+sample+method+junk": ["x", "T", "rdim", "amorph", "sim", "junk"]}
    vs_x = {"x": ["x"], "x+sample": ["x", "rdim", "amorph"],
            "x+method": ["x", "sim"],
            "x+sample+method+junk": ["x", "rdim", "amorph", "sim", "junk"]}
    chd_fit = chd_block(Xf, nf, vs_fit, calibrated)
    chd_x = chd_block(Xx, nx_, vs_x, calibrated)

    # ---- MD contrast
    md, md_dropped = md_rows()
    md = [r for r in md if r["party"] == "CHPC-MD"]
    Xm = np.column_stack([[r[k] for r in md] for k in
                          ("x", "T", "L", "seed", "xsec", "swap")]
                         + [np.log([r["kappa"] for r in md])])
    nm = ["x", "T", "L", "seed", "xsec", "swap", "logk"]
    chd_md = chd_block(Xm, nm, {"xTL": ["x", "T", "L"],
                                "xTL+seed": ["x", "T", "L", "seed"],
                                "all": ["x", "T", "L", "seed", "xsec", "swap"],
                                "seed_only": ["seed"]}, calibrated)

    # ---- decision
    full_fit = chd_fit["xT+sample+method+junk"]["calibrated"]["ancestors"]
    full_x = chd_x["x+sample+method+junk"]["calibrated"]["ancestors"]
    ind = {"P_sample": (["rdim", "amorph"], "sample_group"),
           "P_method": (["sim"], "method_group")}
    partitions = {}
    for pname, (vars_, key) in ind.items():
        n_nonref = sum(1 for r in fit if any(
            (v == "rdim" and r["sample_group"] == "reduced-dim")
            or (v == "amorph" and r["sample_group"] == "amorphous")
            or (v == "sim" and r["method_group"] == "simulation")
            for v in vars_))
        table_used = "fit_table" if n_nonref >= 3 else "x_table"
        anc = full_fit if table_used == "fit_table" else full_x
        c1 = any(v in anc for v in vars_)
        ev = evaluate_partition(fit, key)
        partitions[pname] = {"indicator_vars": vars_, "group_key": key,
                             "n_nonreference_rows_fit_table": n_nonref,
                             "C1_table_used": table_used,
                             "C1_calibrated_ancestors": anc,
                             "C1_pass": c1, **ev,
                             "adopted": bool(c1 and ev["C2_pass"])}
    adopted = [p for p in partitions if partitions[p]["adopted"]]
    adopted.sort(key=lambda p: -partitions[p]["mean_cv_gain_pts"])
    primary = adopted[0] if adopted else None

    fallback = {"fit_table": anova_fallback(fit, with_T=True),
                "x_table": anova_fallback(xtab, with_T=False)}

    results = {
        "what": "CHD stage-0 on the literature party (2026-09-28)",
        "chd_version": C.CHD_VERSION,
        "calibrated_setting": C.setting_name(calibrated),
        "sensitivity_setting": C.setting_name(SENSITIVITY_SETTING),
        "row_counts": counts,
        "md_contrast_rows": {"chpc_md_used": len(md),
                             "dropped_unparseable": md_dropped},
        "chd_literature_fit_table": chd_fit,
        "chd_literature_x_table": chd_x,
        "chd_md_contrast": chd_md,
        "fallback_anova": fallback,
        "partitions": partitions,
    }
    json.dump(results, open(os.path.join(HERE, "stage0_results.json"), "w"),
              indent=1)

    decision = {
        "rule": "adopt a partition iff C1 (indicator is a CHD ancestor of ln kappa "
                "under the calibrated setting) AND C2 (every fittable scope's own "
                f"law beats the pooled law's CV MedAPE on the same rows by >= "
                f"{CV_GAIN_PTS} pts for both hgsr and minisr-pooled; scopes with "
                f"< {MIN_POINTS} rows are split off but refused a law)",
        "calibrated_setting": C.setting_name(calibrated),
        "per_partition": {p: {"C1_pass": v["C1_pass"], "C2_pass": v["C2_pass"],
                              "adopted": v["adopted"],
                              "mean_cv_gain_pts": v["mean_cv_gain_pts"]}
                          for p, v in partitions.items()},
        "decision": "split" if primary else "no split",
        "primary_partition": primary,
        "secondary_candidates": adopted[1:],
    }
    if primary:
        P = partitions[primary]
        key = P["group_key"]
        scopes_all = {}
        for r in lit:
            g = r[key]
            scopes_all.setdefault(g, []).append(r["row_id"])
        decision["scopes"] = {
            f"literature-{g}": {
                "group": g,
                "n_rows_all": len(ids),
                "n_rows_fit_table": P["scopes"].get(g, {}).get("n_rows", 0),
                "law": ("fitted" if g in P["fittable_scopes"] else
                        "none (below MIN_POINTS or no x,T rows): scope-limited, no claim"),
                "row_ids": ids,
            } for g, ids in sorted(scopes_all.items())}
        decision["cv_summary"] = {
            "pooled_all_fit_rows": P["pooled_cv_all_rows"],
            "per_fittable_scope": {g: {e: {
                "own": P["scopes"][g]["engines"][e]["cv_own_scope"]["medape_pct"],
                "pooled_same_rows": P["scopes"][g]["engines"][e]
                ["cv_pooled_law_same_rows"]["medape_pct"],
                "law": P["scopes"][g]["engines"][e]["law"]}
                for e in P["scopes"][g]["engines"]}
                for g in P["fittable_scopes"]}}
    json.dump(decision, open(os.path.join(HERE, "split_decision.json"), "w"),
              indent=1)
    _print(results, decision)


def _count(rows, key):
    c = {}
    for r in rows:
        c[r[key]] = c.get(r[key], 0) + 1
    return c


def _print(res, dec):
    print("row counts:", json.dumps(res["row_counts"]))
    for tab in ("chd_literature_fit_table", "chd_literature_x_table",
                "chd_md_contrast"):
        print(f"== {tab}")
        for lab, v in res[tab].items():
            ng = v["noise_given_all"]
            print(f"  {lab:24s} cal={v['calibrated']['ancestors']} "
                  f"sens={v['sensitivity']['ancestors']} "
                  f"def={v['library_default']['ancestors']} "
                  f"noise|all={ng['min_noise']:.3f} "
                  f"belowZ={ng.get('min_noise_below_Z_low')}")
    print("fallback:", json.dumps(res["fallback_anova"])[:600])
    for p, v in res["partitions"].items():
        print(f"== {p}: C1={v['C1_pass']} ({v['C1_table_used']}: "
              f"{v['C1_calibrated_ancestors']}) C2={v['C2_pass']} "
              f"adopted={v['adopted']}")
        print("   pooled CV all rows:",
              {e: round(x["medape_pct"], 1) for e, x in v["pooled_cv_all_rows"].items()})
        for g, s in v["scopes"].items():
            if "engines" in s:
                for e, x in s["engines"].items():
                    print(f"   {g:14s} n={s['n_rows']:2d} {e:14s} own "
                          f"{x['cv_own_scope']['medape_pct']:.1f}% vs pooled "
                          f"{x['cv_pooled_law_same_rows']['medape_pct']:.1f}%  "
                          f"{x['law']}")
            else:
                print(f"   {g:14s} n={s['n_rows']:2d} {s['law']}")
    print("DECISION:", dec["decision"], dec["primary_partition"])


if __name__ == "__main__":
    main()
