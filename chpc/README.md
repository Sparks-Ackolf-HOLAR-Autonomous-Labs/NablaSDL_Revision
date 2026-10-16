# mat_theory Phase B: CHPC kappa campaign

First CHPC compute for the project (run 2026-09-26). Ports the DGX pilot's
Muller-Plathe rNEMD protocol (`pilot/src/mp_kappa.py`) to CHPC module
LAMMPS, under the scheduling policy of 2026-09-25: **guest partitions
first, grn061 not used**.

## Files

| File | Purpose |
|---|---|
| `in.mp_kappa` | LAMMPS input deck, exact port of the pilot MP protocol (NPT 50 ps, warmup 100 ps, production 500 ps, 20 bins, swaps every 50 steps) |
| `analyze_mp.py` | log + profile -> kappa JSON; same math as the pilot, stdlib-only (CHPC python3 has no numpy) |
| `in.validate` | Phase B gate: Tersoff lattice constant + cohesive energy, 3x3x3 cell box-relax minimization |
| `points.txt` | the 19-point campaign matrix: `x T ncz seed` per line |
| `sbatch_kappa.sh` | SLURM array job, notchpeak-guest / owner-guest, 16 MPI ranks, 4 h, `--requeue` (preemption-safe: each point reruns cheaply) |
| `results/` | collected kappa points (committed as they land) |
| `in.mp_kappa2` | follow-up deck: same protocol, cross-section (`ncxy`) and swap interval (`swapn`) now variables; defaults reproduce `in.mp_kappa` |
| `points_followup.txt` | follow-up matrix: `x T ncz seed ncxy swapn` per line |
| `sbatch_followup.sh` | SLURM array for the follow-ups, same partition/limits |
| `in.gk_si_sw` / `analyze_gk_sw.py` / `sbatch_gk.sh` | endpoint-strategy feasibility: Green-Kubo for pure Si with Stillinger-Weber (`pair sw` supports centroid heat flux; Tersoff does not) |

## Follow-up campaign (2026-09-26, RESULTS.md items 1-4)

- **Cross-section convergence** at x=0.5, 300 K: ncxy = 6, 8 at ncz=24 and
  ncxy = 6 at ncz=48 (baseline is 4x4)
- **Gentler swap rate** at x=0.5, 300 K, ncz=48: swap every 100 and 200
  steps (baseline 50); quantifies the steep-gradient bias
- **Seeds at larger sizes**: x=0.5, 300 K, seeds 202/303 at ncz=48 and 96,
  seed 202 at ncz=144
- **Endpoint strategy evidence**: 2-seed Green-Kubo pure-Si run with SW
  (different potential, homogeneous method, no ballistic size wall) to
  inform the choice between "different potential for
  endpoints" and "scope-limit the theory to alloys"

## Campaign matrix (19 points, all T=300 K unless noted)

- **Size convergence** at x=0.5: ncz = 24, 48, 96, 144 (1/L extrapolation)
- **Seeds** at x=0.5, ncz=24: 202, 303, 404 (error bar; DGX point is the
  cross-party twin at a different seed)
- **x=0.15**: ncz = 24, 48, 96
- **x=0.5 at 1100 K**: ncz = 24, 48, 96 (alloy-dominated regime)
- **Endpoints x=0 (Si), x=1 (Ge)**: ncz = 48, 96, 144 (long phonon MFP,
  the strongest size suppression; these are the points the DGX cannot
  comfortably reach)

## Environment on CHPC

```
module load openmpi/4.1.6 lammps        # lmp 2 Aug 2023, Update 3
POT=/uufs/chpc.utah.edu/sys/installdir/r8/lammps/08022023.3/share/lammps/potentials/SiCGe.tersoff
```

Remote workspace: `~/mat_theory/chpc/` (home, not scratch, so nothing is
purged; results are committed to the repo regardless).

## Submit / status

```
sbatch --array=0-18 sbatch_kappa.sh
squeue -u $USER -M notchpeak
```
