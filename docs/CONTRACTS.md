# Contracts

The public interfaces of the `airdrop` package. [PROBLEM.md](PROBLEM.md) defines what they compute.
Units are km and kg throughout.

## Routes and indices

- Index `0` is the base. Towns are `1..n`, and `towns[i - 1]` is town `i`.
- A route lists town indices in flying order, with the base left out: `base → route[0] → … → route[-1] → base`.
- The empty route `[]` is valid: the plane stays at the base.

## Data

```python
# airdrop/model.py
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

BASES: dict[str, Base]   # "perak", "sarawak", "sabah", "klia", "kuching", "kota_kinabalu"
RURAL_BASES = ("perak", "sarawak", "sabah")
URBAN_BASES = ("klia", "kuching", "kota_kinabalu")

def load_towns(path: str | Path, min_population: int = 0) -> list[Town]
```

- `load_towns` reads `data/cities_clean.csv` and keeps towns with `population >= min_population`. The default keeps all 745.

## Parameters

```python
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

def control_params(p: Params) -> Params   # b = 0, a = c * M_REF (M_REF = 60,000 kg)
```

## Instance

```python
class Instance:
    def __init__(self, base: Base, towns: Sequence[Town], params: Params)
    base: Base
    towns: tuple[Town, ...]
    n: int                      # number of towns
    params: Params
    a: float                    # resolved a
    b: float                    # resolved b
    dist_matrix: np.ndarray     # (n + 1) x (n + 1) haversine km, symmetric, zero diagonal
    def dist(self, i: int, j: int) -> float
    def population(self, i: int) -> int     # 0 for the base
    def fuel_limit(self, k: int) -> float   # min(F, MTOW - E - w * k)
    def fits(self, k: int, fuel: float) -> bool   # w * k <= C and fuel <= fuel_limit(k)
```

## Route evaluation

```python
@dataclass(frozen=True)
class RouteEval:
    population: int
    distance: float          # D, km
    cargo: float             # W0 = w * k
    fuel_needed: float       # F0_needed
    feasible: bool
    reason: str | None       # None, or the first failing check

def evaluate(inst: Instance, route: Sequence[int]) -> RouteEval
def fuel_end(inst: Instance, route: Sequence[int], F0: float) -> float
```

- `reason` is one of `None`, `"bad_index"`, `"duplicate"`, `"payload"`, `"fuel_cap"`, `"takeoff_weight"`, checked in that order.
- A route with a bad index evaluates to population 0, distance 0 and `fuel_needed = inf`.
- A fuel term that overflows gives `fuel_needed = inf` (reason `fuel_cap`), never an exception.
- `fuel_end` is the fuel left on landing when the route is flown with `F0` loaded.

## Solvers

Every solver returns a `SolveResult` and never mutates the instance.

```python
# airdrop/approach_a.py
@dataclass
class SolveResult:
    route: list[int]
    eval: RouteEval          # == evaluate(inst, route)
    stats: dict[str, int]

def greedy_insertion(inst: Instance, selector: Literal["heap", "scan"] = "heap",
                     audit: bool = False) -> SolveResult

# airdrop/baseline.py
def nearest_neighbour(inst: Instance) -> SolveResult

# airdrop/approach_b.py
def local_search(inst: Instance, initial: Sequence[int] | None = None,
                 L: int = 20, max_rounds: int = 10_000) -> SolveResult
```

| Solver | `stats` keys |
|---|---|
| `greedy_insertion` | `score_evals` (candidate scorings), `insertions`. The heap adds `heap_pops` and `heap_pushes` (initial pushes included). `audit=True` adds `mismatches`: steps where the heap's pick differs from the full re-scan's; the audit's own scorings are not in `score_evals`. |
| `nearest_neighbour` | `checks` (candidate feasibility checks), `steps` (towns added). |
| `local_search` | `rounds` (moves applied), one count per move type (`two_opt`, `add`, `swap`, `replace_1_2`), `hit_max_rounds` (1 when `max_rounds` stopped the search with an improving move left). |

- `greedy_insertion` raises `ValueError` for an unknown `selector`.
- `local_search` starts from `nearest_neighbour(inst).route` when `initial` is `None`. An infeasible `initial` raises `ValueError`. `L` is the candidate count per removed town for replace 1 with 2.

## Exact solver

```python
# airdrop/exact_dp.py
def exact_dp(inst: Instance, max_n: int = 15) -> SolveResult
```

