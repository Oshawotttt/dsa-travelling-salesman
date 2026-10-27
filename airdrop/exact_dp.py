"""Exact DP over subsets, the optimality baseline for small instances (docs/PROBLEM.md, Exact DP).

Backward DP: need[U][j] is the least fuel on board on arrival at town j (before its drop, cargo
w * |U|) that lets the plane drop at every town of U with j first, return to base and land with R.
"""
from __future__ import annotations

import math
from typing import Iterator

from airdrop.approach_a import SolveResult
from airdrop.model import Instance, evaluate, phi


TIE = 1e-9  # fuels within this relative difference are a tie, so rounding does not pick the route


def _fuel_before(inst: Instance, f: float, d: float, cargo: float) -> float:
    """Fuel needed before a leg of length d with this cargo to have f after it.

    f + (f + cargo) (e^(bd) - 1) + a (e^(bd) - 1)/b, written with phi so b = 0 stays exact.
    """
    fuel = f + (inst.b * (f + cargo) + inst.a) * phi(inst.b, d)
    return math.inf if math.isnan(fuel) else fuel  # NaN is 0 * inf after an overflow


def _tied_routes(inst: Instance, need: list[list[float]], mask: int, j: int) -> Iterator[list[int]]:
    """Every route through the towns of mask that starts at j and needs need[mask][j] on
    arrival, within TIE at each step, as the smallest town first, so in tuple order."""
    rest = mask & ~(1 << (j - 1))
    if not rest:
        yield [j]
        return
    cargo = inst.params.w * (mask.bit_count() - 1)
    target = need[mask][j] * (1 + TIE)
    for i in range(1, inst.n + 1):
        if not rest >> (i - 1) & 1 or need[rest][i] == math.inf:
            continue
        if _fuel_before(inst, need[rest][i], inst.dist(j, i), cargo) <= target:
            for tail in _tied_routes(inst, need, rest, i):
                yield [j, *tail]


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
    size = [0] * full
    for mask in range(1, full):
        size[mask] = size[mask >> 1] + (mask & 1)
    stats = {"states": 0, "transitions": 0}
    # sets with the largest population so far, as (fuel needed, route); the empty route to start
    best_pop, best = 0, [(p.R, [])]
    for mask in range(1, full):
        k = size[mask]
        if p.w * k > p.C:
            continue
        # TIE slack, so a route that evaluate finds feasible is never pruned by rounding
        limit = inst.fuel_limit(k) * (1 + TIE)
        row = need[mask]
        towns = [t for t in range(1, n + 1) if mask >> (t - 1) & 1]
        for j in towns:
            rest = mask & ~(1 << (j - 1))
            if not rest:
                fuel = _fuel_before(inst, p.R, inst.dist(j, 0), 0.0)
                stats["transitions"] += 1
            else:
                prev = need[rest]
                cargo = p.w * (k - 1)
                options = [_fuel_before(inst, prev[i], inst.dist(j, i), cargo)
                           for i in towns if i != j and prev[i] != math.inf]
                if not options:
                    continue
                stats["transitions"] += len(options)
                fuel = min(options)
            if fuel > limit:
                continue
            row[j] = fuel
            stats["states"] += 1
        takeoff = [(j, _fuel_before(inst, row[j], inst.dist(0, j), p.w * k))
                   for j in towns if row[j] != math.inf]
        if not takeoff:
            continue
        f0 = min(fuel for _, fuel in takeoff)
        pop = sum(inst.population(t) for t in towns)
        if pop < best_pop or f0 > limit:
            continue
        # the smallest route within TIE of f0 that evaluate finds feasible, so the result
        # agrees with evaluate to the last bit
        tied = (route for j, fuel in takeoff if fuel <= f0 * (1 + TIE)
                for route in _tied_routes(inst, need, mask, j))
        route = next((r for r in tied if evaluate(inst, r).feasible), None)
        if route is None:
            continue
        if pop > best_pop:
            best_pop, best = pop, []
        least = min([f0, *(fuel for fuel, _ in best)])
        best = [(fuel, route) for fuel, route in best if fuel <= least * (1 + TIE)]
        if f0 <= least * (1 + TIE):
            best.append((f0, route))
    best_route = min(route for _, route in best)
    return SolveResult(best_route, evaluate(inst, best_route), stats)
