from airdrop.baseline import population_sort_then_fit
from airdrop.model import Base, Instance, Params, Town, evaluate
from airdrop.prefix import RouteState


def test_population_sort_is_feasible_and_locally_two_opt_minimal():
    towns = [Town(i, f"town {i}", lat, lon, population)
             for i, lat, lon, population in (
                 (1, 0.2, 0.1, 4000), (2, 0.1, 0.4, 3000),
                 (3, -0.2, 0.2, 2000), (4, -0.1, -0.3, 1000))]
    inst = Instance(Base(0, "base", 0, 0), towns, Params(F=5000))
    result = population_sort_then_fit(inst)
    assert result.eval == evaluate(inst, result.route)
    assert result.eval.feasible
    assert result.stats["insertions"] + result.stats["skipped"] == inst.n
    state = RouteState(inst, result.route)
    assert all(state.two_opt_fuel(i, j) >= state.fuel_needed - 1e-9
               for i in range(len(result.route)) for j in range(i + 1, len(result.route)))


def test_population_sort_prefers_population_when_only_one_town_fits():
    towns = [Town(1, "near", 0, 0.1, 100), Town(2, "far", 0, 0.2, 1000)]
    roomy = Instance(Base(0, "base", 0, 0), towns, Params())
    both = min(evaluate(roomy, [2, 1]).fuel_needed,
               evaluate(roomy, [1, 2]).fuel_needed)
    one = evaluate(roomy, [2]).fuel_needed
    inst = Instance(roomy.base, towns, Params(F=(one + both) / 2))
    assert population_sort_then_fit(inst).route == [2]
