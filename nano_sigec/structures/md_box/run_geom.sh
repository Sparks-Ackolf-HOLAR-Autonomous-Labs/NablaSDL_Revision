#!/bin/bash
# Rebuild the registered x = 0.3 embedded-SiC MD box geometry (setup + the
# same minimisation as the registered run) and write LAMMPS data files for
# the structure figure. Not a registered run; no kappa is computed.
export LD_LIBRARY_PATH=$(find ~/mat_theory_pilot/mpichlib -name "*.so*" -printf "%h\n" | sort -u | tr '\n' ':')
export OMP_NUM_THREADS=2
LMP=~/mat_theory_pilot/venv/bin/lmp
$LMP -in in.geom -log host.log -screen none -var x 0.3 -var R 0 -var shell 0 -var sic 0 -var seed 20260930 -var pot SiCGe_GeC.tersoff -var out host &
$LMP -in in.geom -log p20.log -screen none -var x 0.3 -var R 20 -var shell 1 -var sic 1 -var seed 20260930 -var pot SiCGe_GeC.tersoff -var out p20 &
wait
