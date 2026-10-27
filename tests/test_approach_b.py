import random

import pytest

from airdrop.approach_a import greedy_insertion
from airdrop.approach_b import local_search
from airdrop.baseline import nearest_neighbour
from airdrop.model import Base, Instance, Params, Town, evaluate

BASE0 = Base(0, "origin", 0.0, 0.0)
HUGE = Params(F=1e9, C=1e9, MTOW=1e12)
STATS = {"rounds", "two_opt", "add", "swap", "replace_1_2", "hit_max_rounds"}


def random_instance(seed, n=7, F=4_000.0, drops=4):
    rng = random.Random(seed)
    towns = [Town(i, f"t{i}", rng.uniform(-2, 2), rng.uniform(-2, 2), rng.randint(100, 10_000))
             for i in range(1, n + 1)]
    return Instance(BASE0, towns, Params(F=F, C=200.0 * drops))


SMALL = [random_instance(seed, F=F, drops=drops)
         for seed in range(6) for F in (3_500.0, 4_500.0) for drops in (4, 7)]


def seeds(inst):
    """Nearest neighbour fills up the route (swaps, 2-opt); the empty route needs adds and
    replacements first. Between them every move type is used."""
    return [nearest_neighbour(inst).route, []]


def cheapest(inst, route, t):
    """route with t inserted at its cheapest position (smallest position on ties), by evaluate."""
    options = [route[:p] + [t] + route[p:] for p in range(len(route) + 1)]
    return min(options, key=lambda r: evaluate(inst, r).fuel_needed)


def oracle_moves(inst, route):
    """Every improving move of the four types, with no candidate limit, as
    (-gain, fuel, type, ids, new_route), built with evaluate only."""
    pop = inst.population
    cur = evaluate(inst, route).fuel_needed
    k = len(route)
    unvisited = [t for t in range(1, inst.n + 1) if t not in route]
    moves = []

    def offer(gain, kind, ids, new):
        ev = evaluate(inst, new)
        if ev.feasible and (gain > 0 or ev.fuel_needed < cur):
            moves.append((-gain, ev.fuel_needed, kind, ids, new))

    for i in range(k):
        for j in range(i + 1, k):
            offer(0, 0, (i, j), route[:i] + route[i:j + 1][::-1] + route[j + 1:])
    for t in unvisited:
        if pop(t) > 0:
            offer(pop(t), 1, (t,), cheapest(inst, route, t))
    for p, r in enumerate(route):
        rest = route[:p] + route[p + 1:]
        for u in unvisited:
            if pop(u) > pop(r):
                offer(pop(u) - pop(r), 2, (r, u), cheapest(inst, rest, u))
            for v in unvisited:
                if v != u and pop(u) + pop(v) > pop(r):
                    offer(pop(u) + pop(v) - pop(r), 3, (r, u, v),
                          cheapest(inst, cheapest(inst, rest, u), v))
    return moves


def oracle_step(inst, route):
    """(new route, move type) of the best move, or None at a local optimum."""
    moves = oracle_moves(inst, route)
    if not moves:
        return None
    best = min(moves)
    return best[4], best[2]


def oracle_descent(inst, route):
    kinds = []
    while (step := oracle_step(inst, route)) is not None:
        route, kind = step
        kinds.append(kind)
    return route, kinds


def test_not_worse_than_seed():
    for inst in SMALL + [random_instance(seed, n=20, F=6_000.0, drops=10) for seed in range(3)]:
        seed_eval = nearest_neighbour(inst).eval
        result = local_search(inst)
        assert result.eval.feasible
        assert result.eval.population >= seed_eval.population
        if result.eval.population == seed_eval.population:
            assert result.eval.fuel_needed <= seed_eval.fuel_needed


def segments_cross(p1, p2, p3, p4):
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return (orient(p1, p2, p3) * orient(p1, p2, p4) < 0
            and orient(p3, p4, p1) * orient(p3, p4, p2) < 0)


def crossings(inst, route):
    pts = [(0.0, 0.0)] + [(t.lat, t.lon) for t in inst.towns]
    nodes = [0, *route, 0]
    edges = [(pts[a], pts[b]) for a, b in zip(nodes, nodes[1:])]
    return sum(segments_cross(*edges[i], *edges[j])
               for i in range(len(edges)) for j in range(i + 2, len(edges))
               if not (i == 0 and j == len(edges) - 1))


