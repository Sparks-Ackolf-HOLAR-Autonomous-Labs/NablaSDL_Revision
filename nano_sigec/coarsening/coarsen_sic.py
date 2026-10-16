#!/usr/bin/env python3
"""Coarsening of few-nanometre 3C-SiC precipitates in Si(Ge): literature-parameterised estimate.

Two models, both volume-diffusion limited (carbon transport through the matrix):
  1. LSW asymptote:  r^3 - r0^3 = K t,  K = 8 sigma D c_e Omega^2 / (9 kT)
     (Lifshitz and Slyozov 1961; Wagner 1961).
  2. Mean-field class model (Kampmann-Wagner type; Wagner, Kampmann and Voorhees 2001)
     with the full exponential Gibbs-Thomson law c_r = c_e exp(l/r), l = 2 sigma Omega / kT.
     Needed because l is 3 to 5 nm, i.e. comparable to the radii of interest, where the
     linearised LSW law underestimates the early rate.
     dr_i/dt = D (cbar - c_ri) / (r_i c_p),  c_p = 1/Omega,
     cbar from the quasi-stationary condition sum_i n_i r_i (cbar - c_ri) = 0
     (precipitated volume conserved; matrix supersaturation negligible once c >> c_e).

Parameters (all DOI-verified, see coarsening.bib and README.md):
  D_C(T)  = 1.9 exp(-3.1 eV/kT) cm^2/s        newman1961 (quoted 1.99 in goesele2000)
          = 0.95 exp(-3.04 eV/kT) cm^2/s      rollert1989 (as tabulated in werner1998)
  c_e(T)  = 4e24 exp(-2.3 eV/kT) cm^-3        bean1971 (as given in werner1998, goesele2000)
  sigma   = 1.55 to 1.60 J/m^2 (SiC/Si(001), ab initio and Tersoff)  pizzagalli2003
  Omega   = a^3/4, a(3C-SiC) = 4.3596 A       (value quoted in pizzagalli2003)

Runs on 1 core in about a minute. Output: results/coarsening_results.json
"""
import json, os, itertools, math
from pathlib import Path
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"; OUT.mkdir(exist_ok=True)

kB = 8.617333e-5          # eV/K
kB_J = 1.380649e-23       # J/K
A_SIC = 4.3596e-10        # m, pizzagalli2003
OMEGA = A_SIC**3 / 4.0    # m^3 per SiC formula unit (one C atom)
C_P = 1.0 / OMEGA         # C atoms per m^3 in SiC
N_SI = 8 / (5.4309e-10)**3  # Si atoms per m^3 (a(Si) quoted in pizzagalli2003), for mole fractions

DIFF = {  # D0 (m^2/s), Ea (eV)
    "newman1961": (1.9e-4, 3.10),
    "rollert1989": (0.95e-4, 3.04),
}
SOL = {"bean1971": (4e24 * 1e6, 2.30)}   # c0 (m^-3), E (eV)
SIGMA = {"pizzagalli2003_abinitio_Cpoor": 1.55, "pizzagalli2003_tersoff": 1.60}
# Sensitivity only (NOT sourced): interface energy of a curved, incoherent few-nm particle
SIGMA_SENS = (1.0, 2.5)


def D(T, src):
    d0, e = DIFF[src]; return d0 * math.exp(-e / (kB * T))


def ce(T, src="bean1971"):
    c0, e = SOL[src]; return c0 * math.exp(-e / (kB * T))


def K_lsw(T, dsrc, sigma):
    return 8 * sigma * D(T, dsrc) * ce(T) * OMEGA**2 / (9 * kB_J * T)   # m^3/s


def cap_length(T, sigma):
    return 2 * sigma * OMEGA / (kB_J * T)


