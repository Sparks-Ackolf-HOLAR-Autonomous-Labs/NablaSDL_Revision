#!/usr/bin/env python3
"""Fig. HG-SR replay, at print size (full width). Same data and panels as
phase_c/hgsr_replay/make_replay_figure.py; reads phase_c/hgsr_replay/replay.json
and the HG-SR basis from phase_c/sr_compare/hgsr.py.
(a) bulk kappa(x) at 300 K from the law in force after each stage;
(b) the terms of 1/kappa selected at each stage, coloured by the HG-SR label."""
import json
import sys

import numpy as np

import paper_fig_style as S

S.apply_style()
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(S.PROJECT / "phase_c" / "sr_compare"))
import hgsr  # noqa: E402

ST = json.load(open(S.PROJECT / "phase_c" / "hgsr_replay" / "replay.json"))["stages"]
basis = {b[0]: b[2] for b in hgsr.make_basis(["x", "T"])}

fig, (ax, bx) = plt.subplots(1, 2, figsize=(S.FULL, 3.3), gridspec_kw={"width_ratios": [1, 1.2]})
cols = plt.cm.viridis(np.linspace(0.05, 0.85, len(ST)))
# stage number and what the stage added (plain labels; the record entries are in panel b)
SHORT = {"R1": "first MD array", "R2": "+ seeds, box sizes", "R3": "alloys only",
         "R4": "+ coverage batch,\nGe-rich pair set aside", "R5": "Ge-rich pair\nresolved, x ≤ 0.90"}
NUM = {s["stage"]: i + 1 for i, s in enumerate(ST)}
# distinct line styles so the stages separate in greyscale; stage 4 is drawn
# with open markers because its curve coincides with stage 5 below x = 0.90
STYLE = {"R1": dict(ls=":", lw=1.3), "R2": dict(ls="-.", lw=1.1), "R3": dict(ls=(0, (5, 2)), lw=1.1),
         "R4": dict(ls="none", marker="o", mfc="white", ms=3.2, markevery=12, mew=0.9),
         "R5": dict(ls="-", lw=1.8)}
for s, c in zip(ST, cols):
    if "terms" not in s:
        continue
    x = np.linspace(max(s["x_range"][0], 0.02), min(s["x_range"][1], 0.98), 200)
    d = {"x": x, "T": np.full_like(x, 300.0)}
    r = sum(k * basis[n](d) for n, k in zip(s["terms"], s["coefs"]))
    ok = r > 0
    ax.plot(x[ok], 1 / r[ok], color=c, zorder=4 if s["stage"] == "R4" else 3,
            label=f"{NUM[s['stage']]}: {SHORT[s['stage']].replace(chr(10), ' ')} ({s['n_bulk_series']})",
            **STYLE[s["stage"]])
ax.set_xlabel("Ge fraction $x$")
ax.set_ylabel(r"bulk $\kappa$ at 300 K (W m$^{-1}$ K$^{-1}$)")
ax.set_ylim(0, 6)
ax.set_xlim(0, 1)
fig.legend(loc="outside lower left", ncol=2, columnspacing=1.0, handlelength=2.6,
           title="stage: what it added (bulk series)", title_fontsize=7, alignment="left")
ax.set_title("Tersoff MD law after each stage")
ax.text(-0.16, 1.02, "(a)", transform=ax.transAxes, fontweight="bold", fontsize=9, va="bottom")

# term labels in neutral and rose tones, apart from the evidence-source colours
LC = {"multi-supported": "#BBBBBB", "regime-sensitive": "#CC6677", "scope": "#882255"}
LCNAME = {"multi-supported": "multi-supported", "regime-sensitive": "regime-sensitive",
          "scope": "limited to one evidence source"}
pretty = {"1": "const", "x": "x", "T": "T", "x^2": "x²", "1/T": "1/T", "x(1-x)": "x(1−x)",
          "x*T": "xT", "x(1-x)*T": "x(1−x)T"}
bx.set_xlim(0, 10)
bx.set_ylim(len(ST) + 0.2, -0.9)
bx.axis("off")
X0 = 4.6
bx.text(0, -0.75, "stage (record entries)", fontweight="bold", fontsize=7)
bx.text(X0, -0.75, "terms of 1/κ selected", fontweight="bold", fontsize=7)
for i, s in enumerate(ST):
    led = "" if s["ledger_seq"] == "-" else f" ({s['ledger_seq']})"
    bx.text(0, i, f"{NUM[s['stage']]}{led}: {SHORT[s['stage']]}", va="center", fontsize=7, linespacing=1.1)
    if "terms" not in s:
        bx.text(X0, i, "refused: " + s["refused"], va="center", color=S.GREY, fontsize=7)
        continue
    xx = X0
    for t in s["terms"]:
        lab = s["term_labels"][t]
        col = LC["scope"] if lab.startswith("scope") else LC[lab]
        w = 0.35 + 0.17 * len(pretty.get(t, t))
        bx.add_patch(plt.Rectangle((xx, i - 0.3), w, 0.6, color=col, lw=0))
        bx.text(xx + w / 2, i, pretty.get(t, t), ha="center", va="center", color="black", fontsize=7)
        xx += w + 0.15
used = [k for k in LC if any(("scope" if v.startswith("scope") else v) == k
                             for s in ST for v in s.get("term_labels", {}).values())]
for j, k in enumerate(used):
    bx.add_patch(plt.Rectangle((X0 + 3.1 * j, len(ST) - 0.15), 0.3, 0.3, color=LC[k], lw=0))
    bx.text(X0 + 0.4 + 3.1 * j, len(ST), LCNAME[k], va="center", fontsize=7)
bx.text(-0.02, 1.02, "(b)", transform=bx.transAxes, fontweight="bold", fontsize=9, va="bottom")
S.save(fig, "fig_hgsr_replay")
