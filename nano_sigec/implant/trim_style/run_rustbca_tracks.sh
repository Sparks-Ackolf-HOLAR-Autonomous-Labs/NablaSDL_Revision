#!/bin/bash
# RustBCA runs behind make_trim_style.py: for each committed ../rustbca_run/*.toml,
# a 20 000-ion range run (unchanged input) and a track run (100 ions; 10 for Kr,
# whose cascades are dense) with ion and recoil trajectories switched on.
# Usage: run_rustbca_tracks.sh /path/to/RustBCA /scratch/dir
set -e
BIN=$1; OUT=$2; SRC=$(cd "$(dirname "$0")/../rustbca_run" && pwd)
mkdir -p "$OUT"; cd "$OUT"
for f in "$SRC"/*.toml; do
  n=$(basename "$f" .toml); N=100; [[ $n == Kr* ]] && N=10
  sed "s/name = \"${n}_\"/name = \"prof_${n}_\"/" "$f" > "prof_$n.toml"
  sed -e "s/name = \"${n}_\"/name = \"traj_${n}_\"/" -e 's/track_trajectories = false/track_trajectories = true/' \
      -e 's/track_recoils = false/track_recoils = true/' -e 's/track_recoil_trajectories = false/track_recoil_trajectories = true/' \
      -e "s/^N = \[[0-9]*\]/N = [$N]/" -e 's/num_chunks = 10/num_chunks = 1/' "$f" > "traj_$n.toml"
  "$BIN" 1D "prof_$n.toml" > /dev/null
  "$BIN" 1D "traj_$n.toml" > /dev/null
done
