
#### Frozen detector (campaign record seq 5 + D1), pre-stated scoring A, raw

| id | entry | category | detected % | hit % | harmful % | miss % | other % | trials with collateral % | detection by severity Q1/Q2/Q3/Q4 |
|---|---|---|---|---|---|---|---|---|---|
| NULL | null campaign (no fault) | null | 0 | 100 | 0 | 0 | 0 | 100 | n/a |
| P01 | biased batch | planted-error | 92 | 52 | 0 | 8 | 40 | 86 | 0.71/1.00/1.00/1.00 |
| P02 | unit slip | planted-error | 100 | 64 | 0 | 0 | 36 | 80 | 1.00/1.00/1.00/1.00 |
| P03 | composition label swap | planted-error | 28 | 18 | 0 | 72 | 10 | 94 | 0.11/0.36/0.50/0.18 |
| P04 | species type swap (x -> 1-x) | planted-error | 40 | 18 | 0 | 60 | 22 | 88 | 0.47/0.60/0.17/0.25 |
| P05 | temperature label offset | planted-error | 78 | 48 | 0 | 22 | 30 | 74 | 0.73/0.67/0.92/0.79 |
| P06 | duplicated batch (double counting) | planted-error | 96 | 56 | 0 | 4 | 40 | 86 | 1.00/1.00/1.00/0.88 |
| P07 | unequilibrated long box | planted-error | 88 | 52 | 0 | 12 | 36 | 94 | 0.75/0.83/0.94/1.00 |
| P08 | party mislabel (MACE rows under CHPC-MD-C) | planted-error | 68 | 54 | 0 | 32 | 14 | 94 | 0.33/0.91/0.88/1.00 |
| M01 | near-solidus (premelting) regime | method-off-data | 20 | 0 | 0 | 80 | 20 | 100 | 0.11/0.08/0.31/0.27 |
| M02 | amorphous-phase contamination | method-off-data | 72 | 12 | 0 | 28 | 60 | 88 | 0.45/0.54/0.93/0.92 |
| M03 | dilute ballistic regime (1/L extrapolation invalid) | method-off-data | 44 | 20 | 0 | 56 | 24 | 98 | 0.00/0.20/0.64/1.00 |
| V01 | regime-localized extra scattering | valid-anomaly | 76 | 24 | 74 | 0 | 2 | 94 | 0.65/1.00/0.73/0.85 |
| V02 | high-T second scattering channel | valid-anomaly | 100 | 8 | 90 | 0 | 2 | 54 | 1.00/1.00/1.00/1.00 |
| V03 | composition asymmetry | valid-anomaly | 100 | 0 | 100 | 0 | 0 | 2 | 1.00/1.00/1.00/1.00 |

#### Post-hoc variant D2 (design-coordinate duplicate key), baseline-adjusted (clean-campaign fires not attributed)

| id | entry | category | detected % | hit % | harmful % | miss % | other % | trials with collateral % | detection by severity Q1/Q2/Q3/Q4 |
|---|---|---|---|---|---|---|---|---|---|
| NULL | null campaign (no fault) | null | 0 | 100 | 0 | 0 | 0 | 4 | n/a |
| P01 | biased batch | planted-error | 80 | 80 | 0 | 20 | 0 | 6 | 0.71/1.00/1.00/1.00 |
| P02 | unit slip | planted-error | 100 | 100 | 0 | 0 | 0 | 2 | 1.00/1.00/1.00/1.00 |
| P03 | composition label swap | planted-error | 16 | 12 | 0 | 84 | 4 | 8 | 0.22/0.29/0.40/0.12 |
| P04 | species type swap (x -> 1-x) | planted-error | 0 | 0 | 0 | 100 | 0 | 4 | 0.40/0.33/0.00/0.00 |
| P05 | temperature label offset | planted-error | 32 | 14 | 0 | 68 | 18 | 14 | 0.73/0.25/0.69/0.79 |
| P06 | duplicated batch (double counting) | planted-error | 90 | 50 | 0 | 10 | 40 | 12 | 1.00/1.00/0.93/0.75 |
| P07 | unequilibrated long box | planted-error | 56 | 56 | 0 | 44 | 0 | 4 | 0.75/0.83/0.94/1.00 |
| P08 | party mislabel (MACE rows under CHPC-MD-C) | planted-error | 56 | 54 | 0 | 44 | 2 | 10 | 0.33/0.82/0.88/1.00 |
| M01 | near-solidus (premelting) regime | method-off-data | 10 | 0 | 0 | 90 | 10 | 82 | 0.00/0.00/0.15/0.20 |
| M02 | amorphous-phase contamination | method-off-data | 38 | 0 | 0 | 62 | 38 | 10 | 0.09/0.23/0.93/0.83 |
| M03 | dilute ballistic regime (1/L extrapolation invalid) | method-off-data | 40 | 20 | 0 | 60 | 20 | 70 | 0.00/0.00/0.64/1.00 |
| V01 | regime-localized extra scattering | valid-anomaly | 46 | 54 | 44 | 0 | 2 | 60 | 0.53/0.80/0.33/0.46 |
| V02 | high-T second scattering channel | valid-anomaly | 18 | 82 | 0 | 0 | 18 | 0 | 1.00/1.00/1.00/1.00 |
| V03 | composition asymmetry | valid-anomaly | 0 | 100 | 0 | 0 | 0 | 0 | 1.00/1.00/1.00/1.00 |
