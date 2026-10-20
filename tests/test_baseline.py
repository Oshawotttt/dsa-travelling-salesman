import random

from airdrop.baseline import nearest_neighbour
from airdrop.model import Base, Instance, Params, Town, evaluate

BASE0 = Base(0, "origin", 0.0, 0.0)


def random_instance(seed, n=25, F=6_000.0):
    rng = random.Random(seed)
    towns = [Town(i, f"t{i}", rng.uniform(-3, 3), rng.uniform(-3, 3), rng.randint(100, 10_000))
             for i in range(1, n + 1)]
    return Instance(BASE0, towns, Params(F=F))


INSTANCES = [random_instance(seed, F=F) for seed in range(5) for F in (4_000.0, 8_000.0)]


def test_nn_feasible():
    for inst in INSTANCES:
        result = nearest_neighbour(inst)
        assert result.eval.feasible
        assert len(result.route) > 0
        assert nearest_neighbour(inst) == result


def test_nn_is_nearest():
    for inst in INSTANCES:
        route = nearest_neighbour(inst).route
        current, left = 0, set(range(1, inst.n + 1))
        for step in range(len(route) + 1):
            fitting = [t for t in sorted(left, key=lambda t: (inst.dist(current, t), t))
                       if evaluate(inst, route[:step] + [t]).feasible]
            if step == len(route):
                assert fitting == []  # stops only when no town fits
            else:
                assert route[step] == fitting[0]
                current = route[step]
                left.discard(current)


def test_nn_skips_unfit():
    A = Town(1, "A", 0.0, 1.0, 1000)
    N = Town(2, "N", 0.0, 2.5, 1000)   # nearest to A, but far from the base
    M = Town(3, "M", 1.5, 0.3, 1000)   # farther from A, closer to the base
    roomy = Instance(BASE0, [A, N, M], Params())
    assert roomy.dist(1, 2) < roomy.dist(1, 3)
    assert roomy.dist(0, 1) < roomy.dist(0, 3) < roomy.dist(0, 2)
    lo, hi = evaluate(roomy, [1, 3]).fuel_needed, evaluate(roomy, [1, 2]).fuel_needed
    assert lo < hi
    inst = Instance(BASE0, [A, N, M], Params(F=(lo + hi) / 2))
    assert nearest_neighbour(inst).route == [1, 3]


def test_nn_consistent():
    for inst in INSTANCES:
        result = nearest_neighbour(inst)
        assert result.eval == evaluate(inst, result.route)
