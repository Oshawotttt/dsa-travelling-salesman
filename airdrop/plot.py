"""Map plots of routes over Malaysia (docs/CONTRACTS.md, Map plots).

Imported on its own (``from airdrop.plot import ...``); ``airdrop`` does not re-export it.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Mapping, Sequence

import folium

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
    already used on this map. Raises ValueError for no routes or more than 5, or naming the
    label of a route that trace rejects.
    """
    if not routes:
        raise ValueError("at least 1 route per map, got 0")
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


def _dot(where: folium.Map | folium.FeatureGroup, lat: float, lon: float, radius: float,
         color: str, weight: float, opacity: float, tooltip: str | None = None) -> None:
    folium.CircleMarker([lat, lon], radius=radius, color=color, weight=weight, fill=True,
                        fill_color=color, fill_opacity=opacity, tooltip=tooltip).add_to(where)


def _tooltip(label: str, stop: Stop) -> str:
    return (f"{escape(label)}, step {stop.step}<br><b>{escape(stop.name)}</b><br>"
            f"population {stop.population:,}<br>fuel on arrival {stop.fuel_kg:,.0f} kg<br>"
            f"cargo on arrival {stop.cargo_kg:,.0f} kg<br>{stop.lat:.4f}, {stop.lon:.4f}")


def plot_routes_html(inst: Instance, routes: Mapping[str, Sequence[int]], path: str | Path,
                     title: str | None = None,
                     colors: Mapping[str, str] | None = None,
                     theme: Mapping[str, str] | None = None) -> Path:
    """Write a zoomable folium map of the routes to an HTML file and return its resolved path.

    Every town is a small circle in theme["towns"], with no tooltip; each route is a straight lat/lon polyline
    in its own toggleable layer, with its towns as larger circles in the route colour and a
    tooltip per drop; the base is the largest circle, in theme["text"]. A fixed legend box
    (top right) shows the title and each route's colour. Opening the file needs internet for
    the CartoDB Positron tiles.
    """
    layers = route_layers(inst, routes, colors)
    palette = {**THEME, **(theme or {})}
    m = folium.Map(location=[inst.base.lat, inst.base.lon], zoom_start=7, tiles="CartoDB positron")
    for t in inst.towns:
        _dot(m, t.lat, t.lon, 2, palette["towns"], 0, 0.8)
    for layer in layers:
        group = folium.FeatureGroup(name=escape(layer.label))
        points = [[s.lat, s.lon] for s in layer.stops]
        if len(layer.stops) > 2:
            folium.PolyLine(points, color=layer.color, weight=3, opacity=0.9).add_to(group)
        for stop in layer.stops[1:-1]:
            _dot(group, stop.lat, stop.lon, 5, layer.color, 1, 1.0, _tooltip(layer.label, stop))
        group.add_to(m)
    base = inst.base
    _dot(m, base.lat, base.lon, 8, palette["text"], 2, 1.0, f"Base: {escape(base.name)}")
    folium.LayerControl(position="topleft", collapsed=False).add_to(m)
    m.get_root().html.add_child(folium.Element(_legend(layers, title, palette)))
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(path))
    return path


def _legend(layers: Sequence[RouteLayer], title: str | None, palette: Mapping[str, str]) -> str:
    rows = "".join(
        f'<div><span style="display:inline-block;width:14px;height:4px;margin-right:6px;'
        f'vertical-align:middle;background:{layer.color}"></span>{escape(layer.label)}</div>'
        for layer in layers)
    head = f"<div><b>{escape(title)}</b></div>" if title else ""
    return (f'<div style="position:fixed;top:10px;right:10px;z-index:9999;padding:8px 10px;'
            f'background:{palette["background"]};color:{palette["text"]};border-radius:4px;'
            f'box-shadow:0 1px 4px rgba(0,0,0,0.3);font-size:13px">{head}{rows}</div>')
