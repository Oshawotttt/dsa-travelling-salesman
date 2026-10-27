"""Nearest neighbour with a fuel cutoff (PROBLEM.md, Baseline): Approach B's starting route."""
from __future__ import annotations

from airdrop.approach_a import SolveResult
from airdrop.model import Instance, evaluate


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
