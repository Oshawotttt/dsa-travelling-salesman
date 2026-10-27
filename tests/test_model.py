import math
import random
from dataclasses import replace
from pathlib import Path

import pytest

from airdrop.model import (
    BASES,
    RURAL_BASES,
    URBAN_BASES,
    Base,
    Instance,
    Params,
    Town,
    control_params,
    evaluate,
    fuel_end,
    haversine_km,
    load_towns,
    trace,
)

DATA = Path(__file__).resolve().parents[1] / "data" / "cities_clean.csv"
BASE0 = Base(0, "origin", 0.0, 0.0)


def town(i, lat, lon, pop=1000):
    return Town(i, f"t{i}", lat, lon, pop)


def random_instance(seed, n=8, params=Params()):
    rng = random.Random(seed)
    towns = [town(i, rng.uniform(-2, 2), rng.uniform(-2, 2), rng.randint(100, 10_000))
             for i in range(1, n + 1)]
    return Instance(BASE0, towns, params)


def test_haversine():
    assert haversine_km(3.0, 101.0, 3.0, 101.0) == 0.0
    assert haversine_km(3.1412, 101.68653, 1.4655, 103.7578) == pytest.approx(296, abs=2)


def test_distance_matrix():
    inst = random_instance(1, n=5)
    points = [(BASE0.lat, BASE0.lon)] + [(t.lat, t.lon) for t in inst.towns]
    for i in range(inst.n + 1):
        assert inst.dist(i, i) == 0.0
        for j in range(inst.n + 1):
            assert inst.dist(i, j) == inst.dist(j, i)
            assert inst.dist(i, j) == pytest.approx(haversine_km(*points[i], *points[j]), rel=1e-12)


def test_empty_route():
    inst = random_instance(2)
    ev = evaluate(inst, [])
    assert ev.population == 0
    assert ev.distance == 0.0
    assert ev.fuel_needed == inst.params.R
    assert ev.feasible and ev.reason is None


def test_fuel_needed_closes():
    inst = random_instance(3)
    rng = random.Random(3)
    for _ in range(3):
        route = rng.sample(range(1, inst.n + 1), rng.randint(1, inst.n))
        ev = evaluate(inst, route)
        assert fuel_end(inst, route, ev.fuel_needed) == pytest.approx(inst.params.R, abs=1e-6)


def simulate_fuel_end(inst, route, F0, step=0.01):
    """Step-by-step flight: burn u = a + b*(cargo + fuel) per km, drop w at each town."""
    p = inst.params
    cargo, fuel = p.w * len(route), F0
    nodes = [0, *route, 0]
    for leg, (i, j) in enumerate(zip(nodes, nodes[1:])):
        remaining = inst.dist(i, j)
        while remaining > 0:
            dx = min(step, remaining)
            fuel -= (inst.a + inst.b * (cargo + fuel)) * dx
            remaining -= dx
        if leg < len(route):
            cargo -= p.w
    return fuel


def test_matches_simulation():
    # three towns about 110 km apart; base -> 1 -> 2 -> 3 -> base is about 500 km
    towns = [town(1, 0.0, 1.0), town(2, 1.0, 1.0), town(3, 1.0, 0.0)]
    inst = Instance(BASE0, towns, Params())
    route = [1, 2, 3]
    ev = evaluate(inst, route)
    assert 400 < ev.distance < 600
    assert simulate_fuel_end(inst, route, ev.fuel_needed) == pytest.approx(inst.params.R, abs=0.1)


def test_order_dependent():
    towns = [town(1, 0.0, 0.5), town(2, 0.0, 3.0), town(3, 1.0, 3.0)]
    inst = Instance(BASE0, towns, Params())
    assert evaluate(inst, [1, 2, 3]).fuel_needed != pytest.approx(
        evaluate(inst, [3, 2, 1]).fuel_needed, rel=1e-9)


