"""Nearest neighbour with a fuel cutoff (docs/PROBLEM.md, Baseline): Approach B's starting route."""
from __future__ import annotations

from airdrop.approach_a import SolveResult
from airdrop.model import Instance, evaluate
from airdrop.prefix import RouteState


def nearest_neighbour(inst: Instance) -> SolveResult:
    """Fly to the nearest town that still lets the plane get home with the reserve, skipping
    nearer towns that do not; stop when no town fits. Distance ties go to the smaller index."""
    route: list[int] = []
    left = set(range(1, inst.n + 1))
    current = 0
    checks = 0
    while True:
        chosen = None
        for t in sorted(left, key=lambda t: (inst.dist(current, t), t)):
            checks += 1
            if evaluate(inst, route + [t]).feasible:
                chosen = t
                break
            # a longer route only needs more fuel, so a town that fails now fails for good
            left.discard(t)
        if chosen is None:
            break
        route.append(chosen)
        left.discard(chosen)
        current = chosen
    return SolveResult(route, evaluate(inst, route), {"checks": checks, "steps": len(route)})


def population_sort_then_fit(inst: Instance) -> SolveResult:
    """Visit towns in descending population order, placing each at its cheapest feasible gap.

    After the single insertion pass, apply fuel-improving 2-opt reversals until none remains.
    Ties use town index, then the first (i, j) reversal. No other local-search moves apply.
    """
    route: list[int] = []
    skipped = 0
    for town in sorted(range(1, inst.n + 1), key=lambda t: (-inst.population(t), t)):
        position, fuel = RouteState(inst, route).best_insertion(town)
        if inst.fits(len(route) + 1, fuel):
            route.insert(position, town)
        else:
            skipped += 1

    reversals = 0
    while True:
        state = RouteState(inst, route)
        best = None
        for i in range(len(route)):
            for j in range(i + 1, len(route)):
                fuel = state.two_opt_fuel(i, j)
                if fuel < state.fuel_needed - 1e-9 and (best is None or fuel < best[0]):
                    best = fuel, i, j
        if best is None:
            break
        _, i, j = best
        route[i:j + 1] = reversed(route[i:j + 1])
        reversals += 1
    return SolveResult(route, evaluate(inst, route),
                       {"insertions": len(route), "skipped": skipped, "two_opt": reversals})
