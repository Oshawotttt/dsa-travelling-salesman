"""Shared runner and output contract for the experiments (docs/CONTRACTS.md, Experiment output)."""
from __future__ import annotations

import csv
import json
import time
from dataclasses import astuple, dataclass, fields
from pathlib import Path
from typing import Mapping, Sequence

from airdrop.approach_a import SolveResult, greedy_insertion
from airdrop.approach_b import local_search
from airdrop.baseline import nearest_neighbour
from airdrop.exact_dp import exact_dp
from airdrop.model import Instance, Stop, trace

ALGORITHMS = ("nn", "a_heap", "a_scan", "b", "b_on_a", "dp")


@dataclass(frozen=True)
class Run:
    experiment: str          # folder name, e.g. "e3_bases"
    run_id: int              # 0, 1, ... within one experiment output
    algorithm: str           # one of ALGORITHMS
    base: str                # key in BASES
    n_towns: int             # inst.n
    sample: int | None       # random seed of the town sample (experiment 4), else None
    F: float                 # fuel cap used
    population: int
    towns_visited: int       # len(route)
    distance_km: float
    fuel_needed_kg: float
    feasible: bool
    time_s: float            # solver wall-clock, best of repeats
    stats: dict[str, int]    # SolveResult.stats


RUNS_COLUMNS = [f.name for f in fields(Run)]
ROUTE_KEY_COLUMNS = ["experiment", "run_id", "algorithm", "base"]
ROUTES_COLUMNS = ROUTE_KEY_COLUMNS + [f.name for f in fields(Stop)]


def solve(inst: Instance, algorithm: str, a_route: Sequence[int] | None = None) -> SolveResult:
    """Run one named algorithm. "b_on_a" is local search started from a_route."""
    if algorithm == "nn":
        return nearest_neighbour(inst)
    if algorithm == "a_heap":
        return greedy_insertion(inst, "heap")
    if algorithm == "a_scan":
        return greedy_insertion(inst, "scan")
    if algorithm == "b":
        return local_search(inst)
    if algorithm == "b_on_a":
        if a_route is None:
            raise ValueError('"b_on_a" needs a_route')
        return local_search(inst, initial=a_route)
    if algorithm == "dp":
        return exact_dp(inst)
    raise ValueError(f"unknown algorithm {algorithm!r}")


def run(experiment: str, run_id: int, inst: Instance, base: str, algorithm: str,
        sample: int | None = None, repeats: int = 1,
        a_route: Sequence[int] | None = None) -> tuple[Run, list[Stop], SolveResult]:
    """Solve, keeping the best wall-clock time of `repeats` solver calls (trace not timed), and trace
    the route."""
    best = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = solve(inst, algorithm, a_route)
        elapsed = time.perf_counter() - start
        best = elapsed if best is None else min(best, elapsed)
    ev = result.eval
    r = Run(experiment, run_id, algorithm, base, inst.n, sample, inst.params.F, ev.population,
            len(result.route), ev.distance, ev.fuel_needed, ev.feasible, best, dict(result.stats))
    return r, trace(inst, result.route), result


def write_outputs(out_dir: Path, runs: Sequence[Run], stops: Mapping[int, Sequence[Stop]]) -> None:
    """Write runs.csv (one row per run) and routes.csv (one row per stop of each run, in step order)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "runs.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(RUNS_COLUMNS)
        for r in runs:
            row = list(astuple(r))
            row[RUNS_COLUMNS.index("sample")] = "" if r.sample is None else r.sample
            row[RUNS_COLUMNS.index("stats")] = json.dumps(r.stats)
            writer.writerow(row)
    with open(out_dir / "routes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(ROUTES_COLUMNS)
        for r in runs:
            for stop in sorted(stops[r.run_id], key=lambda s: s.step):
                writer.writerow([r.experiment, r.run_id, r.algorithm, r.base, *astuple(stop)])


_RUN_TYPES = {"run_id": int, "n_towns": int, "F": float, "population": int, "towns_visited": int,
              "distance_km": float, "fuel_needed_kg": float, "time_s": float}


def read_runs(path: Path) -> list[dict]:
    """Rows of a runs.csv with typed values: `sample` None when empty, `feasible` a bool, `stats` a dict."""
    with open(path, newline="", encoding="utf-8") as f:
        out = []
        for row in csv.DictReader(f):
            for key, cast in _RUN_TYPES.items():
                row[key] = cast(row[key])
            row["sample"] = int(row["sample"]) if row["sample"] else None
            row["feasible"] = row["feasible"] == "True"
            row["stats"] = json.loads(row["stats"])
            out.append(row)
        return out
