#!/usr/bin/env python3
"""Figure for the implant-route study: reads implant_results.json and srim_raw/ only.
(a) carbon box profiles from the five-energy recipe in Si0.8Ge0.2;
(b) kappa_L reduction of 1 vol% cavities versus cavity radius (design value and post-anneal anchors);
(c) Kr 500 keV in Si: point-defect kappa(z) at two retained fractions against the measured bound."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = sys.argv[:1]
import analyze_implant as A  # noqa: E402  (hash check only; main() is not run)

R = json.load(open(os.path.join(HERE, "implant_results.json")))
plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7})
fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.4), constrained_layout=True)

# (a) carbon box
zg = np.arange(0.0, 1000.0, 2.0)
n = R["B_c_box"]["n_cm3"]
for lab, col in (("1at%", "#2b6cb0"), ("3at%", "#c05621")):
    doses = R["B_c_box"]["recipes"][lab]["doses_cm2"]
    tot = np.zeros_like(zg)
    for ion, e, x in A.D["recipes"]["B_c_SiGe"]:
        zr, c, _, _ = A.profiles(A.name(ion, e, x))
        tot += doses[f"{e}keV"] * np.interp(zg, zr, c, right=0.0)
    ax[0].plot(zg, 100 * tot / n, color=col, lw=1.2, label=lab.replace("at%", " at% target"))
ax[0].axvspan(30, 300, color="0.9", zorder=0)
ax[0].set_xlim(0, 450)
ax[0].set_xlabel("Depth (nm)")
ax[0].set_ylabel("C content (at%)")
ax[0].set_title("(a) Five-energy C implant, Si$_{0.8}$Ge$_{0.2}$")
ax[0].legend(frameon=False, loc="upper right")

# (b) cavities: reduction and Ge saving versus radius
K = R["A_kappa_1vol_x0.2"]
for T, mk in ((300, "o"), (1100, "s")):
    for l2, ls in ((1.0, "-"), (4.0, "--")):
        rs = [5, 10, 20]
        y = [-K[f"T{T}_R{r}_lam{l2:g}"]["pct"] for r in rs]
        ax[1].plot(rs, y, ls, marker=mk, ms=3, lw=1, color="#2b6cb0" if T == 300 else "#c05621",
                   label=f"{T} K" if l2 == 1.0 else None)
ax[1].axhline(5, color="0.5", lw=0.7, ls=":")
ax[1].axvspan(5, 20, color="0.92", zorder=0)
ax[1].text(5.3, 1.0, "reported radii after\n700-900 $^\\circ$C anneals", fontsize=6, color="0.35")
ax[1].set_xlabel("Cavity radius (nm)")
ax[1].set_ylabel("$\\kappa_L$ reduction at 1 vol% (%)")
ax[1].set_title("(b) Cavities in Si$_{0.8}$Ge$_{0.2}$, 0.3 $\\mu$m grains")
ax[1].set_ylim(0, None)
ax[1].legend(frameon=False)

# (c) Kr chain
C = R["C_chain"]
z = np.array(C["depth_nm_every5"])
for f, col in zip(C["kappa_profile"], ("#2b6cb0", "#c05621", "#2f855a")):
    ax[2].semilogy(z, C["kappa_profile"][f], color=col, lw=1.1, label=f"f = {float(f):.2g}")
ax[2].axhline(10, color="k", lw=0.8, ls="--")
ax[2].text(330, 6.0, "measured bound,\n10$^{14}$ cm$^{-2}$", fontsize=6)
ax[2].set_xlim(0, 600)
ax[2].set_xlabel("Depth (nm)")
ax[2].set_ylabel("$\\kappa$ (W m$^{-1}$ K$^{-1}$)")
ax[2].set_title("(c) Kr 500 keV in Si, vacancies only")
ax[2].legend(frameon=False, loc="upper left", title="retained fraction", title_fontsize=7)
ax[2].set_ylim(5, 400)
out = os.path.join(HERE, "fig_implant.png")
fig.savefig(out, dpi=300)
fig.savefig(out.replace(".png", ".pdf"))
print(out)