def test_two_opt_uncrosses():
    towns = [Town(1, "a", 1.0, 1.0, 1), Town(2, "b", 1.0, 2.0, 1),
             Town(3, "c", 2.0, 2.0, 1), Town(4, "d", 2.0, 1.0, 1)]
    inst = Instance(BASE0, towns, HUGE)
    crossed = [1, 3, 2, 4]
    assert crossings(inst, crossed) > 0
    result = local_search(inst, initial=crossed)
    assert result.stats["two_opt"] >= 1
    assert result.eval.fuel_needed < evaluate(inst, crossed).fuel_needed
    assert crossings(inst, result.route) == 0


def test_add():
    towns = [Town(1, "a", 0.0, 1.0, 500), Town(2, "b", 1.0, 1.0, 700)]
    inst = Instance(BASE0, towns, HUGE)
    result = local_search(inst, initial=[1])
    assert sorted(result.route) == [1, 2]
    assert result.stats["add"] == 1


def test_swap():
    # room for one drop: the more populous town replaces the seed
    towns = [Town(1, "near", 0.0, 0.5, 10), Town(2, "far", 0.0, 2.0, 100)]
    inst = Instance(BASE0, towns, Params(F=1e9, MTOW=1e12, C=200.0))
    result = local_search(inst, initial=[1])
    assert result.route == [2]
    assert result.stats["swap"] == 1


def replace_instance():
    # A is far and alone worth 10; B and C near the base are worth 6 each. A plus either does
    # not fit, neither beats A alone, but the pair does.
    towns = [Town(1, "A", 0.0, 3.0, 10), Town(2, "B", 0.3, 0.0, 6), Town(3, "C", -0.3, 0.0, 6)]
    roomy = Instance(BASE0, towns, HUGE)
    F = evaluate(roomy, [1]).fuel_needed + 10
    inst = Instance(BASE0, towns, Params(F=F))
    assert not evaluate(inst, [2, 1]).feasible and not evaluate(inst, [1, 3]).feasible
    assert evaluate(inst, [2, 3]).feasible
    return inst


def test_replace_1_2():
    inst = replace_instance()
    result = local_search(inst, initial=[1])
    assert sorted(result.route) == [2, 3]
    assert result.stats["replace_1_2"] == 1
    assert result.stats["add"] == result.stats["swap"] == 0


def test_replace_neighbourhood_L():
    inst = replace_instance()
    assert local_search(inst, initial=[1], L=1).route == [1]
    assert local_search(inst, initial=[1], L=1).stats["replace_1_2"] == 0
    for inst in SMALL:
        for seed in seeds(inst):
            route, _ = oracle_descent(inst, seed)
            for L in (inst.n, inst.n + 5):
                assert local_search(inst, initial=seed, L=L).route == route


def test_best_move_chosen():
    kinds = set()
    for inst in SMALL:
        for seed in seeds(inst):
            route, rounds = seed, 0
            while (step := oracle_step(inst, route)) is not None:
                route, kind = step
                kinds.add(kind)
                rounds += 1
                result = local_search(inst, initial=seed, L=inst.n, max_rounds=rounds)
                assert result.route == route
                assert result.stats["rounds"] == rounds
            final = local_search(inst, initial=seed, L=inst.n, max_rounds=rounds)
            assert final.route == route and final.stats["hit_max_rounds"] == 0
    assert kinds == {0, 1, 2, 3}  # 2-opt, add, swap and replace 1 with 2 all exercised


def test_local_optimum():
    for inst in SMALL:
        for seed in seeds(inst):
            result = local_search(inst, initial=seed, L=inst.n)
            assert oracle_moves(inst, result.route) == []


def test_custom_seed():
    inst = random_instance(3, n=12, F=6_000.0, drops=8)
    seed = greedy_insertion(inst, "scan").route
    assert local_search(inst, initial=seed, max_rounds=0).route == seed
    result = local_search(inst, initial=seed)
    assert result.eval.population >= evaluate(inst, seed).population
    assert local_search(inst).route == local_search(inst, initial=nearest_neighbour(inst).route).route
    with pytest.raises(ValueError):
        local_search(inst, initial=list(range(1, inst.n + 1)))


def test_consistent_and_stats():
    for inst in SMALL:
        result = local_search(inst)
        assert result.eval == evaluate(inst, result.route)
        assert local_search(inst) == result
        assert set(result.stats) == STATS
        moves = sum(result.stats[m] for m in ("two_opt", "add", "swap", "replace_1_2"))
        assert result.stats["rounds"] == moves
    capped = local_search(replace_instance(), initial=[1], max_rounds=0)
    assert capped.stats["hit_max_rounds"] == 1 and capped.route == [1]
