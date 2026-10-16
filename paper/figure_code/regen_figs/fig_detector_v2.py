#!/usr/bin/env python3
"""Fig. detector v2, at print size (full width). Same data and panels as
phase_c/detector_v2/make_v2_figure.py: (a) lattice constant of each rebuilt
production point against Ge fraction, (b) bond-angle spread against
temperature, (c) detection and harm per fault-catalogue entry for the first
and second detector versions over 50 trials (error bars: 95 % Wilson
binomial intervals)."""
import json

import numpy as np

import paper_fig_style as S

S.apply_style()
import matplotlib.pyplot as plt  # noqa: E402

PC = S.PROJECT / "phase_c"
desc = json.load(open(PC / "detector_v2" / "descriptors.json"))
des = json.load(open(PC / "production" / "production_design.json"))
pt = {r["point_id"]: (r["x"], r["T"]) for r in des["runs"]}
v2 = json.load(open(PC / "detector_v2" / "results_v2.json"))["table"]
v1 = {k: v["summary"] for k, v in
      json.load(open(PC / "production" / "fault_study_results_frozen.json"))["entries"].items()}
N = 50


def wilson(p, n=N, z=1.96):
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return np.array([p - (c - h), (c + h) - p])


fig = plt.figure(figsize=(S.FULL, 4.5))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1])
ax = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
cm = plt.get_cmap("viridis")
for pid, d in desc.items():
    x, T = pt[pid]
    a = (8 * d["vol_atom"]) ** (1 / 3)
    amorph = d["angle_sd"] >= 10
    near = pid in ("N0", "N1")
    mk = "s" if amorph else ("^" if near else "o")
    c = cm((T - 300) / 1200)
    kw = dict(s=16, marker=mk, color=c, edgecolor="k" if (amorph or near) else "none", lw=0.5)
    ax[0].scatter(x, a, **kw)
    ax[1].scatter(T, d["angle_sd"], **kw)
xx = np.linspace(0, 1, 50)
ax[0].plot(xx, 5.432 + (5.657 - 5.432) * xx, "k--", lw=0.8, label="Tersoff Vegard line, 0 K")
ax[0].set_xlabel("Ge fraction $x$")
ax[0].set_ylabel(r"lattice constant (Å)")
ax[0].legend(loc="upper left")
ax[1].axhline(10, color=S.GREY, lw=0.8, ls=":")
ax[1].set_xlabel("temperature (K)")
ax[1].set_ylabel(r"bond-angle spread (°)")
for mk, lab, ec in (("o", "crystal", "none"), ("^", "near-melting probe", "k"), ("s", "amorphous probe", "k")):
    ax[1].scatter([], [], marker=mk, color=S.GREY, edgecolor=ec, lw=0.5, s=16, label=lab)
ax[1].legend(loc="upper right", bbox_to_anchor=(1.0, 0.92))
ax[1].set_ylim(0, 18)
sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(300, 1500))
cb = fig.colorbar(sm, ax=ax[1], fraction=0.05, pad=0.02, aspect=15)
cb.set_label("temperature (K)", fontsize=7)
cb.ax.tick_params(labelsize=7)

ent = ["P03", "P04", "P05", "M01", "M02", "P01", "P02", "P06", "V01"]
lab = ["composition\nswap", "species\nswap", "$T$ label\noffset", "premelting\nrows",
       "amorphous\nrows", "biased\nbatch", "unit\nslip", "duplicate\nbatch", "local valid\nanomaly"]
i = np.arange(len(ent))
d1 = np.array([v1[k]["detected_rate_adj"] for k in ent])
d2 = np.array([v2[k]["detected_adj"] for k in ent])
ekw = dict(ecolor=S.INK, elinewidth=0.6, capsize=1.5)
ax[2].bar(i - 0.2, d1, 0.4, color="#BBBBBB", yerr=wilson(d1), error_kw=ekw, label="first version, detected")
ax[2].bar(i + 0.2, d2, 0.4, color="#0072B2", yerr=wilson(d2), error_kw=ekw, label="second version, detected")
h1 = v1["V01"]["A_adj"].get("harmful", 0) / N
h2 = v2["V01"]["harmful_adj"]
ax[2].errorbar([8 - 0.2, 8 + 0.2], [h1, h2], yerr=np.c_[wilson(h1), wilson(h2)], fmt="x",
               color="#D55E00", ms=6, mew=1.2, elinewidth=0.6, capsize=1.5,
               label="harmful action (valid anomaly)", clip_on=False, zorder=5)
ax[2].set_xticks(i)
ax[2].set_xticklabels(lab)
ax[2].set_xlim(-0.6, len(ent) - 0.4)
ax[2].set_ylabel("fraction of 50 trials")
ax[2].set_ylim(-0.04, 1.25)
ax[2].set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax[2].legend(loc="upper left", ncol=3)
for k, a in zip("abc", ax):
    a.text(-0.06 if k == "c" else -0.16, 1.02, f"({k})", transform=a.transAxes,
           fontweight="bold", fontsize=9, va="bottom")
S.save(fig, "fig_detector_v2")
