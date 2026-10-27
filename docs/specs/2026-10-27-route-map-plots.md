# Route map plots over Malaysia

**Status:** approved
**Repo:** `D:\SMU\CS201\proj\graph-map` (git worktree of `dsa-travelling-salesman`)
**Context file to update:** none named
**Source docs:** `CONTRACTS.md` (Routes and indices, Data, Solvers, Route trace), `PROBLEM.md`, `EXPERIMENT.md`, `DECISIONS.md`, `TODO.md` (Code: "Map plot of A's and B's routes, to check they look sensible"), `README.md`. The repo has no CLAUDE.md, no ADRs, no glossary. Terms follow PROBLEM.md and CONTRACTS.md: *town*, *base*, *drop*, *route*, *stop*.

**Commands** (from the repo root, after `pip install -r requirements.txt`):
- Full test suite: `python -m pytest`
- Single test file: `python -m pytest tests/test_plot.py`
- Typecheck: none
- Lint: none

## 1. Dependencies and blockers

| Subtask | Blocked by |
|---|---|
| S1 Route geometry from a solver result | none |
| S2 Interactive HTML map (folium) | S1 |

Run order: S1, S2.

External blockers:
- none for installs: `pip install --dry-run --only-binary=:all: matplotlib contextily folium` on Python 3.14.7 resolves to wheels (folium 0.20.0). `transient`.
- The worktree `D:/SMU/CS201/proj/dsa-travelling-salesman` (branch `feat/experiments`) also edits `requirements.txt` and `README.md`. Merge conflicts on those two files are expected when both branches merge. `transient`.

Uncommitted changes: none at planning time. If anything other than this spec is uncommitted when the run starts, stop and ask the user.
Branch: current branch `feat/graph-map`, no new branch.

## 2. Suggested splits

No split: S2 depends on S1 (route geometry) and both edit `airdrop/plot.py` and `tests/test_plot.py`.

## 3. Out of scope

- Static PNG output (matplotlib + contextily). Decision (user): "remove png extension for now". `transient`.
- CLI or `python -m` entry point for plotting; library functions only, in `airdrop/plot.py`; no experiment script, no slide embedding (user: "okay to all"). Recorded in S2's doc delta (README "Plotting routes" says the functions are called from Python).
- Experiment scripts and their plots (EXPERIMENT.md experiments 1–5), owned by `feat/experiments`. `transient`.
- Embedding `route.html` in slides (reveal.js / Quarto). `transient`.
- Offline map tiles or caching tiles in the repo. Recorded in S2's doc delta (internet caveat).
- Great-circle leg drawing (user: "okay to all"). `transient`.
- Custom fonts; the map uses the browser default font (user: "okay to all"). `transient`.
- Building the Canva slides; the user applies the palette in Canva. `transient`.
- Changes to the solvers, `evaluate`, `trace` or the fuel model. `transient`.

## 4. Interfaces

S1 hands geometry to S2. Doc delta to `docs/CONTRACTS.md`, new section "Map plots".

```python
# airdrop/plot.py
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
    color: str                       # hex, from colors / ROUTE_COLORS (see below)
    stops: tuple[Stop, ...]          # trace(inst, route): takeoff, drops, landing

def route_layers(inst: Instance, routes: Mapping[str, Sequence[int]],
                 colors: Mapping[str, str] | None = None) -> list[RouteLayer]

def plot_routes_html(inst: Instance, routes: Mapping[str, Sequence[int]], path: str | Path,
                     title: str | None = None,
                     colors: Mapping[str, str] | None = None,
                     theme: Mapping[str, str] | None = None) -> Path
```

- `routes` maps a label (e.g. `"A"`, `"B"`) to a route in the CONTRACTS.md route format (town indices, base left out). A caller passes `{"A": result.route}` from any `SolveResult`. One map holds 1 to 5 routes.
- Route colour: `colors[label]` if given, else `ROUTE_COLORS[label]`, else the first `ROUTE_COLORS` value (in `ROUTE_COLORS` order) not already used on that map. More than 5 routes raises `ValueError`.
- `theme` keys override `THEME` keys; missing keys fall back to `THEME`.
- Tiles: CartoDB Positron (folium `tiles="CartoDB positron"`), attribution kept.
- `route_layers` keeps the order of `routes`. It raises `ValueError` for any route that `trace` rejects (bad index, infinite fuel), naming the label.
- An empty route `[]` gives a layer of two stops (takeoff and landing at the base) and draws no legs.
- `plot_routes_html` creates parent directories, writes the file, and returns the resolved path.

## 5. Subtasks

### S1 Route geometry from a solver result