def class_model(T, dsrc, sigma, r0, width, t_end, r_targets=(2.5e-9, 5e-9, 10e-9),
                t_report=(), n_cls=1000, r_cut=0.25e-9):
    """Mean-field Lagrangian class model. Returns dict with time to reach each target
    number-mean radius and radii at report times."""
    Dm, c_e, l = D(T, dsrc), ce(T), cap_length(T, sigma)
    z = np.linspace(-3.5, 3.5, n_cls)
    r = r0 * np.exp(width * z)
    n = np.exp(-0.5 * z**2)                 # lognormal number weights (relative)
    t = 0.0
    hit = {f"{x*1e9:g}nm": None for x in r_targets}
    rep = {}
    t_rep = sorted(t_report)
    vol0 = np.sum(n * r**3)
    traj = []
    next_log = -6.0
    while t < t_end and r.size > 1:
        x = np.minimum(l / r, 600.0)
        cr = c_e * np.exp(x)
        cbar = np.sum(n * r * cr) / np.sum(n * r)
        v = Dm * (cbar - cr) / (r * C_P)
        big = r > 2 * r_cut
        dt = 0.05 * np.min(r[big] / np.maximum(np.abs(v[big]), 1e-300))
        dt = min(dt, t_end - t, max(t, 1e-12) * 0.1)
        # mass-conserving step: choose cbar so that the precipitated volume is unchanged
        V0 = np.sum(n * r**3)
        def vol(cb):
            rn = r + Dm * (cb - cr) / (r * C_P) * dt
            return np.sum(n * np.where(rn > r_cut, rn, 0.0)**3)
        lo, hi = cr.min(), max(cbar, cr.min()) * 2 + c_e
        while vol(hi) < V0:
            hi *= 2
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if vol(mid) < V0: lo = mid
            else: hi = mid
        cbar = 0.5 * (lo + hi)
        v = Dm * (cbar - cr) / (r * C_P)
        # report times inside the step
        while t_rep and t + dt >= t_rep[0]:
            tt = t_rep.pop(0); rr = r + v * (tt - t); m = rr > r_cut
            rep[tt] = float(np.sum(n[m] * rr[m]) / np.sum(n[m]))
        r = r + v * dt; t += dt
        keep = r > r_cut
        r, n = r[keep], n[keep]
        rmean = float(np.sum(n * r) / np.sum(n))
        for x_, key in zip(r_targets, hit):
            if hit[key] is None and rmean >= x_:
                hit[key] = t
        if t > 0 and math.log10(t) >= next_log:
            traj.append((t, rmean, float(np.sum(n * r**4) / np.sum(n * r**3))))
            next_log = math.log10(t) + 0.05
    for tt in t_rep:
        rep[tt] = float(np.sum(n * r) / np.sum(n))
    traj.append((t, float(np.sum(n * r) / np.sum(n)), float(np.sum(n * r**4) / np.sum(n * r**3))))
    return dict(t_hit=hit, r_at=rep, traj=traj, vol_ratio=float(np.sum(n * r**3) / vol0))


CONDITIONS = {
    # name: (T in K, list of hold times in s)
    "SPS_1273K": (1273.0, [300, 1800]),
    "SPS_1373K": (1373.0, [300, 1800]),
    "SPS_1473K": (1473.0, [300, 1800]),
    "HP_1473K": (1473.0, [3600, 14400]),
    "HP_1573K": (1573.0, [3600, 14400]),
    "service_1073K": (1073.0, [3.6e7]),
    "service_1173K": (1173.0, [3.6e7]),
    "service_1273K": (1273.0, [3.6e7]),
}
T_END = 3.6e9   # 1e6 h, long enough to reach 10 nm at every temperature listed


