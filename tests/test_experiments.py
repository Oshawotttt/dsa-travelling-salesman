import csv
import random
from dataclasses import fields

import pytest

from airdrop.approach_a import greedy_insertion
from airdrop.approach_b import local_search
from airdrop.baseline import nearest_neighbour
from airdrop.exact_dp import exact_dp
from airdrop.model import Base, Instance, Params, Stop, Town, evaluate, trace
from experiments.common import ALGORITHMS, read_runs, run, solve, write_outputs

BASE0 = Base(0, "origin", 0.0, 0.0)


def random_towns(seed, n):
    rng = random.Random(seed)
    return [Town(i, f"t{i}", rng.uniform(-2, 2), rng.uniform(-2, 2), rng.randint(100, 10_000))
            for i in range(1, n + 1)]


def small_instance(seed=0, n=8, params=Params(F=4_000.0)):
    return Instance(BASE0, random_towns(seed, n), params)


def test_solve_dispatch():
    inst = small_instance()
    a_route = greedy_insertion(inst, "heap").route
    direct = {
        "nn": nearest_neighbour(inst),
        "a_heap": greedy_insertion(inst, "heap"),
        "a_scan": greedy_insertion(inst, "scan"),
        "b": local_search(inst),
        "b_on_a": local_search(inst, initial=a_route),
        "dp": exact_dp(inst),
    }
    assert set(ALGORITHMS) == set(direct)
    for name in ALGORITHMS:
        assert solve(inst, name, a_route=a_route).route == direct[name].route
    with pytest.raises(ValueError):
        solve(inst, "unknown")
    with pytest.raises(ValueError):
        solve(inst, "b_on_a")


RUNS_HEADER = ["experiment", "run_id", "algorithm", "base", "n_towns", "sample", "F", "population",
               "towns_visited", "distance_km", "fuel_needed_kg", "feasible", "time_s", "stats"]
ROUTES_HEADER = ["experiment", "run_id", "algorithm", "base", "step", "index", "geonameid", "name", "lat",
                 "lon", "population", "leg_km", "distance_km", "leg_fuel_kg", "fuel_kg", "cargo_kg",
                 "weight_kg", "population_reached"]


def header(path):
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def test_output_headers(tmp_path):
    inst = small_instance()
    r, stops, _ = run("e0_test", 0, inst, "origin", "nn")
    write_outputs(tmp_path, [r], {0: stops})
    assert header(tmp_path / "runs.csv") == RUNS_HEADER
    assert header(tmp_path / "routes.csv") == ROUTES_HEADER


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_outputs_match_trace(tmp_path):
    inst = small_instance()
    a_route = greedy_insertion(inst, "heap").route
    runs, stops, routes = [], {}, {}
    for run_id, name in enumerate(ALGORITHMS):
        r, s, result = run("e0_test", run_id, inst, "origin", name, a_route=a_route)
        runs.append(r)
        stops[run_id] = s
        routes[run_id] = result.route
    write_outputs(tmp_path, runs, stops)

    route_rows = rows(tmp_path / "routes.csv")
    for run_id, name in enumerate(ALGORITHMS):
        route = routes[run_id]
        got = [row for row in route_rows if int(row["run_id"]) == run_id]
        expected = trace(inst, route)
        assert len(got) == len(route) + 2
        assert [int(row["step"]) for row in got] == list(range(len(route) + 2))
        for row, stop in zip(got, expected):
            assert row["experiment"] == "e0_test" and row["algorithm"] == name and row["base"] == "origin"
            for field in fields(Stop):
                assert type(getattr(stop, field.name))(row[field.name]) == getattr(stop, field.name)

    for row in rows(tmp_path / "runs.csv"):
        ev = evaluate(inst, routes[int(row["run_id"])])
        assert int(row["population"]) == ev.population
        assert float(row["distance_km"]) == ev.distance
        assert float(row["fuel_needed_kg"]) == ev.fuel_needed
        assert row["feasible"] == str(ev.feasible)


def test_read_runs(tmp_path):
    inst = small_instance()
    r0, s0, _ = run("e0_test", 0, inst, "origin", "a_heap")
    r1, s1, _ = run("e0_test", 1, inst, "origin", "nn", sample=7)
    write_outputs(tmp_path, [r0, r1], {0: s0, 1: s1})
    got = read_runs(tmp_path / "runs.csv")
    assert [row["run_id"] for row in got] == [0, 1]
    assert got[0]["sample"] is None and got[1]["sample"] == 7
    assert got[0]["stats"] == r0.stats and got[1]["stats"] == r1.stats
    assert isinstance(got[0]["stats"]["insertions"], int)
    assert got[0]["feasible"] is True and got[0]["population"] == r0.population
    assert got[0]["F"] == 4_000.0 and got[0]["time_s"] == r0.time_s
    with open(tmp_path / "runs.csv", newline="", encoding="utf-8") as f:
        assert list(csv.DictReader(f))[0]["sample"] == ""
