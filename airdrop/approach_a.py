"""Approach A: greedy insertion by population / marginal fuel (PROBLEM.md, Approach A)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from airdrop.model import Instance, RouteEval, evaluate
from airdrop.prefix import RouteState


@dataclass
class SolveResult:
    route: list[int]
    eval: RouteEval
    stats: dict[str, int]


def fits(inst: Instance, k: int, fuel: float) -> bool:
    """A route of k towns needing this much fuel meets the payload, tank and takeoff limits."""
    return inst.params.w * k <= inst.params.C and fuel <= inst.fuel_limit(k)


def score_key(inst: Instance, state: RouteState, t: int) -> tuple[tuple[float, int, int], int, float]:
    """(key, pos, fuel) for inserting t at its cheapest position. Larger key is better:
    population / marginal fuel (+inf when marginal <= 0), then larger population, then smaller index."""
    pos, fuel = state.best_insertion(t)
    marginal = fuel - state.fuel_needed
    pop = inst.population(t)
    score = pop / marginal if marginal > 0 else math.inf
    return (score, pop, -t), pos, fuel


def _scan(inst: Instance, stats: dict[str, int]) -> list[int]:
    route: list[int] = []
    state = RouteState(inst, route)
    left = list(range(1, inst.n + 1))
    while left:
        best = None
        keep = []
        for t in left:
            key, pos, fuel = score_key(inst, state, t)
            stats["score_evals"] += 1
            # the cheapest insertion only gets dearer as the route grows, so an unfit town stays unfit
            if not fits(inst, len(route) + 1, fuel):
                continue
            keep.append(t)
            if best is None or key > best[0]:
                best = (key, t, pos)
        if best is None:
            break
        _, t, pos = best
        route.insert(pos, t)
        state = RouteState(inst, route)
        keep.remove(t)
        left = keep
        stats["insertions"] += 1
    return route


def greedy_insertion(inst: Instance, selector: Literal["heap", "scan"] = "heap",
                     audit: bool = False) -> SolveResult:
    """Grow the route from base -> base, each step inserting the town with the best
    population / marginal fuel at its cheapest position, until no town fits."""
    stats = {"score_evals": 0, "insertions": 0}
    if selector == "scan":
        route = _scan(inst, stats)
    else:
        raise ValueError(f"unknown selector {selector!r}")
    return SolveResult(route, evaluate(inst, route), stats)