- Returns the optimal route: largest population; ties go to the least fuel needed; remaining ties go to the smallest route as a tuple. Fuels within `1e-9` relative count as tied.
- `route` and `eval` as for every solver; `eval == evaluate(inst, route)`.
- `stats`: `states` (table entries kept), `transitions` (every `before` call that computes a candidate `need` entry, including the landing leg of `|U| = 1`; takeoff legs are not counted).
- Raises `ValueError` when `inst.n > max_n`.
- When no town fits, `route == []`.

## Route trace

```python
# airdrop/model.py
@dataclass(frozen=True)
class Stop:
    step: int                # 0 = takeoff at base, 1..k = drops in order, k + 1 = landing at base
    index: int               # 0 for the base, town index otherwise
    geonameid: int
    name: str
    lat: float
    lon: float
    population: int          # 0 at the base
    leg_km: float            # length of the leg flown to reach this stop (0 at takeoff)
    distance_km: float       # distance flown so far
    leg_fuel_kg: float       # fuel burnt on that leg (0 at takeoff)
    fuel_kg: float           # fuel on board on arrival (takeoff: F0_needed; landing: R)
    cargo_kg: float          # cargo on board on arrival, before the drop
    weight_kg: float         # E + cargo_kg + fuel_kg
    population_reached: int  # total population of drops up to and including this stop

def trace(inst: Instance, route: Sequence[int]) -> list[Stop]
```

- Works for a route from any solver; no solver is instrumented. `Stop` and `trace` are exported from `airdrop`.
- Returns `len(route) + 2` stops. Raises `ValueError` when `evaluate(inst, route).fuel_needed` is `inf` or the route has a bad index. A route that is infeasible with finite fuel (duplicate, payload, fuel cap, takeoff weight) is still traced.
- Fuel on board assumes the plane loads exactly `F0_needed`, so it lands with the fixed reserve `R` (1,700 kg), not a percentage reserve. The landing stop's `fuel_kg` is the forward-flown value (equal to `R` within rounding), so the `leg_fuel_kg` values add up to `F0_needed - fuel_kg` at landing.
- Fuel on a leg of length `d` with cargo `W`: `fuel_after = f + (f + W)·expm1(-b·d) + a·expm1(-b·d)/b` (`f - a·d` at `b = 0`).
- Takeoff and landing stops carry the base's `geonameid`, `name`, `lat`, `lon`.

## Map plots

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
    color: str                       # hex, from colors / ROUTE_COLORS
    stops: tuple[Stop, ...]          # trace(inst, route): takeoff, drops, landing

def route_layers(inst: Instance, routes: Mapping[str, Sequence[int]],
                 colors: Mapping[str, str] | None = None) -> list[RouteLayer]

def plot_routes_html(inst: Instance, routes: Mapping[str, Sequence[int]], path: str | Path,
                     title: str | None = None,
                     colors: Mapping[str, str] | None = None,
                     theme: Mapping[str, str] | None = None) -> Path

def stop_layers(routes: Mapping[str, Sequence[Stop]],
                colors: Mapping[str, str] | None = None) -> list[RouteLayer]
def plot_stops_html(base: Base, towns: Sequence[Town], routes: Mapping[str, Sequence[Stop]],
                    path: str | Path, title: str | None = None,
                    colors: Mapping[str, str] | None = None,
                    theme: Mapping[str, str] | None = None) -> Path
```

- `airdrop.plot` is imported on its own (`from airdrop.plot import ...`) and is not re-exported from `airdrop`, so `import airdrop` never needs `folium`.
- `routes` maps a label (e.g. `"A"`, `"B"`) to a route in the [route format](#routes-and-indices) (town indices, base left out); pass `{"A": result.route}` from any `SolveResult`. Geometry comes from `trace`. One map holds 1 to 5 routes.
- An empty `routes` raises `ValueError("at least 1 route per map, got 0")`; more than 5 raises `ValueError`. The limit is checked before any route is traced.
- Route colour: `colors[label]` if the label is a key of `colors` (even with a falsy value such as `""`), else `ROUTE_COLORS[label]`, else the first `ROUTE_COLORS` value (in `ROUTE_COLORS` order) not already used on that map. Colours resolve in two passes (known labels first, then unknown labels in route order), so an unknown label listed before a known one never takes the known label's colour. "Already used" compares colours case-insensitively.
- `theme` keys override `THEME` keys; missing keys fall back to `THEME`.
- `route_layers` keeps the order of `routes`. A route that `trace` rejects (bad index, infinite fuel) raises `ValueError(f"route {label!r}: <trace message>")`, chained from the `trace` error.
- An empty route `[]` gives a layer of two stops (takeoff and landing at the base) and draws no legs.
- `stop_layers` and `plot_stops_html` take routes already traced: each value is a route's stops, takeoff to landing (as `trace` returns them, or as `read_routes` reads them back). Count limits and colours are as for `route_layers`; the stops are used as given, not re-traced. `plot_stops_html` draws `towns` as the small background circles and `base` as the base marker; otherwise its output is the same as `plot_routes_html` for the same stops.
- `plot_routes_html` creates parent directories, writes the HTML file, and returns the resolved path.
- Map content: tiles are Wikimedia's OpenStreetMap rendering with English labels (`TILES`, `TILES_ATTR` in `airdrop/plot.py`; CartoDB Positron now needs an API key); the map opens framed on the base and every route stop (30 px padding), or centred on the base at zoom 7 when no route leaves it. Every town in the instance is a small circle marker in the `towns` colour, with no tooltip. Each route is its own `folium.FeatureGroup` named by its label. Its legs are straight lat/lon polylines between stops (not great-circle arcs), and its visited towns are larger circle markers in the route colour. The base is the largest circle marker, in the `text` colour, with a tooltip naming it.
- Each visited town's tooltip shows route label, step number, name, population, fuel on arrival (kg), cargo on arrival (kg) and `lat, lon` to 4 decimals, from `trace`. There are no permanent town labels.
- `LayerControl` sits top left, expanded, and lists the route layers as overlays; the Wikimedia tile layer is not listed in it. Town and base markers are added to the map directly and cannot be toggled.
- A fixed legend box (top right) lists each route label with its colour swatch, and the title if given, on the `background` colour with `text` colour text.
- Labels, names and the title are HTML-escaped (with `` ` `` and `$` also escaped) before going into tooltips, layer names and the legend.

