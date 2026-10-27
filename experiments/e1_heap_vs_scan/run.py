"""Experiment 1: how much work A's lazy heap saves over the re-scan, and how often it picks a
different town, as the number of towns grows (docs/EXPERIMENT.md).

Run from the repo root: python -m experiments.e1_heap_vs_scan.run
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from airdrop.approach_a import greedy_insertion
from airdrop.model import BASES, Instance, Params, Town, load_towns
from experiments.common import read_runs, run, write_outputs

EXPERIMENT = "e1_heap_vs_scan"
THRESHOLDS = (100_000, 50_000, 15_000, 0)
SELECTORS = ("a_heap", "a_scan")


def run_experiment(towns: Sequence[Town], out_dir: Path, thresholds: Sequence[int] = THRESHOLDS,
                   base: str = "perak", repeats: int = 3) -> None:
    """One a_heap and one a_scan run per population threshold, default Params. The a_heap row's
    stats get `mismatches` from a separate audit=True call."""
    runs, stops = [], {}
    for threshold in thresholds:
        inst = Instance(BASES[base], [t for t in towns if t.population >= threshold], Params())
        for algorithm in SELECTORS:
            r, s, _ = run(EXPERIMENT, len(runs), inst, base, algorithm, repeats=repeats)
            if algorithm == "a_heap":
                mismatches = greedy_insertion(inst, "heap", audit=True).stats["mismatches"]
                r = replace(r, stats={**r.stats, "mismatches": mismatches})
            stops[r.run_id] = s
            runs.append(r)
    write_outputs(out_dir, runs, stops)


def plot(out_dir: Path) -> None:
    """Score evals per selector (log y), and the heap's mismatches per insertion, against towns."""
    out_dir = Path(out_dir)
    runs = read_runs(out_dir / "runs.csv")
    fig, (ax_evals, ax_mis) = plt.subplots(1, 2, figsize=(11, 4.5))
    for algorithm, label in (("a_heap", "A, lazy heap"), ("a_scan", "A, full re-scan")):
        rs = sorted((r for r in runs if r["algorithm"] == algorithm), key=lambda r: r["n_towns"])
        ax_evals.plot([r["n_towns"] for r in rs], [r["stats"]["score_evals"] for r in rs], "o-", label=label)
    ax_evals.set_yscale("log")
    ax_evals.set_xlabel("Number of towns")
    ax_evals.set_ylabel("Score evaluations (log scale)")
    ax_evals.set_title("Work per selector")
    ax_evals.legend()
    heap = sorted((r for r in runs if r["algorithm"] == "a_heap"), key=lambda r: r["n_towns"])
    ax_mis.plot([r["n_towns"] for r in heap],
                [r["stats"]["mismatches"] / max(r["stats"]["insertions"], 1) for r in heap],
                "o-", color="tab:red", label="Heap pick ≠ re-scan pick")
    ax_mis.set_ylim(0, 1.05)
    ax_mis.set_xlabel("Number of towns")
    ax_mis.set_ylabel("Mismatches ÷ insertions")
    ax_mis.set_title("How often the heap picks a different town")
    ax_mis.legend()
    fig.suptitle(f"Experiment 1: heap vs scan (F = {runs[0]['F']:,.0f} kg, base {runs[0]['base']})")
    fig.tight_layout()
    fig.savefig(out_dir / "plot.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    out = Path(__file__).resolve().parent / "out"
    run_experiment(load_towns(root / "data" / "cities_clean.csv"), out)
    plot(out)