def main():
    res = {"parameters": {
        "Omega_m3": OMEGA, "a_SiC_A": A_SIC * 1e10, "c_p_m-3": C_P,
        "D_sources": {k: {"D0_cm2_s": v[0] * 1e4, "Ea_eV": v[1]} for k, v in DIFF.items()},
        "c_e_source": {"bean1971": {"c0_cm-3": 4e24, "E_eV": 2.3}},
        "sigma_J_m2": SIGMA, "sigma_sensitivity_unsourced": SIGMA_SENS,
        "initial_psd": "lognormal in r, median r0, width (sd of ln r) 0.2 or 0.4",
    }, "per_T": {}, "conditions": {}, "class_model": {}}
    temps = sorted({c[0] for c in CONDITIONS.values()} | {1323.0, 1423.0, 1523.0})
    for T in temps:
        res["per_T"][f"{T:.0f}"] = {
            "D_cm2_s": {k: D(T, k) * 1e4 for k in DIFF},
            "c_e_cm-3": ce(T) * 1e-6, "c_e_atfrac": ce(T) / N_SI,
            "cap_length_nm": {k: cap_length(T, s) * 1e9 for k, s in SIGMA.items()},
            "K_LSW_nm3_per_h": {f"{d}|{s}": K_lsw(T, d, sv) * 1e27 * 3600
                                for d in DIFF for s, sv in SIGMA.items()},
        }
    combos = list(itertools.product(DIFF, SIGMA, (1e-9, 2e-9), (0.2, 0.4)))
    sens = [("newman1961", "sens_lo", 1e-9, 0.2), ("newman1961", "sens_hi", 2e-9, 0.4)]
    for T in temps:
        rows = []
        times = sorted({tt for c in CONDITIONS.values() if c[0] == T for tt in c[1]})
        for d, s, r0, w in combos + sens:
            sv = SIGMA[s] if s in SIGMA else (SIGMA_SENS[0] if s == "sens_lo" else SIGMA_SENS[1])
            out = class_model(T, d, sv, r0, w, T_END, t_report=times)
            rows.append(dict(D=d, sigma=s, sigma_J_m2=sv, r0_nm=r0 * 1e9, width=w,
                             t_hit_h={k: (v / 3600 if v is not None else None) for k, v in out["t_hit"].items()},
                             r_mean_nm_at_s={f"{k:g}": v * 1e9 for k, v in out["r_at"].items()},
                             traj_h_nm=[(a / 3600, b * 1e9, c * 1e9) for a, b, c in out["traj"]],
                             vol_conservation=out["vol_ratio"]))
            print(f"T={T:.0f} {d:11s} {s:30s} r0={r0*1e9:.0f} w={w} "
                  + " ".join(f"{k}:{(v/3600 if v else float('nan')):.3g}h" for k, v in out["t_hit"].items())
                  + f"  vol={out['vol_ratio']:.3f}")
        res["class_model"][f"{T:.0f}"] = rows
    # summary bands (literature parameters only; sensitivity rows excluded)
    for name, (T, holds) in CONDITIONS.items():
        rows = [x for x in res["class_model"][f"{T:.0f}"] if x["sigma"] in SIGMA]
        summ = {}
        for r0 in (1.0, 2.0):
            sub = [x for x in rows if x["r0_nm"] == r0]
            summ[f"r0={r0:g}nm"] = {
                "r_mean_nm_after_hold": {f"{h:g}s": [min(x["r_mean_nm_at_s"][f"{h:g}"] for x in sub),
                                                      max(x["r_mean_nm_at_s"][f"{h:g}"] for x in sub)] for h in holds},
                "t_hit_h_band": {k: [min((x["t_hit_h"][k] or math.inf) for x in sub),
                                     max((x["t_hit_h"][k] or math.inf) for x in sub)]
                                 for k in sub[0]["t_hit_h"]},
            }
            sub_s = [x for x in res["class_model"][f"{T:.0f}"] if x["sigma"].startswith("sens") and x["r0_nm"] == r0]
            summ[f"r0={r0:g}nm"]["sensitivity_unsourced_sigma"] = {
                x["sigma"]: {"sigma_J_m2": x["sigma_J_m2"], "t_hit_h": x["t_hit_h"],
                             "r_mean_nm_after_hold": x["r_mean_nm_at_s"]} for x in sub_s}
        res["conditions"][name] = {"T_K": T, "holds_s": holds, **summ}
    def clean(o):
        if isinstance(o, float):
            return float(f"{o:.5g}") if math.isfinite(o) else None
        if isinstance(o, dict): return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [clean(v) for v in o]
        return o
    (OUT / "coarsening_results.json").write_text(json.dumps(clean(res), indent=1).replace(",\n", ","))


if __name__ == "__main__":
    main()
