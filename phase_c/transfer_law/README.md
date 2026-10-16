# A1 prototype: a symbolic transfer law between evidence parties (2026-09-29)

Improvement plan item A1 (`../../papers/notes/04_improvement_plan_2026-09-29.md`).
The screening demo's biggest single mover was the hand-built BTE-DFT
calibration of the Tersoff-parented law. Here that calibration becomes a
fitted, revisable object: `transfer_law.py` searches exhaustively (up to
three terms plus intercept) for ln r(x, T), r = kappa_BTE-DFT / kappa_law,
over the 11 BTE nodes inside the law's validity domain, scored by
leave-one-node-out CV. Deterministic, so dropping a node reproduces a
from-scratch refit exactly (the same exact-revision property as HG-SR).

## Result

Selected: **ln r = 1.042 + 2.061 x(1-x) - 0.915 x (T/1000)**, LOO RMSE
0.062 in ln r (about 6%). Read as physics: the Tersoff alloy suppression
is a factor exp(1.04) = 2.8 at the dilute ends, grows to about 4.7 at
mid-composition (the x(1-x) mass-disorder term, so Tersoff under-counts
something that scales with alloy disorder), and shrinks with temperature
on the Ge-rich side.

Screening decision (minimum lattice kappa), symbolic transfer vs the
screening demo's interpolated calibration:

| T (K) | symbolic: argmin x, kappa_min, window | interpolated: argmin x, kappa_min, window |
|---|---|---|
| 300 | 0.42, 6.48 W/mK, 0.20-0.65 | 0.395, 6.25 W/mK, 0.24-0.69 |
| 700 | 0.55, 5.15 W/mK, 0.29-0.73 | 0.60, 4.88 W/mK, 0.27-0.73 |
| 1100 | 0.645, 3.93 W/mK, 0.42-0.77 | 0.43, 4.24 W/mK, 0.26-0.60 |

**The finding is the 1100 K disagreement.** At 1100 K there is no BTE node
above x = 0.5 inside the domain (x = 0.85 at 1100 K exceeds 0.85 of the
solidus), so on the Ge-rich side the interpolated calibration is flat by
construction and the symbolic law extrapolates its x t term. The two
reasonable calibrations put the optimum 0.2 apart in x. The answer there
rests on no first-principles evidence at all, which is exactly what the
autonomous loop (A2) should detect and buy: one almaBTE point at x = 0.7,
1100 K (about one guest-CPU hour) decides it. Per-node provenance
(`node_provenance_max_coef_shift` in `transfer_law_results.json`) shows
the x = 0.5, 1100 K node moves the coefficients most (0.19), so it is the
single-point dependency to protect.

Not yet done: campaign record integration (a `re-anchor` shard operation), the
same object for the MACE and literature-bulk parties, and bootstrap CIs.
