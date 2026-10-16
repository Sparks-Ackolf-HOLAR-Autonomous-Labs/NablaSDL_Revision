#!/usr/bin/env python3
"""Detector v2 figure: (a) lattice constant of every rebuilt production
point against Ge fraction, (b) bond-angle spread against temperature,
(c) detection and harm per catalog entry, v1 frozen vs v2."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
desc = json.load(open(os.path.join(HERE, "descriptors.json")))
des = json.load(open(os.path.join(HERE, "..", "production", "production_design.json")))
pt = {}
for r in des["runs"]:
    pt[r["point_id"]] = (r["x"], r["T"])
v2 = json.load(open(os.path.join(HERE, "results_v2.json")))["table"]
v1 = {k: v["summary"] for k, v in json.load(open(os.path.join(HERE, "..", "production", "fault_study_results_frozen.json")))["entries"].items()}
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(7.0, 4.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.55, wspace=0.3)
ax = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
cm = plt.get_cmap("viridis")
for pid, d in desc.items():
    x, T = pt[pid]
    a = (8 * d["vol_atom"]) ** (1 / 3)
    amorph = d["angle_sd"] >= 10
    near = pid in ("N0", "N1")
    mk = "s" if amorph else ("^" if near else "o")
    c = cm((T - 300) / 1200)
    ax[0].scatter(x, a, s=14, marker=mk, color=c, edgecolor="k" if (amorph or near) else "none", lw=0.5)
    ax[1].scatter(T, d["angle_sd"], s=14, marker=mk, color=c, edgecolor="k" if (amorph or near) else "none", lw=0.5)
xx = np.linspace(0, 1, 50)
ax[0].plot(xx, 5.432 + (5.657 - 5.432) * xx, "k--", lw=0.8, label="Vegard line, Tersoff at 0 K")
ax[0].set_xlabel("Ge fraction $x$"); ax[0].set_ylabel(r"lattice constant ($\AA$)")
ax[0].legend(frameon=False, loc="upper left", fontsize=7)
ax[1].axhline(10, color="0.5", lw=0.8, ls=":")
ax[1].text(1500, 10.4, "split threshold", fontsize=7, color="0.4", ha="right")
ax[1].set_xlabel("temperature (K)"); ax[1].set_ylabel(r"bond-angle spread ($^\circ$)")
ax[1].scatter([], [], marker="o", color="0.6", s=14, label="crystal")
ax[1].scatter([], [], marker="^", color="0.6", edgecolor="k", lw=0.5, s=14, label="near-melting probe")
ax[1].scatter([], [], marker="s", color="0.6", edgecolor="k", lw=0.5, s=14, label="amorphous probe")
ax[1].legend(frameon=False, fontsize=7, loc="upper right", bbox_to_anchor=(1.0, 0.93))
ent = ["P03", "P04", "P05", "M01", "M02", "P01", "P02", "P06", "V01"]
lab = ["composition\nswap", "species\nswap", "T label\noffset", "premelting\nrows", "amorphous\nrows", "biased\nbatch", "unit\nslip", "duplicate\nbatch", "local valid\nanomaly"]
i = np.arange(len(ent))
d1 = [v1[k]["detected_rate_adj"] for k in ent]
d2 = [v2[k]["detected_adj"] for k in ent]
ax[2].bar(i - 0.2, d1, 0.4, color="0.7", label="v1, detected")
ax[2].bar(i + 0.2, d2, 0.4, color="#2a6fb0", label="v2, detected")
h1 = v1["V01"]["A_adj"].get("harmful", 0) / 50
ax[2].plot([8 - 0.2], [h1], "x", color="#c0392b", ms=6, label="harmful (valid anomaly)")
ax[2].plot([8 + 0.2], [v2["V01"]["harmful_adj"]], "x", color="#c0392b", ms=6)
ax[2].set_xticks(i); ax[2].set_xticklabels(lab, fontsize=7)
ax[2].set_ylabel("fraction of 50 trials"); ax[2].set_ylim(0, 1.05)
ax[2].legend(frameon=False, fontsize=6.5, loc="upper left", bbox_to_anchor=(0.0, 1.18), ncol=3)
sm = plt.cm.ScalarMappable(cmap=cm, norm=plt.Normalize(300, 1500))
cb = fig.colorbar(sm, ax=ax[1], fraction=0.05, pad=0.02); cb.set_label("T (K)", fontsize=7)
for k, a in zip("abc", ax):
    a.text(-0.12 if k == "c" else -0.2, 1.04, f"({k})", transform=a.transAxes, fontweight="bold")
fig.savefig(os.path.join(HERE, "fig_detector_v2.pdf"), bbox_inches="tight")
fig.savefig(os.path.join(HERE, "fig_detector_v2.png"), dpi=200, bbox_inches="tight")
