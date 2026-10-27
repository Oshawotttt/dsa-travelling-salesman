"""Exact DP over subsets, the optimality baseline for small instances (docs/PROBLEM.md, Exact DP).

Backward DP: need[U][j] is the least fuel on board on arrival at town j (before its drop, cargo
w * |U|) that lets the plane drop at every town of U with j first, return to base and land with R.
"""
from __future__ import annotations

import math

from airdrop.approach_a import SolveResult
from airdrop.model import Instance, evaluate, phi


def _before(inst: Instance, f: float, d: float, cargo: float) -> float:
    """Fuel needed before a leg of length d with this cargo to have f after it.

    f + (f + cargo) (e^(bd) - 1) + a (e^(bd) - 1)/b, written with phi so b = 0 stays exact.
    """
    fuel = f + (inst.b * (f + cargo) + inst.a) * phi(inst.b, d)
    return math.inf if math.isnan(fuel) else fuel  # NaN is 0 * inf after an overflow


def exact_dp(inst: Instance, max_n: int = 15) -> SolveResult:
    """The optimal route: largest population, then least fuel needed, then smallest route as a
    tuple. O(n^2 2^n) time, O(n 2^n) memory, so only for inst.n <= max_n."""
    n = inst.n
    if n > max_n:
        raise ValueError(f"exact_dp needs n <= {max_n}, got {n}")
    p = inst.params
    inf = math.inf
    full = 1 << n
    # town t (1..n) is bit t - 1; index 0 of each row is unused
    need = [[inf] * (n + 1) for _ in range(full)] if n else []
    nxt = [[0] * (n + 1) for _ in range(full)] if n else []
    size = [0] * full
    for mask in range(1, full):
        size[mask] = size[mask >> 1] + (mask & 1)
    stats = {"states": 0, "transitions": 0}
    best_key, best_route = (0, p.R, ()), []
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
                fuel, via = _before(inst, p.R, inst.dist(j, 0), 0.0), 0
                stats["transitions"] += 1
            else:
                fuel, via = inf, 0
                prev = need[rest]
                cargo = p.w * (k - 1)
                for i in towns:  # ascending, and strict < keeps the smallest i on ties
                    if i == j or prev[i] == inf:
                        continue
                    stats["transitions"] += 1
                    f = _before(inst, prev[i], inst.dist(j, i), cargo)
                    if f < fuel:
                        fuel, via = f, i
            if fuel > limit:
                continue
            row[j], nxt[mask][j] = fuel, via
            stats["states"] += 1
        # takeoff: the first town j that needs the least fuel
        f0, first = inf, 0
        for j in towns:
            if row[j] == inf:
                continue
            f = _before(inst, row[j], inst.dist(0, j), p.w * k)
            if f < f0:
                f0, first = f, j
        if not inst.fits(k, f0):
            continue
        pop = sum(inst.population(t) for t in towns)
        if pop < best_key[0] or (pop == best_key[0] and f0 > best_key[1]):
            continue
        route, rest, t = [], mask, first
        while t:
            route.append(t)
            t, rest = nxt[rest][t], rest & ~(1 << (t - 1))
        key = (pop, f0, tuple(route))
        if pop > best_key[0] or f0 < best_key[1] or key[2] < best_key[2]:
            best_key, best_route = key, route
    return SolveResult(best_route, evaluate(inst, best_route), stats)
