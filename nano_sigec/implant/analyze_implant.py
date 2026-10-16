#!/usr/bin/env python3
"""Analysis of the pre-registered implant-route study (implant_design.json, ledger seq 151).

Reads only the committed SRIM outputs (srim_raw/), the RustBCA ranges
(rustbca_ranges.json) and the committed almaBTE host modes through the
light-dopant model (ledger 74-76). Refuses to run if the design changed.
Writes implant_results.json. Runtime: seconds."""
import hashlib, json, os, sys
import numpy as np
from scipy.optimize import nnls

HERE = os.path.dirname(os.path.abspath(__file__))
reg = open(os.path.join(HERE, "PREREGISTERED_SHA256")).read().split()[0]
DES = os.path.join(HERE, "implant_design.json")
if hashlib.sha256(open(DES, "rb").read()).hexdigest() != reg:
    sys.exit("implant_design.json changed after registration")
D = json.load(open(DES))
sys.path.insert(0, os.path.join(HERE, "..", "light_dopants"))
import analyze_light_dopants as LD  # noqa: E402  (checks its own registered hash)

RAW = os.path.join(HERE, "srim_raw")
N_SI, N_GE = 4.995e22, 4.416e22
NX = lambda x: (1 - x) * N_SI + x * N_GE  # atoms per cm^3
SQ2PI = np.sqrt(2 * np.pi)


def name(ion, e, x):
    return f"{ion}_{'Si' if x == 0 else f'Si{1 - x:g}Ge{x:g}'}_{e}keV"


def table(path):
    """Numeric rows of a SRIM RANGE.txt / VACANCY.txt depth table: depth (A) + columns."""
    rows = []
    for line in open(path, errors="ignore"):
        p = line.split()
        if len(p) >= 3:
            try:
                rows.append([float(v) for v in p])
            except ValueError:
                pass
    a = np.array([r for r in rows if len(r) == len(rows[-1])])
    return a[:, 0], a[:, 1:]


def stats(n):
    z = []
    for line in open(os.path.join(RAW, f"{n}_RANGE_3D.txt"), errors="ignore"):
        p = line.split()
        if len(p) == 4 and p[0].isdigit():
            z.append(float(p[1]))
    z = np.array(z) / 10.0
    z = z[z > 0]
    return {"ions_stopped": int(len(z)), "Rp_nm": float(z.mean()), "dRp_nm": float(z.std())}


def profiles(n):
    zr, cr = table(os.path.join(RAW, f"{n}_RANGE.txt"))      # (atoms/cm3)/(atoms/cm2)
    zv, cv = table(os.path.join(RAW, f"{n}_VACANCY.txt"))    # vacancies/(A ion)
    return zr / 10.0, cr[:, 0], zv / 10.0, cv.sum(axis=1)


def kap_saving(R, phi, l2, T):
    xm = LD.xmatch(T, incl=[LD.void(R, phi, l2)], porosity=phi)
    return None if xm is None else 100 * (1 - xm / LD.X0)