## Route state

```python
# airdrop/prefix.py
class RouteState:
    def __init__(self, inst: Instance, route: Sequence[int])   # O(k)
    route: tuple[int, ...]
    fuel_needed: float
    def insert_fuel(self, t: int, pos: int) -> float           # O(1): insert t before route[pos], pos in 0..k
    def best_insertion(self, t: int) -> tuple[int, float]      # O(k): (pos, fuel), ties to the smallest pos
    def best_insertions(self, towns: Sequence[int]) -> tuple[list[int], list[float]]  # vectorised, in towns order
    def remove_fuel(self, pos: int) -> float                   # O(1): remove route[pos]
    def two_opt_fuel(self, i: int, j: int) -> float            # O(1): reverse route[i..j], 0 <= i < j < k
```

- Each method returns the fuel needed by the route after the move, without applying it.

## Experiment output

```python
# experiments/common.py
ALGORITHMS = ("nn", "a_heap", "a_scan", "b", "b_on_a", "dp")

@dataclass(frozen=True)
class Run:
    experiment: str          # folder name, e.g. "e3_bases"
    run_id: int              # 0, 1, ... within one experiment output
    algorithm: str           # one of ALGORITHMS
    base: str                # key in BASES
    n_towns: int             # inst.n
    sample: int | None       # random seed of the town sample (experiment 4), else None
    F: float                 # fuel cap used
    population: int
    towns_visited: int       # len(route)
    distance_km: float
    fuel_needed_kg: float
    feasible: bool
    time_s: float            # solver wall-clock, best of repeats
    stats: dict[str, int]    # SolveResult.stats

def solve(inst: Instance, algorithm: str, a_route: Sequence[int] | None = None) -> SolveResult
def run(experiment: str, run_id: int, inst: Instance, base: str, algorithm: str,
        sample: int | None = None, repeats: int = 1,
        a_route: Sequence[int] | None = None) -> tuple[Run, list[Stop], SolveResult]
def write_outputs(out_dir: Path, runs: Sequence[Run], stops: Mapping[int, Sequence[Stop]]) -> None
def read_runs(path: Path) -> list[dict]
def read_routes(path: Path) -> dict[int, list[Stop]]
```

Every solver run in every experiment goes through `run()`, and every plot is drawn only from the CSV files, never from in-memory results. The map plot of routes reads `routes.csv`.

Algorithm names:

| Name | Calls |
|---|---|
| `nn` | `nearest_neighbour(inst)` |
| `a_heap` | `greedy_insertion(inst, "heap")` |
| `a_scan` | `greedy_insertion(inst, "scan")` |
| `b` | `local_search(inst)` |
| `b_on_a` | `local_search(inst, initial=a_route)` |
| `dp` | `exact_dp(inst)` |

- `solve` raises `ValueError` for an unknown algorithm, and for `"b_on_a"` without `a_route`. `run` raises `ValueError` when `repeats < 1`.
- `time_s` is wall-clock `time.perf_counter()` around the solver call only (not `trace`, not CSV writing). With `repeats > 1` it is the minimum, and `run` returns the last call's `SolveResult` (the solvers are deterministic). Experiments 1 and 2 use 3 repeats, the others 1.

