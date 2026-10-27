"""Exact DP over subsets, the optimality baseline for small instances (docs/PROBLEM.md, Exact DP).

Backward DP: need[U][j] is the least fuel on board on arrival at town j (before its drop, cargo
w * |U|) that lets the plane drop at every town of U with j first, return to base and land with R.
"""
from __future__ import annotations

import math

from airdrop.approach_a import SolveResult
from airdrop.model import Instance, evaluate, phi


TIE = 1e-9  # fuels within this relative difference are a tie, so rounding does not pick the route


def _fuel_before(inst: Instance, f: float, d: float, cargo: float) -> float:
    """Fuel needed before a leg of length d with this cargo to have f after it.

    f + (f + cargo) (e^(bd) - 1) + a (e^(bd) - 1)/b, written with phi so b = 0 stays exact.
    """
    fuel = f + (inst.b * (f + cargo) + inst.a) * phi(inst.b, d)
    return math.inf if math.isnan(fuel) else fuel  # NaN is 0 * inf after an overflow


def _smallest_tied(options: list[tuple[int, float]]) -> tuple[int, float]:
    """(town, fuel) with the smallest town among those within TIE of the least fuel."""
    least = min(fuel for _, fuel in options)
    return min(o for o in options if o[1] <= least * (1 + TIE))


def exact_dp(inst: Instance, max_n: int = 15) -> SolveResult:
    """The optimal route: largest population, then least fuel needed, then smallest route as a
    tuple (fuels within TIE count as equal). O(n^2 2^n) time, O(n 2^n) memory, so only for
    inst.n <= max_n."""
    n = inst.n
    if n > max_n:
        raise ValueError(f"exact_dp needs n <= {max_n}, got {n}")
    p = inst.params
    full = 1 << n
    # town t (1..n) is bit t - 1; index 0 of each row is unused
    need = [[math.inf] * (n + 1) for _ in range(full)] if n else []
    next_town = [[0] * (n + 1) for _ in range(full)] if n else []
    size = [0] * full
    for mask in range(1, full):
        size[mask] = size[mask >> 1] + (mask & 1)
    stats = {"states": 0, "transitions": 0}
    best_pop, best_fuel, best_route = 0, p.R, []
    for mask in range(1, full):
        k = size[mask]
        if p.w * k > p.C:
            continue
        limit = inst.fuel_limit(k)
        row = need[mask]
        towns = [t for t in range(1, n + 1) if mask >> (t - 1) & 1]
        for j in towns:
            rest = mask & ~(1 << (j - 1))
            if not rest:
                via, fuel = 0, _fuel_before(inst, p.R, inst.dist(j, 0), 0.0)
                stats["transitions"] += 1
            else:
                prev = need[rest]
                cargo = p.w * (k - 1)
                options = [(i, _fuel_before(inst, prev[i], inst.dist(j, i), cargo))
                           for i in towns if i != j and prev[i] != math.inf]
                if not options:
                    continue
                stats["transitions"] += len(options)
                via, fuel = _smallest_tied(options)
            if fuel > limit:
                continue
            row[j], next_town[mask][j] = fuel, via
            stats["states"] += 1
        # takeoff: the smallest first town j among those needing the least fuel
        options = [(j, _fuel_before(inst, row[j], inst.dist(0, j), p.w * k))
                   for j in towns if row[j] != math.inf]
        if not options:
            continue
        first, f0 = _smallest_tied(options)
        if not inst.fits(k, f0):
            continue
        pop = sum(inst.population(t) for t in towns)
        if pop < best_pop or (pop == best_pop and f0 > best_fuel * (1 + TIE)):
            continue
        route, rest, t = [], mask, first
        while t:
            route.append(t)
            t, rest = next_town[rest][t], rest & ~(1 << (t - 1))
        if pop > best_pop or f0 < best_fuel * (1 - TIE) or route < best_route:
            best_pop, best_fuel, best_route = pop, f0, route
    return SolveResult(best_route, evaluate(inst, best_route), stats)
