#!/usr/bin/env python3
"""Agreement between the first extractor (Qwen, extracted_points.json) and
the blind second extractor (labels_second.json) on the 67 literature rows.

Reports raw agreement and Cohen's kappa on:
  sample class (7-way), sample group (4-way SAMPLE_GROUP of stage0_data.py),
  method (5-way), method group (METHOD_GROUP of stage0_data.py);
confusion matrices, the disagreeing rows, and the rows whose kappa value
cannot be found verbatim in the snippet. Also repeats the agreement on the
17-row fit table (rows with x, T, kappa) that drives criterion C2.

Usage: python3 agreement.py   ->  agreement.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
CHD = os.path.dirname(HERE)
MT = os.path.normpath(os.path.join(CHD, "..", ".."))
sys.path.insert(0, CHD)
from stage0_data import SAMPLE_GROUP, METHOD_GROUP  # noqa: E402

KG = os.path.join(MT, "pilot", "kg", "extracted_points.json")
CLASSES = ["bulk", "film", "nanowire", "nanostructured", "superlattice",
           "amorphous", "other"]
GROUPS = ["bulk", "reduced-dim", "amorphous", "unclassified"]
METHODS = ["experiment", "MD", "BTE/DFT", "model-fit", "unclear"]
MGROUPS = ["measurement", "simulation", "unclear"]


def cohen_kappa(a, b, cats):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[c] * cb[c] for c in cats) / n ** 2
    k = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return {"n": n, "raw_agreement": po, "expected_agreement": pe,
            "cohen_kappa": k}


def confusion(a, b, cats):
    cats = [c for c in cats if c in set(a) | set(b)] + sorted(
        (set(a) | set(b)) - set(cats))
    return {"rows_first_extractor": cats, "cols_second_extractor": cats,
            "matrix": [[sum(1 for x, y in zip(a, b) if x == r and y == c)
                        for c in cats] for r in cats]}


def block(first, second, cats):
    return {**cohen_kappa(first, second, cats),
            "confusion": confusion(first, second, cats)}


def main():
    pts = json.load(open(KG))
    sec = {r["row"]: r for r in
           json.load(open(os.path.join(HERE, "labels_second.json")))["rows"]}
    lit = [i for i, p in enumerate(pts) if str(p.get("corpusId")).isdigit()]
    assert sorted(sec) == lit

    def labels(idx):
        f_sys = [pts[i].get("system") for i in idx]
        s_sys = [sec[i]["sample_class"] for i in idx]
        f_met = [pts[i].get("method") for i in idx]
        s_met = [sec[i]["method"] for i in idx]
        return {
            "sample_class_7way": block(f_sys, s_sys, CLASSES),
            "sample_group_4way": block(
                [SAMPLE_GROUP.get(s, "unclassified") for s in f_sys],
                [SAMPLE_GROUP[s] for s in s_sys], GROUPS),
            "method_5way": block(f_met, s_met, METHODS),
            "method_group_3way": block(
                [METHOD_GROUP.get(m, "unclear") for m in f_met],
                [METHOD_GROUP[m] for m in s_met], MGROUPS),
        }

    fit_idx = [i for i in lit if pts[i].get("x_ge") is not None
               and pts[i].get("T_K") is not None and pts[i].get("kappa_W_mK")]
    x_idx = [i for i in lit if pts[i].get("x_ge") is not None
             and pts[i].get("kappa_W_mK")]

    disagree = []
    for i in lit:
        p, s = pts[i], sec[i]
        fg = SAMPLE_GROUP.get(p.get("system"), "unclassified")
        sg = SAMPLE_GROUP[s["sample_class"]]
        fm, sm = p.get("method"), s["method"]
        if p.get("system") != s["sample_class"] or fm != sm:
            disagree.append({
                "row": i, "snippet_hash": p["snippet_hash"],
                "x_ge": p.get("x_ge"), "T_K": p.get("T_K"),
                "kappa": p.get("kappa_W_mK"),
                "in_fit_table": i in fit_idx,
                "first_system": p.get("system"), "second_sample_class":
                s["sample_class"], "group_differs": fg != sg,
                "first_group": fg, "second_group": sg,
                "first_method": fm, "second_method": sm,
                "method_group_differs":
                    METHOD_GROUP.get(fm, "unclear") != METHOD_GROUP[sm],
                "second_confidence": s["confidence"],
                "evidence_quote": s["evidence_quote"], "note": s["note"]})

    not_in = [{"row": i, "kappa": pts[i].get("kappa_W_mK"),
               "x_ge": pts[i].get("x_ge"), "T_K": pts[i].get("T_K"),
               "value_note": sec[i]["value_note"], "note": sec[i]["note"],
               "in_fit_table": i in fit_idx, "in_x_table": i in x_idx}
              for i in lit if not sec[i]["value_in_snippet"]]
    non_sige = [{"row": i, "material": sec[i]["material"],
                 "x_ge": pts[i].get("x_ge"), "kappa": pts[i].get("kappa_W_mK"),
                 "in_fit_table": i in fit_idx, "in_x_table": i in x_idx}
                for i in lit if sec[i]["material"] not in
                ("SiGe", "Si", "Ge", "Si/Ge SL")]

    out = {
        "what": "first (Qwen) vs second (Claude, blind) extractor agreement, "
                "literature party",
        "n_literature_rows": len(lit),
        "all_67_rows": labels(lit),
        "x_table_rows": {"n": len(x_idx), **labels(x_idx)},
        "fit_table_rows": {"n": len(fit_idx), "rows": fit_idx,
                           **labels(fit_idx)},
        "n_rows_disagree_class_or_method": len(disagree),
        "n_rows_disagree_sample_class": sum(
            d["first_system"] != d["second_sample_class"] for d in disagree),
        "n_rows_disagree_sample_group": sum(d["group_differs"]
                                             for d in disagree),
        "n_rows_disagree_method": sum(d["first_method"] != d["second_method"]
                                      for d in disagree),
        "disagreements": disagree,
        "value_not_in_snippet": {
            "n": len(not_in),
            "n_derived": sum(r["value_note"] == "derived" for r in not_in),
            "n_absent": sum(r["value_note"] == "absent" for r in not_in),
            "rows": not_in},
        "non_SiGe_family_rows": {"n": len(non_sige), "rows": non_sige},
        "second_confidence_counts": dict(Counter(sec[i]["confidence"]
                                                 for i in lit)),
    }
    json.dump(out, open(os.path.join(HERE, "agreement.json"), "w"), indent=1,
              ensure_ascii=False)
    for scope in ("all_67_rows", "x_table_rows", "fit_table_rows"):
        print(f"== {scope}")
        for k, v in out[scope].items():
            if isinstance(v, dict) and "cohen_kappa" in v:
                print(f"  {k:20s} n={v['n']:2d} raw={v['raw_agreement']:.3f} "
                      f"kappa={v['cohen_kappa']:.3f}")
    print("disagree class/method/group:", out["n_rows_disagree_sample_class"],
          out["n_rows_disagree_method"], out["n_rows_disagree_sample_group"])
    print("value not in snippet:", out["value_not_in_snippet"]["n"],
          "(derived", out["value_not_in_snippet"]["n_derived"], ", absent",
          out["value_not_in_snippet"]["n_absent"], ")")
    print("non-SiGe-family rows:", out["non_SiGe_family_rows"]["n"])


if __name__ == "__main__":
    main()
