# Bond angle distributions (2026-10-01)

Question: what do the bond angle distributions show? The earlier structure
figures (P1 Figs. 6 and 7) show bond lengths only. This
folder measures the bond angle distribution (BAD) on three structure sets.
Not a registered study; no campaign-record entry; no CHPC or GPU time.

| File | What it is |
|---|---|
| `md/in.struct`, `md/run_struct.sh` | Tersoff Si-Ge rebuilds of the Phase C production probes and matching crystal rows (same cell, seed, potential and preparation as `phase_c/production/in.mp_amorph` / `chpc/in.mp_kappa2`), then 10 ps NVT with a dump every ps; DGX CPU, 12 runs, 25 min wall |
| `md/*.dump.gz`, `md/*.log` | snapshots (11 per run) and LAMMPS logs |
| `analyze_bad.py` | angles j-i-k over first-shell neighbours (cutoff 2.95 A for Tersoff, 2.75 A for MACE); per-frame and pooled descriptors |
| `radial_profile.py` | angle spread against distance from each embedded SiC particle centre |
| `bad_results.json` | all numbers (histograms in 1 degree bins) |
| `make_bad_figure.py`, `fig_bond_angles.{png,pdf}` | four-panel figure |

The probe rows are rebuilt on a different machine and rank count, so the atoms
are not the same as in the CHPC runs; the preparation is the same.

## Findings

**1. One angle number separates the amorphous rows that the fault detector
missed.** Spread (s.d.) of all bond angles per snapshot, 2 seeds x 11 frames:

| Row | s.d. (deg) | angles outside 109.5 +/- 20 deg | 5-fold sites | angles below 80 deg |
|---|---|---|---|---|
| crystal x = 0.5, 300 K | 2.9 | 0 | 0 | 0 |
| crystal x = 0.5, 700 K | 4.3 | 0 | 0 | 0 |
| near-melting probe x = 0.7, 1450 K | 6.3 | 0.2% | 0 | 0 |
| near-melting probe x = 0.5, 1500 K | 6.5 | 0.3% | 0 | 0 |
| amorphous probe x = 0.5, 300 K | 16.6-16.8 | 19-19.4% | 18% | 4.4-4.5% |
| amorphous probe x = 0.5, 700 K | 17.0-17.3 | 20-21% | 17-19% | 4.4-4.7% |

No snapshot falls between 7 and 16 deg, so the gap is about 2.5 times the
largest crystal value. In the production fault study (`phase_c/production/FAULT_STUDY.md`)
the amorphous rows N2 and N3 entered the law as low-kappa alloy points
because the detector saw only kappa, composition, temperature and box length;
the FAULT_STUDY follow-up asked for a structural descriptor. Angle spread is
that descriptor, and unlike energy per atom it needs no composition-dependent
reference energy. It also says what it cannot do: the near-melting rows are
still tetrahedral crystals at 1450-1500 K (Tersoff superheats the crystal), so
structure cannot flag them and the solidus guard stays the right tool.

The amorphous structure itself carries a known empirical-potential feature:
18% of sites are 5-fold coordinated, with the matching small peak near 60 deg
and shoulder near 75 deg. That is method off-data for any amorphous row and
belongs on its scope label.

**2. Around substitutional carbon the distortion is angular, on the Si
neighbours.** MACE-MP-0 cells (`nano_sigec/structures/cif`):

| Cell, centre | mean (deg) | s.d. (deg) |
|---|---|---|
| Si0.8Ge0.2, no C, all sites | 109.46 | 1.0 |
| Si0.8Ge0.2 + 4 C, angles at C | 109.46 | 1.5 |
| Si0.8Ge0.2 + 4 C, angles at Si bonded to C | 108.98 | 8.3 (two groups near 101 and 117 deg) |
| Si0.5Ge0.5 + 4 C, angles at C | 112.77 | 5.3 |
| Si0.5Ge0.5 + 4 C, angles at Si bonded to C | 109.0 | 8.3 |

Si/Ge size mismatch alone bends angles by about 1 deg. A carbon site keeps
its own tetrahedron (four equally shortened Si-C bonds, -16% in Fig. 7), so
the 16% bond contraction is absorbed by bending at the next atom out: the
angles at each Si bonded to C split by about 8 deg. In the Ge-richer host the
C tetrahedron itself opens (mean 112.8 deg) because its neighbours are no
longer all alike. Bond bending is the soft deformation of the diamond
lattice, so the strain field that scatters phonons around substitutional C is
mostly angular; this supports treating the strain term for substitutional C
as an upper bound rather than a mass-only term, and it is a second reason
(next to the 1.4-1.7 eV MACE energy) for carbon to leave the lattice.

**3. A nominal 2 nm SiC particle is mostly interface.** Tersoff x = 0.3 box
with two R = 2 nm 3C-SiC particles (the rebuilt particle geometry, 0 K
minimised):

- crystalline 3C-SiC (angle s.d. below 0.1 deg) only out to r = 1.45 nm;
- a disordered band from r = 1.5 to 2.3 nm, peak s.d. 32 deg at the
  nominal surface, where 57% of angles leave the tetrahedral window and the
  mean coordination reaches 5.2;
- the Si0.7Ge0.3 host is crystalline again 0.3 nm outside the surface.

By volume, about 62% of the nominal particle lies outside the crystalline
core. The continuum scattering model treats a particle as a crystalline
sphere with one density or stiffness contrast against the host. At R = 2 nm
that picture describes less than half the particle, which is a plausible
(untested) reason the 2 nm MD point sat below the model's density edge
(campaign-record entries 60-61), and it predicts an effective contrast that depends on
particle size. The band thickness (about 0.8 nm) is set by the 20% SiC/SiGe
lattice mismatch under Tersoff and by a minimisation that stopped at its
iteration cap, so its width is method-dependent; a MACE relaxation of a
smaller particle would test it.

## What this adds to the method (P1-P3)

- Structure-level descriptors (angle spread, coordination) are a cheap
  entry check for MD evidence: one more physical bound of the kind the
  pipeline already applies at entry (E1), here for phase identity.
- For the SiGeC example, angles turn "C contracts its bonds" into "C bends
  its neighbours" and turn "SiC particle" into "crystalline core plus a
  disordered shell", both of which change how the scattering inputs should
  be labelled.

Not done: no pre-registered detector version uses the descriptor yet, and
none of the paper drafts include this figure.
