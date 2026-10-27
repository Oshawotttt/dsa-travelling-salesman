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
```

- `airdrop.plot` is imported on its own (`from airdrop.plot import ...`) and is not re-exported from `airdrop`, so `import airdrop` never needs `folium`.
- `routes` maps a label (e.g. `"A"`, `"B"`) to a route in the [route format](#routes-and-indices) (town indices, base left out); pass `{"A": result.route}` from any `SolveResult`. Geometry comes from `trace`. One map holds 1 to 5 routes.
- An empty `routes` raises `ValueError("at least 1 route per map, got 0")`; more than 5 raises `ValueError`. The limit is checked before any route is traced.
- Route colour: `colors[label]` if the label is a key of `colors` (even with a falsy value such as `""`), else `ROUTE_COLORS[label]`, else the first `ROUTE_COLORS` value (in `ROUTE_COLORS` order) not already used on that map. Colours resolve in two passes (known labels first, then unknown labels in route order), so an unknown label listed before a known one never takes the known label's colour. "Already used" compares colours case-insensitively.
- `theme` keys override `THEME` keys; missing keys fall back to `THEME`.
- `route_layers` keeps the order of `routes`. A route that `trace` rejects (bad index, infinite fuel) raises `ValueError(f"route {label!r}: <trace message>")`, chained from the `trace` error.
- An empty route `[]` gives a layer of two stops (takeoff and landing at the base) and draws no legs.
- `plot_routes_html` creates parent directories, writes the HTML file, and returns the resolved path.
- Map content: tiles are CartoDB Positron (`tiles="CartoDB positron"`, attribution kept); the map opens centred on the base at zoom 7. Every town in the instance is a small circle marker in the `towns` colour, with no tooltip. Each route is its own `folium.FeatureGroup` named by its label. Its legs are straight lat/lon polylines between stops (not great-circle arcs), and its visited towns are larger circle markers in the route colour. The base is the largest circle marker, in the `text` colour, with a tooltip naming it.
- Each visited town's tooltip shows route label, step number, name, population, fuel on arrival (kg), cargo on arrival (kg) and `lat, lon` to 4 decimals, from `trace`. There are no permanent town labels.
- `LayerControl` sits top left, expanded, and lists the route layers as overlays; the Positron tile layer is its only base layer. Town and base markers are added to the map directly and cannot be toggled.
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
