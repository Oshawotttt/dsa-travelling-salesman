# dsa-travelling-salesman

Payload-aware aid airdrop: a plane leaves a base, drops 200 kg of supplies over a subset of Malaysian towns and returns with a fuel reserve.
Fuel burn depends on the plane's current weight, so the cost of a leg depends on everything flown before it.
The goal is to reach as many people as possible.
[docs/PROBLEM.md](docs/PROBLEM.md) defines the problem, the fuel model and both approaches.
[docs/CONTRACTS.md](docs/CONTRACTS.md) lists the package's public interfaces.

## Folder structure

```
airdrop/             Python package
  model.py           towns, the six bases (3 rural, 3 non-rural), aircraft parameters, distances, route evaluator, per-stop route trace
  prefix.py          RouteState: prefix sums giving O(1) insertion, removal and 2-opt fuel costs
  approach_a.py      Approach A: greedy insertion, lazy max-heap or full re-scan selector
  baseline.py        nearest neighbour with a fuel cutoff (Approach B's starting route)
  approach_b.py      Approach B: best-improvement local search (2-opt, add, swap, replace 1 with 2)
  exact_dp.py        exact backward subset DP for small instances (up to 15 towns)
  plot.py            interactive HTML map of labelled routes (folium); imported on its own, not from airdrop
tests/               pytest suite, one file per module
data/                town data, not in git (see Data below)
docs/
  PROBLEM.md         problem definition
  CONTRACTS.md       public interfaces of the package
  DECISIONS.md       decision log
  EXPERIMENT.md      experiments to run for the presentation
  TODO.md            open work
  specs/             task specs
eda.ipynb            data exploration and cleaning; writes data/cities_clean.csv
requirements.txt     dependencies (folium, numpy, pytest)
pyproject.toml       pytest configuration
```

Implemented: nearest neighbour, Approach A (heap and re-scan), Approach B and the exact DP.
Also implemented: the interactive HTML route map.
Not implemented: the experiment scripts and their plots.
Wind, climb, descent and airspace are not modelled.

## Setup

Python 3.10 or later.

```
pip install -r requirements.txt
```

### Data

`data/` is git-ignored. Put `cities_clean.csv` (built by `eda.ipynb` from GeoNames `MY.txt`) in `data/`.
The unit tests use small hand-built instances and skip the one test that reads the CSV when the file is missing.

## Running the tests

From the repo root:

```
python -m pytest                       # full suite
python -m pytest tests/test_model.py   # one file
```

## Using the solvers

Run from the repo root, so that `airdrop` and `data/` are found:

```python
from airdrop import BASES, Instance, Params, control_params, load_towns, trace
from airdrop.approach_a import greedy_insertion
from airdrop.approach_b import local_search
from airdrop.baseline import nearest_neighbour
from airdrop.exact_dp import exact_dp

towns = load_towns("data/cities_clean.csv", min_population=100_000)  # 86 towns
inst = Instance(BASES["perak"], towns, Params())                     # C-130H defaults

a = greedy_insertion(inst)                  # Approach A, lazy heap
scan = greedy_insertion(inst, "scan")       # Approach A, full re-scan
audit = greedy_insertion(inst, "heap", audit=True)
nn = nearest_neighbour(inst)                # baseline, and B's default seed
b = local_search(inst)                      # Approach B from the nearest-neighbour route
b_on_a = local_search(inst, initial=a.route)  # B on A's route (combined result)
stops = trace(inst, a.route)                # per-stop record: position, fuel, cargo, weight, population reached

for name, r in [("A heap", a), ("A scan", scan), ("NN", nn), ("B", b), ("B on A", b_on_a)]:
    print(f"{name:7} towns={len(r.route):3} population={r.eval.population:>10,} "
          f"fuel={r.eval.fuel_needed:8.0f} kg feasible={r.eval.feasible}")
print("heap picks that differ from the re-scan:", audit.stats["mismatches"])

control = Instance(BASES["perak"], towns, control_params(Params()))  # weight effect off
print("A under the control:", greedy_insertion(control).eval.population)

small = Instance(BASES["perak"], towns[:12], Params())
best = exact_dp(small)                      # optimal route; raises ValueError above 15 towns
```

Every solver returns a `SolveResult` with `route`, `eval` (a `RouteEval`) and `stats` (counters for the run).
To evaluate any route yourself, use `airdrop.evaluate(inst, route)`.
[docs/CONTRACTS.md](docs/CONTRACTS.md) has the full signatures, fields, stats and errors.

## Plotting routes

`airdrop.plot` writes a zoomable folium map of Malaysia as an `.html` file, with one toggleable layer per route.
It is called from Python only: there is no command-line entry point, no PNG output, and no experiment script.

```python
from airdrop.plot import plot_routes_html

plot_routes_html(inst, {"A": a.route, "B": b.route}, "out/route.html", title="Perak base")
```

- One map holds 1 to 5 routes. Default colours: NN `#EE7733`, A `#0077BB`, B `#EE3377`, B on A `#33BBEE`, DP `#009988`; legend box `#F4F6F8` with `#1F2A36` text; unvisited towns `#A9B4C2`. Override with the `colors` and `theme` arguments.
- Hover a visited town for its route, step, name, population, fuel and cargo.
- The map needs internet every time it is opened: the CartoDB Positron tiles are fetched live and are not cached or bundled offline.
- Tile caveat: folium warns `CartoDB tiles now require an API key`. The tile URL it writes has no key and still served tiles on 2026-10-27; access may stop working later.
- The HTML file can be embedded in slides with an `<iframe>`.
- Only `folium` is added to `requirements.txt`; `matplotlib` and `contextily` are not needed.
- [docs/CONTRACTS.md](docs/CONTRACTS.md) (Map plots) has the signatures and behaviour.

Run time: on all 745 towns from the Perak base, `greedy_insertion` takes a few seconds and `local_search` about a minute (127 rounds).
Lower `L` to speed up local search.
