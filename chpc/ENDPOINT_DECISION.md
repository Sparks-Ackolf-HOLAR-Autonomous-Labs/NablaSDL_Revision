# The Phase B endpoint decision

**Decision, 2026-09-27: "B then A".** Part B is executed: the alloy
scope-limit (x in [0.05, 0.95] on Tersoff-MD claims) is the campaign
campaign record's first shard operation (`../phase_c/ledger_campaign.jsonl`),
enforced by `fit_party.py`, reversible by a `restore` entry once endpoint
values are available. Part A followed: GPUMD bring-up on the DGX, see
`../gpumd/BRINGUP.md`.

## Context

Pure Si and Ge are still ballistic at 18432 atoms with direct rNEMD
(`RESULTS.md`), and Green-Kubo is impossible in LAMMPS for both `tersoff`
and `sw` (no valid many-body heat flux, verified through LAMMPS 7 Feb
2024). Credible x = 0 and x = 1 anchor points therefore cannot come from
the rNEMD method.

## Options considered

**A: GPUMD on the DGX.**
[GPUMD](https://github.com/brucefan1983/GPUMD) implements Tersoff-class
potentials with a correct many-body heat current and both homogeneous
methods (Green-Kubo/EMD and HNEMD), which converge with far smaller boxes
than direct NEMD, and it is CUDA-native (the DGX has a GB10 GPU with
CUDA 13).
- Gives Tersoff endpoint kappa in the same potential family as the alloy
  party (one method family over the full composition range), plus a
  methods cross-check at one alloy point (HNEMD against rNEMD).
- Costs a build from source on aarch64 with CUDA and a validation against
  a published Tersoff-Si GPUMD value before any result is used; GPU memory
  use is modest.
- Risk low to moderate: GPUMD is actively maintained, but it is one more
  code to validate.

**B: scope-limit the theory to alloys.** Declare the validity domain
x in [0.05, 0.95]: the theory covers alloy-scattering-dominated transport;
pure elements are outside its scope and enter only through the literature
party as separate anchor evidence.
- No compute, immediate; the scope-limit is itself a shard operation with
  a campaign-record entry, executed because the evidence required it.
- The fitted law loses the x -> 0 and x -> 1 limits (where kappa rises by
  two orders of magnitude), so it makes no claim about dilute alloys.

**C: MACE/GAP endpoints (not chosen).** A machine-learned potential party
(CHPC has `mace`, `mace-lmp` and `quip` modules) would give more accurate
absolute kappa and an independent method family, but it is a new evidence
party with its own validation campaign, not an endpoint patch.

## Why "B then A"

The scope-limit states what the evidence available on 2026-09-27
supports and is reversible by design: when GPUMD endpoint values exist,
the scope-limit is lifted by a `restore` campaign-record entry, which exercises the
non-destructive revision operators. GPUMD bring-up proceeded as
background GPU work on the DGX.
