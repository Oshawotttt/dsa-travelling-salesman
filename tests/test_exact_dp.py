import random
from itertools import permutations

import pytest

from airdrop.approach_a import greedy_insertion
from airdrop.approach_b import local_search
from airdrop.baseline import nearest_neighbour
from airdrop.exact_dp import exact_dp
from airdrop.model import Base, Instance, Params, Town, control_params, evaluate

BASE0 = Base(0, "origin", 0.0, 0.0)


def random_instance(seed, n, params=Params()):
    rng = random.Random(seed)
    towns = [Town(i, f"t{i}", rng.uniform(-2, 2), rng.uniform(-2, 2), rng.randint(100, 10_000))
             for i in range(1, n + 1)]
    return Instance(BASE0, towns, params)


def test_max_n():
    inst = random_instance(0, n=4)
    with pytest.raises(ValueError):
        exact_dp(inst, max_n=3)
    with pytest.raises(ValueError):
        exact_dp(random_instance(0, n=16))


def brute_force(inst):
    """(population, fuel needed) of the best route over every ordered subset, by evaluate."""
    best = (0, inst.params.R)
    for k in range(1, inst.n + 1):
        for route in permutations(range(1, inst.n + 1), k):
            ev = evaluate(inst, route)
            if ev.feasible and (ev.population, -ev.fuel_needed) > (best[0], -best[1]):
                best = (ev.population, ev.fuel_needed)
    return best


# tight F lets a few towns in, loose F lets the payload or takeoff weight bind
SMALL = [random_instance(seed, n=1 + seed % 7, params=params)
         for seed, params in enumerate([Params(F=3_500.0, C=800.0), Params(F=6_000.0, C=1_000.0),
                                        control_params(Params(F=3_500.0, C=800.0)),
                                        Params(MTOW=Params().E + 3_000.0)] * 5)]


@pytest.mark.parametrize("inst", SMALL)
def test_matches_brute_force(inst):
    ev = exact_dp(inst).eval
    population, fuel = brute_force(inst)
    assert ev.population == population
    assert ev.fuel_needed == pytest.approx(fuel, rel=1e-6)


@pytest.mark.parametrize("inst", SMALL)
def test_consistent(inst):
    result = exact_dp(inst)
    assert result.eval == evaluate(inst, result.route)
    assert result.eval.feasible
    assert set(result.stats) == {"states", "transitions"}


def test_beats_heuristics():
    for seed in range(10):
        inst = random_instance(100 + seed, n=12, params=Params(F=4_000.0, C=1_400.0))
        dp = exact_dp(inst).eval.population
        greedy = greedy_insertion(inst).route
        others = [nearest_neighbour(inst), greedy_insertion(inst), greedy_insertion(inst, "scan"),
                  local_search(inst), local_search(inst, initial=greedy)]
        for other in others:
            assert dp >= other.eval.population


def test_nothing_fits():
    # the only town is about 1,100 km away: more than the tank holds for the round trip
    inst = Instance(BASE0, [Town(1, "far", 0.0, 10.0, 5_000)], Params(F=3_000.0))
    result = exact_dp(inst)
    assert result.route == []
    assert result.eval.population == 0
    assert exact_dp(Instance(BASE0, [], Params())).route == []


def test_deterministic():
    inst = random_instance(7, n=9, params=Params(F=4_000.0, C=1_000.0))
    assert exact_dp(inst) == exact_dp(inst)
