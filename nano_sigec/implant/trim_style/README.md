# TRIM-style diagrams from the saved implant outputs (2026-10-12)

Two options were produced for SRIM/TRIM pictures (2026-10-12). This folder is
option 1: diagrams drawn from the SRIM text outputs
already in `../srim_raw/`, with no SRIM rerun. Option 2 (the TRIM program's own
plot window) is in `../trim_gui/`.

## Figures

| File | What it shows |
|---|---|
| `fig_trimstyle_<recipe>.png/.pdf` | four panels for each of the four recipes with a RustBCA cross-check: (a) RustBCA ion paths with the Si and Ge recoil cascades, side view; (b) SRIM final ion positions, side view, every stopped ion; (c) stopped-ion depth profile from both codes; (d) SRIM vacancies per angstrom per ion (ions plus recoils, Kinchin-Pease estimate) |
| `fig_srim_final_positions_all.png/.pdf` | SRIM final ion positions, side view, for all 13 recipes |
| `trimstyle_stats.json` | mean range and straggle from both codes, read from the same files the figures use |

Panel (a) is the RustBCA counterpart of the TRIM plot window. SRIM's batch runs
used quick Kinchin-Pease damage with no collision file, so SRIM itself has no
saved paths; RustBCA records every ion and recoil path when asked.

## How the numbers tie back

The 20 000-ion RustBCA range runs here use the committed inputs in
`../rustbca_run/` unchanged and reproduce `../rustbca_ranges.json` exactly
(Rp 126.0, 352.3, 388.5 and 286.5 nm). The SRIM Rp values read from
`RANGE_3D.txt` match the "Ion Average Range" line of each `RANGE.txt`
(for example 113.9 nm for C at 40 keV into Si0.8Ge0.2).

| Recipe | SRIM Rp / dRp (nm) | RustBCA Rp / dRp (nm) |
|---|---|---|
| C 40 keV into Si0.8Ge0.2 | 113.9 / 43.9 | 126.0 / 51.1 |
| He 40 keV into Si0.8Ge0.2 | 314.8 / 95.9 | 352.3 / 110.9 |
| He 40 keV into Si | 351.9 / 96.0 | 388.5 / 105.2 |
| Kr 500 keV into Si | 299.1 / 86.2 | 286.5 / 81.2 |

Same pattern as the G0 gate in `../README.md`: RustBCA puts light ions about
10% deeper, and the two codes agree within about 4% for the heavy ion.

## Track runs

`run_rustbca_tracks.sh` makes the track inputs from the committed ones by
changing only the ion count (100 ions; 10 for Kr, whose cascades are dense)
and the three `track_*` switches. Recoils are followed down to the committed
1 eV cutoff, which is why the cascades look denser than in a TRIM window.
The track files (650 MB) are kept in a scratch directory and are not
committed; rerun the script to regenerate them (about 40 s on 4 threads).

```
./run_rustbca_tracks.sh ~/tools/RustBCA/target/release/RustBCA ~/mat_theory_trimstyle
python3 make_trim_style.py ~/mat_theory_trimstyle   # needs numpy + matplotlib
```
