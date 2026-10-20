# dsa-travelling-salesman

Payload-aware aid airdrop: a plane leaves a base, drops 200 kg of supplies over a subset of Malaysian towns and returns with a fuel reserve.
Fuel burn depends on the plane's current weight, so the cost of a leg depends on everything flown before it.
The goal is to reach as many people as possible.
[PROBLEM.md](PROBLEM.md) defines the problem, the fuel model and both approaches.

## Folder structure

```
airdrop/             Python package
  model.py           towns, the five bases, aircraft parameters, distances, route evaluator
  prefix.py          RouteState: prefix sums giving O(1) insertion, removal and 2-opt fuel costs
  approach_a.py      Approach A: greedy insertion, lazy max-heap or full re-scan selector
  baseline.py        nearest neighbour with a fuel cutoff (Approach B's starting route)
  approach_b.py      Approach B: best-improvement local search (2-opt, add, swap, replace 1 with 2)
tests/               pytest suite, one file per module
data/                town data, not in git (see Data below)
docs/                assignment brief and task specs
eda.ipynb            data exploration and cleaning; writes data/cities_clean.csv
PROBLEM.md           problem definition
requirements.txt     dependencies (numpy, pytest)
pyproject.toml       pytest configuration
```

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
from airdrop import BASES, Instance, Params, control_params, load_towns
from airdrop.approach_a import greedy_insertion
from airdrop.approach_b import local_search
from airdrop.baseline import nearest_neighbour

towns = load_towns("data/cities_clean.csv", min_population=100_000)  # 86 towns
inst = Instance(BASES["perak"], towns, Params())                     # C-130H defaults

a = greedy_insertion(inst)                  # Approach A, lazy heap
scan = greedy_insertion(inst, "scan")       # Approach A, full re-scan
audit = greedy_insertion(inst, "heap", audit=True)
nn = nearest_neighbour(inst)                # baseline, and B's default seed
b = local_search(inst)                      # Approach B from the nearest-neighbour route
b_on_a = local_search(inst, initial=a.route)  # B on A's route (combined result)

for name, r in [("A heap", a), ("A scan", scan), ("NN", nn), ("B", b), ("B on A", b_on_a)]:
    print(f"{name:7} towns={len(r.route):3} population={r.eval.population:>10,} "
          f"fuel={r.eval.fuel_needed:8.0f} kg feasible={r.eval.feasible}")
print("heap picks that differ from the re-scan:", audit.stats["mismatches"])

control = Instance(BASES["perak"], towns, control_params(Params()))  # weight effect off
print("A under the control:", greedy_insertion(control).eval.population)
```

Every solver returns a `SolveResult` with:

- `route`: town indices in flying order, base left out (`towns[i - 1]` is town `i`);
- `eval`: a `RouteEval` with `population`, `distance` (km), `cargo` (kg), `fuel_needed` (kg), `feasible` and `reason` (the first failed check, or `None`);
- `stats`: counters for the run.
  - `greedy_insertion`: `score_evals` (candidate scorings), `insertions`. The heap adds `heap_pops` and `heap_pushes` (the initial pushes included). `audit=True` adds `mismatches`: steps where the heap's pick differs from the full re-scan's. The audit's own scorings are not counted in `score_evals`.
  - `nearest_neighbour`: `checks` (candidate feasibility checks) and `steps` (towns added).
  - `local_search`: `rounds` (moves applied), one count per move type (`two_opt`, `add`, `swap`, `replace_1_2`), and `hit_max_rounds` (1 when `max_rounds` stopped the search with an improving move left).

To evaluate any route yourself, use `airdrop.evaluate(inst, route)`.
All aircraft constants are fields of `Params` (`F`, `E`, `C`, `MTOW`, `c`, `w`, `R`, and optionally `a` and `b`).
`local_search` takes `initial` (a feasible route; an infeasible one raises `ValueError`), `L` (candidates per removed town for replace 1 with 2, default 20) and `max_rounds` (default 10,000).

Run time: on all 745 towns from the Perak base, `greedy_insertion` takes a few seconds and `local_search` about a minute (127 rounds).
Lower `L` to speed up local search.
