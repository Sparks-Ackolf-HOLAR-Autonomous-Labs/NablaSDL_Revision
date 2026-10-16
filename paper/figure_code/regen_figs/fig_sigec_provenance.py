"""Fig. (fig:provenance): provenance and reach of revision of the SiGeC conclusion.

Linear hypergraph drawing: rows are vertices (five evidence groups, then two
derived claims C1 and C2); each column is one hyperedge (support set 1 to 4),
drawn as a shaded region that spans every member vertex; the head above each
column names the claim the set supports. Filled dot: the claim depends on that
member; hollow dot: the member is present but the claim is insensitive to it.
Schematic: the membership, sensitivities and the quoted numbers are those of
the earlier make_sigec_story_figs.py (fig_provenance), which quotes
nano_sigec RESULTS.md; the Ge saving after the first atomistic check (27 to
33%) and after the radius checks (16% at 2.5 nm, 300 K) are the values of the
main text and the ESI table of contrast dependence (tab:contrast). Full journal width.
"""
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

S.apply_style()
SC = S.SOURCE_COLOURS
W, H = S.FULL, 2.95

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
    ("C1", "claim C1: carbon ends as SiC in Si-rich pockets", S.GREY),
    ("C2", "claim C2: sintered SiGe as 0.1 to 0.9 μm grains", S.GREY),
]
y0, dy = 2.33, 0.335
ys = {k: y0 - i * dy for i, (k, _, _) in enumerate(rows)}
xl, xr = 2.82, 4.50          # extent of the row guide lines
for k, lab, c in rows:
    y = ys[k]
    ax.plot([xl, xr], [y, y], color=S.LIGHT, lw=0.8, zorder=0)
    ax.add_patch(Rectangle((0.03, y - 0.09), 0.05, 0.18, fc=c, ec="none"))
    ax.text(0.13, y, lab, va="center", fontsize=7, color=S.INK)
ax.plot([0.03, xr], [ys["C1"] + dy / 2] * 2, color=S.GREY, lw=0.6, ls=":")

# hyperedges: support-set number, column x, claim supported, {member: claim depends on it?}
H_EDGES = [(1, 3.00, "C1", {"mace": 1, "exp": 1}),
           (2, 3.42, "C2", {"bte": 1, "star": 1}),
           (3, 3.84, "C3", {"bte": 1, "model": 0, "C1": 1, "C2": 1}),
           (4, 4.26, "C4", {"bte": 1, "model": 1, "C1": 1, "C2": 1})]
colour = {k: c for k, _, c in rows}
ax.text(xl - 0.05, y0 + 0.40, "support set", ha="right", va="center", fontsize=7, color=S.INK)
ax.text(xl - 0.05, y0 + 0.22, "supports", ha="right", va="center", fontsize=7, color=S.INK)
for num, x, claim, mem in H_EDGES:
    yy = [ys[m] for m in mem]
    ax.add_patch(FancyBboxPatch((x - 0.1, min(yy) - 0.12), 0.2, max(yy) - min(yy) + 0.24,
                                boxstyle="round,pad=0,rounding_size=0.08",
                                fc="#E4E4E4", ec=S.INK, lw=0.7, zorder=1))
    for m, dep in mem.items():
        ax.scatter([x], [ys[m]], s=30, c=[colour[m] if dep else "white"], edgecolors=[colour[m]],
                   linewidths=1.2, zorder=3)
    ax.text(x, y0 + 0.40, str(num), ha="center", va="center", fontsize=7, color=S.INK)
    ax.text(x, y0 + 0.22, claim, ha="center", va="center", fontsize=8, weight="bold", color=S.INK)

# what the two end claims say (right-hand side, one line each)
xt = 4.66
ax.text(xt, ys["exp"], "C3: SiC, R ≥ 10 nm: ≤ 11% per at% C", fontsize=7, color=S.INK, va="center")
ax.text(xt, ys["bte"], "C4: few-nm SiC: 13 to 27% per at% C", fontsize=7, color=S.INK, va="center")
ax.text(xt, ys["model"], "revising the bracket reaches C4 only", fontsize=7, color=S.INK,
        va="center", style="italic")

# Ge saving before and after the checks
bx, bw, bt, bb = xt, 2.03, ys["C1"] + 0.17, ys["C2"] - 0.22
ax.add_patch(FancyBboxPatch((bx, bb), bw, bt - bb, boxstyle="round,pad=0,rounding_size=0.05",
                            fc="white", ec=S.INK, lw=0.8))
ax.text(bx + bw / 2, bt - 0.07, "Ge saving at equal $\\kappa_L$ (C3, C4)", ha="center", va="top",
        fontsize=7, weight="bold", color=S.INK)
for i, (when, val) in enumerate((("before the check", "27 to 51%"), ("after the first check", "27 to 33%"),
                                 ("after the radius checks", "16%"))):
    yv = bt - 0.29 - i * 0.15
    ax.text(bx + 0.08, yv, when, ha="left", va="center", fontsize=7, color=S.INK)
    ax.text(bx + bw - 0.08, yv, val, ha="right", va="center", fontsize=7, color=S.INK, weight="bold")

# reach of revising the bracket: dashed outline around its row
ax.add_patch(Rectangle((0.01, ys["model"] - 0.15), xr - 0.01 + 0.06, 0.30, fc="none", ec=S.INK,
                       lw=0.9, ls="--", zorder=4))

S.save(fig, "fig_sigec_provenance")
