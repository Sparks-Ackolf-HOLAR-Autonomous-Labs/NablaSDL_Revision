#!/bin/bash
# Rebuild the 44 Phase C production points (ncz 24 cell, production seed and
# deck) on the DGX CPU: 2 OpenMP threads each, 10 at a time.
cd "$(dirname "$0")"
export LD_LIBRARY_PATH=$(find ~/mat_theory_pilot/mpichlib -name "*.so*" -printf "%h\n" | sort -u | tr '\n' ':')
export OMP_NUM_THREADS=2
LMP=~/mat_theory_pilot/venv/bin/lmp
python3 - <<'PY' > points.txt
import json
d = json.load(open("../../production/production_design.json"))
seen = set()
for r in d["runs"]:
    if r["point_id"] in seen:
        continue
    seen.add(r["point_id"])
    ph = "amorph" if r["deck"] == "amorph" else "crystal"
    print(r["point_id"], ph, r["x"], r["T"], r["seed"])
PY
run() { [ -f $1.done ] && return; $LMP -in in.rebuild -log $1.log -screen none -var phase $2 -var x $3 -var T $4 -var seed $5 -var out $1 && gzip -f $1.dump && touch $1.done; }
n=0
while read pid ph x T s; do
  run $pid $ph $x $T $s &
  n=$((n+1)); if [ $n -ge 10 ]; then wait -n; n=$((n-1)); fi
done < points.txt
wait
echo ALLDONE > rebuild_done
