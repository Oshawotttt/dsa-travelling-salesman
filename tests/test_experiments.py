import csv
import random
import shutil
from dataclasses import fields

import pytest

from airdrop.approach_a import greedy_insertion
from airdrop.approach_b import local_search
from airdrop.baseline import nearest_neighbour
from airdrop.exact_dp import exact_dp
from airdrop.model import BASES, Base, Instance, Params, Stop, Town, evaluate, trace
from experiments.e1_heap_vs_scan import run as e1
from experiments.e2_run_time import run as e2
from experiments.e3_bases import run as e3
from experiments.e4_optimality_gap import run as e4
from experiments import maps
from experiments.common import ALGORITHMS, read_routes, read_runs, run, solve, write_outputs

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


def test_run_needs_a_repeat():
    with pytest.raises(ValueError):
        run("e0_test", 0, small_instance(), "origin", "nn", repeats=0)


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


def towns_near(base, seed, n):
    """n towns within about 1 degree of a base, populations spread over 1,000..200,000."""
    rng = random.Random(seed)
    return [Town(i, f"t{i}", base.lat + rng.uniform(-1, 1), base.lon + rng.uniform(-1, 1),
                 rng.randint(1_000, 200_000)) for i in range(1, n + 1)]


def assert_conforms(out_dir):
    """Both output files have the section 4 headers, and routes.csv has len(route) + 2 rows per run."""
    assert header(out_dir / "runs.csv") == RUNS_HEADER
    assert header(out_dir / "routes.csv") == ROUTES_HEADER
    route_rows = rows(out_dir / "routes.csv")
    runs = read_runs(out_dir / "runs.csv")
    assert len({r["run_id"] for r in runs}) == len(runs)
    for r in runs:
        steps = [int(row["step"]) for row in route_rows if int(row["run_id"]) == r["run_id"]]
        assert steps == list(range(r["towns_visited"] + 2))
    return runs


def assert_plot_from_csv_alone(plot, out_dir, tmp_path):
    """plot works on a folder holding only runs.csv, and writes a non-empty plot.png."""
    alone = tmp_path / "alone"
    alone.mkdir()
    shutil.copy(out_dir / "runs.csv", alone / "runs.csv")
    plot(alone)
    assert (alone / "plot.png").stat().st_size > 0


def test_e1(tmp_path):
    towns = towns_near(BASES["perak"], 1, 12)
    thresholds = (100_000, 0)
    e1.run_experiment(towns, tmp_path, thresholds=thresholds, repeats=1)
    runs = assert_conforms(tmp_path)
    assert sorted((r["n_towns"], r["algorithm"]) for r in runs) == sorted(
        (sum(t.population >= thr for t in towns), name) for thr in thresholds for name in ("a_heap", "a_scan"))
    assert all(r["F"] == 21_100 for r in runs)
    assert all("mismatches" in r["stats"] for r in runs if r["algorithm"] == "a_heap")
    assert_plot_from_csv_alone(e1.plot, tmp_path, tmp_path)


def test_e2(tmp_path):
    towns = towns_near(BASES["perak"], 2, 12)
    thresholds = (100_000, 0)
    e2.run_experiment(towns, tmp_path, thresholds=thresholds, repeats=1)
    runs = assert_conforms(tmp_path)
    assert sorted((r["n_towns"], r["algorithm"]) for r in runs) == sorted(
        (sum(t.population >= thr for t in towns), name)
        for thr in thresholds for name in ("nn", "a_heap", "a_scan", "b"))
    assert all(r["F"] == 21_100 for r in runs)
    assert_plot_from_csv_alone(e2.plot, tmp_path, tmp_path)


def test_read_routes(tmp_path):
    inst = small_instance()
    r0, s0, _ = run("e0_test", 0, inst, "origin", "a_heap")
    r1, s1, _ = run("e0_test", 1, inst, "origin", "nn")
    write_outputs(tmp_path, [r0, r1], {0: s0, 1: s1})
    assert read_routes(tmp_path / "routes.csv") == {0: s0, 1: s1}


def maps_output(tmp_path):
    """Two instances (F 4,000 and 5,000 kg) with two runs each, plus a second sample at 4,000 kg."""
    runs, stops = [], {}
    for F, sample, names in ((4_000.0, 0, ("nn", "a_heap")), (5_000.0, 0, ("b", "a_scan")),
                             (4_000.0, 1, ("dp",))):
        inst = small_instance(params=Params(F=F))
        for name in names:
            r, s, _ = run("e0_test", len(runs), inst, "origin", name, sample=sample)
            runs.append(r)
            stops[r.run_id] = s
    write_outputs(tmp_path, runs, stops)
    return stops