- **Goal:** `airdrop/plot.py` exists with `THEME`, `ROUTE_COLORS`, `RouteLayer` and `route_layers`, turning labelled routes into coloured per-stop geometry via `trace`. `folium` is in `requirements.txt`.
- **Blocked by:** none
- **Files:** `airdrop/plot.py`, `tests/test_plot.py`, `requirements.txt`
- **Seams:** `airdrop.plot.route_layers`, `airdrop.plot.RouteLayer`, `airdrop.plot.THEME`, `airdrop.plot.ROUTE_COLORS`
- **Decisions:**
  - Input shape is the route from CONTRACTS.md (town indices, base left out) and `SolveResult.route`; geometry comes from `trace` (user: "use the output shape in contracts"). Doc delta.
  - Several labelled routes per map, each its own colour and legend entry, up to 5 (user: "yes" to a palette with NN, A, B, B on A, DP route colours). Doc delta (CONTRACTS.md).
  - Palette (user: "we can make just like the body to be similar colours, then the route can be bright colours for differentiation", then "yes"): background `#F4F6F8`, text and base marker `#1F2A36`, unvisited towns `#A9B4C2`, NN `#EE7733`, A `#0077BB`, B `#EE3377`, B on A `#33BBEE`, DP `#009988`. These are the defaults in `THEME` and `ROUTE_COLORS`; callers can override them. Doc delta (CONTRACTS.md, README).
  - A label not in `ROUTE_COLORS` takes the first route colour (in `ROUTE_COLORS` order) not already used on that map. More than 5 routes on one map raises `ValueError` (user: "okay to all"). Doc delta (CONTRACTS.md).
  - `requirements.txt` gains `folium` only; `matplotlib` and `contextily` are not added (user: "okay to all"). Doc delta (README).
  - `airdrop/__init__.py` does not import `airdrop.plot`, so `import airdrop` never needs folium (code: `airdrop/__init__.py` exports only model names). Doc delta (CONTRACTS.md).
- **Acceptance criteria:**
  - [x] `route_layers` on a hand-built instance returns one layer per label in input order, each with `len(route) + 2` stops whose `index` sequence is `[0, *route, 0]` and whose `lat`/`lon` equal the base's and towns' (test in `tests/test_plot.py`).
  - [x] Empty route gives a layer with two base stops (test).
  - [x] Bad index raises `ValueError` whose message contains the label (test).
  - [x] Colours: labels `"A"`, `"B"` get `#0077BB`, `#EE3377`; `colors={"A": "#123456"}` overrides A; an unknown label next to `"A"` gets `#EE7733` (first unused); 6 routes raise `ValueError` (tests).
  - [x] `python -c "import airdrop, sys; assert 'folium' not in sys.modules"` exits 0.
  - [x] `python -m pytest` passes.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: new "Map plots" section with `THEME`, `ROUTE_COLORS`, `RouteLayer`, `route_layers` and the bullets under Interfaces; note that `airdrop.plot` is imported on its own and is not re-exported from `airdrop`.
  - `README.md`: `requirements.txt` line in the folder tree lists `folium`; `plot.py` added to the tree.
  - Decision made: colours resolve in two passes: first `colors[label]` or `ROUTE_COLORS[label]` for every label, then unknown labels take the unused `ROUTE_COLORS` values in route order. Why: an unknown label listed before a known one (e.g. `{"x": ..., "NN": ...}`) would otherwise take the known label's colour and two routes would share it. `docs/CONTRACTS.md` (Map plots).
  - Decision made: a route `trace` rejects raises `ValueError(f"route {label!r}: <trace message>")` (the label in Python repr, e.g. `'A'`, or `"O'Neil"` when it holds an apostrophe), chained from the `trace` error. Why: the spec asks for the label; keeping `trace`'s message keeps the cause. `docs/CONTRACTS.md` (Map plots).
  - Decision made (code review): an empty `routes` mapping raises `ValueError("at least 1 route per map, got 0")`, from `route_layers` and so from `plot_routes_html`. Why: Interfaces says "One map holds 1 to 5 routes"; without it an empty map with an empty legend was written. `docs/CONTRACTS.md` (Map plots).
  - Decision made (code review): "not already used" compares colours case-insensitively, so `colors={"x": "#ee7733"}` keeps a spare label off `#EE7733`. Why: hex case does not change the colour; two routes would otherwise share one. `docs/CONTRACTS.md` (Map plots).
  - Decision made: the 5-route limit is checked before any route is traced. Why: fails fast without tracing. Needs no doc beyond the limit itself.

### S2 Interactive HTML map (folium)

