#!/usr/bin/env python3
"""ESI Fig. (fig:implant): the three implant recipes of the ESI implant
paragraph compared in one figure (full width, print size).

Columns: C at 40 keV and He at 40 keV into Si0.8Ge0.2, Kr at 500 keV into Si.
Top row: depth distribution of the ions stopped in the SRIM run
(nano_sigec/implant/srim_raw/<recipe>_RANGE_3D.txt), with the mean projected
range of both codes (SRIM from the same file; RustBCA mean and standard
deviation from nano_sigec/implant/rustbca_ranges.json, 20 000 ions).
Bottom row: SRIM vacancies per angstrom per ion (ions and recoils,
Kinchin-Pease estimate; <recipe>_VACANCY.txt). The He column shades the
220-410 nm cavity layer of the text. Replaces the three four-panel TRIM-style
figures, whose ion-path panels needed RustBCA track files that are not
stored in the repository. Parsers are those of
nano_sigec/implant/trim_style/make_trim_style.py.
"""
import json
import sys

import numpy as np
import paper_fig_style as S

S.apply_style()
sys.path.insert(0, str(S.PROJECT / "nano_sigec" / "implant" / "trim_style"))
import make_trim_style as T  # noqa: E402  (only its SRIM parsers are used)

S.apply_style()  # make_trim_style sets its own rcParams on import
import matplotlib.pyplot as plt  # noqa: E402

RB = json.loads((S.PROJECT / "nano_sigec" / "implant" / "rustbca_ranges.json").read_text())
RECIPES = [("C_Si0.8Ge0.2_40keV", "C, 40 keV into Si$_{0.8}$Ge$_{0.2}$\n(SiC route)"),
           ("He_Si0.8Ge0.2_40keV", "He, 40 keV into Si$_{0.8}$Ge$_{0.2}$\n(cavity route)"),
           ("Kr_Si_500keV", "Kr, 500 keV into Si\n(measured-bound check)")]
SRIM_C, RB_C, CAV = S.INK, "#CC6677", "#DDDDDD"

fig, axs = plt.subplots(2, 3, figsize=(S.FULL, 4.1), sharex="col")
for j, (rec, title) in enumerate(RECIPES):
    r3 = T.read_range3d(rec)
    depth = r3[:, 0]
    rb = RB[rec]
    xmax = 1.1 * max(np.percentile(depth, 99.9), rb["Rp_nm"] + 3 * rb["dRp_nm"])
    ax = axs[0, j]
    if rec.startswith("He"):
        for a in axs[:, j]:
            a.axvspan(220, 410, color=CAV, lw=0, zorder=0)
        ax.text(315, 0.97, "cavity layer", transform=ax.get_xaxis_transform(), ha="center",
                va="top", fontsize=7, color=S.INK)
    bins = np.linspace(0, xmax, 50)
    ax.hist(depth, bins=bins, density=True, histtype="stepfilled", color="#BBBBBB", lw=0)
    ax.hist(depth, bins=bins, density=True, histtype="step", color=SRIM_C, lw=0.9)
    top = ax.get_ylim()[1]
    yb = 0.12 * top
    ax.errorbar([depth.mean()], [yb * 2.2], xerr=[[depth.std()], [depth.std()]], fmt="o", color=SRIM_C,
                ms=3.5, capsize=2, lw=0.9, label="SRIM projected range, mean ± s.d.")
    ax.errorbar([rb["Rp_nm"]], [yb], xerr=[[rb["dRp_nm"]], [rb["dRp_nm"]]], fmt="s", color=RB_C,
                ms=3.5, capsize=2, lw=0.9, label="RustBCA projected range, mean ± s.d.")
    ax.set_ylim(0, top * 1.12)
    ax.set_yticks([])
    ax.set_title(title, fontsize=8)
    print(f"{rec}: SRIM Rp {depth.mean():.1f} nm (sd {depth.std():.1f}, n {len(depth)}); "
          f"RustBCA Rp {rb['Rp_nm']} nm (sd {rb['dRp_nm']})")
    ax = axs[1, j]
    d, v = T.read_vacancy(rec)
    ax.plot(d, v, color=SRIM_C, lw=1.1)
    ax.set_xlim(0, xmax)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("depth (nm)")
    print(f"   vacancy peak at {d[np.argmax(v)]:.0f} nm, {v.max():.3f} per angstrom per ion")
h, lab = axs[0, 0].get_legend_handles_labels()
fig.legend(h, lab, loc="outside lower center", ncol=2, handletextpad=0.3)
axs[0, 0].set_ylabel("stopped ions\n(normalised)")
axs[1, 0].set_ylabel("vacancies per Å per ion")
for k, a in zip("abcdef", axs.flat):
    a.text(-0.02, 1.02, f"({k})", transform=a.transAxes, fontweight="bold", fontsize=9, va="bottom",
           ha="right")
S.save(fig, "fig_implant")
