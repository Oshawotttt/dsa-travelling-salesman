import pytest

from airdrop.model import Base, Instance, Params, Town
from airdrop.plot import ROUTE_COLORS, THEME, RouteLayer, plot_routes_html, route_layers

BASE = Base(1, "Home Base", 4.5, 101.0)
TOWNS = [
    Town(11, "Alpha", 4.6, 101.1, 1000),
    Town(12, "Bravo", 4.7, 101.3, 2000),
    Town(13, "Charlie", 4.4, 101.2, 3000),
]


def instance():
    return Instance(BASE, TOWNS, Params())


def colors_of(layers):
    return {layer.label: layer.color for layer in layers}


def html_of(tmp_path, routes, **kwargs):
    path = plot_routes_html(instance(), routes, tmp_path / "route.html", **kwargs)
    return path.read_text(encoding="utf-8")


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


def test_infinite_fuel_names_label():
    inst = Instance(BASE, TOWNS, Params(c=100.0))
    with pytest.raises(ValueError, match="Far Route"):
        route_layers(inst, {"Far Route": [1, 2, 3]})


def test_no_routes_raises():
    with pytest.raises(ValueError, match="at least 1 route"):
        route_layers(instance(), {})


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
    with pytest.raises(ValueError, match="at most 5 routes"):
        route_layers(instance(), routes)


def test_default_palette():
    assert THEME == {"background": "#F4F6F8", "text": "#1F2A36", "towns": "#A9B4C2"}
    assert list(ROUTE_COLORS.items()) == [
        ("NN", "#EE7733"), ("A", "#0077BB"), ("B", "#EE3377"), ("B on A", "#33BBEE"), ("DP", "#009988"),
    ]


def test_html_creates_file_and_parent_dir(tmp_path):
    path = tmp_path / "out" / "route.html"
    result = plot_routes_html(instance(), {"A": [1, 2]}, path)
    assert result == path.resolve()
    assert path.is_file()


def test_html_names_routes_base_and_visited_towns(tmp_path):
    html = html_of(tmp_path, {"Route One": [1, 2], "Route Two": [3]})
    for text in ["Route One", "Route Two", "Home Base", "Alpha", "Bravo", "Charlie"]:
        assert text in html


def test_html_has_visited_town_coordinates(tmp_path):
    html = html_of(tmp_path, {"A": [1, 3]})
    for lat, lon in [("4.6000", "101.1000"), ("4.4000", "101.2000")]:
        assert lat in html and lon in html


def test_html_uses_positron_route_colors_and_theme(tmp_path):
    html = html_of(tmp_path, {"A": [1], "mine": [2]}, colors={"A": "#123456"})
    for text in ["positron", "#123456", "#EE7733", THEME["background"], THEME["text"]]:
        assert text.lower() in html.lower()


def test_theme_overrides_text_color(tmp_path):
    html = html_of(tmp_path, {"A": [1]}, theme={"text": "#000000"})
    assert "#000000" in html
    assert THEME["text"] not in html
    assert THEME["background"] in html


def test_empty_route_and_shared_towns_render(tmp_path):
    html = html_of(tmp_path, {"A": [], "B": [1, 2], "B on A": [2, 1, 3]}, title="Shared")
    for text in ["B on A", "Shared", "Alpha"]:
        assert text in html


def test_unvisited_towns_have_no_tooltip(tmp_path):
    html = html_of(tmp_path, {"A": [1]})
    assert "Alpha" in html
    assert "Bravo" not in html and "Charlie" not in html
