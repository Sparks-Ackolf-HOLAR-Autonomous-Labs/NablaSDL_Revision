#!/usr/bin/env python3
"""Sensitivity of the stage-0 P_sample split decision to the extractor.

Reuses stage0_literature.py (imported, not modified) and re-evaluates the
pre-stated criteria C1 and C2 for the sample partition under:
  A  first extractor labels (reproduces split_decision.json)
  B  second extractor's sample group on every row
  C  only rows where both extractors agree on the sample group
  D  B, further dropping rows whose kappa is not verbatim in the snippet,
     whose chemistry is not SiGe-family (GeSn, SiSn, Sn, BiSbTe), or whose
     x_ge is misattributed (range endpoint, dopant level) (extra check)
C1 is evaluated exactly as in stage0_literature.main(): the calibrated CHD
setting on the full variable set {x, (T), rdim, amorph, sim, junk}, using
the fit table if it has >= 3 non-reference rows, else the x-table. The
method indicator `sim` is kept from the first extractor in all variants
so that only the sample labels vary (B/C/D also report it with the
second extractor's method group, "B_m").

Usage: ~/venvs/chd/bin/python sensitivity.py   ->  sensitivity.json
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CHD = os.path.dirname(HERE)
sys.path.insert(0, CHD)
import stage0_literature as S  # noqa: E402
from stage0_data import (literature_rows, SAMPLE_GROUP,  # noqa: E402
                         METHOD_GROUP, KG)
import chd_common as C  # noqa: E402


def lit_with_second():
    """literature_rows() in file order, annotated with the second labels."""
    raw = json.load(open(KG))
    idx = [i for i, p in enumerate(raw) if str(p.get("corpusId")).isdigit()]
    lab = {r["row"]: r for r in json.load(open(
        os.path.join(HERE, "labels_second.json")))["rows"]}
    rows = literature_rows()
    assert len(rows) == len(idx)
    for r, i in zip(rows, idx):
        s = lab[i]
        r["kg_row"] = i
        r["sample_group_first"] = r["sample_group"]
        r["method_group_first"] = r["method_group"]
        r["sample_group_second"] = SAMPLE_GROUP[s["sample_class"]]
        r["method_group_second"] = METHOD_GROUP[s["method"]]
        r["suspect_value"] = (not s["value_in_snippet"]
                              or s["material"] not in
                              ("SiGe", "Si", "Ge", "Si/Ge SL")
                              or any(k in (s["note"] or "") for k in
                                     ("misattribut", "not Ge fraction")))
    return rows


def run_variant(rows, sample_key, method_key, calibrated):
    rows = [dict(r, sample_group=r[sample_key], method_group=r[method_key])
            for r in rows]
    fit = [r for r in rows if r["x"] is not None and r["T"] is not None
           and r["kappa"]]
    xtab = [r for r in rows if r["x"] is not None and r["kappa"]]
    n_nonref = sum(r["sample_group"] in ("reduced-dim", "amorphous")
                   for r in fit)
    t0 = time.time()
    if n_nonref >= 3:
        X, names = S.encode(fit, with_T=True)
        vs = ["x", "T", "rdim", "amorph", "sim", "junk"]
        table = "fit_table"
    else:
        X, names = S.encode(xtab, with_T=False)
        vs = ["x", "rdim", "amorph", "sim", "junk"]
        table = "x_table"
    idx = [names.index(v) for v in vs + ["logk"]]
    r = C.run_chd(X[:, idx], vs + ["logk"], "logk", calibrated)
    anc = r["ancestors"]
    c1 = any(v in anc for v in ("rdim", "amorph"))
    t_chd = time.time() - t0
    ev = S.evaluate_partition(fit, "sample_group")
    scopes = {}
    for g, s in ev["scopes"].items():
        if "engines" in s:
            scopes[g] = {"n_rows": s["n_rows"], **{e: {
                "cv_own_medape": x["cv_own_scope"]["medape_pct"],
                "cv_pooled_same_rows_medape":
                    x["cv_pooled_law_same_rows"]["medape_pct"],
                "cv_gain_pts": x["cv_gain_pts"], "law": x["law"]}
                for e, x in s["engines"].items()}}
        else:
            scopes[g] = {"n_rows": s["n_rows"], "law": s["law"]}
    return {
        "n_literature_rows": len(rows), "n_fit_table": len(fit),
        "n_x_table": len(xtab),
        "fit_table_by_group": S._count(fit, "sample_group"),
        "x_table_by_group": S._count(xtab, "sample_group"),
        "C1_table_used": table, "C1_calibrated_ancestors": anc,
        "C1_pass": c1, "chd_seconds": round(t_chd, 1),
        "pooled_cv_all_fit_rows": {e: v["medape_pct"] for e, v in
                                   ev["pooled_cv_all_rows"].items()},
        "scopes": scopes, "fittable_scopes": ev["fittable_scopes"],
        "C2_pass": ev["C2_pass"], "mean_cv_gain_pts": ev["mean_cv_gain_pts"],
        "adopted": bool(c1 and ev["C2_pass"]),
        "fit_table_kg_rows": [r["kg_row"] for r in fit],
    }


def main():
    cal = json.load(open(os.path.join(CHD, "calibration.json")))
    calibrated = tuple(cal["chosen_setting"]["setting"].split("|"))
    rows = lit_with_second()
    agree = [r for r in rows
             if r["sample_group_first"] == r["sample_group_second"]]
    clean = [r for r in rows if not r["suspect_value"]]
    variants = {
        "A_first_extractor": (rows, "sample_group_first",
                              "method_group_first"),
        "B_second_extractor_sample_group": (rows, "sample_group_second",
                                            "method_group_first"),
        "B_m_second_extractor_sample_and_method": (
            rows, "sample_group_second", "method_group_second"),
        "C_both_agree_on_group_only": (agree, "sample_group_first",
                                       "method_group_first"),
        "D_second_labels_verbatim_values_only": (
            clean, "sample_group_second", "method_group_second"),
    }
    out = {"what": "P_sample split sensitivity to the literature extractor",
           "calibrated_setting": C.setting_name(calibrated),
           "rule_C2": f"every fittable scope (>= {S.MIN_POINTS} rows) own-law "
                      f"CV MedAPE <= pooled-law CV MedAPE on same rows - "
                      f"{S.CV_GAIN_PTS} pts, both engines",
           "variants": {}}
    for name, (rs, sk, mk) in variants.items():
        t0 = time.time()
        v = run_variant(rs, sk, mk, calibrated)
        v["seconds"] = round(time.time() - t0, 1)
        out["variants"][name] = v
        b = v["scopes"].get("bulk", {})
        print(f"== {name}: n_fit={v['n_fit_table']} {v['fit_table_by_group']} "
              f"C1={v['C1_pass']} ({v['C1_table_used']} {v['C1_calibrated_ancestors']}) "
              f"C2={v['C2_pass']} adopted={v['adopted']} [{v['seconds']}s]")
        for e in ("hgsr", "minisr-pooled"):
            if e in b:
                print(f"   bulk n={b['n_rows']} {e}: own {b[e]['cv_own_medape']:.1f}% "
                      f"vs pooled {b[e]['cv_pooled_same_rows_medape']:.1f}% "
                      f"gain {b[e]['cv_gain_pts']:.1f}")
        json.dump(out, open(os.path.join(HERE, "sensitivity.json"), "w"),
                  indent=1)


if __name__ == "__main__":
    main()
