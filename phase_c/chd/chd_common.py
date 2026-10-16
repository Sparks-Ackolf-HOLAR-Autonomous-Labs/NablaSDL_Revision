"""Shared CHD (Computational Hypergraph Discovery) helpers for stage-0.

Wraps ComputationalHypergraphDiscovery v2.1.0 (Bourdais et al., PNAS
2024; jax, CPU) so that calibrate_chd.py and stage0_literature.py use
exactly the same code path:

- run_chd(): the library's own ancestor search for ONE target node
  (GraphDiscovery.fit(targets=[target])) with a named setting (kernel
  set + mode chooser), returning the ancestor set, the chosen kernel,
  the noise ratio n/(n+s) after pruning, and the pruning path (noise
  ratio vs number of ancestors), which the library only plots; we
  capture it by replacing its plotting hook with a recorder.
- noise_given(): the noise ratio of the target when its candidate
  ancestors are restricted to a given set (library's possible_edges
  mechanism + its own kernel regression), per kernel, with the Z-test
  band (5th/95th percentile of the noise ratio a pure-noise target
  would get). This is the "how much of log kappa do these variables
  leave unexplained" measurement.

Everything is deterministic: CHD's jax PRNG key is fixed (key 0).
Environment: native venv `~/venvs/chd` (python3.12 aarch64) with
`pip install ComputationalHypergraphDiscovery jax tqdm networkx
matplotlib`; see STAGE0_RESULTS.md.
"""
from __future__ import annotations

import os

os.environ.setdefault("MPLBACKEND", "Agg")      # library calls plt.show()
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("JAX_PLATFORMS", "cpu")   # GPU is shared: CPU only

import warnings  # noqa: E402

warnings.filterwarnings("ignore")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as onp  # noqa: E402

import ComputationalHypergraphDiscovery as CHD  # noqa: E402
from ComputationalHypergraphDiscovery import _GraphDiscoveryMain as _gdm  # noqa: E402
from ComputationalHypergraphDiscovery.Modes import (  # noqa: E402
    GaussianMode, LinearMode, QuadraticMode)
from ComputationalHypergraphDiscovery.decision import (  # noqa: E402
    MaxIncrementModeChooser, MinNoiseKernelChooser, ThresholdModeChooser)
from jax import random  # noqa: E402

CHD_VERSION = "2.1.0"

# ---------------------------------------------------------------------------
# pruning-path recorder (the library passes the path only to a plot call)
_PATH = []


class _NoFig:
    pass


def _recorder(ancestor_number, list_of_noises, list_of_Zs, node_name,
              ancestor_modes_number=None):
    _PATH.append({"node": node_name,
                  "n_ancestors": [int(a) for a in ancestor_number],
                  "noise": [float(v) for v in list_of_noises],
                  "Z_low": [float(z[0]) for z in list_of_Zs],
                  "chosen_n_ancestors": (None if ancestor_modes_number is None
                                         else int(ancestor_modes_number))})
    fig = plt.figure(figsize=(0.1, 0.1))
    return fig, None


_gdm.plot_noise_evolution = _recorder

# ---------------------------------------------------------------------------
# named settings: kernel set x mode chooser

KERNEL_SETS = {
    "lin+quad+gauss": lambda: [LinearMode(), QuadraticMode(), GaussianMode(l=1)],
    "lin+quad": lambda: [LinearMode(), QuadraticMode()],
    "lin": lambda: [LinearMode()],
}
MODE_CHOOSERS = {
    "maxinc": lambda: MaxIncrementModeChooser(),
    "thr0.4": lambda: ThresholdModeChooser(0.4),
    "thr0.6": lambda: ThresholdModeChooser(0.6),
    "thr0.8": lambda: ThresholdModeChooser(0.8),
}
DEFAULT_SETTING = ("lin+quad+gauss", "maxinc")   # library defaults


def all_settings():
    return [(k, m) for k in KERNEL_SETS for m in MODE_CHOOSERS]


def setting_name(s):
    return f"{s[0]}|{s[1]}"


def _clean(X, names, target):
    """Drop constant columns (CHD refuses them); never drop the target."""
    X = onp.asarray(X, dtype=float)
    keep = [j for j, n in enumerate(names)
            if n == target or X[:, j].std() > 0]
    dropped = [names[j] for j in range(len(names)) if j not in keep]
    return X[:, keep], [names[j] for j in keep], dropped


def run_chd(X, names, target, setting=DEFAULT_SETTING, key=0):
    """CHD ancestor search for `target`. Returns a dict with ancestors,
    kernel, noise after pruning, pruning path, constant columns dropped."""
    X, names, dropped = _clean(X, names, target)
    ks, mc = setting
    gd = CHD.GraphDiscovery(X, list(names), kernels=KERNEL_SETS[ks](),
                            verbose=False)
    _PATH.clear()
    gd.fit(targets=[target], key=random.PRNGKey(key),
           kernel_chooser=MinNoiseKernelChooser(),
           mode_chooser=MODE_CHOOSERS[mc]())
    plt.close("all")
    node = gd.G.nodes[target]
    anc = sorted(gd.G.predecessors(target))
    path = _PATH[-1] if _PATH else None
    return {"ancestors": anc,
            "kernel": node.get("type"),
            "noise_after_pruning": (None if "noise" not in node
                                    else float(node["noise"])),
            "pruning_path": path,
            "dropped_constant": dropped}


def noise_given(X, names, target, candidates, kernel_set="lin+quad+gauss",
                key=0):
    """Noise ratio n/(n+s) of `target` regressed (CHD kernel regression)
    on exactly the `candidates` set, per kernel, plus the Z-test band.
    Lower noise = more of the target explained. A noise ratio above the
    kernel's Z_low is statistically indistinguishable from a pure-noise
    target (CHD's own step-7 criterion)."""
    X, names, dropped = _clean(X, names, target)
    cands = [c for c in candidates if c in names]
    if not cands:
        return {"candidates": [], "per_kernel": {}, "min_noise": 1.0,
                "dropped_constant": dropped}
    G = nx.DiGraph()
    G.add_nodes_from(names)
    G.add_edges_from((c, target) for c in cands)
    gd = CHD.GraphDiscovery(X, list(names), kernels=KERNEL_SETS[kernel_set](),
                            possible_edges=G, verbose=False)
    gas, active = gd._prepare_modes_for_ancestor_finding([target])
    k, *sub = random.split(random.PRNGKey(key), 2)
    perf = gd.get_kernel_performance(active, gas, onp.array(sub))
    _, noises, zl, zh, gam, _ = perf
    per = {}
    for i, kern in enumerate(gd.kernels):
        per[str(kern)] = {"noise": float(noises[0, i]),
                          "Z_low": float(zl[0, i]), "Z_high": float(zh[0, i]),
                          "gamma": float(gam[0, i])}
    best = min(per.values(), key=lambda d: d["noise"])
    return {"candidates": cands, "per_kernel": per,
            "min_noise": best["noise"],
            "min_noise_below_Z_low": bool(best["noise"] < best["Z_low"]),
            "dropped_constant": dropped}
