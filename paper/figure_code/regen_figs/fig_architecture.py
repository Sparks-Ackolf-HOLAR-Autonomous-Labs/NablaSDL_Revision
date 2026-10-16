"""Fig. (fig:arch): the decision pipeline from evidence to revised law.

Pure diagram, no data. Stage names match Algorithm 1 and the decision-trace
table in draft.tex. Drawn at full journal width (S.FULL) in inch coordinates
so every label prints at 7 pt or larger.
"""
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

S.apply_style()

EVID, SHARD, CTRL, LEDG = "#DCE8F4", "#F8E4D0", "#E3EFDA", "#ECECEC"
W, H = S.FULL, 3.90

fig = plt.figure(figsize=(W, H), layout="none")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")


def box(x, y, w, h, title, body, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=fc, ec=S.INK, lw=0.7))
    ax.text(x + w / 2, y + h - 0.08, title, ha="center", va="top", fontsize=8,
            fontweight="bold", color=S.INK)
    ax.text(x + w / 2, y + h - 0.32, body, ha="center", va="top", fontsize=7,
            color=S.INK, linespacing=1.2)


def arrow(p, q, rad=0.0, ls="-"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, lw=0.8,
                                 color=S.INK, connectionstyle=f"arc3,rad={rad}",
                                 linestyle=ls, shrinkA=0, shrinkB=0))


def strip(y, h, text, fc):
    ax.add_patch(FancyBboxPatch((0.04, y), W - 0.08, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=fc, ec=S.INK, lw=0.7))
    ax.text(W / 2, y + h / 2, text, ha="center", va="center", fontsize=7, color=S.INK,
            linespacing=1.2)


# controller strip (top)
strip(3.44, 0.42, "Explore-exploit-revise controller: explore or exploit over composition, temperature and "
      "microstructure;\nrevision mode runs the experiments that answer the top revision question", CTRL)

# evidence row: five boxes
n, gap, x0 = 5, 0.18, 0.04
bw = (W - 0.08 - gap * (n - 1)) / n
ytop, bh = 2.06, 1.24
ev = [("Evidence sources", "published values\n(machine-read)\nTersoff MD\nMACE-MP MD\nDFT phonon BTE\ndatabases"),
      ("E1 Ingest, screen", "provenance tags\ncross-source bounds\nduplicate check\nagainst source DOI\nphysics guards"),
      ("E2 Structure", "calibrated on planted\ncases first; names\nthe dominant driver,\nthen splits the scope\nor not"),
      ("E3 Fit (HG-SR)", "per scope, balanced\nover hyperedges;\nexact refit; term\nprovenance and\nreach of a revision"),
      ("Claims", "law with its\nvalidity domain\nand scope labels")]
evx = [x0 + i * (bw + gap) for i in range(n)]
for x, (t, b) in zip(evx, ev):
    box(x, ytop, bw, bh, t, b, EVID)
for i in range(n - 1):
    arrow((evx[i] + bw, ytop + bh / 2), (evx[i + 1], ytop + bh / 2))

# shard row: six boxes, right to left
m, sgap = 6, 0.14
sw = (W - 0.08 - sgap * (m - 1)) / m
ybot, sh = 0.54, 1.00
st = [("S1 Score", "red flags give\nthe priority R(c)"),
      ("S2 Design", "lowest-cost\ndecisive test\nor defer; a\nbatch cannot\nclear itself"),
      ("S3 Run", "run; commit raw\nfile hashes\nbefore analysis"),
      ("S4 Decide", "two-bar triage\nselects one of\nnine actions"),
      ("S5 Verify", "refit equals a\nclean retrain;\nbitwise check;\nrecord chain"),
      ("S6 Learn", "outcome label\nfor R(c); lesson\nwith provenance")]
sx = [W - 0.04 - sw - i * (sw + sgap) for i in range(m)]
for x, (t, b) in zip(sx, st):
    box(x, ybot, sw, sh, t, b, SHARD)
for i in range(m - 1):
    arrow((sx[i], ybot + sh / 2), (sx[i + 1] + sw, ybot + sh / 2))

# vertical links
xr = W - 0.04 - min(bw, sw) / 2
arrow((xr, ytop), (xr, ybot + sh))           # claims -> score
xl = x0 + min(bw, sw) / 2
arrow((xl, ybot + sh), (xl, ytop))           # learn -> evidence
arrow((sx[4] + sw / 2, ybot + sh), (evx[3] + bw * 0.35, ytop), rad=-0.12, ls="--")  # verify -> refit
ax.text(2.75, 1.80, "revised evidence state: exact refit", fontsize=7,
        style="italic", ha="center", va="center", color=S.INK,
        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))
xc = evx[3] - gap / 2
arrow((xc, 3.44), (xc, ybot + sh), ls=":")   # controller -> run
arrow((xl, 3.44), (xl, ytop + bh), ls=":")  # controller -> sources

# ledger strip (bottom)
strip(0.04, 0.36, "Append-only hash-chained campaign record: pre-registrations, batch Merkle roots, and every "
      "revision action with its cause and evidence", LEDG)
for x in sx:
    ax.plot([x + sw / 2] * 2, [0.40, ybot], color=S.INK, lw=0.5, ls=":")

S.save(fig, "fig_architecture")
