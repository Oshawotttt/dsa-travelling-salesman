"""Approach A: greedy insertion by population / marginal fuel (PROBLEM.md, Approach A)."""
from __future__ import annotations

import heapq
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


def _argmax(inst: Instance, state: RouteState, towns: list[int], stats: dict[str, int] | None):
    """Best (key, t, pos) among towns whose cheapest insertion fits, and the towns that fit."""
    best, fit = None, []
    k = len(state.route) + 1
    for t in towns:
        key, pos, fuel = score_key(inst, state, t)
        if stats is not None:
            stats["score_evals"] += 1
        # the cheapest insertion only gets dearer as the route grows, so an unfit town stays unfit
        if not fits(inst, k, fuel):
            continue
        fit.append(t)
        if best is None or key > best[0]:
            best = (key, t, pos)
    return best, fit


def _scan(inst: Instance, stats: dict[str, int]) -> list[int]:
    route: list[int] = []
    state = RouteState(inst, route)
    left = list(range(1, inst.n + 1))
    while left:
        best, left = _argmax(inst, state, left, stats)
        if best is None:
            break
        _, t, pos = best
        route.insert(pos, t)
        state = RouteState(inst, route)
        left.remove(t)
        stats["insertions"] += 1
    return route


def _entry(key: tuple[float, int, int]) -> tuple[float, int, int]:
    """heapq is a min-heap: (-score, -population, index)."""
    return -key[0], -key[1], -key[2]


def _heap(inst: Instance, stats: dict[str, int], audit: bool) -> list[int]:
    """Max-heap with lazy re-evaluation: pop the top, re-score it against the current route,
    insert it if it still beats the next key, otherwise push it back with its new score."""
    stats.update(heap_pops=0, heap_pushes=0)
    if audit:
        stats["mismatches"] = 0
    route: list[int] = []
    state = RouteState(inst, route)
    heap = []
    for t in range(1, inst.n + 1):
        key, _, fuel = score_key(inst, state, t)
        stats["score_evals"] += 1
        if fits(inst, 1, fuel):
            heap.append(_entry(key))
            stats["heap_pushes"] += 1
    heapq.heapify(heap)
    while heap:
        t = heapq.heappop(heap)[2]
        stats["heap_pops"] += 1
        key, pos, fuel = score_key(inst, state, t)
        stats["score_evals"] += 1
        if not fits(inst, len(route) + 1, fuel):
            continue
        entry = _entry(key)
        if heap and entry > heap[0]:
            heapq.heappush(heap, entry)
            stats["heap_pushes"] += 1
            continue
        if audit:
            best, _ = _argmax(inst, state, [t] + [e[2] for e in heap], None)
            stats["mismatches"] += best[1] != t
        route.insert(pos, t)
        state = RouteState(inst, route)
        stats["insertions"] += 1
    return route


def greedy_insertion(inst: Instance, selector: Literal["heap", "scan"] = "heap",
                     audit: bool = False) -> SolveResult:
    """Grow the route from base -> base, each step inserting the town with the best
    population / marginal fuel at its cheapest position, until no town fits."""
    stats = {"score_evals": 0, "insertions": 0}
    if selector == "scan":
        route = _scan(inst, stats)
    elif selector == "heap":
        route = _heap(inst, stats, audit)
    else:
        raise ValueError(f"unknown selector {selector!r}")
    return SolveResult(route, evaluate(inst, route), stats)
