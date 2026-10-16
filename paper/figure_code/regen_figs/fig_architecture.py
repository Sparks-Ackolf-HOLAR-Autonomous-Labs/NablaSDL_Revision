"""Fig. (fig:arch): the decision pipeline from evidence to revised law.

Pure diagram, no data. Stage names match Algorithm 1 and the decision-trace
table in draft.tex; each stage carries one SiGe example from the campaign
(italic line), taken from the main text. Drawn at full journal width (S.FULL)
in inch coordinates so every label prints at 7 pt or larger.
"""
import paper_fig_style as S
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

S.apply_style()

EVID, SHARD, CTRL, LEDG = "#DCE8F4", "#F8E4D0", "#E3EFDA", "#ECECEC"
W, H = S.FULL, 4.62

fig = plt.figure(figsize=(W, H), layout="none")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")


def box(x, y, w, h, title, body, example, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=fc, ec=S.INK, lw=0.7))
    ax.text(x + w / 2, y + h - 0.07, title, ha="center", va="top", fontsize=8,
            fontweight="bold", color=S.INK)
    ax.text(x + w / 2, y + h - 0.28, body, ha="center", va="top", fontsize=7,
            color=S.INK, linespacing=1.15)
    if example:
        ax.text(x + w / 2, y + 0.06, example, ha="center", va="bottom", fontsize=7,
                style="italic", color="#1F4E79", linespacing=1.15)


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
strip(4.16, 0.42, "Explore-exploit-revise controller: explore or exploit over composition, temperature and "
      "microstructure;\nin revision mode it runs the experiments that answer the most pressing revision question", CTRL)

# evidence row: five boxes
n, gap, x0 = 5, 0.18, 0.04
bw = (W - 0.08 - gap * (n - 1)) / n
ytop, bh = 2.50, 1.50
ev = [("Evidence sources", "published values\nTersoff MD, MACE MD\nDFT phonon BTE\nexperimental\ndatabases",
       "e.g. 935 SiGe\nconductivity values"),
      ("E1 Ingest, screen", "tag source, method\nand sample; reject\nduplicates and values\nthat break a\nphysical bound",
       "e.g. MACE values\nwith a unit slip"),
      ("E2 Structure", "test for a hidden\nvariable before any\nfit; split the\nevidence if one\ndrives it",
       "e.g. literature split\ninto bulk, film, nano"),
      ("E3 Fit (HG-SR)", "one law per scope;\neach study votes once;\nrecord which evidence\nsupports each term",
       "e.g. SiGe alloy law\nwith four terms"),
      ("Claims", "law with its\nvalid range and\nthe sources it\nrests on",
       "e.g. law valid for\n0.05 ≤ x ≤ 0.90")]
evx = [x0 + i * (bw + gap) for i in range(n)]
for x, (t, b, e) in zip(evx, ev):
    box(x, ytop, bw, bh, t, b, e, EVID)
for i in range(n - 1):
    arrow((evx[i] + bw, ytop + bh / 2), (evx[i + 1], ytop + bh / 2))

# revision row: six boxes, right to left
m, sgap = 6, 0.14
sw = (W - 0.08 - sgap * (m - 1)) / m
ybot, sh = 0.62, 1.50
st = [("S1 Score", "rank claims by\nthe warning signs\nagainst them\n(residual, batch\noffset, coverage)",
       "e.g. two Ge-rich\npoints, x = 0.94,\nflagged"),
      ("S2 Design", "choose the\nlowest-cost test\nthat decides it,\nfrom a source\nother than the\nflagged batch",
       "e.g. fresh seeds\nand neighbours at\nx = 0.90, 0.97"),
      ("S3 Run", "run it; store\nthe raw files\nbefore reading\nthem",
       "e.g. 19 Tersoff\nMD runs"),
      ("S4 Decide", "the rule stated in\nadvance picks one\naction: keep, set\naside, limit range,\nsplit, correct\nor forget",
       "e.g. law limited\nto x ≤ 0.90"),
      ("S5 Verify", "the refit equals\na fit from scratch\non the revised\nevidence, bit\nfor bit",
       "e.g. forgetting\na biased source\nrestores the law"),
      ("S6 Learn", "log the outcome\nto improve the\nranking; keep the\nlesson with its\nsource",
       "e.g. new sources\nscreened on their\nfirst values")]
sx = [W - 0.04 - sw - i * (sw + sgap) for i in range(m)]
for x, (t, b, e) in zip(sx, st):
    box(x, ybot, sw, sh, t, b, e, SHARD)
for i in range(m - 1):
    arrow((sx[i], ybot + sh / 2), (sx[i + 1] + sw, ybot + sh / 2))

# vertical links
xr = W - 0.04 - min(bw, sw) / 2
arrow((xr, ytop), (xr, ybot + sh))           # claims -> score
xl = x0 + min(bw, sw) / 2
arrow((xl, ybot + sh), (xl, ytop))           # learn -> evidence
arrow((sx[4] + sw / 2, ybot + sh), (evx[3] + bw * 0.35, ytop), rad=-0.12, ls="--")  # verify -> refit
ax.text(2.75, 2.30, "revised evidence: exact refit", fontsize=7,
        style="italic", ha="center", va="center", color=S.INK,
        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none"))
xc = evx[3] - gap / 2
arrow((xc, 4.16), (xc, ybot + sh), ls=":")   # controller -> run
arrow((xl, 4.16), (xl, ytop + bh), ls=":")  # controller -> sources

# record strip (bottom), two lines so the text stays inside the box
strip(0.04, 0.44, "Campaign record, append-only, each entry linked to the one before it: plans and decision rules "
      "registered before runs,\nfingerprints of raw files taken before analysis, and every revision with "
      "its cause and evidence", LEDG)
for x in sx:
    ax.plot([x + sw / 2] * 2, [0.48, ybot], color=S.INK, lw=0.5, ls=":")

S.save(fig, "fig_architecture")
