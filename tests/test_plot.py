import pytest

from airdrop.model import Base, Instance, Params, Town
from airdrop.plot import ROUTE_COLORS, THEME, RouteLayer, route_layers

BASE = Base(1, "Home Base", 4.5, 101.0)
TOWNS = [
    Town(11, "Alpha", 4.6, 101.1, 1000),
    Town(12, "Bravo", 4.7, 101.3, 2000),
    Town(13, "Charlie", 4.4, 101.2, 3000),
]


def instance():
    return Instance(BASE, TOWNS, Params())


def test_layers_follow_routes_in_order():
    inst = instance()
    routes = {"B": [3, 1], "A": [2]}
    layers = route_layers(inst, routes)
    assert [layer.label for layer in layers] == ["B", "A"]
    for layer, route in zip(layers, routes.values()):
        assert isinstance(layer, RouteLayer)
        assert len(layer.stops) == len(route) + 2
        assert [s.index for s in layer.stops] == [0, *route, 0]
        places = [BASE, *(TOWNS[i - 1] for i in route), BASE]
        assert [(s.lat, s.lon) for s in layer.stops] == [(p.lat, p.lon) for p in places]


def test_empty_route_is_takeoff_and_landing_at_base():
    [layer] = route_layers(instance(), {"A": []})
    assert [s.index for s in layer.stops] == [0, 0]
    assert [s.name for s in layer.stops] == [BASE.name, BASE.name]


def test_bad_index_names_label():
    with pytest.raises(ValueError, match="Bad Route"):
        route_layers(instance(), {"A": [1], "Bad Route": [1, 9]})


def colors_of(layers):
    return {layer.label: layer.color for layer in layers}


def test_default_colors_by_label():
    layers = route_layers(instance(), {"A": [1], "B": [2]})
    assert colors_of(layers) == {"A": "#0077BB", "B": "#EE3377"}


def test_colors_override_defaults():
    layers = route_layers(instance(), {"A": [1], "B": [2]}, colors={"A": "#123456"})
    assert colors_of(layers) == {"A": "#123456", "B": "#EE3377"}


def test_unknown_label_takes_first_unused_color():
    layers = route_layers(instance(), {"A": [1], "mine": [2]})
    assert colors_of(layers) == {"A": "#0077BB", "mine": "#EE7733"}


def test_more_than_five_routes_raises():
    routes = {f"r{i}": [1] for i in range(6)}
    with pytest.raises(ValueError):
        route_layers(instance(), routes)


def test_default_palette():
    assert THEME == {"background": "#F4F6F8", "text": "#1F2A36", "towns": "#A9B4C2"}
    assert list(ROUTE_COLORS.items()) == [
        ("NN", "#EE7733"), ("A", "#0077BB"), ("B", "#EE3377"), ("B on A", "#33BBEE"), ("DP", "#009988"),
    ]
