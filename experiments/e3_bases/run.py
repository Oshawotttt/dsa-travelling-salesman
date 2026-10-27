"""Experiment 3: population reached from each of the 6 bases, rural against non-rural per region,
for each algorithm, with B on A as a separate row (docs/EXPERIMENT.md).

Run from the repo root: python -m experiments.e3_bases.run
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from airdrop.model import BASES, RURAL_BASES, Instance, Params, Town, load_towns
from experiments.common import read_runs, run, write_outputs

EXPERIMENT = "e3_bases"
# region -> (rural base, non-rural base), docs/DECISIONS.md 2026-10-27
REGIONS = {"Peninsula": ("perak", "klia"), "Sarawak": ("sarawak", "kuching"),
           "Sabah": ("sabah", "kota_kinabalu")}
MAIN_CHART = ("nn", "a_heap", "b")
LABELS = {"nn": "Nearest neighbour", "a_heap": "A", "b": "B", "b_on_a": "B on A"}


def run_experiment(towns: Sequence[Town], out_dir: Path, bases: Sequence[str] = tuple(BASES)) -> None:
    """For each base, default Params: NN, A (heap), B, and B seeded with that base's A route."""
    runs, stops = [], {}
    for base in bases:
        inst = Instance(BASES[base], towns, Params())
        a_route = None
        for algorithm in (*MAIN_CHART, "b_on_a"):
            r, s, result = run(EXPERIMENT, len(runs), inst, base, algorithm, a_route=a_route)
            if algorithm == "a_heap":
                a_route = result.route
            stops[r.run_id] = s
            runs.append(r)
    write_outputs(out_dir, runs, stops)


def _base_label(base: str) -> str:
    return f"{base}\n({'rural' if base in RURAL_BASES else 'non-rural'})"


def plot(out_dir: Path) -> None:
    """Main panel: bars grouped by region, rural and non-rural side by side, one bar per algorithm.
    Second panel: B on A per base."""
    out_dir = Path(out_dir)
    runs = read_runs(out_dir / "runs.csv")
    population = {(r["base"], r["algorithm"]): r["population"] / 1e6 for r in runs}
    order = [base for pair in REGIONS.values() for base in pair]
    x = range(len(order))
    width = 0.27
    fig, (ax, ax_b_on_a) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [2, 1]})
    for i, algorithm in enumerate(MAIN_CHART):
        ax.bar([p + (i - 1) * width for p in x], [population[b, algorithm] for b in order], width,
               label=LABELS[algorithm])
    for i in range(1, len(REGIONS)):
        ax.axvline(2 * i - 0.5, color="grey", linewidth=0.8)
    for i, region in enumerate(REGIONS):
        ax.text(2 * i + 0.5, 1.02, region, transform=ax.get_xaxis_transform(), ha="center")
    ax.set_xticks(list(x), [_base_label(b) for b in order])
    ax.set_ylabel("Population reached (millions)")
    ax.set_title("NN, A and B from each base", pad=22)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=len(MAIN_CHART))
    ax_b_on_a.bar(list(x), [population[b, "b_on_a"] for b in order], 0.6, color="tab:purple",
                  label=LABELS["b_on_a"])
    ax_b_on_a.set_xticks(list(x), [_base_label(b) for b in order], fontsize=8)
    ax_b_on_a.set_ylabel("Population reached (millions)")
    ax_b_on_a.set_title("B on A (local search from A's route)", pad=22)
    ax_b_on_a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16))
    fig.suptitle(f"Experiment 3: bases (F = {runs[0]['F']:,.0f} kg, {runs[0]['n_towns']} towns)")
    fig.tight_layout()
    fig.savefig(out_dir / "plot.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    out = Path(__file__).resolve().parent / "out"
    run_experiment(load_towns(root / "data" / "cities_clean.csv"), out)
    plot(out)
