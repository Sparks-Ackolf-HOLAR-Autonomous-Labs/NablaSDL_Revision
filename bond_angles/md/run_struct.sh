#!/bin/bash
# 12 structure rebuilds on the DGX CPU (2 threads each, 6 at a time).
cd "$(dirname "$0")"
export LD_LIBRARY_PATH=$(find ~/mat_theory_pilot/mpichlib -name "*.so*" -printf "%h\n" | sort -u | tr '\n' ':')
export OMP_NUM_THREADS=2
LMP=~/mat_theory_pilot/venv/bin/lmp
run() { $LMP -in in.struct -log $1.log -screen none -var phase $2 -var x $3 -var T $4 -var seed $5 -var out $1; }
for s in 0 100; do
  run A300_s$s amorph 0.5 300 $((2003+s)) &
  run A700_s$s amorph 0.5 700 $((2004+s)) &
  run X300_s$s crystal 0.5 300 $((2003+s)) &
  run X700_s$s crystal 0.5 700 $((2004+s)) &
  run M1500_s$s crystal 0.5 1500 $((2001+s)) &
  run M1450_s$s crystal 0.7 1450 $((2002+s)) &
  wait
done
