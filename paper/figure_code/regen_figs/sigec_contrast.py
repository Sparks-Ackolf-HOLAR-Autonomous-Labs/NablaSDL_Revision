"""Shared helper for the SiGeC figures: the measured radius-dependent SiC
contrast and its seed range, propagated through the committed scattering model.

The adopted contrast (record entry 110) is the geometric mean over two seeds
of the effective contrast lam2 measured by embedded-particle MD at R = 1.0,
1.5, 2.0, 3.0 and 5.0 nm (nano_sigec/small_sic/r50/r50_results.json,
"measured_curve"); between radii it is interpolated log-log and beyond 5 nm
the last segment is extrapolated without increase, the same rule as
nano_sigec/small_sic/r50/measured_curves.py. The seed range is the same rule
applied to the per-radius minimum and maximum seed values ("lam2_seeds").
kappa_L comes from the committed model (nano_sigec/radius_contrast/
fit_radius_contrast.py, unscaled almaBTE modes); with the central contrast
this reproduces measured_curves.json exactly. Reads committed files only;
writes nothing. Importing takes about 10 s (the mode data are loaded once).
"""
import json
import sys

import numpy as np
import paper_fig_style as S

_NS = S.PROJECT / "nano_sigec"
sys.path.insert(0, str(_NS / "radius_contrast"))
import fit_radius_contrast as FR  # noqa: E402

_R50 = json.loads((_NS / "small_sic" / "r50" / "r50_results.json").read_text())
_MID = [(float(r), float(v)) for r, v in _R50["measured_curve"]]
_SEEDS = {p["R_A"] / 10.0: p["lam2_seeds"] for p in _R50["points"].values()}
_RADII = [r for r, _ in _MID]
CURVES = {"mid": _MID,
          "lo": [(r, float(min(_SEEDS[r]))) for r in _RADII],
          "hi": [(r, float(max(_SEEDS[r]))) for r in _RADII]}
SEED_NOTE = "two seeds per radius"


def lam2(Rn, which="mid"):
    """Effective contrast at radius Rn (nm) for the central curve or a seed edge."""
    cur = CURVES[which]
    lx = np.log([c[0] for c in cur])
    ly = np.log([c[1] for c in cur])
    if Rn <= 5.0:
        return float(np.exp(np.interp(np.log(Rn), lx, ly)))
    s = min(0.0, (ly[-1] - ly[-2]) / (lx[-1] - lx[-2]))
    return float(np.exp(ly[-1] + s * (np.log(Rn) - lx[-1])))


def kappa(x, T, y, Rn, which="mid", d=FR.D_EFF):
    """kappa_L (W/m/K) of SiGe host x with carbon fraction y as SiC of radius Rn (nm)."""
    if y == 0:
        return FR.MODES[x].kappa2(T, d)
    return FR.MODES[x].kappa2(T, d, 0.0, np_R=Rn * 1e-9, np_phi=FR.S.phi(x, y),
                              lam2=lam2(Rn, which))


def x_equal(y, Rn, which="mid", T=300):
    """Ge fraction whose kappa_L with carbon equals carbon-free Si0.8Ge0.2."""
    return FR.S.xmin_for([kappa(x, T, y, Rn, which) for x in FR.S.XS], FR.K0[T])


def band(values):
    """(low, high) envelope of the three curves, point by point."""
    arr = np.array(values, dtype=float)
    return arr.min(axis=0), arr.max(axis=0)


YS = list(FR.S.YS)
