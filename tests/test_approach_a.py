import math
import random

from airdrop.approach_a import greedy_insertion
from airdrop.model import Base, Instance, Params, Town, evaluate

BASE0 = Base(0, "origin", 0.0, 0.0)


def random_instance(seed, n=25, F=6_000.0):
    rng = random.Random(seed)
    towns = [Town(i, f"t{i}", rng.uniform(-3, 3), rng.uniform(-3, 3), rng.randint(100, 10_000))
             for i in range(1, n + 1)]
    return Instance(BASE0, towns, Params(F=F))


INSTANCES = [random_instance(seed) for seed in range(5)]


def oracle_scan(inst):
    """Greedy insertion written with evaluate only: each step, among towns whose cheapest
    insertion stays feasible, insert the best population / marginal fuel at that position."""
    route, left = [], set(range(1, inst.n + 1))
    while True:
        current = evaluate(inst, route).fuel_needed
        best = None
        for t in sorted(left):
            options = [(evaluate(inst, route[:p] + [t] + route[p:]), p) for p in range(len(route) + 1)]
            ev, pos = min(options, key=lambda o: (o[0].fuel_needed, o[1]))
            if not ev.feasible:
                left.discard(t)
                continue
            marginal = ev.fuel_needed - current
            score = inst.population(t) / marginal if marginal > 0 else math.inf
            key = (score, inst.population(t), -t)
            if best is None or key > best[0]:
                best = (key, t, pos)
        if best is None:
            return route
        _, t, pos = best
        route.insert(pos, t)
        left.discard(t)


def test_scan_feasible():
    for inst in INSTANCES:
        result = greedy_insertion(inst, "scan")
        assert result.eval.feasible
        assert 0 < len(result.route) < inst.n


def test_result_matches_evaluate():
    for inst in INSTANCES:
        result = greedy_insertion(inst, "scan")
        assert result.eval == evaluate(inst, result.route)


def test_scan_is_argmax():
    for inst in INSTANCES:
        assert greedy_insertion(inst, "scan").route == oracle_scan(inst)


def test_budget_extremes():
    inst = INSTANCES[0]
    single = min(evaluate(inst, [t]).fuel_needed for t in range(1, inst.n + 1))
    starved = Instance(BASE0, inst.towns, Params(F=(inst.params.R + single) / 2))
    assert greedy_insertion(starved, "scan").route == []
    huge = Instance(BASE0, inst.towns, Params(F=1e9, C=1e9, MTOW=1e12))
    assert sorted(greedy_insertion(huge, "scan").route) == list(range(1, inst.n + 1))


def test_weight_drives_choice():
    # all on the equator: X far out, B near X, A near the base; A and B both sit on the
    # base -> X leg, so either adds no distance. Only the 200 kg carried from the base differs.
    X = Town(1, "X", 0.0, 4.0, 1_000_000)
    B = Town(2, "B", 0.0, 3.0, 1_000)
    A = Town(3, "A", 0.0, 1.0, 1_000)
    roomy = Instance(BASE0, [X, B, A], Params())
    # room for X plus one of A, B but not both
    F = evaluate(roomy, [2, 1]).fuel_needed + 0.1
    assert evaluate(roomy, [3, 2, 1]).fuel_needed > F
    inst = Instance(BASE0, [X, B, A], Params(F=F))
    assert greedy_insertion(inst, "scan").route == [3, 1]


def test_scan_deterministic():
    for inst in INSTANCES:
        assert greedy_insertion(inst, "scan") == greedy_insertion(inst, "scan")


def test_scan_stats():
    inst = INSTANCES[0]
    result = greedy_insertion(inst, "scan")
    assert set(result.stats) == {"score_evals", "insertions"}
    assert result.stats["insertions"] == len(result.route)
    assert result.stats["score_evals"] >= inst.n


def test_heap_feasible():
    for inst in INSTANCES:
        result = greedy_insertion(inst, "heap")
        assert result.eval.feasible
        assert result.eval == evaluate(inst, result.route)
        assert 0 < len(result.route) < inst.n


def test_heap_first_pick_matches_scan():
    # payload for one drop only, so the route is exactly the first pick
    for seed in range(10):
        inst = random_instance(seed)
        one = Instance(BASE0, inst.towns, Params(F=inst.params.F, C=200.0))
        heap, scan = greedy_insertion(one, "heap").route, greedy_insertion(one, "scan").route
        assert len(scan) == 1
        assert heap == scan


def test_audit_consistent():
    instances = INSTANCES + [random_instance(seed, n=12, F=F)
                             for seed in range(10, 20) for F in (3_000.0, 4_000.0)]
    clean = 0
    for inst in instances:
        result = greedy_insertion(inst, "heap", audit=True)
        assert result.route == greedy_insertion(inst, "heap").route
        if result.stats["mismatches"] == 0:
            clean += 1
            assert result.route == greedy_insertion(inst, "scan").route
    assert clean > 0


def test_audit_detects_rise():
    # X far out on the equator is picked first. C, just past X, is dear from the empty route
    # but cheap next to X, so its score rises above D's; the heap still holds C's old key.
    X = Town(1, "X", 0.0, 4.0, 1_000_000)
    C = Town(2, "C", 0.0, 4.5, 1_000)
    D = Town(3, "D", 1.5, 0.0, 1_000)
    inst = Instance(BASE0, [X, C, D], Params(F=1e9, C=1e9, MTOW=1e12))
    result = greedy_insertion(inst, "heap", audit=True)
    assert result.stats["mismatches"] >= 1
    assert sorted(result.route) == [1, 2, 3]


def test_heap_stats():
    inst = INSTANCES[0]
    plain = greedy_insertion(inst, "heap")
    assert set(plain.stats) == {"score_evals", "insertions", "heap_pops", "heap_pushes"}
    assert plain.stats["insertions"] == len(plain.route)
    assert plain.stats["heap_pops"] >= plain.stats["insertions"]
    audited = greedy_insertion(inst, "heap", audit=True)
    assert set(audited.stats) == set(plain.stats) | {"mismatches"}


def test_heap_deterministic():
    for inst in INSTANCES:
        assert greedy_insertion(inst, "heap", audit=True) == greedy_insertion(inst, "heap", audit=True)
