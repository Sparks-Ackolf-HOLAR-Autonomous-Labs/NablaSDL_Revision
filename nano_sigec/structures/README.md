# SiGeC crystal structures (CIF) for the P1 figure

Built 2026-10-01 for the structure figure
`papers/paper1_j_mater_chem_a/figures/fig_sigec_structures.*`
(`make_structure_figure.py`). Nothing here is new evidence: no campaign record
entry, no conclusion depends on it.

## `cif/`: MACE-MP-0 cells, reproduced from the committed CHPC runs

`rebuild_cif.py` imports the builder and settings of
`../m1c/chpc/mace_relax_m1c.py` (seeded Ge and C placement, MACE-MP-0
medium float64, FIRE then LBFGS on a hydrostatic cell filter), re-relaxes
8 of the 51 M1c cells on the DGX CPU (4 threads, 12 min in total), and writes `<task>_built.cif`
(ideal sites, Vegard cell) and `<task>_relaxed.cif`.

| check | result |
|---|---|
| energy vs CHPC (x86, 16 cores) | largest difference 1e-12 meV/atom |
| lattice parameter vs CHPC | largest difference 5e-13 % |

So the committed M1c relaxations are bit-reproducible on a second
architecture (aarch64), which is a reproduction witness for P2. Detail in
`rebuild_check.json`.

Cells: bulk Si, Ge, 3C-SiC (8 atoms); Si0.8Ge0.2 with 0 and 4 C on
lattice sites; the carbon site-preference pair (C beside 3 Ge, beside 0
Ge) at x = 0.2; Si0.5Ge0.5 with 4 C (216 sites each).

## `md_box/`: the x = 0.3 embedded-SiC MD box (campaign-record entries 78-80)

`in.geom` is the registered input deck `../small_sic/x03/in.sic_particle`
cut before the rNEMD part, followed by the same minimisation and a
`write_data`. `run_geom.sh` builds the bare host and the R = 2 nm particle
case (seed 20260930) with the DGX LAMMPS wheel (one MPI rank, 2 OpenMP threads).
Outputs: `host_relaxed.cif` (46 080 atoms), `p20_relaxed.cif` (49 094
atoms), `p20.data.gz`, `md_box_lattice.json` (Tersoff Si0.7Ge0.3
a = 5.4966 A against Vegard 5.4991 A).

Same geometry rule as the registered run (particle centres, Si shell to
R + 7 A, 3C-SiC inside R, gate G1 gap 7.07 A, identical to the CHPC log),
but not the same Ge placement: LAMMPS `set type/fraction` draws per MPI
rank, so 1 rank here and 16 on CHPC give 11 370 vs 11 538 Ge atoms. The
minimisation stops at its iteration cap, as in the registered run.

## Composition notation

Overall composition Si_{(1-x)(1-y)} Ge_{x(1-y)} C_y, with x the Ge
fraction of the SiGe host and y the carbon atomic fraction. The pick
x = 0.3, y = 0.03 is Si0.679Ge0.291C0.030 overall. With carbon as SiC,
the particles hold 3 at% C + 3 at% Si, leaving a host of Ge fraction
0.291/0.94 = 0.310; the scattering model keeps the host at x (a 0.01
shift in host composition, inside the flat minimum of kappa_L(x)).
