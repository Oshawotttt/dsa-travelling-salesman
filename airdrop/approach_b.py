"""Approach B: best-improvement local search under the full fuel model (PROBLEM.md, Approach B).

Moves, each round over the whole neighbourhood:
- 2-opt (i, j): reverse route[i..j]; improves when it needs less fuel.
- add (t): insert unvisited t at its cheapest position; improves when it fits.
- swap (r, u): remove visited r, insert a more populous unvisited u at its cheapest position
  in the route without r; improves when it fits.
- replace 1 with 2 (r, u, v): remove r, insert u then v, each at its cheapest position;
  improves when it fits and pop(u) + pop(v) > pop(r). u and v come from the L unvisited towns
  with the best single-insertion score into the route without r; both orders of a pair are tried.

The applied move has the largest population gain, then the least fuel needed, then the type
order above, then the smallest ids (positions i, j for 2-opt; town indices otherwise).
"""
from __future__ import annotations

from typing import Callable, Sequence

from airdrop.approach_a import SolveResult, insertion_key
from airdrop.baseline import nearest_neighbour
from airdrop.model import Instance, evaluate
from airdrop.prefix import RouteState

MOVES = ("two_opt", "add", "swap", "replace_1_2")
TWO_OPT, ADD, SWAP, REPLACE = range(4)

# (-gain, fuel needed, move type, ids): the smallest key is the best move
MoveKey = tuple[int, float, int, tuple[int, ...]]


def _best_move(inst: Instance, route: list[int], L: int) -> tuple[MoveKey, Callable[[], list[int]]] | None:
    """The best improving move as (key, build the new route), or None at a local optimum."""
    pop = inst.population
    k = len(route)
    state = RouteState(inst, route)
    current = state.fuel_needed
    visited = set(route)
    unvisited = [t for t in range(1, inst.n + 1) if t not in visited]
    best: list = [None]

    def offer(key: MoveKey, build: Callable[[], list[int]]) -> None:
        if best[0] is None or key < best[0][0]:
            best[0] = (key, build)

    for i in range(k):
        for j in range(i + 1, k):
            fuel = state.two_opt_fuel(i, j)
            if fuel < current:
                offer((0, fuel, TWO_OPT, (i, j)),
                      lambda i=i, j=j: route[:i] + route[i:j + 1][::-1] + route[j + 1:])

    positions, fuels = state.best_insertions(unvisited)
    for t, pos, fuel in zip(unvisited, positions, fuels):
        if pop(t) > 0 and inst.fits(k + 1, fuel):
            offer((-pop(t), fuel, ADD, (t,)), lambda t=t, pos=pos: route[:pos] + [t] + route[pos:])

    for p, r in enumerate(route):
        rest = route[:p] + route[p + 1:]
        rest_state = RouteState(inst, rest)
        positions, fuels = rest_state.best_insertions(unvisited)
        single = {u: (pos, fuel) for u, pos, fuel in zip(unvisited, positions, fuels)}
        for u, (pos, fuel) in single.items():
            if pop(u) > pop(r) and inst.fits(k, fuel):
                offer((pop(r) - pop(u), fuel, SWAP, (r, u)),
                      lambda rest=rest, u=u, pos=pos: rest[:pos] + [u] + rest[pos:])
        top = sorted(unvisited, key=lambda u: insertion_key(inst, u, single[u][1], rest_state.fuel_needed),
                     reverse=True)[:L]
        for u in top:
            others = [v for v in top if v != u and pop(u) + pop(v) > pop(r)]
            if not others:
                continue
            pos_u = single[u][0]
            with_u = rest[:pos_u] + [u] + rest[pos_u:]
            positions, fuels = RouteState(inst, with_u).best_insertions(others)
            for v, pos, fuel in zip(others, positions, fuels):
                if inst.fits(k + 1, fuel):
                    offer((pop(r) - pop(u) - pop(v), fuel, REPLACE, (r, u, v)),
                          lambda with_u=with_u, v=v, pos=pos: with_u[:pos] + [v] + with_u[pos:])
    return best[0]


def local_search(inst: Instance, initial: Sequence[int] | None = None,
                 L: int = 20, max_rounds: int = 10_000) -> SolveResult:
    """Apply the best improving move each round until none improves or max_rounds moves are made.
    initial=None starts from the nearest-neighbour route; a given initial route must be feasible."""
    route = list(nearest_neighbour(inst).route if initial is None else initial)
    if not evaluate(inst, route).feasible:
        raise ValueError("initial route is not feasible")
    stats = {"rounds": 0, **{m: 0 for m in MOVES}, "hit_max_rounds": 0}
    while (move := _best_move(inst, route, L)) is not None:
        if stats["rounds"] == max_rounds:
            stats["hit_max_rounds"] = 1
            break
        key, build = move
        route = build()
        stats["rounds"] += 1
        stats[MOVES[key[2]]] += 1
    return SolveResult(route, evaluate(inst, route), stats)
