"""Map plots of routes over Malaysia (docs/CONTRACTS.md, Map plots).

Imported on its own (``from airdrop.plot import ...``); ``airdrop`` does not re-export it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from airdrop.model import Instance, Stop, trace

THEME: dict[str, str] = {            # slide body: one slate family, light
    "background": "#F4F6F8",         # legend box
    "text": "#1F2A36",               # legend text, base marker
    "towns": "#A9B4C2",              # unvisited towns
}
ROUTE_COLORS: dict[str, str] = {     # Paul Tol "vibrant", in this order
    "NN": "#EE7733",
    "A": "#0077BB",
    "B": "#EE3377",
    "B on A": "#33BBEE",
    "DP": "#009988",
}


@dataclass(frozen=True)
class RouteLayer:
    label: str
    color: str                       # hex, from colors / ROUTE_COLORS
    stops: tuple[Stop, ...]          # trace(inst, route): takeoff, drops, landing


def route_layers(inst: Instance, routes: Mapping[str, Sequence[int]],
                 colors: Mapping[str, str] | None = None) -> list[RouteLayer]:
    """One layer per labelled route, in the order of routes.

    Colour: colors[label], else ROUTE_COLORS[label], else the first ROUTE_COLORS value not
    already used on this map. Raises ValueError for more than 5 routes, or naming the label of
    a route that trace rejects.
    """
    if len(routes) > len(ROUTE_COLORS):
        raise ValueError(f"at most {len(ROUTE_COLORS)} routes per map, got {len(routes)}")
    chosen = {label: (colors or {}).get(label, ROUTE_COLORS.get(label)) for label in routes}
    spare = [c for c in ROUTE_COLORS.values() if c not in chosen.values()]
    layers = []
    for label, route in routes.items():
        try:
            stops = tuple(trace(inst, route))
        except ValueError as e:
            raise ValueError(f"route {label!r}: {e}") from e
        color = chosen[label] or spare.pop(0)
        layers.append(RouteLayer(label, color, stops))
    return layers