def test_b_zero_control():
    towns = [town(1, 0.0, 0.5), town(2, 0.0, 3.0), town(3, 1.0, 3.0)]
    p0 = Params(b=0.0)
    inst = Instance(BASE0, towns, p0)
    d = (haversine_km(0, 0, 0, 0.5) + haversine_km(0, 0.5, 0, 3) + haversine_km(0, 3, 1, 3)
         + haversine_km(1, 3, 0, 0))
    forward = evaluate(inst, [1, 2, 3]).fuel_needed
    assert forward == pytest.approx(p0.R + 7.0e-5 * 33_600 * d, rel=1e-12)
    assert evaluate(inst, [3, 2, 1]).fuel_needed == pytest.approx(forward, rel=1e-12)
    tiny = Instance(BASE0, towns, Params(b=1e-12))
    assert evaluate(tiny, [1, 2, 3]).fuel_needed == pytest.approx(forward, abs=1e-3)


def test_params_defaults_and_control():
    inst = Instance(BASE0, [], Params())
    assert inst.a == pytest.approx(2.352, abs=1e-12)
    assert inst.b == 7.0e-5
    explicit = Instance(BASE0, [], Params(a=3.0, b=1e-4))
    assert (explicit.a, explicit.b) == (3.0, 1e-4)
    ctrl = control_params(Params())
    assert ctrl.b == 0
    assert ctrl.a == pytest.approx(4.2, abs=1e-9)
    assert replace(ctrl, a=None, b=None) == Params()


def test_infeasible_reasons():
    towns = [town(1, 0.0, 1.0), town(2, 0.0, 10.0)]
    p = Params()
    inst = Instance(BASE0, towns, p)
    assert evaluate(inst, [0]).reason == "bad_index"
    assert evaluate(inst, [3]).reason == "bad_index"
    assert evaluate(inst, [1, 1]).reason == "duplicate"
    assert evaluate(Instance(BASE0, towns, replace(p, C=199.0)), [1]).reason == "payload"
    # town 2 is about 2,200 km away and back: needs far more than R + 2,000 kg
    assert evaluate(Instance(BASE0, towns, replace(p, F=p.R + 2_000)), [2]).reason == "fuel_cap"
    tight = replace(p, F=1e9, MTOW=p.E + p.w + p.R + 2_000)
    assert evaluate(Instance(BASE0, towns, tight), [2]).reason == "takeoff_weight"
    for ev in (evaluate(inst, [1]), evaluate(inst, [1, 2])):
        assert ev.feasible and ev.reason is None


def test_overflow_is_infeasible():
    towns = [town(1, 0.0, 1.0), town(2, 1.0, 1.0)]
    for params in (Params(b=2.0), Params(b=2.0, a=0.0), Params(b=2.0, a=0.0, R=0.0)):
        ev = evaluate(Instance(BASE0, towns, params), [1, 2])
        assert ev.fuel_needed == math.inf
        assert not ev.feasible and ev.reason == "fuel_cap"


def test_bases():
    assert len(BASES) == 6
    assert set(BASES) == set(RURAL_BASES) | set(URBAN_BASES)
    assert set(RURAL_BASES) == {"perak", "sarawak", "sabah"}
    assert set(URBAN_BASES) == {"klia", "kuching", "kota_kinabalu"}
    assert {b.geonameid for b in BASES.values()} == {
        1734611, 1737158, 1733926, 6301255, 1734503, 1772439,
    }


@pytest.mark.skipif(not DATA.exists(), reason="data/cities_clean.csv missing")
def test_data_smoke():
    towns = load_towns(DATA, min_population=0)
    assert len(towns) == 745
    expected = {
        "perak": 30.8, "sarawak": 40.0, "sabah": 39.7,
        "klia": 6.2, "kuching": 7.4, "kota_kinabalu": 1.7,
    }
    for key, km in expected.items():
        base = BASES[key]
        nearest = min(haversine_km(base.lat, base.lon, t.lat, t.lon) for t in towns)
        assert nearest == pytest.approx(km, abs=0.5)


def test_trace_empty():
    inst = random_instance(4)
    stops = trace(inst, [])
    assert [(s.step, s.index, s.population) for s in stops] == [(0, 0, 0), (1, 0, 0)]
    assert [s.fuel_kg for s in stops] == [inst.params.R, inst.params.R]
    assert stops[0].geonameid == stops[1].geonameid == BASE0.geonameid


def test_trace_errors():
    inst = random_instance(5, n=3)
    for route in ([0], [4], ["1"]):
        with pytest.raises(ValueError):
            trace(inst, route)
    with pytest.raises(ValueError):
        trace(Instance(BASE0, inst.towns, Params(b=2.0)), [1, 2])


