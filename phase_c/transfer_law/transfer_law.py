#!/usr/bin/env python3
"""A1 prototype (improvement plan 2026-09-29): a symbolic, revisable
transfer law between two evidence parties, replacing the hand-built
per-regime calibration of the screening demo.

Object: ln r(x, T) with r = kappa_BTE-DFT / kappa_law(Tersoff-parented
final law), over the BTE nodes inside the law's validity domain. Search:
exhaustive subsets (up to 3 terms + intercept) of the basis
{x, x^2, x(1-x), t, x t, t^2} with t = T/1000, scored by leave-one-node-out
CV of ln r (the HG-SR style: deterministic, exhaustive, so removing a node
reproduces a from-scratch refit exactly). Output: the selected law, its
per-node provenance (leave-one-node-out coefficient change), and the
screening decision it implies at 300/700/1100 K, next to the
interpolated calibration used by the screening demo.

CPU only, seconds. Usage: ~/mat_theory_pilot/venv/bin/python transfer_law.py
"""
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# load only the definitions of the screening demo (everything above its
# "run" section), so importing it neither reruns nor rewrites its results
import types  # noqa: E402
_SD = os.path.join(HERE, "..", "screening_demo", "screening_demo.py")
sd = types.ModuleType("screening_demo_defs")
sd.__file__ = _SD
exec(compile(open(_SD).read().split("# " + "-" * 64 + " run -----")[0], _SD, "exec"),
     sd.__dict__)

BASIS = {"x": lambda x, t: x, "x^2": lambda x, t: x ** 2,
         "x(1-x)": lambda x, t: x * (1 - x), "t": lambda x, t: t,
         "x t": lambda x, t: x * t, "t^2": lambda x, t: t ** 2}


def nodes():
    out = []
    for (x, T), k in sorted(sd.BTE.items()):
        if sd.in_domain(x, T):
            out.append((x, T, np.log(k / float(sd.law_kappa(sd.LAW_TERMS, x, T)[0]))))
    return out


def design(names, xs, ts):
    return np.column_stack([np.ones_like(xs)] + [BASIS[n](xs, ts) for n in names])


def fit(names, pts):
    xs, ts, y = (np.array([p[i] for p in pts]) for i in range(3))
    ts = ts / 1000.0
    c, *_ = np.linalg.lstsq(design(names, xs, ts), y, rcond=None)
    return c


def loo(names, pts):
    err = []
    for i in range(len(pts)):
        tr = pts[:i] + pts[i + 1:]
        c = fit(names, tr)
        x, T, y = pts[i]
        err.append(float((design(names, np.array([x]), np.array([T / 1000.0])) @ c)[0] - y))
    return float(np.sqrt(np.mean(np.square(err)))), err


def main():
    pts = nodes()
    cands = []
    for k in range(0, 4):
        for names in itertools.combinations(BASIS, k):
            if len(names) + 1 >= len(pts) - 1:
                continue
            rmse, _ = loo(list(names), pts)
            cands.append((rmse + 0.01 * len(names), rmse, list(names)))
    cands.sort()
    score, rmse, names = cands[0]
    c = fit(names, pts)
    prov = {}
    for i, (x, T, _) in enumerate(pts):
        ci = fit(names, pts[:i] + pts[i + 1:])
        prov[f"x{x}_T{int(T)}"] = float(np.max(np.abs(ci - c)))

    def r_sym(x, T):
        x = np.atleast_1d(np.asarray(x, float))
        return np.exp(design(names, x, np.full_like(x, T / 1000.0)) @ c)

    decisions = {}
    for T in sd.TEMPS:
        def f_sym(xa, T=T):
            k = sd.law_kappa(sd.LAW_TERMS, xa, T) * r_sym(xa, T)
            return np.where([sd.in_domain(xi, T) for xi in np.atleast_1d(xa)], k, np.nan)
        d_sym = sd.decide(f_sym, T)
        d_int = sd.decide(lambda xa, T=T: sd.scope_kappa(sd.LAW_TERMS, xa, T), T)
        decisions[str(int(T))] = {"symbolic_transfer": d_sym, "interpolated_calibration": d_int}
    out = {"nodes": [{"x": x, "T": T, "ln_ratio": round(y, 4)} for x, T, y in pts],
           "selected": {"terms": ["1"] + names, "coefs": [round(v, 4) for v in c],
                        "loo_rmse_ln_ratio": round(rmse, 4)},
           "top5": [{"terms": ["1"] + n, "loo_rmse": round(r, 4)} for _, r, n in cands[:5]],
           "node_provenance_max_coef_shift": {k: round(v, 4) for k, v in prov.items()},
           "decisions": decisions}
    json.dump(out, open(os.path.join(HERE, "transfer_law_results.json"), "w"), indent=1, default=float)
    print(json.dumps({k: out[k] for k in ("selected", "top5")}, indent=1))
    for T, d in decisions.items():
        print(T, {k: (v.get("argmin_x"), v.get("kappa_min")) for k, v in d.items()})


if __name__ == "__main__":
    main()