`runs.csv` columns, in this order:
`experiment, run_id, algorithm, base, n_towns, sample, F, population, towns_visited, distance_km, fuel_needed_kg, feasible, time_s, stats`
- `sample` is empty when `None`; `feasible` is `True`/`False`; `stats` is a JSON object string.
- One row per run, in `run_id` order.

`routes.csv` columns, in this order:
`experiment, run_id, algorithm, base, step, index, geonameid, name, lat, lon, population, leg_km, distance_km, leg_fuel_kg, fuel_kg, cargo_kg, weight_kg, population_reached`
- One row per `Stop` of `trace(inst, route)`: `len(route) + 2` rows per run, in `step` order. Rows follow the order of `runs`, then `step`.
- Joins to `runs.csv` on `(experiment, run_id)`.
- The columns of both files are derived from the `Run` and `Stop` dataclass fields (`routes.csv` is the 4 key columns then every `Stop` field), so the files cannot drift from the dataclasses.

`read_runs` returns one dict per row with typed values: `run_id`, `n_towns`, `population`, `towns_visited` as `int`; `F`, `distance_km`, `fuel_needed_kg`, `time_s` as `float`; `feasible` as `bool`; `sample` as `None` when empty, else `int`; `stats` parsed from JSON. Plots need no casting.

`read_routes` returns each run's stops as `Stop` objects keyed by `run_id`, each list in `step` order; values are cast to the `Stop` field types, so it returns what `trace` returned.

### Route maps

```
python -m experiments.maps FOLDER [FOLDER ...] [--out DIR]
```

```python
# experiments/maps.py
LABELS = {"nn": "NN", "a_heap": "A", "a_scan": "A scan", "b": "B", "b_on_a": "B on A", "dp": "DP"}

def map_name(base: str, n_towns: int, sample: int | None, F: float) -> str
def write_maps(out_dir: Path, maps_dir: Path | None = None) -> list[Path]
def main(argv: Sequence[str] | None = None) -> None
```

- Reads `runs.csv` and `routes.csv` of an experiment output folder only; nothing is re-solved and `data/` is not read.
- One map per instance: runs with the same `(base, n_towns, sample, F)`, in first-run order. Each run is one layer, labelled by `LABELS` (so it gets its `ROUTE_COLORS` colour); `a_scan` takes a spare colour. Every experiment has at most 5 runs per instance.
- File: `<maps_dir>/<base>_n<n_towns>[_s<sample>]_F<F>.html`, e.g. `perak_n745_F21100.html`, `perak_n12_s3_F4890.html`. `maps_dir` defaults to `<out_dir>/maps`.
- Title: `<experiment>: <base>, <n_towns> towns[, sample <sample>], F <F> kg`.
- The base marker is the takeoff stop. The grey background circles are the towns visited by any route on that map: towns no route visits are not in the CSVs, so they are not drawn.
- `main` prints each written path. It exits with an argparse error when a folder lacks `runs.csv` or `routes.csv`, or when `--out` is given with more than one folder.

Each experiment folder `experiments/eN_<name>/` has `run.py` with:

```python
def run_experiment(towns: Sequence[Town], out_dir: Path, **grid) -> None   # writes runs.csv, routes.csv
def plot(out_dir: Path) -> None                                           # reads out_dir/runs.csv only, writes plot.png
```

Grid keywords and defaults (the module entry point passes only the towns and the output folder):

| Experiment | `run_experiment` signature |
|---|---|
| `e1_heap_vs_scan`, `e2_run_time` | `(towns, out_dir, thresholds=(100_000, 50_000, 15_000, 0), base="perak", repeats=3)` |
| `e3_bases` | `(towns, out_dir, bases=tuple(BASES))` |
| `e4_optimality_gap` | `(towns, out_dir, seeds=range(10), sample_size=12, base="perak", min_samples=8, share=0.8)` |

`experiments/e4_optimality_gap/run.py` also exposes:

```python
def full_fit_F(samples: Sequence[Sequence[Town]], base: Base, min_samples: int = 8) -> float
def coverage_F(samples: Sequence[Sequence[Town]], base: Base, share: float = 0.8) -> float
def peninsular_towns(path: Path) -> list[Town]   # towns whose CSV `region` is Peninsular
```

- Both `F` functions return a multiple of 10 kg in `[R, 21,100]`, found by binary search that assumes the rule is false below the answer and true above it. They raise `ValueError` when the rule fails at 21,100 kg.
- `full_fit_F`: the DP route visits every town in at least `min_samples` samples. `coverage_F`: the mean DP route length is at least `share` of the sample size (compared with a `1e-9` tolerance on the totals).