def feasible_routes(seed, params):
    """A few random feasible routes of 1..8 towns on an 8-town instance, with their instance."""
    inst = random_instance(seed, params=params)
    rng = random.Random(seed)
    routes = [rng.sample(range(1, inst.n + 1), rng.randint(1, inst.n)) for _ in range(4)]
    assert all(evaluate(inst, route).feasible for route in routes)
    return inst, routes


def test_trace_endpoints():
    for params in (Params(), control_params(Params())):
        inst, routes = feasible_routes(6, params)
        for route in routes:
            ev = evaluate(inst, route)
            stops = trace(inst, route)
            assert len(stops) == len(route) + 2
            takeoff, landing = stops[0], stops[-1]
            assert (takeoff.step, takeoff.index, landing.step, landing.index) == (0, 0, len(route) + 1, 0)
            assert [s.index for s in stops[1:-1]] == route
            assert [s.step for s in stops] == list(range(len(route) + 2))
            assert takeoff.fuel_kg == ev.fuel_needed
            assert takeoff.cargo_kg == inst.params.w * len(route)
            assert (takeoff.leg_km, takeoff.distance_km, takeoff.leg_fuel_kg) == (0.0, 0.0, 0.0)
            assert landing.fuel_kg == pytest.approx(inst.params.R, rel=1e-6)
            assert landing.distance_km == pytest.approx(ev.distance, rel=1e-12)
            assert landing.population_reached == ev.population
            assert landing.cargo_kg == 0.0
            for s in stops[1:-1]:
                t = inst.towns[s.index - 1]
                assert (s.geonameid, s.name, s.lat, s.lon, s.population) == (
                    t.geonameid, t.name, t.lat, t.lon, t.population)


def simulate_stops(inst, route, F0, step=0.01):
    """Fuel on arrival at each drop and at landing, from the step-by-step flight above."""
    p = inst.params
    cargo, fuel, arrivals = p.w * len(route), F0, []
    nodes = [0, *route, 0]
    for leg, (i, j) in enumerate(zip(nodes, nodes[1:])):
        remaining = inst.dist(i, j)
        while remaining > 0:
            dx = min(step, remaining)
            fuel -= (inst.a + inst.b * (cargo + fuel)) * dx
            remaining -= dx
        arrivals.append(fuel)
        if leg < len(route):
            cargo -= p.w
    return arrivals


def test_trace_matches_fuel_end():
    for params in (Params(), control_params(Params())):
        inst, routes = feasible_routes(7, params)
        for route in routes:
            F0 = evaluate(inst, route).fuel_needed
            stops = trace(inst, route)
            assert stops[-1].fuel_kg == pytest.approx(fuel_end(inst, route, F0), rel=1e-9)
            arrivals = simulate_stops(inst, route, F0)
            for s, fuel in zip(stops[1:], arrivals):
                assert s.fuel_kg == pytest.approx(fuel, abs=0.01)


def test_trace_invariants():
    for params in (Params(), control_params(Params())):
        inst, routes = feasible_routes(8, params)
        p = inst.params
        for route in routes:
            stops = trace(inst, route)
            for prev, s in zip(stops, stops[1:]):
                assert s.fuel_kg <= prev.fuel_kg
                assert s.leg_fuel_kg == pytest.approx(prev.fuel_kg - s.fuel_kg, rel=1e-12, abs=1e-9)
                assert s.leg_km == pytest.approx(inst.dist(prev.index, s.index), rel=1e-12)
                assert s.distance_km == pytest.approx(prev.distance_km + s.leg_km, rel=1e-12)
                assert s.population_reached == prev.population_reached + s.population
                expected_cargo = prev.cargo_kg - (p.w if prev.step > 0 else 0.0)
                assert s.cargo_kg == pytest.approx(expected_cargo, abs=1e-9)
            for s in stops:
                assert s.weight_kg == pytest.approx(p.E + s.cargo_kg + s.fuel_kg, rel=1e-12)


def test_trace_exported():
    import airdrop
    assert airdrop.trace is trace
    assert "Stop" in airdrop.__all__ and "trace" in airdrop.__all__
