# First autonomous acquisition: almaBTE x = 0.7 (2026-09-29)

Run 2026-09-29. Improvement-plan item A2, first
real instance: the engine noticed that its 1100 K screening answer rested
on no first-principles evidence, priced the one point that would decide
it, and bought it.

## Order of events (all on `../ledger_campaign.jsonl`)

| seq | what | commit |
|---|---|---|
| 34 | design, both calibrations' predictions, decision rules D1 to D4 and a sanity gate, hashed (`acquisition_design.json`, sha `cb7d656c`) | `736b0ce` (pushed before submission) |
| n/a | decision script `decide_acquisition.py` written and pushed | `34b0026` (before the result existed) |
| 35 | raw almaBTE outputs (`raw/`, `../../party4_bte/results/bte_x0.7_T*.json`) Merkle-committed | `55a303a` (before the rule was applied) |
| 36 to 38 | shard operations from the rule: strengthen, downweight, re-anchor | this commit |

Run: CHPC job 15891220 on notchpeak-guest (owner-guest), 28 min on one
core, protocol identical to the 18 party-4a points (VCA + mass disorder,
24^3 grid, full iterative BTE). grn061 untouched.

## Result

| T (K) | kappa_BTE observed | predicted, symbolic transfer | predicted, interpolated calibration |
|---|---|---|---|
| 300 | 8.21 | 7.55 | 6.93 |
| 700 | 6.03 | 5.46 | 5.14 |
| 1100 | **4.95** | 3.97 | 5.53 |

- **D1 (which calibration wins at 1100 K):** the interpolated calibration
  (|ln error| 0.110 vs 0.222). The symbolic transfer law had extrapolated
  a composition-temperature cross term (x T) into a region with no
  first-principles node, and that term was wrong. It is downweighted
  (archived, not forgotten); the interpolated calibration is strengthened.
- **Sanity gate:** passed (4.95 inside the pre-registered neighbour bracket).
- **D2 (refit with the three new in-domain nodes, same basis and rule):**
  the selected transfer law changes form, from
  `ln r = 1.04 + 2.06 x(1-x) - 0.92 x t` to
  `ln r = 1.29 - 0.48 x + 1.93 x(1-x) - 0.37 t` (t = T/1000; LOO RMSE
  0.076, about 8%). The cross term is gone; the mass-disorder term x(1-x)
  is stable across the refit, which is the physically expected part.
- **D3 (screening verdict at 1100 K):** the refit puts the lowest-kappa
  composition at x = 0.505 (kappa_min 4.42 W/mK, 5% window x = 0.24 to
  0.715). Neither pre-acquisition answer (0.645 symbolic, 0.43
  interpolated) is within 0.05, so by the pre-registered rule **both are
  refuted**. In materials terms: the 0.2 disagreement in x collapses to
  0.075, the minimum is shallow and sits near mid-composition at all three
  temperatures (0.49 / 0.495 / 0.505), and the Ge-rich optimum the old
  symbolic law suggested at 1100 K was an artifact of extrapolation.

## Why it matters for the papers

This is the first acquisition the engine chose for itself for a reason it
could state (a decision resting on no first-principles node, with a 39%
prediction gap between two defensible calibrations), priced (one guest
CPU-hour), pre-registered and closed without human judgement in the loop.
It also shows the value of acquisition over model choice: neither
candidate calibration was right; one datapoint changed the law's form.

Files: `acquisition_design.json`, `PREREGISTERED_SHA256`,
`design_acquisition.py`, `preregister.py`, `decide_acquisition.py`,
`decision.json`, `transfer_law_refit.json`, `raw/` (+ `SHA256SUMS`).
