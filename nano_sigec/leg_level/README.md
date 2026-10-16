# Leg-level reading of the SiGeC recipe (9 Oct 2026; post hoc)

`leg_level.py` (seconds, CPU) combines the 300 K and 1100 K picks, and the
500, 700, 900 K points the same model carries, into the quantity a
thermoelectric leg conducts. For a leg between a 300 K cold end and an
1100 K hot end the conductive heat leak is (A/L) times the integral of
kappa over temperature, so legs are ranked by the temperature-averaged
kappa_bar. Model: committed SiGeC kappa_L model, ledger-105 measured
small-SiC curve, effective grains 0.3 um. Derived reporting only; no campaign record
decision. Output `leg_level.json`.

| Result | Value |
|---|---|
| Best composition by temperature (3 at% C as 2.5 nm SiC) | x = 0.3 at 300 K; x = 0.5 from 500 K up |
| Best uniform leg, 300 to 1100 K | x = 0.5, kappa_bar 2.215 W/mK |
| x = 0.3 leg | 2.225 W/mK, 0.43 % more heat leak, 40 % less Ge than x = 0.5 |
| x = 0.2 leg | 10.4 % more heat leak |
| Graded leg (x = 0.3 cold segment, 0.5 elsewhere) | 0.05 % better than the best uniform leg |
| Ge saving at equal leg heat leak vs carbon-free Si0.8Ge0.2 | 15 % (1 at% C, 2.5 nm), 8 % (1 at%, 5 nm), 34 % (3 at%, 2.5 nm), 23 % (3 at%, 5 nm) |

Reading: the two single-temperature picks disagree, but at the level of
the device they describe the same flat valley. Composition anywhere in
x = 0.3 to 0.5 gives the same heat leak within half a percent, so the
choice inside that window belongs to criteria the kappa model does not
carry (Ge cost, power factor, processing). Grading the leg is not worth it
for kappa alone. Limits: lattice kappa only (no electronic part, no power
factor or ZT), fixed end temperatures, Peltier and Joule terms ignored.
