"""Reproduce Finding 5 on all 745 towns and six bases at F = 21,100 kg.

Run from the repository root: python -m experiments.e5_population_sort.run
By default, verify the input against E3 and reuse its committed B routes. Use --fresh-b
to recompute both B variants (slow).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from airdrop.model import BASES, Instance, Params, Town, evaluate, load_towns
from experiments.common import Run, read_routes, read_runs, run, write_outputs

EXPERIMENT = "e5_population_sort"
ALGORITHMS = ("a_heap", "sort_then_fit", "b", "b_on_a")
BASE_ORDER = ("perak", "klia", "sarawak", "sabah", "kuching", "kota_kinabalu")
BASE_LABELS = ("Perak", "KLIA", "Long Geng", "Kg Balat", "Kuching", "Kota Kinabalu")


def run_experiment(towns: Sequence[Town], out_dir: Path,
                   bases: Sequence[str] = BASE_ORDER, reference_dir: Path | None = None,
                   input_path: Path | None = None) -> None:
    """Run A and sort; reuse verified E3 B routes, or recompute B when no reference is given."""
    reference = {}
    old_stops = {}
    if reference_dir is not None:
        reference_dir = Path(reference_dir)
        reference = {(r["base"], r["algorithm"]): r
                     for r in read_runs(reference_dir / "runs.csv")}
        old_stops = read_routes(reference_dir / "routes.csv")
    runs, stops = [], {}
    for base in bases:
        inst = Instance(BASES[base], towns, Params())
        a_route = None
        for algorithm in ALGORITHMS:
            if reference_dir is not None and algorithm in ("b", "b_on_a"):
                old = reference[base, algorithm]
                if old["n_towns"] != inst.n or old["F"] != inst.params.F:
                    raise ValueError(f"E3 input mismatch at {base}")
                old_trace = old_stops[old["run_id"]]
                old_route = [s.index for s in old_trace[1:-1]]
                old_eval = evaluate(inst, old_route)
                if (old_trace[-1].population_reached != old["population"]
                        or not old_eval.feasible or old_eval.population != old["population"]
                        or abs(old_eval.fuel_needed - old["fuel_needed_kg"]) > 1e-6):
                    raise ValueError(f"E3 route mismatch at {base}, {algorithm}")
                record = replace(Run(**old), experiment=EXPERIMENT, run_id=len(runs))
                runs.append(record)
                stops[record.run_id] = old_trace
                continue
            record, trace, result = run(EXPERIMENT, len(runs), inst, base, algorithm,
                                        a_route=a_route)
            if algorithm == "a_heap":
                a_route = result.route
                if reference_dir is not None:
                    old = reference[base, "a_heap"]
                    old_route = [s.index for s in old_stops[old["run_id"]][1:-1]]
                    if (old["population"] != record.population or old_route != result.route
                            or old["n_towns"] != inst.n or old["F"] != inst.params.F):
                        raise ValueError(f"cleaned data differs from E3 at {base}")
            runs.append(record)
            stops[record.run_id] = trace
    write_outputs(out_dir, runs, stops)
    write_summary(out_dir)
    provenance = {"b_reused": reference_dir is not None}
    if input_path is not None:
        provenance["input"] = "experiments/e5_population_sort/input/cities_clean.csv"
        provenance["input_sha256"] = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    if reference_dir is not None:
        provenance.update({"b_source": "experiments/e3_bases/out",
                           "reference_runs_sha256": hashlib.sha256((reference_dir / "runs.csv").read_bytes()).hexdigest(),
                           "reference_routes_sha256": hashlib.sha256((reference_dir / "routes.csv").read_bytes()).hexdigest(),
                           "input_check": "A routes and population match E3 at all requested bases; B routes re-evaluated"})
    with open(Path(out_dir) / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
        f.write("\n")


def summary_rows(out_dir: Path) -> list[dict]:
    """Compare sort-then-fit with the larger of B's two published seed variants."""
    by_base = {}
    for row in read_runs(out_dir / "runs.csv"):
        if not row["feasible"]:
            raise ValueError(f"infeasible {row['algorithm']} route at {row['base']}")
        by_base.setdefault(row["base"], {})[row["algorithm"]] = row
    rows = []
    for base, methods in by_base.items():
        if set(methods) != set(ALGORITHMS):
            raise ValueError(f"missing method at {base}: {set(ALGORITHMS) - set(methods)}")
        best_b = max(("b", "b_on_a"), key=lambda a: methods[a]["population"])
        a = methods["a_heap"]
        sort = methods["sort_then_fit"]
        b = methods[best_b]
        rows.append({"base": base, "n_towns": sort["n_towns"], "F": sort["F"],
                     "a_population": a["population"], "sort_population": sort["population"],
                     "best_b_algorithm": best_b, "best_b_population": b["population"],
                     "sort_gap_pct": 100 * (b["population"] - sort["population"]) / b["population"],
                     "sort_towns": sort["towns_visited"], "sort_fuel_kg": sort["fuel_needed_kg"]})
    return rows


def write_summary(out_dir: Path) -> None:
    rows = summary_rows(out_dir)
    with open(out_dir / "summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def plot(out_dir: Path) -> None:
    """Draw from saved CSV output, without rerunning solvers."""
    rows = {r["base"]: r for r in summary_rows(out_dir)}
    x = range(len(BASE_ORDER))
    fig, ax = plt.subplots(figsize=(10, 5))
    for offset, key, label, color in ((-0.25, "a_population", "A (lazy heap)", "#D35358"),
                                      (0, "sort_population", "Sort-then-fit", "#303039"),
                                      (0.25, "best_b_population", "Best of B", "#5368DF")):
        ax.bar([i + offset for i in x], [rows[b][key] / 1e6 for b in BASE_ORDER],
               width=0.24, label=label, color=color)
    ax.set_xticks(list(x), BASE_LABELS)
    ax.set_ylabel("Population reached (millions)")
    ax.set_title("Finding 5: population sort versus A and best of B (745 towns, F = 21,100 kg)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "plot.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-b", action="store_true", help="recompute both B variants (slow)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    input_path = Path(__file__).resolve().parent / "input" / "cities_clean.csv"
    out = Path(__file__).resolve().parent / "out"
    reference = None if args.fresh_b else root / "experiments" / "e3_bases" / "out"
    run_experiment(load_towns(input_path), out, reference_dir=reference, input_path=input_path)
    plot(out)
