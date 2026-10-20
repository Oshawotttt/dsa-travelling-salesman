import math
import random

import pytest

from airdrop.model import Base, Instance, Params, Town, evaluate
from airdrop.prefix import RouteState

BASE0 = Base(0, "origin", 0.0, 0.0)


def random_instance(seed, n=35, params=Params()):
    rng = random.Random(seed)
    towns = [Town(i, f"t{i}", rng.uniform(-5, 5), rng.uniform(-5, 5), rng.randint(100, 10_000))
             for i in range(1, n + 1)]
    return Instance(BASE0, towns, params)


def random_routes(inst, seed, count=50, k_max=30):
    rng = random.Random(seed)
    return [rng.sample(range(1, inst.n + 1), rng.randint(0, k_max)) for _ in range(count)]


def check_all_moves(inst, route):
    state = RouteState(inst, route)
    k = len(route)
    assert state.route == tuple(route)
    assert state.fuel_needed == pytest.approx(evaluate(inst, route).fuel_needed, rel=1e-9)
    for t in (t for t in range(1, inst.n + 1) if t not in route):
        for pos in range(k + 1):
            expected = evaluate(inst, route[:pos] + [t] + route[pos:]).fuel_needed
            assert state.insert_fuel(t, pos) == pytest.approx(expected, rel=1e-6)
    for pos in range(k):
        expected = evaluate(inst, route[:pos] + route[pos + 1:]).fuel_needed
        assert state.remove_fuel(pos) == pytest.approx(expected, rel=1e-6)
    for i in range(k):
        for j in range(i + 1, k):
            expected = evaluate(inst, route[:i] + route[i:j + 1][::-1] + route[j + 1:]).fuel_needed
            assert state.two_opt_fuel(i, j) == pytest.approx(expected, rel=1e-6)


def test_matches_evaluate():
    inst = random_instance(10)
    for route in random_routes(inst, 11):
        check_all_moves(inst, route)


def test_matches_evaluate_b_zero():
    inst = random_instance(12, params=Params(b=0.0))
    for route in random_routes(inst, 13):
        check_all_moves(inst, route)


def test_best_insertion():
    inst = random_instance(14)
    for route in random_routes(inst, 15, count=20):
        state = RouteState(inst, route)
        for t in (t for t in range(1, inst.n + 1) if t not in route):
            fuels = [evaluate(inst, route[:p] + [t] + route[p:]).fuel_needed
                     for p in range(len(route) + 1)]
            pos, fuel = state.best_insertion(t)
            assert fuel == pytest.approx(min(fuels), rel=1e-9)
            assert fuels[pos] == pytest.approx(min(fuels), rel=1e-9)
    # with b = 0, before or after a single town is the same distance: smallest position wins
    flat = random_instance(16, n=3, params=Params(b=0.0))
    state = RouteState(flat, [1])
    assert state.insert_fuel(2, 0) == state.insert_fuel(2, 1)
    assert state.best_insertion(2)[0] == 0


def test_small_routes():
    inst = random_instance(17, n=3)
    empty = RouteState(inst, [])
    assert empty.fuel_needed == inst.params.R
    assert empty.insert_fuel(2, 0) == pytest.approx(evaluate(inst, [2]).fuel_needed, rel=1e-9)
    assert empty.best_insertion(2) == (0, empty.insert_fuel(2, 0))
    single = RouteState(inst, [1])
    assert single.remove_fuel(0) == pytest.approx(inst.params.R, rel=1e-12)
    for pos in (0, 1):
        expected = evaluate(inst, [2, 1] if pos == 0 else [1, 2]).fuel_needed
        assert single.insert_fuel(2, pos) == pytest.approx(expected, rel=1e-9)


def test_no_overflow():
    # long east-west hops along the equator, about 22,000 km in all
    towns = [Town(i, f"t{i}", 0.0, lon, 1000) for i, lon in enumerate([60, 120, 179, 120, 60], 1)]
    towns[3] = Town(4, "t4", 10.0, 120.0, 1000)
    towns[4] = Town(5, "t5", 10.0, 60.0, 1000)
    inst = Instance(BASE0, towns, Params(b=1e-3))
    route = [1, 2, 3, 4, 5]
    assert evaluate(inst, route).distance > 20_000
    check_all_moves(inst, route[:4])
    state = RouteState(inst, route)
    assert math.isfinite(state.fuel_needed)
    for value in [state.remove_fuel(p) for p in range(5)] + [state.two_opt_fuel(0, 4)]:
        assert math.isfinite(value)
    check_all_moves(inst, route)


def test_large_exponent_out_and_back():
    # far out, back to a town near the base, far out the other way: b*D from about 60 to 600
    towns = [Town(1, "t1", 0.0, 90.0, 1000), Town(2, "t2", 0.0, 1.0, 1000),
             Town(3, "t3", 0.0, -90.0, 1000)]
    for b in (1.5e-3, 3e-3, 1.2e-2, 1.5e-2):
        inst = Instance(BASE0, towns, Params(b=b))
        for route in ([1, 2, 3], [3, 2, 1], [1, 2], [2, 1, 3]):
            check_all_moves(inst, route)
