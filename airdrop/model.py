"""Towns, bases, aircraft parameters and the closed-form route evaluator (PROBLEM.md, Fuel model).

Units are km and kg. Index 0 is the base; towns are 1..n. A route lists town indices
with the base left out: base -> route[0] -> ... -> route[-1] -> base.
"""
from __future__ import annotations

import csv
import math
import operator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Sequence

import numpy as np

EARTH_RADIUS_KM = 6371.0088
M_REF: float = 60_000.0  # representative mid-mission mass, kg

_EXP_MAX = 709.0  # math.exp overflows a float a little above this


@dataclass(frozen=True)
class Town:
    geonameid: int
    name: str
    lat: float
    lon: float
    population: int


@dataclass(frozen=True)
class Base:
    geonameid: int
    name: str
    lat: float
    lon: float


# PROBLEM.md, Bases table; coordinates as in data/MY.txt
BASES: dict[str, Base] = {
    "perak": Base(1734611, "Kampung Sungai Semaliang", 4.98333, 101.21667),
    "kelantan": Base(7609811, "Kemajuan Tanah Gugusan Aring", 4.8811, 102.3238),
    "johor": Base(7567448, "Kampung Ponjot", 2.2366, 103.5823),
    "sarawak": Base(1737158, "Long Geng", 2.61667, 114.13333),
    "sabah": Base(1733926, "Kampung Balat", 5.3222, 117.6087),
}


@dataclass(frozen=True)
class Params:
    F: float = 21_100.0      # fuel cap (internal tank), kg
    E: float = 33_600.0      # operating empty weight, kg
    C: float = 19_630.0      # max payload, kg
    MTOW: float = 70_300.0   # max takeoff weight, kg
    c: float = 7.0e-5        # fuel per km per kg of total mass
    w: float = 200.0         # drop weight per town, kg
    R: float = 1_700.0       # fuel reserve after landing, kg
    a: float | None = None   # None -> c * E
    b: float | None = None   # None -> c


def control_params(p: Params) -> Params:
    """Weight effect off (b = 0), same average burn per km as a plane of mass M_REF."""
    return replace(p, b=0.0, a=p.c * M_REF)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlam = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def load_towns(path: str | Path, min_population: int = 0) -> list[Town]:
    """Read data/cities_clean.csv, keeping towns with population >= min_population."""
    towns = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pop = int(row["population"])
            if pop >= min_population:
                towns.append(Town(int(row["geonameid"]), row["name"], float(row["latitude"]),
                                  float(row["longitude"]), pop))
    return towns


def exp(x: float) -> float:
    """e^x, returning inf instead of raising on overflow."""
    return math.exp(x) if x < _EXP_MAX else math.inf


def phi(b: float, x: float) -> float:
    """(e^(b x) - 1) / b, with the limit x at b = 0. Satisfies phi(x + y) = e^(b y) phi(x) + phi(y)."""
    if b == 0:
        return x
    if b * x >= _EXP_MAX:
        return math.inf
    return math.expm1(b * x) / b


class Instance:
    def __init__(self, base: Base, towns: Sequence[Town], params: Params):
        self.base = base
        self.towns: tuple[Town, ...] = tuple(towns)
        self.n = len(self.towns)
        self.params = params
        self.a: float = params.c * params.E if params.a is None else params.a
        self.b: float = params.c if params.b is None else params.b
        lat = np.radians([base.lat] + [t.lat for t in self.towns])
        lon = np.radians([base.lon] + [t.lon for t in self.towns])
        dphi = lat[None, :] - lat[:, None]
        dlam = lon[None, :] - lon[:, None]
        h = np.sin(dphi / 2) ** 2 + np.cos(lat)[:, None] * np.cos(lat)[None, :] * np.sin(dlam / 2) ** 2
        d = 2 * EARTH_RADIUS_KM * np.arcsin(np.minimum(1.0, np.sqrt(h)))
        d = (d + d.T) / 2
        np.fill_diagonal(d, 0.0)
        self._dist: list[list[float]] = d.tolist()
        self._pop = [0] + [t.population for t in self.towns]

    def dist(self, i: int, j: int) -> float:
        return self._dist[i][j]

    def population(self, i: int) -> int:
        return self._pop[i]

    def fuel_limit(self, k: int) -> float:
        p = self.params
        return min(p.F, p.MTOW - p.E - p.w * k)


@dataclass(frozen=True)
class RouteEval:
    population: int
    distance: float          # D
    cargo: float             # W0 = w * k
    fuel_needed: float       # F0_needed
    feasible: bool
    reason: str | None       # None, or the first failing check


def _valid_indices(inst: Instance, route: Sequence[int]) -> bool:
    for i in route:
        try:
            i = operator.index(i)
        except TypeError:
            return False
        if not 1 <= i <= inst.n:
            return False
    return True


def _drop_offsets(inst: Instance, route: Sequence[int]) -> tuple[list[float], float]:
    """Distance flown from the base to each drop, and the total distance D."""
    offsets, s, prev = [], 0.0, 0
    for t in route:
        s += inst.dist(prev, t)
        offsets.append(s)
        prev = t
    return offsets, s + inst.dist(prev, 0)


def evaluate(inst: Instance, route: Sequence[int]) -> RouteEval:
    p = inst.params
    k = len(route)
    cargo = p.w * k
    if not _valid_indices(inst, route):
        return RouteEval(0, 0.0, cargo, math.inf, False, "bad_index")
    route = [operator.index(i) for i in route]
    population = sum(inst.population(t) for t in route)
    offsets, D = _drop_offsets(inst, route)
    b = inst.b
    # F0_needed = (R - K) e^(bD) = R e^(bD) + a (e^(bD) - 1)/b + w * sum(e^(b s_i) - 1),
    # s_i = distance flown before drop i
    fuel = p.R * exp(b * D) + inst.a * phi(b, D) + p.w * b * sum(phi(b, s) for s in offsets)
    if math.isnan(fuel):  # 0 * inf after an overflow
        fuel = math.inf
    if len(set(route)) < k:
        reason = "duplicate"
    elif cargo > p.C:
        reason = "payload"
    elif fuel > p.F:
        reason = "fuel_cap"
    elif fuel > p.MTOW - p.E - cargo:
        reason = "takeoff_weight"
    else:
        reason = None
    return RouteEval(population, D, cargo, fuel, reason is None, reason)


def fuel_end(inst: Instance, route: Sequence[int], F0: float) -> float:
    """Fuel left on landing when the route is flown with F0 loaded.

    fuel_end = (u0 e^(-bD) - b * sum(w e^(-b R_i)) - a) / b with u0 = a + b (W0 + F0),
    R_i = distance flown after drop i; written with expm1 so b -> 0 stays exact.
    """
    p = inst.params
    offsets, D = _drop_offsets(inst, route)
    b = inst.b
    if b == 0:
        return F0 - inst.a * D
    # W0 e^(-bD) - sum(w e^(-b R_i)) = w * sum(e^(-bD) - e^(-b R_i))
    drops = p.w * sum(math.expm1(-b * D) - math.expm1(-b * (D - s)) for s in offsets)
    return F0 * math.exp(-b * D) + inst.a * math.expm1(-b * D) / b + drops
