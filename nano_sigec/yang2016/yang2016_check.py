#!/usr/bin/env python3
"""Check of P1's coarse-SiC claim against Yang et al. 2016 (not pre-registered;
reporting check, session 128, 2026-10-14).

Yang, Wu, Ren, Zhang and Chen, J. Inorg. Mater. 31(9), 997 (2016),
DOI 10.15541/jim20160060 (open access): p-type Si80Ge20B0.6, ball milled
(BM) and spark plasma sintered, with 0, 0.3, 0.5 and 1.0 vol% SiC added as
about 50 nm powder; in the sintered body the SiC is "several tens to two
hundred nanometres" (TEM), mean diameter about 100 nm, grains about 500 nm.
Measured: kappa_L of the 0.5 vol% sample is 2.54 W/mK at 1000 K, 10% below
the BM sample without SiC (same milling) and 25% below the unmilled matrix;
at 1.0 vol% kappa_L rises again. kappa_L there is kappa - L0 T sigma with
L0 = 2.45e-8 V^2/K^2.

The comparison that isolates the SiC is BM + SiC against BM. This script
evaluates P1's model for that ratio at x = 0.2, 1000 K, SiC radius 25, 50
and 100 nm (diameters 50-200 nm), the three effective grain sizes P1 uses,
and both contrast limits of r30/large_radius_bracket.py.
Output: yang2016_check.json.
"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
NS = os.path.dirname(HERE)
sys.path.insert(0, NS)
sys.path.insert(0, os.path.join(NS, "small_sic", "r30"))
os.environ.setdefault("SIGEC_M1_SUMMARY", os.path.join(NS, "m1c", "m1c_summary.json"))
import analyze_sigec as A  # noqa: E402

r = json.load(open(os.path.join(NS, "small_sic", "r30", "r30_results.json")))
xs = np.log([c[0] for c in r["measured_curve"]]); ys = np.log([c[1] for c in r["measured_curve"]])


def lam_meas(Rn):
    if Rn <= 3.0:
        return float(np.exp(np.interp(np.log(Rn), xs, ys)))
    s = min(0.0, (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]))
    return float(np.exp(ys[-1] + s * (np.log(Rn) - xs[-1])))


lam_const = lambda Rn: A.contrast(0.2, "density")  # noqa: E731
m = A.SModes(0.2)
T = 1000.0
out = {"source": "Yang et al., J. Inorg. Mater. 31, 997 (2016), 10.15541/jim20160060",
       "measured": {"vol_pct": 0.5, "T_K": 1000, "kappa_L_W_mK": 2.54,
                    "drop_vs_BM_pct": -10.0, "drop_vs_matrix_pct": -25.0,
                    "note": "kappa_L rises again at 1.0 vol% SiC"},
       "rows": []}
for vol in (0.003, 0.005, 0.010):
    for Rn in (25, 50, 100):
        for d in A.DEFF:
            k0 = A.lnT_interp(m.kappa2(900, d), m.kappa2(1100, d), T)
            row = {"vol_pct": 100 * vol, "R_nm": Rn, "d_eff_um": d * 1e6}
            for lab, lf in (("constant", lam_const), ("measured_extrapolated", lam_meas)):
                kk = [m.kappa2(TT, d, 0.0, np_R=Rn * 1e-9, np_phi=vol, lam2=lf(Rn)) for TT in (900, 1100)]
                row[lab + "_pct"] = round(100 * (A.lnT_interp(*kk, T) / k0 - 1), 3)
            out["rows"].append(row)
r05 = [x for x in out["rows"] if x["vol_pct"] == 0.5]
out["summary_0p5vol"] = {
    "largest_model_reduction_pct": min(min(x["constant_pct"], x["measured_extrapolated_pct"]) for x in r05),
    "smallest_model_reduction_pct": max(max(x["constant_pct"], x["measured_extrapolated_pct"]) for x in r05),
    "measured_pct": -10.0}
json.dump(out, open(os.path.join(HERE, "yang2016_check.json"), "w"), indent=1)
print(json.dumps(out["summary_0p5vol"], indent=1))
for x in out["rows"]:
    print(x)
