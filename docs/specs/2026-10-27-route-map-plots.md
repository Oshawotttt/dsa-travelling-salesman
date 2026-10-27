# Route map plots over Malaysia

**Status:** draft
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
| S2 Static PNG map (matplotlib + contextily) | S1 |
| S3 Interactive HTML map (folium) | S1 |

Run order: S1, S2, S3.

External blockers:
- none for installs: `pip install --dry-run --only-binary=:all: matplotlib contextily folium` on Python 3.14.7 resolves to wheels (contextily 1.7.1, folium 0.20.0, rasterio 1.5.2). `transient`.
- The worktree `D:/SMU/CS201/proj/dsa-travelling-salesman` (branch `feat/experiments`) also edits `requirements.txt` and `README.md`. Merge conflicts on those two files are expected when both branches merge. `transient`.

Uncommitted changes: none at planning time. If anything other than this spec is uncommitted when the run starts, stop and ask the user.
Branch: current branch `feat/graph-map`, no new branch.

## 2. Open questions

1. **OPEN Q1** (S1, S2, S3): one route per map, or several labelled routes on one map (e.g. A and B together, each its own colour and legend entry)? Draft assumes several: `routes: Mapping[str, Sequence[int]]`.
2. **ASSUMED Q2** (S2, S3): every town in the instance is drawn as a small grey node; towns on a route are drawn larger in the route's colour; the base is a distinct marker (black triangle on the PNG, a marker with a home icon on the HTML).
3. **OPEN Q3** (S2): PNG map extent. Option (a): fit to all instance towns and the base, with a 5 % margin. Option (b): fixed extent covering all of Malaysia (lon 99.5–119.5, lat 0.8–7.5). Draft assumes (a).
4. **ASSUMED Q4** (S2, S3): legs are straight lines between stops (straight in Web Mercator on the PNG, straight lat/lon polylines on the HTML), not great-circle arcs.
5. **ASSUMED Q5** (S2, S3): PNG shows no town labels except the base name and a legend; the HTML shows a tooltip per visited town with step number, name, population, fuel on arrival (kg) and cargo on arrival (kg), taken from `trace`.
6. **ASSUMED Q6** (all): library functions only, in `airdrop/plot.py`. No CLI, no experiment script, no slide embedding (reveal.js/Quarto iframe is the user's own step).
7. **ASSUMED Q7** (S2): PNG tiles come from `contextily.providers.OpenStreetMap.Mapnik`; the HTML uses folium's default OpenStreetMap tiles. Attribution is kept on both.

## 3. Suggested splits

No split: S2 and S3 both depend on S1 (route geometry) and all three edit `airdrop/plot.py` and `tests/test_plot.py`.

## 4. Out of scope

- CLI or `python -m` entry point for plotting (ASSUMED Q6). Recorded in S3's doc delta (README "Plotting routes" says the functions are called from Python).
- Experiment scripts and their plots (EXPERIMENT.md experiments 1–5), owned by `feat/experiments`. `transient`.
- Embedding `route.html` in slides (reveal.js / Quarto). `transient`.
- Offline map tiles or caching tiles in the repo. Recorded in S2's and S3's doc deltas (internet caveat).
- Great-circle leg drawing (ASSUMED Q4). `transient`.
- Changes to the solvers, `evaluate`, `trace` or the fuel model. `transient`.

## 5. Interfaces

S1 hands geometry to S2 and S3. Doc delta to `docs/CONTRACTS.md`, new section "Map plots".

```python
# airdrop/plot.py
@dataclass(frozen=True)
class RouteLayer:
    label: str
    stops: tuple[Stop, ...]          # trace(inst, route): takeoff, drops, landing

def route_layers(inst: Instance, routes: Mapping[str, Sequence[int]]) -> list[RouteLayer]

def plot_routes_png(inst: Instance, routes: Mapping[str, Sequence[int]], path: str | Path,
                    basemap: bool = True, title: str | None = None) -> Path

def plot_routes_html(inst: Instance, routes: Mapping[str, Sequence[int]], path: str | Path,
                     title: str | None = None) -> Path
```

- `routes` maps a label (e.g. `"A"`, `"B"`) to a route in the CONTRACTS.md route format (town indices, base left out). A caller passes `{"A": result.route}` from any `SolveResult`.
- `route_layers` keeps the order of `routes`. It raises `ValueError` for any route that `trace` rejects (bad index, infinite fuel), naming the label.
- An empty route `[]` gives a layer of two stops (takeoff and landing at the base) and draws no legs.
- Both plot functions create parent directories, write the file, and return the resolved path.
- `basemap=False` skips contextily and needs no internet.

## 6. Subtasks

### S1 Route geometry from a solver result

- **Goal:** `airdrop/plot.py` exists with `RouteLayer` and `route_layers`, turning labelled routes into per-stop geometry via `trace`. Plot dependencies are in `requirements.txt`.
- **Blocked by:** none
- **Files:** `airdrop/plot.py`, `tests/test_plot.py`, `requirements.txt`
- **Seams:** `airdrop.plot.route_layers`, `airdrop.plot.RouteLayer`
- **Decisions:**
  - Input shape is the route from CONTRACTS.md (town indices, base left out) and `SolveResult.route`; geometry comes from `trace` (user: "use the output shape in contracts"). Doc delta.
  - Several labelled routes per call (OPEN Q1).
  - `requirements.txt` gains `matplotlib`, `contextily`, `folium` (user: "Then add them to requirements.txt"). Doc delta (README).
  - `airdrop/__init__.py` does not import `airdrop.plot`, so `import airdrop` never needs matplotlib, contextily or folium (code: `airdrop/__init__.py` exports only model names). Doc delta (CONTRACTS.md).
- **Acceptance criteria:**
  - [ ] `route_layers` on a hand-built instance returns one layer per label in input order, each with `len(route) + 2` stops whose `index` sequence is `[0, *route, 0]` and whose `lat`/`lon` equal the base's and towns' (test in `tests/test_plot.py`).
  - [ ] Empty route gives a layer with two base stops (test).
  - [ ] Bad index raises `ValueError` whose message contains the label (test).
  - [ ] `python -c "import airdrop, sys; assert 'matplotlib' not in sys.modules"` exits 0.
  - [ ] `python -m pytest` passes.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: new "Map plots" section with `RouteLayer`, `route_layers` and the bullets under Interfaces; note that `airdrop.plot` is imported on its own and is not re-exported from `airdrop`.
  - `README.md`: `requirements.txt` line in the folder tree lists the new dependencies; `plot.py` added to the tree.

### S2 Static PNG map (matplotlib + contextily)

- **Goal:** `plot_routes_png` writes a PNG with all towns as nodes, each route as a coloured path base → drops → base, and an OpenStreetMap basemap behind it.
- **Blocked by:** S1
- **Files:** `airdrop/plot.py`, `tests/test_plot.py`
- **Seams:** `airdrop.plot.plot_routes_png`
- **Decisions:**
  - matplotlib draws towns and route lines; contextily fetches OpenStreetMap tiles behind the plot (user). Doc delta (README).
  - "The PNG needs internet only when you generate it" (user). Doc delta (README).
  - matplotlib uses a non-interactive backend inside `plot_routes_png` (no window opens). `transient`.
  - Coordinates are converted to Web Mercator (EPSG:3857) before plotting, so contextily tiles line up. `transient`.
  - Node and base styling (ASSUMED Q2), extent (OPEN Q3), straight legs (ASSUMED Q4), no town labels (ASSUMED Q5), tile provider (ASSUMED Q7).
- **Acceptance criteria:**
  - [ ] `plot_routes_png(inst, {"A": [...], "B": [...]}, tmp_path / "out" / "map.png", basemap=False)` creates the file and parent dir, returns its path, and the file starts with the PNG signature `b"\x89PNG"` (test, no network).
  - [ ] With `basemap=False`, contextily's `add_basemap` is not called (test patches it to raise).
  - [ ] With `basemap=True`, `add_basemap` is called once with `crs="EPSG:3857"` (test patches it; no network).
  - [ ] Empty route and two routes sharing towns both render without error (test).
  - [ ] `python -m pytest` passes with no network access needed.
- **Doc deltas:**
  - `docs/CONTRACTS.md` "Map plots": `plot_routes_png` signature and behaviour (`basemap`, return value, parent dirs).
  - `README.md`: "Plotting routes" section with a PNG example; caveat that the basemap needs internet when the PNG is generated.

### S3 Interactive HTML map (folium)

- **Goal:** `plot_routes_html` writes a zoomable folium map of Malaysia with the towns, each route as a coloured polyline with a layer toggle, and per-stop tooltips.
- **Blocked by:** S1
- **Files:** `airdrop/plot.py`, `tests/test_plot.py`
- **Seams:** `airdrop.plot.plot_routes_html`
- **Decisions:**
  - folium draws the route on a zoomable Malaysia map and saves it as an `.html` file (user). Doc delta (README).
  - "The HTML map needs internet every time someone opens it" (user). Doc delta (README).
  - Each route is its own `folium.FeatureGroup` named by its label, with a `LayerControl`. `transient`.
  - Styling (ASSUMED Q2), straight legs (ASSUMED Q4), tooltips (ASSUMED Q5), tiles (ASSUMED Q7).
- **Acceptance criteria:**
  - [ ] `plot_routes_html(inst, {"A": route}, tmp_path / "out" / "route.html")` creates the file and parent dir and returns its path (test, no network: folium only writes HTML).
  - [ ] The HTML contains each route label, the base name and every visited town's name (test).
  - [ ] The HTML contains each visited town's coordinates as written by folium (test checks `lat` and `lon` values to 4 decimals appear).
  - [ ] Empty route renders without error (test).
  - [ ] `python -m pytest` passes.
- **Doc deltas:**
  - `docs/CONTRACTS.md` "Map plots": `plot_routes_html` signature and behaviour.
  - `README.md` "Plotting routes": HTML example; caveat that the HTML needs internet every time it is opened; it can be embedded in slides with an `<iframe>`.
  - `docs/TODO.md`: tick "Map plot of A's and B's routes, to check they look sensible" only after the human checks pass (left to the user). `transient`.

## 7. Human checks

- [ ] S2: Run the README PNG example on all 745 towns from the Perak base with A and B. Open the PNG. Expected: Malaysia OSM basemap visible; towns align with their real locations (e.g. Ipoh, George Town on land, not in the sea); each route starts and ends at the base triangle; legend shows A and B.
- [ ] S3: Run the README HTML example, open `route.html` in a browser with internet. Expected: zoomable map over Malaysia; both routes toggle in the layer control; hovering a visited town shows step, name, population, fuel and cargo.
- [ ] S2/S3: Visual sanity of routes: no leg crosses the whole peninsula back and forth without reason (TODO.md: "to check they look sensible").