def test_maps_one_per_instance(tmp_path):
    stops = maps_output(tmp_path)
    paths = maps.write_maps(tmp_path)
    assert [p.name for p in paths] == ["origin_n8_s0_F4000.html", "origin_n8_s0_F5000.html",
                                       "origin_n8_s1_F4000.html"]
    assert all(p.parent == (tmp_path / "maps").resolve() for p in paths)
    first = paths[0].read_text(encoding="utf-8")
    assert "e0_test: origin, 8 towns, sample 0, F 4,000 kg" in first
    assert "NN" in first and "A" in first and "A scan" not in first
    for s in stops[0][1:-1] + stops[1][1:-1]:
        assert s.name in first
    assert "A scan" in paths[1].read_text(encoding="utf-8")


def test_maps_cli(tmp_path, capsys):
    maps_output(tmp_path)
    maps.main([str(tmp_path), "--out", str(tmp_path / "elsewhere")])
    printed = capsys.readouterr().out.split()
    assert len(printed) == 3 and all("elsewhere" in line for line in printed)
    with pytest.raises(SystemExit):
        maps.main([str(tmp_path / "missing")])
    with pytest.raises(SystemExit):
        maps.main([str(tmp_path), str(tmp_path), "--out", str(tmp_path / "x")])


def test_e3(tmp_path):
    towns = [Town(100 * k + t.geonameid, t.name, t.lat, t.lon, t.population)
             for k, key in enumerate(BASES) for t in towns_near(BASES[key], k, 2)]
    e3.run_experiment(towns, tmp_path)
    runs = assert_conforms(tmp_path)
    algorithms = ("nn", "a_heap", "b", "b_on_a")
    assert sorted((r["base"], r["algorithm"]) for r in runs) == sorted(
        (base, name) for base in BASES for name in algorithms)
    assert all(r["F"] == 21_100 and r["n_towns"] == len(towns) for r in runs)
    population = {(r["base"], r["algorithm"]): r["population"] for r in runs}
    for base in BASES:
        assert population[base, "b_on_a"] >= population[base, "a_heap"]
    assert_plot_from_csv_alone(e3.plot, tmp_path, tmp_path)


R = Params().R


def gap_samples():
    pool = towns_near(BASES["perak"], 4, 15)
    return [random.Random(seed).sample(pool, 6) for seed in range(5)]


def dp_lengths(samples, F):
    return [len(exact_dp(Instance(BASES["perak"], s, Params(F=F))).route) for s in samples]


def test_full_fit_F():
    samples = gap_samples()
    F = e4.full_fit_F(samples, BASES["perak"], min_samples=3)
    assert F % 10 == 0 and R <= F <= 21_100
    assert sum(k == 6 for k in dp_lengths(samples, F)) >= 3
    assert sum(k == 6 for k in dp_lengths(samples, F - 10)) < 3


def test_coverage_F():
    samples = gap_samples()
    F = e4.coverage_F(samples, BASES["perak"], share=0.8)
    assert F % 10 == 0 and R <= F <= 21_100
    # 80% of 5 samples x 6 towns is 24 towns in all; these samples reach exactly 24
    assert sum(dp_lengths(samples, F)) == 24
    assert sum(dp_lengths(samples, F - 10)) < 24


def run_e4(towns, out_dir):
    e4.run_experiment(towns, out_dir, seeds=(0, 1), sample_size=6, min_samples=2)


def test_e4(tmp_path):
    towns = towns_near(BASES["perak"], 5, 15)
    run_e4(towns, tmp_path)
    runs = assert_conforms(tmp_path)
    heuristics = ("nn", "a_heap", "b", "b_on_a")
    Fs = sorted({r["F"] for r in runs})
    assert len(Fs) == 2
    assert sorted((r["sample"], r["F"], r["algorithm"]) for r in runs) == sorted(
        (seed, F, name) for seed in (0, 1) for F in Fs for name in ("dp", *heuristics))
    assert all(r["n_towns"] == 6 for r in runs)
    dp = {(r["sample"], r["F"]): r["population"] for r in runs if r["algorithm"] == "dp"}
    for r in runs:
        assert r["population"] <= dp[r["sample"], r["F"]]
    assert_plot_from_csv_alone(e4.plot, tmp_path, tmp_path)


def test_e4_deterministic(tmp_path):
    towns = towns_near(BASES["perak"], 5, 15)
    run_e4(towns, tmp_path / "one")
    run_e4(towns, tmp_path / "two")
    assert (tmp_path / "one" / "routes.csv").read_bytes() == (tmp_path / "two" / "routes.csv").read_bytes()
    strip = lambda runs: [{k: v for k, v in r.items() if k != "time_s"} for r in runs]
    assert strip(read_runs(tmp_path / "one" / "runs.csv")) == strip(read_runs(tmp_path / "two" / "runs.csv"))
