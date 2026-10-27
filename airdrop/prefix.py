"""Prefix sums over one route, so insertion, removal and 2-opt costs are O(1) (docs/PROBLEM.md, Approach B).

Nodes are v_0 = base, v_1..v_k = the towns, v_(k+1) = base, and S_m is the distance flown
from the base to v_m. The fuel needed depends only on D = S_(k+1) and on sum(phi(S_m)) over
the drops (see model.fuel_needed_from). A move changes D by the edges it swaps, leaves the
drops before it alone, and shifts every later drop by the same delta, which
phi(x + delta) = e^(b delta) phi(x) + phi(delta) turns into one scale and one add.
A reversed segment v_(i+1)..v_(j+1) puts drop m at A - S_m. With B = S_(j+1) this is
phi(A - S_m) = e^(b (B - S_m)) phi(A - B) + phi(B - S_m), and phi(B - S_m) comes from suffix
sums of phi(D - S_m) shifted by -(D - B).

Overflow and precision: every stored term is phi of a distance in [0, D], and every sum is
taken over terms of one sign, with the smaller terms subtracted (prefix sums of the growing
phi(S_m), suffix sums of the shrinking phi(D - S_m)). Each product is at most the size of a
term of the answer, so nothing overflows before the answer does.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

from airdrop.model import Instance, fuel_needed_array, fuel_needed_from, phi, phi_array, safe_exp


class RouteState:
    """Prefix sums over one route. Build O(k); every query O(1) except best_insertion O(k)."""

    def __init__(self, inst: Instance, route: Sequence[int]):
        self.inst = inst
        self.route: tuple[int, ...] = tuple(route)
        b = inst.b
        nodes = [0, *self.route, 0]
        self._nodes = nodes
        self._edge = [inst.dist(i, j) for i, j in zip(nodes, nodes[1:])]
        S = [0.0]
        for e in self._edge:
            S.append(S[-1] + e)
        self._S = S
        k, D = len(self.route), S[-1]
        # P[m] = sum(phi(S_l)) over drops l = 1..m; Q[m] = sum(phi(D - S_l)) over drops l = m..k
        P = [0.0]
        for m in range(1, k + 1):
            P.append(P[-1] + phi(b, S[m]))
        Q = [0.0] * (k + 2)
        for m in range(k, 0, -1):
            Q[m] = Q[m + 1] + phi(b, D - S[m])
        self._P, self._Q = P, Q
        self.fuel_needed: float = fuel_needed_from(inst, S[-1], P[-1])

    def _shifted(self, first: int, last: int, delta: float) -> float:
        """sum(phi(S_m + delta)) over drops first..last."""
        if first > last:
            return 0.0
        return safe_exp(self.inst.b * delta) * (self._P[last] - self._P[first - 1]) \
            + (last - first + 1) * phi(self.inst.b, delta)

    def insert_fuel(self, t: int, pos: int) -> float:
        """Fuel needed after inserting t before route[pos], pos in 0..k."""
        k, d, v = len(self.route), self.inst.dist, self._nodes
        d_in = d(v[pos], t)
        delta = d_in + d(t, v[pos + 1]) - self._edge[pos]
        drops = self._P[pos] + phi(self.inst.b, self._S[pos] + d_in) + self._shifted(pos + 1, k, delta)
        return fuel_needed_from(self.inst, self._S[-1] + delta, drops)

    def best_insertion(self, t: int) -> tuple[int, float]:
        """(pos, fuel_needed) of the cheapest insertion of t; ties go to the smallest pos."""
        best_pos, best = 0, self.insert_fuel(t, 0)
        for pos in range(1, len(self.route) + 1):
            fuel = self.insert_fuel(t, pos)
            if fuel < best:
                best_pos, best = pos, fuel
        return best_pos, best

    def best_insertions(self, towns: Sequence[int]) -> tuple[list[int], list[float]]:
        """best_insertion for many towns at once, vectorised over towns and positions:
        (positions, fuels) in the order of towns. Same formulas as insert_fuel."""
        if len(towns) == 0:
            return [], []
        inst, b = self.inst, self.inst.b
        k = len(self.route)
        T = np.asarray(towns)
        v = np.asarray(self._nodes)
        dm = inst.dist_matrix
        d_in = dm[v[:-1]][:, T]                       # (k+1, m): previous node -> t
        delta = d_in + dm[v[1:]][:, T] - np.asarray(self._edge)[:, None]
        S = np.asarray(self._S[:k + 1])[:, None]
        P = np.asarray(self._P)
        after = (P[k] - P)[:, None]                   # drops after the slot
        count = (k - np.arange(k + 1))[:, None]
        with np.errstate(over="ignore", invalid="ignore"):
            drops = (P[:, None] + phi_array(b, S + d_in) + np.exp(b * delta) * after
                     + count * phi_array(b, delta))
        fuel = fuel_needed_array(inst, self._S[-1] + delta, drops)
        best = np.argmin(fuel, axis=0)                # first minimum: smallest position on ties
        return best.tolist(), fuel[best, np.arange(len(T))].tolist()

    def remove_fuel(self, pos: int) -> float:
        """Fuel needed after removing route[pos]."""
        k, v = len(self.route), self._nodes
        delta = self.inst.dist(v[pos], v[pos + 2]) - self._edge[pos] - self._edge[pos + 1]
        drops = self._P[pos] + self._shifted(pos + 2, k, delta)
        return fuel_needed_from(self.inst, self._S[-1] + delta, drops)

    def two_opt_fuel(self, i: int, j: int) -> float:
        """Fuel needed after reversing route[i..j] inclusive, 0 <= i < j < k."""
        k, d, v, b = len(self.route), self.inst.dist, self._nodes, self.inst.b
        d_in = d(v[i], v[j + 1])
        delta = d_in + d(v[i + 1], v[j + 2]) - self._edge[i] - self._edge[j + 1]
        # drops v_(i+1)..v_(j+1) land at A - S_m = (A - B) + (B - S_m), B = S_(j+1)
        S, D, count = self._S, self._S[-1], j - i + 1
        to_end = D - S[j + 1]
        # sum(phi(B - S_m)) = sum(phi((D - S_m) - to_end)), all terms >= 0
        back = safe_exp(-b * to_end) * (self._Q[i + 1] - self._Q[j + 2]) + count * phi(b, -to_end)
        # sum(e^(b (B - S_m))) = count + b * back
        inside = phi(b, S[i] + d_in) * (count + b * back) + back
        drops = self._P[i] + inside + self._shifted(j + 2, k, delta)
        return fuel_needed_from(self.inst, self._S[-1] + delta, drops)
