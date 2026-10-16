#!/usr/bin/env python3
"""P1 figure: the HG-SR law as the campaign went (replay.json).
(a) bulk kappa(x) at 300 K from the law in force after each stage, with the
    stage's validity range; (b) each stage's selected terms, coloured by the
    HG-SR term label. Usage: ~/mat_theory_pilot/venv/bin/python make_replay_figure.py"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sr_compare"))
import hgsr  # noqa: E402

S = json.load(open(os.path.join(HERE, "replay.json")))["stages"]
basis = {b[0]: b[2] for b in hgsr.make_basis(["x", "T"])}
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "legend.fontsize": 7})
fig, (ax, bx) = plt.subplots(1, 2, figsize=(7.0, 2.9), gridspec_kw={"width_ratios": [1, 1.25]})
cols = plt.cm.viridis(np.linspace(0.05, 0.85, len(S)))
for s, c in zip(S, cols):
    if "terms" not in s:
        continue
    x = np.linspace(max(s["x_range"][0], 0.02), min(s["x_range"][1], 0.98), 200)
    d = {"x": x, "T": np.full_like(x, 300.0)}
    r = sum(k * basis[n](d) for n, k in zip(s["terms"], s["coefs"]))
    ok = r > 0
    ax.plot(x[ok], 1 / r[ok], color=c, lw=1.8 if s["stage"] == S[-1]["stage"] else 1.1,
            ls="--" if s["stage"] == "R4" else "-",
            label=f"{s['stage']} ({s['n_bulk_series']} series)")
ax.set_xlabel("Ge fraction $x$")
ax.set_ylabel(r"bulk $\kappa$ at 300 K (W m$^{-1}$ K$^{-1}$, Tersoff)")
ax.set_ylim(0, 6); ax.set_xlim(0, 1)
ax.legend(frameon=False, loc="upper center")
ax.text(-0.16, 1.02, "(a)", transform=ax.transAxes, fontweight="bold")

LC = {"multi-supported": "#4C9A6A", "regime-sensitive": "#E0A030", "scope": "#C0504D"}
pretty = {"1": "const", "x": "x", "T": "T", "x^2": "x²", "1/T": "1/T", "x(1-x)": "x(1−x)",
          "x*T": "xT", "x(1-x)*T": "x(1−x)T"}
SHORT = {"R1": "first MD array", "R2": "+ seeds, box sizes", "R3": "alloys only",
         "R4": "+ coverage batch,\nGe-rich pair quarantined", "R5": "Ge-rich pair resolved,\nx ≤ 0.90"}
bx.set_xlim(0, 10); bx.set_ylim(len(S) + 0.1, -0.9); bx.axis("off")
bx.text(0, -0.75, "stage", fontweight="bold"); bx.text(4.1, -0.75, "terms of 1/κ selected by HG-SR", fontweight="bold")
for i, s in enumerate(S):
    bx.text(0, i, f"{s['stage']} (seq {s['ledger_seq']})\n{SHORT[s['stage']]}", va="center", fontsize=6.5)
    if "terms" not in s:
        bx.text(4.1, i, "refused: " + s["refused"], va="center", color="0.4")
        continue
    xx = 4.1
    for t in s["terms"]:
        lab = s["term_labels"][t]
        col = LC["scope"] if lab.startswith("scope") else LC[lab]
        w = 0.3 + 0.15 * len(pretty.get(t, t))
        bx.add_patch(plt.Rectangle((xx, i - 0.28), w, 0.56, color=col, alpha=0.85, lw=0))
        bx.text(xx + w / 2, i, pretty.get(t, t), ha="center", va="center", color="white", fontsize=6.5)
        xx += w + 0.15
used = {("scope" if v.startswith("scope") else v) for s in S for v in s.get("term_labels", {}).values()}
for j, (k, c) in enumerate([kc for kc in LC.items() if kc[0] in used]):
    bx.add_patch(plt.Rectangle((4.1 + 3.0 * j, len(S) - 0.4), 0.3, 0.3, color=c, lw=0))
    bx.text(4.5 + 3.0 * j, len(S) - 0.25, k if k != "scope" else "scope:party", va="center", fontsize=6.5)
bx.text(-0.05, 1.02, "(b)", transform=bx.transAxes, fontweight="bold")
fig.tight_layout()
outd = os.path.join(HERE, "..", "..", "papers", "paper1_j_mater_chem_a", "figures")
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(outd, f"fig_hgsr_replay.{ext}"), dpi=300)
print("ok")
