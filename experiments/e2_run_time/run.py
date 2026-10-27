"""Experiment 2: how each algorithm's run time grows with the number of towns (docs/EXPERIMENT.md).

Run from the repo root: python -m experiments.e2_run_time.run
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from airdrop.model import BASES, Instance, Params, Town, load_towns
from experiments.common import read_runs, run, write_outputs

EXPERIMENT = "e2_run_time"
THRESHOLDS = (100_000, 50_000, 15_000, 0)
ALGORITHMS = ("nn", "a_heap", "a_scan", "b")
LABELS = {"nn": "Nearest neighbour", "a_heap": "A, lazy heap", "a_scan": "A, full re-scan", "b": "B (local search)"}


def run_experiment(towns: Sequence[Town], out_dir: Path, thresholds: Sequence[int] = THRESHOLDS,
                   base: str = "perak", repeats: int = 3) -> None:
    """One run per (population threshold, algorithm), default Params, best of `repeats` times."""
    runs, stops = [], {}
    for threshold in thresholds:
        inst = Instance(BASES[base], [t for t in towns if t.population >= threshold], Params())
        for algorithm in ALGORITHMS:
            r, s, _ = run(EXPERIMENT, len(runs), inst, base, algorithm, repeats=repeats)
            stops[r.run_id] = s
            runs.append(r)
    write_outputs(out_dir, runs, stops)


def plot(out_dir: Path) -> None:
    """Run time against number of towns, one line per algorithm, log y axis."""
    out_dir = Path(out_dir)
    runs = read_runs(out_dir / "runs.csv")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for algorithm in ALGORITHMS:
        rs = sorted((r for r in runs if r["algorithm"] == algorithm), key=lambda r: r["n_towns"])
        ax.plot([r["n_towns"] for r in rs], [r["time_s"] for r in rs], "o-", label=LABELS[algorithm])
    ax.set_yscale("log")
    ax.set_xlabel("Number of towns")
    ax.set_ylabel("Run time, best of repeats (s, log scale)")
    ax.set_title(f"Experiment 2: run time (F = {runs[0]['F']:,.0f} kg, base {runs[0]['base']})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "plot.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    out = Path(__file__).resolve().parent / "out"
    run_experiment(load_towns(root / "data" / "cities_clean.csv"), out)
    plot(out)
