"""Experiment 4: how close the heuristics come to the exact DP on 10 random 12-town samples of
Peninsular towns, at F_full (almost every town fits) and F_tight (about 80% fit) (docs/EXPERIMENT.md).

Run from the repo root: python -m experiments.e4_optimality_gap.run
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Callable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from airdrop.exact_dp import exact_dp
from airdrop.model import BASES, Base, Instance, Params, Town, load_towns
from experiments.common import read_runs, run, write_outputs

EXPERIMENT = "e4_optimality_gap"
HEURISTICS = ("nn", "a_heap", "b", "b_on_a")
LABELS = {"nn": "NN", "a_heap": "A", "b": "B", "b_on_a": "B on A"}
STEP = 10.0  # F is searched over multiples of 10 kg
F_MAX = Params().F


def _dp_lengths(samples: Sequence[Sequence[Town]], base: Base, F: float) -> list[int]:
    return [len(exact_dp(Instance(base, s, Params(F=F))).route) for s in samples]


def _smallest_F(ok: Callable[[float], bool]) -> float:
    """Smallest multiple of STEP in [R, F_MAX] where ok holds, by binary search (ok is taken to be
    false below that value and true above). Raises ValueError when ok fails at F_MAX."""
    lo, hi = math.ceil(Params().R / STEP), int(F_MAX // STEP)
    if not ok(hi * STEP):
        raise ValueError(f"no F up to {F_MAX:,.0f} kg meets the rule")
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid * STEP):
            hi = mid
        else:
            lo = mid + 1
    return lo * STEP


def full_fit_F(samples: Sequence[Sequence[Town]], base: Base, min_samples: int = 8) -> float:
    """F_full: smallest F at which the DP route visits every town in at least min_samples samples."""
    return _smallest_F(lambda F: sum(k == len(s) for k, s in zip(_dp_lengths(samples, base, F), samples))
                       >= min_samples)


def coverage_F(samples: Sequence[Sequence[Town]], base: Base, share: float = 0.8) -> float:
    """F_tight: smallest F at which the DP routes visit on average at least `share` of each sample."""
    total = sum(len(s) for s in samples)
    # compare totals with a tolerance: 0.8 * 12 is 9.600000000000001, so a mean of exactly 80% would fail
    return _smallest_F(lambda F: sum(_dp_lengths(samples, base, F)) >= share * total - 1e-9)


def run_experiment(towns: Sequence[Town], out_dir: Path, seeds: Sequence[int] = range(10),
                   sample_size: int = 12, base: str = "perak", min_samples: int = 8,
                   share: float = 0.8) -> None:
    """Draw one sample per seed from `towns`, find F_full and F_tight over all samples, then solve
    every sample at both with the DP and each heuristic."""
    samples = [random.Random(seed).sample(list(towns), sample_size) for seed in seeds]
    Fs = (full_fit_F(samples, BASES[base], min_samples), coverage_F(samples, BASES[base], share))
    runs, stops = [], {}
    for F in Fs:
        for seed, sample in zip(seeds, samples):
            inst = Instance(BASES[base], sample, Params(F=F))
            a_route = None
            for algorithm in ("dp", "nn", "a_heap", "b", "b_on_a"):
                r, s, result = run(EXPERIMENT, len(runs), inst, base, algorithm, sample=seed, a_route=a_route)
                if algorithm == "a_heap":
                    a_route = result.route
                stops[r.run_id] = s
                runs.append(r)
    write_outputs(out_dir, runs, stops)


def plot(out_dir: Path) -> None:
    """One panel per F: the gap (heuristic population / DP population) per algorithm, one dot per
    sample, with the average marked."""
    out_dir = Path(out_dir)
    runs = read_runs(out_dir / "runs.csv")
    Fs = sorted({r["F"] for r in runs}, reverse=True)
    names = ["F_full", "F_tight"] if len(Fs) == 2 else [f"F{i + 1}" for i in range(len(Fs))]
    fig, axes = plt.subplots(1, len(Fs), figsize=(6 * len(Fs), 4.5), sharey=True, squeeze=False)
    for ax, F, name in zip(axes[0], Fs, names):
        at_F = [r for r in runs if r["F"] == F]
        optimum = {r["sample"]: r["population"] for r in at_F if r["algorithm"] == "dp"}
        for x, algorithm in enumerate(HEURISTICS):
            gaps = [r["population"] / optimum[r["sample"]] for r in at_F
                    if r["algorithm"] == algorithm and optimum[r["sample"]] > 0]
            ax.scatter([x] * len(gaps), gaps, alpha=0.6, color="tab:blue",
                       label="One sample" if x == 0 else None)
            ax.scatter([x], [sum(gaps) / len(gaps)], marker="_", s=600, color="tab:red", linewidths=2,
                       label="Average" if x == 0 else None)
        ax.set_xticks(range(len(HEURISTICS)), [LABELS[a] for a in HEURISTICS])
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Algorithm")
        ax.set_title(f"{name} = {F:,.0f} kg")
        ax.legend(loc="lower right")
    axes[0][0].set_ylabel("Gap: population ÷ optimal population")
    n_samples = len({r["sample"] for r in runs})
    fig.suptitle(f"Experiment 4: optimality gap ({n_samples} samples of {runs[0]['n_towns']} towns, "
                 f"base {runs[0]['base']})")
    fig.tight_layout()
    fig.savefig(out_dir / "plot.png", dpi=150)
    plt.close(fig)


def peninsular_towns(path: Path) -> list[Town]:
    """Towns of data/cities_clean.csv whose region is Peninsular, in file order."""
    with open(path, newline="", encoding="utf-8") as f:
        peninsular = {int(row["geonameid"]) for row in csv.DictReader(f) if row["region"] == "Peninsular"}
    return [t for t in load_towns(path) if t.geonameid in peninsular]


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    out = Path(__file__).resolve().parent / "out"
    run_experiment(peninsular_towns(root / "data" / "cities_clean.csv"), out)
    plot(out)
