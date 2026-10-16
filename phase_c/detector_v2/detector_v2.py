#!/usr/bin/env python3
"""Phase C detector v2: the production detector (ledger seq 5) plus a
structure layer that reads two measured descriptors of every run.

Rows: {run_id, batch_id, x, T, ncz, seed, kappa, n_atoms,
       vol_atom (A^3 per atom, NPT average), angle_sd (deg, s.d. of all
       first-shell bond angles)}.

Changes against v1, each named before this file was written (FAULT_STUDY.md
"for the next detector", session 34; bond_angles/README.md, session 56):
  S1 phase check: angle_sd >= ANGLE_SPLIT -> split (not the tetrahedral
     crystal the law describes).  Session 56 descriptor.
  S2 label checks: the lattice constant a = (8 vol_atom)^(1/3) and angle_sd
     are fitted on the campaign's own crystalline points, a(x, T) and
     angle_sd^2(x, T); each point's labels are compared with the (x*, T*)
     its structure implies.  Batch-coherent T offsets and point-level x or
     T contradictions -> correct (identified cause: an independent
     measurement of the same run contradicts the label and gives the
     corrected value).  FAULT_STUDY item 2: physics-aware label checks.
  S3 declared domain: label x > 0.90 -> scope-limit (ledger seq 29, the
     Ge-rich shard action).
  S4 physics guard at T >= 0.85 T_sol (was 1.0).  FAULT_STUDY item 3.
  S5 duplicate key on design coordinates (post-hoc variant D2, ledger 14).
The statistical stages of v1 then run unchanged on the corrected rows with
the v1 thresholds (no re-tuning).  Rows without descriptors skip S1-S2.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "production"))
import detector as v1  # noqa: E402

ANGLE_SPLIT = 10.0     # deg; crystal rows 2.9-6.5, amorphous 16.6-17.3 (session 56)
X_DOMAIN = 0.90        # ledger seq 29
H_GUARD = 0.85         # fraction of the real solidus
SIG_X_FLOOR = 0.01     # realized-composition noise of a 3072-atom cell is about 0.009
SIG_T_FLOOR = 30.0     # K
Z_POINT = v1.Z_POINT
Z_BATCH = v1.Z_BATCH
TRIM_ITER = 2
X_GRID = np.linspace(-0.2, 1.2, 701)
T_GRID = np.linspace(100.0, 1900.0, 721)


def lattice(vol_atom):
    return (8.0 * float(vol_atom)) ** (1.0 / 3.0)


def _fa(x, T):
    t = T / 1000.0
    return np.column_stack([np.ones_like(x), x, x * x, t, x * t])


def _fs(x, T):
    t = T / 1000.0
    return np.column_stack([np.ones_like(x), x, x * (1 - x), t])


def _fit(F, y):
    """Least squares with two passes of trimming at Z_POINT robust z."""
    keep = np.ones(len(y), bool)
    for _ in range(TRIM_ITER + 1):
        c, *_ = np.linalg.lstsq(F[keep], y[keep], rcond=None)
        r = y - F @ c
        med = np.median(r[keep])
        mad = 1.4826 * np.median(np.abs(r[keep] - med)) + 1e-12
        new = np.abs(r - med) / mad < Z_POINT
        if new.sum() < F.shape[1] + 3 or (new == keep).all():
            break
        keep = new
    return c, keep


class StructureModel:
    def __init__(self, pts):
        x = np.array([p["x"] for p in pts], float)
        T = np.array([p["T"] for p in pts], float)
        a = np.array([p["a"] for p in pts], float)
        s2 = np.array([p["angle_sd"] ** 2 for p in pts], float)
        self.ca, _ = _fit(_fa(x, T), a)
        self.cs, _ = _fit(_fs(x, T), s2)
        X, TT = np.meshgrid(X_GRID, T_GRID, indexing="ij")
        self.ga = (_fa(X.ravel(), TT.ravel()) @ self.ca).reshape(X.shape)
        self.gs = (_fs(X.ravel(), TT.ravel()) @ self.cs).reshape(X.shape)
        ra = a - _fa(x, T) @ self.ca
        rs = s2 - _fs(x, T) @ self.cs
        self.sa = 1.4826 * np.median(np.abs(ra - np.median(ra))) + 1e-6
        self.ss = 1.4826 * np.median(np.abs(rs - np.median(rs))) + 1e-6

    def implied(self, a, sd):
        """(x*, T*) minimizing the standardized misfit on the grid."""
        m = ((self.ga - a) / self.sa) ** 2 + ((self.gs - sd ** 2) / self.ss) ** 2
        i, j = np.unravel_index(np.argmin(m), m.shape)
        return float(X_GRID[i]), float(T_GRID[j])


def _points(rows):
    pts = {}
    for r in rows:
        pts.setdefault((r["batch_id"], round(r["x"], 6), round(r["T"], 3),
                        r["seed"]), []).append(r)
    out = []
    for (b, x, T, s), rs in pts.items():
        out.append({"batch_id": b, "x": x, "T": T, "seed": s, "rows": rs,
                    "run_ids": sorted(r["run_id"] for r in rs),
                    "a": float(np.mean([lattice(r["vol_atom"]) for r in rs])),
                    "angle_sd": float(np.mean([r["angle_sd"] for r in rs]))})
    return out


def _robust_sig(v, floor):
    v = np.asarray(v, float)
    return max(1.4826 * float(np.median(np.abs(v - np.median(v)))), floor)


def structure_layer(rows):
    """S1 + S2. Returns (ops, rows_after) with corrected labels."""
    ops = []
    have = [r for r in rows if "vol_atom" in r and "angle_sd" in r]
    rest = [r for r in rows if not ("vol_atom" in r and "angle_sd" in r)]
    if not have:
        return ops, rows
    # S1: phase
    amorph = [r for r in have if r["angle_sd"] >= ANGLE_SPLIT]
    if amorph:
        ops.append({"op": "split", "layer": "structure",
                    "target_runs": sorted(r["run_id"] for r in amorph),
                    "reason": f"bond-angle spread >= {ANGLE_SPLIT} deg: not the "
                              "tetrahedral crystal the law describes (other "
                              "phase, separate scope)"})
    cryst = [r for r in have if r["angle_sd"] < ANGLE_SPLIT]
    pts = _points(cryst)
    if len(pts) < 10:
        return ops, rest + cryst
    model = StructureModel(pts)
    for p in pts:
        p["xs"], p["Ts"] = model.implied(p["a"], p["angle_sd"])
        p["dx"], p["dT"] = p["xs"] - p["x"], p["Ts"] - p["T"]
    sx = _robust_sig([p["dx"] for p in pts], SIG_X_FLOOR)
    sT = _robust_sig([p["dT"] for p in pts], SIG_T_FLOOR)

    # S2a: batch-coherent temperature offset
    fixed = set()
    for b in sorted({p["batch_id"] for p in pts}):
        inb = [p for p in pts if p["batch_id"] == b]
        if len(inb) < 2:
            continue
        d = np.array([p["dT"] for p in inb])
        z = float(np.mean(d) / (sT / np.sqrt(len(d))))
        same = float(np.mean(np.sign(d) == np.sign(np.mean(d))))
        if abs(z) >= Z_BATCH and same >= 0.75:
            dT = float(np.median(d))
            cause = ("temperature labels shifted by about 273 K (Celsius/Kelvin)"
                     if abs(abs(dT) - v1.C_TO_K) < 3 * sT else
                     f"structure-implied temperature offset {dT:+.0f} K")
            runs = sorted(r for p in inb for r in p["run_ids"])
            ops.append({"op": "correct", "layer": "structure", "target_batch": b,
                        "target_runs": runs,
                        "reason": f"batch-coherent T offset z={z:.1f}; cause: "
                                  f"{cause}; labels relabelled"})
            for p in inb:
                for r in p["rows"]:
                    r["T"] = r["T"] + dT
                p["T"] += dT
                p["dT"] -= dT
                fixed.add(id(p))
    # S2b: point-level composition and temperature contradictions
    flagged = [p for p in pts if abs(p["dx"]) / sx >= Z_POINT
               or (abs(p["dT"]) / sT >= Z_POINT and id(p) not in fixed)]
    done = set()
    for p in flagged:
        if id(p) in done:
            continue
        what, partner = None, None
        if abs(p["dx"]) / sx >= Z_POINT:
            for q in flagged:
                if q is not p and id(q) not in done and \
                        abs(p["xs"] - q["x"]) < 3 * sx and abs(q["xs"] - p["x"]) < 3 * sx:
                    what, partner = "composition label swap between two points", q
                    break
            if what is None:
                what = ("species map reversed (label x is 1 - x)"
                        if abs(p["xs"] - (1 - p["x"])) < 3 * sx else
                        f"composition label contradicted by lattice constant "
                        f"(implied x = {p['xs']:.3f})")
        else:
            what = f"temperature label contradicted by structure (implied T = {p['Ts']:.0f} K)"
        grp = [p] + ([partner] if partner is not None else [])
        for q in grp:
            done.add(id(q))
            for r in q["rows"]:
                if "composition" in what or "species" in what:
                    # deviation D3 (ledger): the implied-x grid spans
                    # [-0.2, 1.2]; a relabel is clipped to the physical
                    # range [0, 1] so a row cannot crash the regime binning
                    r["x"] = round(min(max(q["xs"], 0.0), 1.0), 4)
                else:
                    r["T"] = round(q["Ts"], 1)
        ops.append({"op": "correct", "layer": "structure",
                    "target_runs": sorted(r for q in grp for r in q["run_ids"]),
                    "reason": f"{what}; labels relabelled from structure"})
    return ops, rest + cryst


def detect(rows: list[dict]) -> dict:
    rows = [dict(r) for r in rows]
    ops, rows = structure_layer(rows)
    split_ids = {r for o in ops if o["op"] == "split" for r in o["target_runs"]}
    live = [r for r in rows if r["run_id"] not in split_ids]
    # S3 declared domain (ledger 29)
    dom = [r for r in live if r["x"] > X_DOMAIN]
    if dom:
        ops.append({"op": "scope-limit", "layer": "domain",
                    "target_runs": sorted(r["run_id"] for r in dom),
                    "reason": f"x > {X_DOMAIN}: outside the declared law domain "
                              "(ledger seq 29)"})
    live = [r for r in live if r["x"] <= X_DOMAIN]
    # S4 physics guard at 0.85 of the solidus
    melt = [r for r in live if r["T"] >= H_GUARD * v1.solidus(r["x"])]
    if melt:
        ops.append({"op": "scope-limit", "layer": "physics",
                    "target_runs": sorted(r["run_id"] for r in melt),
                    "reason": f"T >= {H_GUARD} T_solidus: premelting band of the "
                              "real alloy, crystalline Tersoff MD outside its "
                              "validity"})
    live = [r for r in live if r["T"] < H_GUARD * v1.solidus(r["x"])]
    # S5 + v1 statistical stages
    old = v1.DUP_MODE
    v1.DUP_MODE = "design"
    try:
        res = v1.detect(live)
    finally:
        v1.DUP_MODE = old
    res["ops"] = ops + res["ops"]
    return res


if __name__ == "__main__":
    import json
    print(json.dumps(detect(json.load(open(sys.argv[1]))), indent=1, default=str))