- **Goal:** `plot_routes_html` writes a zoomable folium map of Malaysia with every town, each route as a coloured polyline in its own toggleable layer, per-stop tooltips and a colour legend.
- **Blocked by:** S1
- **Files:** `airdrop/plot.py`, `tests/test_plot.py`
- **Seams:** `airdrop.plot.plot_routes_html`
- **Decisions:**
  - folium draws the route on a zoomable Malaysia map and saves it as an `.html` file (user). Doc delta (README).
  - "The HTML map needs internet every time someone opens it" (user). Doc delta (README).
  - Tiles are `"CartoDB positron"` (user: "yes"). Doc delta (README).
  - Each route is its own `folium.FeatureGroup` named by its label, with a `LayerControl`. `transient`.
  - Every town in the instance is a small circle marker in `towns` colour; towns on a route are larger circle markers in the route's colour; the base is the largest circle marker, in `text` colour, with a tooltip naming it (user: "okay to all"). Doc delta (CONTRACTS.md).
  - Legs are straight lat/lon polylines between stops, not great-circle arcs (user: "okay to all"). Doc delta (CONTRACTS.md).
  - Each visited town has a tooltip with route label, step number, name, population, fuel on arrival (kg) and cargo on arrival (kg), taken from `trace`. No permanent town labels (user: "okay to all"). Doc delta (CONTRACTS.md).
  - A legend box (fixed, top right) lists each route label with its colour swatch and the title if given, on `background` colour with `text` colour text; folium's `LayerControl` alone shows no colours (user: "okay to all"). Doc delta (CONTRACTS.md).
- **Acceptance criteria:**
  - [x] `plot_routes_html(inst, {"A": route}, tmp_path / "out" / "route.html")` creates the file and parent dir and returns its path (test, no network: folium only writes HTML).
  - [x] The HTML contains each route label, the base name and every visited town's name (test).
  - [x] The HTML contains each visited town's `lat` and `lon` to 4 decimals (test).
  - [x] The HTML contains `positron` (tile layer), each layer's hex colour, and `THEME["background"]` and `THEME["text"]` (test).
  - [x] `theme={"text": "#000000"}` puts `#000000` in the HTML (test).
  - [x] Empty route and two routes sharing towns render without error (test).
  - [x] `python -m pytest` passes.
- **Doc deltas:**
  - `docs/CONTRACTS.md` "Map plots": `plot_routes_html` signature and behaviour.
  - `README.md` "Plotting routes": HTML example; caveat that the HTML needs internet every time it is opened; it can be embedded in slides with an `<iframe>`.
  - Decision made: each visited town's tooltip also shows its `lat, lon` to 4 decimals. Why: the acceptance criterion asks for 4-decimal coordinates in the HTML, and folium writes floats in shortest form (`4.6`), so only formatted text guarantees them; it also helps the human location check. `docs/CONTRACTS.md` (Map plots, tooltip contents).
  - Decision made (code review): unvisited-town markers carry no tooltip; only visited towns (route tooltip) and the base have one. Why: the spec gives tooltips to visited towns only, and 745 extra tooltips bloat the HTML. `docs/CONTRACTS.md` (Map plots).
  - Decision made: the `LayerControl` sits top left, expanded, and lists the route layers as overlays, with the Positron tile layer as its only base layer (folium's default for `tiles="CartoDB positron"`, kept so the Interfaces tile line holds as written); town and base markers are added to the map directly, not toggleable. Why: the legend takes the top right, and a towns toggle is not in the spec. `docs/CONTRACTS.md` (Map plots).
  - Decision made: the map opens centred on the base at zoom 7. Why: the spec names no start view; zoom 7 shows the peninsula or one Borneo state. `docs/CONTRACTS.md` (Map plots).
  - Decision made: labels, names and the title are HTML-escaped before going into tooltips, layer names and the legend. Why: town names contain apostrophes and route labels are caller text. Needs no doc: no behaviour a caller sees changes.
  - Decision made: kept the spec's `tiles="CartoDB positron"` although xyzservices 2026.9.1 makes folium warn `UserWarning: CartoDB tiles now require an API key`. Why: the tile URL folium writes has no key and `https://a.basemaps.cartocdn.com/light_all/5/25/15.png` returned 200 `image/png` on 2026-10-27; tile access may stop working later. `README.md` (Plotting routes, tile caveat).
  - `docs/TODO.md`: tick "Map plot of A's and B's routes, to check they look sensible" only after the human checks pass (left to the user). `transient`.

## 6. Human checks

- [ ] S2: Run the README HTML example on all 745 towns from the Perak base with A and B. Open `route.html` in a browser with internet. Expected: zoomable pale grey Positron map over Malaysia; towns sit at their real locations (e.g. Ipoh, George Town on land, not in the sea); each route starts and ends at the base marker; both routes toggle in the layer control; legend shows A in `#0077BB` and B in `#EE3377`; hovering a visited town shows label, step, name, population, fuel and cargo.
- [ ] S2: Colours of the legend box and routes match the Canva slides.
- [ ] S2: Visual sanity of routes: no leg crosses the whole peninsula back and forth without reason (TODO.md: "to check they look sensible").