def main():
    res = {"design_sha256": reg, "srim": {}, "pred": {}, "gates": {}}
    for grp in ("A_he_anchor_Si", "A_he_SiGe", "B_c_SiGe", "C_kr_anchor_Si"):
        for ion, e, x in D["recipes"][grp]:
            n = name(ion, e, x)
            s = stats(n)
            _, _, zv, v = profiles(n)
            s["vac_per_ion_KP"] = float(np.trapezoid(v, zv * 10.0))
            res["srim"][n] = s
    S = res["srim"]
    rb = json.load(open(os.path.join(HERE, "rustbca_ranges.json")))
    g0 = {k: 100 * (rb[k]["Rp_nm"] / S[k]["Rp_nm"] - 1) for k in rb}
    res["gates"]["G0_codes"] = {"Rp_diff_pct_RustBCA_vs_SRIM": g0, "pass": all(abs(v) <= 15 for v in g0.values())}
    r50 = S["He_Si_50keV"]["Rp_nm"]
    res["gates"]["G1_anchor_range"] = {"SRIM_Rp_nm": r50, "lit_nm": 450, "pass": abs(r50 / 450 - 1) <= 0.10}
    P = res["pred"]

    # ---- A: He cavities
    crit = D["literature_anchors"]["he_bubble_critical_conc_cm3"][0]
    dmin100 = crit * SQ2PI * S["He_Si_100keV"]["dRp_nm"] * 1e-7
    P["PI1"] = {"dose_min_100keV_cm2": dmin100, "lit_window": [1e16, 2.5e16], "pass": 0.5e16 <= dmin100 <= 5e16}
    a = S["He_Si_40keV"]
    f_need = 0.01 * N_SI * 250e-7 / (5e16 * a["vac_per_ion_KP"])
    P["PI2"] = {"vac_per_ion": a["vac_per_ion_KP"], "f_needed_1vol": f_need, "bound": 0.06, "pass": f_need <= 0.06,
                "vol_pct_at_f": {f"{f:g}": 100 * f * 5e16 * a["vac_per_ion_KP"] / (N_SI * 250e-7) for f in (0.01, 0.03, 0.06)}}
    peak_anchor = 5e16 / (SQ2PI * a["dRp_nm"] * 1e-7)
    rec = {}
    for ion, e, x in D["recipes"]["A_he_SiGe"]:
        s = S[name(ion, e, x)]
        dose = peak_anchor * SQ2PI * s["dRp_nm"] * 1e-7
        rec[f"{e}keV"] = {"layer_nm": [max(0.0, s["Rp_nm"] - s["dRp_nm"]), s["Rp_nm"] + s["dRp_nm"]],
                          "dose_cm2_anchor_peak": dose, "dose_min_cm2_critical": crit * SQ2PI * s["dRp_nm"] * 1e-7,
                          "vol_pct_at_f0.03": 100 * 0.03 * dose * s["vac_per_ion_KP"] / (NX(x) * 2 * s["dRp_nm"] * 1e-7)}
    res["A_he_recipes_SiGe"] = {"anchor_peak_He_cm3": peak_anchor, "recipes": rec}
    kap = {}
    for T in (300, 1100):
        k0 = LD.kap(LD.X0, T)
        for R in (5e-9, 10e-9, 20e-9):
            for l2 in (1.0, 4.0):
                kap[f"T{T}_R{R * 1e9:g}_lam{l2:g}"] = {
                    "pct": LD.pct(LD.kap(LD.X0, T, incl=[LD.void(R, 0.01, l2)], porosity=0.01), k0),
                    "ge_saving_pct": kap_saving(R, 0.01, l2, T)}
    res["A_kappa_1vol_x0.2"] = kap
    r20 = [kap[f"T{T}_R20_lam{l:g}"] for T in (300, 1100) for l in (1.0, 4.0)]
    P["PI3"] = {"max_reduction_pct_R20": max(-r["pct"] for r in r20), "min_reduction_pct_R20": min(-r["pct"] for r in r20),
                "pass": all(-r["pct"] >= 5 for r in r20)}
    s20 = [kap[f"T300_R20_lam{l:g}"]["ge_saving_pct"] for l in (1.0, 4.0)]
    P["PI4"] = {"ge_saving_300K_R20": s20, "pass": all(v is not None and v < 25 for v in s20)}

    # ---- B: carbon box profile in Si0.8Ge0.2
    zg = np.arange(0.0, 1000.0, 2.0)
    Bc, Bv = [], []
    for ion, e, x in D["recipes"]["B_c_SiGe"]:
        zr, c, zv, v = profiles(name(ion, e, x))
        Bc.append(np.interp(zg, zr, c, right=0.0))
        Bv.append(np.interp(zg, zv, v, right=0.0) * 1e8)  # vacancies per cm per ion
    Bc, Bv = np.array(Bc).T, np.array(Bv).T
    win = (zg >= 30) & (zg <= 300)
    n = NX(0.2)
    box = {}
    for at in (0.01, 0.03):
        tgt = at * n
        dose, _ = nnls(Bc[win] / tgt, np.ones(win.sum()))
        prof = Bc @ dose
        dpa = (Bv @ dose) / n
        box[f"{at * 100:g}at%"] = {"doses_cm2": dict(zip([f"{e}keV" for _, e, _ in D["recipes"]["B_c_SiGe"]], dose.tolist())),
                                   "total_dose_cm2": float(dose.sum()),
                                   "rms_dev_pct": float(100 * np.sqrt(np.mean((prof[win] / tgt - 1) ** 2))),
                                   "max_dev_pct": float(100 * np.max(np.abs(prof[win] / tgt - 1))),
                                   "peak_dpa_KP": float(dpa.max()),
                                   "C_cm3_window_mean": float(prof[win].mean())}
    cap = D["literature_anchors"]["c_spe_substitutional_cap_cm3"][0]
    res["B_c_box"] = {"window_nm": [30, 300], "n_cm3": n, "recipes": box,
                      "substitutional_cap_cm3": cap, "excess_over_cap_at_1at%": 0.01 * n / cap[1]}
    P["PI5"] = {"rms_dev_pct": {k: v["rms_dev_pct"] for k, v in box.items()},
                "pass": all(v["rms_dev_pct"] <= 15 for v in box.values())}
    P["PI6"] = {"peak_dpa_1at%": box["1at%"]["peak_dpa_KP"], "pass": box["1at%"]["peak_dpa_KP"] >= 1}

    # ---- C: damage-to-kappa chain, Kr 500 keV in Si at 1e14 cm-2
    _, _, zv, v = profiles("Kr_Si_500keV")
    cpk = 1e14 * v.max() * 1e8 / N_SI  # vacancy fraction at the damage peak for f = 1
    kz = lambda f: LD.kap(0.0, 300, d=1e-3, gamma=9 * f * cpk)
    k0 = LD.kap(0.0, 300, d=1e-3)
    lo, hi = 1e-6, 1.0
    if kz(hi) > 10:
        f_req = None
    else:
        for _ in range(60):
            mid = np.sqrt(lo * hi)
            lo, hi = (mid, hi) if kz(mid) > 10 else (lo, mid)
        f_req = hi
    prof = {f"{f:g}": [LD.kap(0.0, 300, d=1e-3, gamma=9 * f * 1e14 * vv * 1e8 / N_SI) for vv in v[::5]]
            for f in (0.01, 0.06) + ((f_req,) if f_req else ())}
    res["C_chain"] = {"kappa_pristine_model": k0, "kappa_pristine_measured": 120.0, "vac_frac_peak_f1": cpk,
                      "kappa_at_peak": {f"{f:g}": kz(f) for f in (0.01, 0.03, 0.06, 0.1, 1.0)},
                      "f_req_for_10WmK": f_req, "depth_nm_every5": (zv[::5]).tolist(), "kappa_profile": prof,
                      "Rp_nm": S["Kr_Si_500keV"]["Rp_nm"]}
    P["PI7"] = {"f_req": f_req, "pass": (f_req is None) or f_req > 0.06}

    # ---- registered decisions
    sv = [x for x in s20 if x is not None]
    worst = min(sv) if len(sv) == len(s20) else 0.0
    res["decision"] = {
        "gates_pass": res["gates"]["G0_codes"]["pass"] and res["gates"]["G1_anchor_range"]["pass"],
        "cavity_claim": ("strengthen" if worst >= 25 else "scope-limit" if worst >= 10 else "downweight"),
        "cavity_worst_saving_R20_300K": worst,
        "sic_route": "recorded as practical route" if P["PI5"]["pass"] else "recorded with measured flatness only",
        "chain": "usable with f as named weak input" if (f_req is not None and f_req <= 0.06) else "scope-limited",
    }
    json.dump(res, open(os.path.join(HERE, "implant_results.json"), "w"), indent=1, default=float)
    print(json.dumps({"gates": res["gates"], "pred": P, "decision": res["decision"],
                      "A_recipes": res["A_he_recipes_SiGe"], "B": res["B_c_box"]["recipes"],
                      "C": {k: res["C_chain"][k] for k in ("kappa_pristine_model", "vac_frac_peak_f1", "kappa_at_peak", "f_req_for_10WmK")}},
                     indent=1, default=float))


if __name__ == "__main__":
    main()
