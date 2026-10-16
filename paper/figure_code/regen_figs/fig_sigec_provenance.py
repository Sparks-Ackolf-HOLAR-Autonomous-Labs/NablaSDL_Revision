"""Fig. (fig:provenance): provenance and blast radius of the SiGeC conclusion.

Linear hypergraph drawing: rows are vertices (five evidence groups, then two
derived claims); each column is one hyperedge, drawn as a shaded region that
spans every member vertex, labelled with the claim it supports. Filled dot:
the claim depends on that member; hollow dot: the member is present but the
claim is insensitive to it. Schematic: the membership, sensitivities and the
quoted numbers are those of the earlier make_sigec_story_figs.py
(fig_provenance), which quotes nano_sigec RESULTS.md. Full journal width.
"""
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

S.apply_style()
SC = S.SOURCE_COLOURS
W, H = S.FULL, 2.62

fig = plt.figure(figsize=(W, H), layout="none")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

rows = [  # key, label, colour
    ("mace", "MACE-MP-0: 51 converged relaxations", SC["mace_md"]),
    ("exp", "Zhao et al., Lu et al.: sintered SiGe with C", SC["literature"]),
    ("bte", "DFT phonon BTE: 9 compositions, 5 temperatures", SC["bte_dft"]),
    ("star", "Starrydata2: sintered Si$_{0.8}$Ge$_{0.2}$ records", SC["starrydata"]),
    ("model", "SiC scattering model (contrast bracket)", S.INK),
    ("C1", "C1: carbon ends as SiC in Si-rich pockets", S.GREY),
    ("C2", "C2: sintered SiGe acts as 0.1 to 0.9 μm grains", S.GREY),
]
y0, dy = 2.25, 0.335
ys = {k: y0 - i * dy for i, (k, _, _) in enumerate(rows)}
xl, xr = 2.72, 4.46          # extent of the row guide lines
for k, lab, c in rows:
    y = ys[k]
    ax.plot([xl, xr], [y, y], color=S.LIGHT, lw=0.8, zorder=0)
    ax.add_patch(Rectangle((0.03, y - 0.09), 0.05, 0.18, fc=c, ec="none"))
    ax.text(0.13, y, lab, va="center", fontsize=7, color=S.INK)
ax.plot([0.03, xr], [ys["C1"] + dy / 2] * 2, color=S.GREY, lw=0.6, ls=":")

# hyperedges: column x, {member: claim depends on it?}
H_EDGES = [("C1", 2.92, {"mace": 1, "exp": 1}),
           ("C2", 3.36, {"bte": 1, "star": 1}),
           ("C3", 3.80, {"bte": 1, "model": 0, "C1": 1, "C2": 1}),
           ("C4", 4.24, {"bte": 1, "model": 1, "C1": 1, "C2": 1})]
colour = {k: c for k, _, c in rows}
for name, x, mem in H_EDGES:
    yy = [ys[m] for m in mem]
    ax.add_patch(FancyBboxPatch((x - 0.1, min(yy) - 0.12), 0.2, max(yy) - min(yy) + 0.24,
                                boxstyle="round,pad=0,rounding_size=0.08",
                                fc="#E4E4E4", ec=S.INK, lw=0.7, zorder=1))
    for m, dep in mem.items():
        ax.scatter([x], [ys[m]], s=30, c=[colour[m] if dep else "white"], edgecolors=[colour[m]],
                   linewidths=1.2, zorder=3)
    ax.text(x, y0 + 0.24, name, ha="center", va="bottom", fontsize=8, weight="bold", color=S.INK)

# what each derived claim says (right-hand side)
xt = 4.6
ax.text(xt, (ys["mace"] + ys["exp"]) / 2,
        "C3: SiC with R ≥ 10 nm lowers $\\kappa_L$ by at\nmost 11% per at% C; the drop reported by\n"
        "Zhao et al. is not from SiC (C3 does not\ndepend on the bracket)",
        fontsize=7, color=S.INK, va="center", linespacing=1.2)
ax.text(xt, ys["bte"] - 0.12, "C4: few-nm SiC lowers $\\kappa_L$ by 13 to 27%\nper at% C "
        "(depends on the bracket)", fontsize=7, color=S.INK, va="center", linespacing=1.2)
ax.text(xt, ys["model"] - 0.02, "Revising the bracket changes C4 and the\nsize of the Ge "
        "saving; C1 to C3 stand", fontsize=7, color=S.INK, va="center", linespacing=1.2,
        style="italic")
ax.add_patch(FancyBboxPatch((xt, ys["C2"] - 0.17), 2.08, 0.42, boxstyle="round,pad=0,rounding_size=0.05",
                            fc="white", ec=S.INK, lw=0.8))
ax.text(xt + 1.04, ys["C2"] + 0.04, "Ge saving (C3, C4), pre-check:\n27 to 51% less Ge at equal $\\kappa_L$",
        ha="center", va="center", fontsize=7, weight="bold", color=S.INK, linespacing=1.2)

# blast radius of revising the bracket: dashed outline around its row
ax.add_patch(Rectangle((0.01, ys["model"] - 0.15), xr - 0.01 + 0.06, 0.30, fc="none", ec=S.INK,
                       lw=0.9, ls="--", zorder=4))

S.save(fig, "fig_sigec_provenance")
