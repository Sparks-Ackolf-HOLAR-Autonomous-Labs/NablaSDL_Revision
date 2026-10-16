#!/usr/bin/env python3
"""Fault study for detector v2: the same blind catalog (ledger seq 4), the
same 50 pre-registered trial seeds per entry, the same scoring
(production/fault_study.py score()), run for detector v2.

Structure attachment rule (fixed in design_v2.json before any descriptor
existed): a row's structure follows the physical run, not its labels.
  - every real row carries the descriptors measured on its point's rebuild;
  - label faults (P03, P04, P05) and kappa-only faults (P01, P02, P07, M03,
    V01-V03) leave the structure untouched (inject_faults deep-copies rows);
  - duplicated rows (P06) keep their source's structure;
  - M02 (amorphous contamination): affected rows take the measured
    amorphous rebuild (N2 at 300 K or N3 at 700 K, nearest T; volume scaled
    by the crystal volume ratio between the row's x and 0.5);
  - P08 (MACE rows under the Tersoff label): volume scaled by the cube of
    the measured MACE-MP-0 / Tersoff lattice ratio (Si 5.464/5.432, Ge
    5.736/5.657, linear in x);
  - rows added by M01 (crystal, premelting): descriptors generated from the
    real-row structure fit at the true (x, T) plus a bootstrapped residual.
Usage: python3 fault_study_v2.py rows_v2.json [n_trials]
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.join(HERE, "..", "production")
sys.path.insert(0, HERE)
sys.path.insert(0, PROD)
sys.path.insert(0, os.path.join(PROD, "fault_catalog"))

import detector_v2 as D  # noqa: E402
import fault_study as FS  # noqa: E402
import inject_faults as IF  # noqa: E402

A_TER = (5.4320, 5.6567)
A_MACE = (5.464, 5.736)


def _ratio_mace(x):
    return (1 - x) * A_MACE[0] / A_TER[0] + x * A_MACE[1] / A_TER[1]


class Attach:
    def __init__(self, rows):
        self.base = {r["run_id"]: r for r in rows}
        cr = [r for r in rows if r["angle_sd"] < D.ANGLE_SPLIT]
        pts = D._points(cr)
        x = np.array([p["x"] for p in pts]); T = np.array([p["T"] for p in pts])
        v = np.array([p["rows"][0]["vol_atom"] for p in pts])
        s2 = np.array([p["angle_sd"] ** 2 for p in pts])
        self.cv, *_ = np.linalg.lstsq(D._fa(x, T), v, rcond=None)
        self.cs, *_ = np.linalg.lstsq(D._fs(x, T), s2, rcond=None)
        self.rv = v - D._fa(x, T) @ self.cv
        self.rs = s2 - D._fs(x, T) @ self.cs
        self.am = {round(r["T"]): r for r in rows if r["angle_sd"] >= D.ANGLE_SPLIT}

    def vol(self, x, T):
        return float((D._fa(np.array([x], float), np.array([T], float)) @ self.cv)[0])

    def apply(self, rows_t, truth, rng):
        eid = truth["entry_id"]
        aff = set(truth["affected_run_ids"])
        for r in rows_t:
            rid = r["run_id"]
            if eid == "M02" and rid in aff:
                Tn = min(self.am, key=lambda t: abs(t - r["T"]))
                a = self.am[Tn]
                r["angle_sd"] = a["angle_sd"]
                r["vol_atom"] = a["vol_atom"] * self.vol(r["x"], r["T"]) / self.vol(0.5, r["T"])
            elif eid == "P08" and rid in aff:
                r["vol_atom"] = r["vol_atom"] * _ratio_mace(r["x"]) ** 3
            elif eid == "M01" and rid in set(truth["added_run_ids"]):
                # true (x, T) of an added row are its labels (M01 writes no label error)
                k = int(rng.integers(len(self.rv)))
                r["vol_atom"] = self.vol(r["x"], r["T"]) + float(self.rv[k])
                s2 = float((D._fs(np.array([r["x"]], float), np.array([r["T"]], float)) @ self.cs)[0]) + float(self.rs[k])
                r["angle_sd"] = float(np.sqrt(max(s2, 0.01)))
        return rows_t


def _sig(o):
    return (o["op"], tuple(sorted(o["target_runs"])))


def main():
    rows = json.load(open(sys.argv[1]))
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    att = Attach(rows)
    clean = D.detect(rows)
    baseline = frozenset(_sig(o) for o in clean["ops"])
    out = {"detector": "v2", "clean_campaign": clean, "entries": {}}
    for eid in ["NULL"] + IF.entries():
        trials = []
        for ts in IF.trial_seeds(eid, n):
            rows_t, truth = IF.inject(rows, eid, ts)
            att.apply(rows_t, truth, np.random.default_rng(10_000_000 + ts))
            res = D.detect(rows_t)
            s = FS.score(res, truth, rows_t, baseline)
            s["trial_seed"] = ts
            s["ops_all"] = [(o["op"], o.get("layer"), len(o["target_runs"])) for o in res["ops"]]
            trials.append(s)
        summ = {"category": truth["category"], "expected": truth["expected_operator"]}
        for suf in ("", "_adj"):
            summ["detected_rate" + suf] = sum(t["detected" + suf] for t in trials) / n
            summ["A" + suf] = dict(Counter(t["outcome_A" + suf] for t in trials))
            summ["B" + suf] = dict(Counter(t["outcome_B" + suf] for t in trials))
            summ["trials_with_collateral" + suf] = sum(bool(t["collateral" + suf]) for t in trials)
        summ["ops_seen"] = dict(Counter(o for t in trials for o in t["ops_on_affected"]))
        out["entries"][eid] = {"summary": summ, "trials": trials}
        print(eid, json.dumps({k: summ[k] for k in ("detected_rate_adj", "A_adj", "trials_with_collateral_adj")}))
    dst = os.path.join(HERE, "fault_study_results_v2.json")
    json.dump(out, open(dst, "w"), indent=1, default=str)
    print("->", dst)


if __name__ == "__main__":
    main()
