# Experiment scripts with a shared output contract

**Status:** approved
**Repo:** `D:\SMU\CS201\proj\dsa-travelling-salesman`
**Context file to update:** none named
**Source docs:** `README.md`, and in `docs/`: `EXPERIMENT.md`, `PROBLEM.md` (Evaluation plan, Bases, Parameters), `CONTRACTS.md` (solvers, `exact_dp`, `Stop`/`trace`), `DECISIONS.md`, `DOMAIN-RESEARCH.md`, `TODO.md`. The repo has no CLAUDE.md, no ADRs, no glossary. Terms follow PROBLEM.md: *town*, *base*, *drop*, *route*, *fuel needed* (`F₀_needed`), *fuel cap* (`F`).

**Commands** (from the repo root, after `pip install -r requirements.txt`):
- Full test suite: `python -m pytest`
- Single test file: `python -m pytest tests/test_experiments.py`
- Typecheck: none
- Lint: none

## 1. Dependencies and blockers

| Subtask | Blocked by |
|---|---|
| S1 Run contract and shared runner | none |
| S2 Fixed fuel cap in the experiment plan (docs only) | none |
| S3 Experiment 1: heap vs scan | S1, S2 |
| S4 Experiment 2: run time | S1, S2 |
| S5 Experiment 3: bases | S1, S2 |
| S6 Experiment 4: optimality gap | S1, S2 |

Run order: S1, S2, S3, S4, S5, S6.

External blockers:
- `data/cities_clean.csv` must be present to run the full experiments (it is, locally). Tests do not read it.
- A second worktree `graph-map/` (branch `feat/graph-map`) sits inside the repo folder, untracked. It is for the map plot of routes, which will read the `routes.csv` defined in S1.

Uncommitted changes that must stay out of the commits: the untracked folder `graph-map/` (a git worktree). Never `git add` it, and never use `git add -A` or `git add .`. If anything other than this spec and `graph-map/` is uncommitted when the run starts, stop and ask the user.
Branch: current branch `feat/experiments`, no new branch.

## 2. Suggested splits

No split: S3–S6 are each blocked by S1 (they all write through its runner and contract) and by S2 (the plan they implement).

## 3. Out of scope

- The fuel sweep experiment (population against `F` per algorithm), and any `F` sweep. Removed by the user; recorded by S2's doc deltas.
- The map plot of routes (worktree `graph-map/`, branch `feat/graph-map`). This task only writes `routes.csv` in the contract it reads. `transient`.
- The control experiment (`control_params`). Already dropped, see `docs/DECISIONS.md` 2026-10-27. `transient`.
- Changes to the solvers, the fuel model, `trace`, `Params` defaults or `eda.ipynb`. `transient`.
- Slides. `transient`.

## 4. Interfaces

Doc delta to `docs/CONTRACTS.md` (new section "Experiment output") on S1.

```python
# experiments/common.py  (S1)
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
    # "b_on_a" needs a_route; an unknown algorithm, or "b_on_a" without a_route, raises ValueError
def run(experiment: str, run_id: int, inst: Instance, base: str, algorithm: str,
        sample: int | None = None, repeats: int = 1,
        a_route: Sequence[int] | None = None) -> tuple[Run, list[Stop], SolveResult]
def write_outputs(out_dir: Path, runs: Sequence[Run], stops: Mapping[int, Sequence[Stop]]) -> None
def read_runs(path: Path) -> list[dict]
```

`runs.csv` columns, in this order:
`experiment, run_id, algorithm, base, n_towns, sample, F, population, towns_visited, distance_km, fuel_needed_kg, feasible, time_s, stats`
- `sample` is empty when `None`; `feasible` is `True`/`False`; `stats` is a JSON object string.

`routes.csv` columns, in this order:
`experiment, run_id, algorithm, base, step, index, geonameid, name, lat, lon, population, leg_km, distance_km, leg_fuel_kg, fuel_kg, cargo_kg, weight_kg, population_reached`
- One row per `Stop` of `trace(inst, route)`: `len(route) + 2` rows per run, in `step` order.
- Joins to `runs.csv` on `(experiment, run_id)`.

Each experiment folder `experiments/eN_<name>/` has `run.py` with:

```python
def run_experiment(towns: Sequence[Town], out_dir: Path, **grid) -> None   # writes runs.csv, routes.csv
def plot(out_dir: Path) -> None                                           # reads out_dir/runs.csv only, writes plot.png
```

It is run as `python -m experiments.eN_<name>.run` from the repo root. That loads `data/cities_clean.csv` and writes to `experiments/eN_<name>/out/`.

## 5. Subtasks

### S1 Run contract and shared runner

- **Goal:** one module runs any algorithm on an instance, times it, traces its route, and writes `runs.csv` and `routes.csv` in the contract above.
- **Blocked by:** none
- **Files:** `experiments/__init__.py`, `experiments/common.py` (new), `tests/test_experiments.py` (new), `requirements.txt`.
- **Seams:** `solve`, `run`, `write_outputs`, `read_runs`; `airdrop.evaluate`, `airdrop.trace`.
- **Decisions:**
  - Every solver run in every experiment goes through `run()`, which writes `runs.csv` (one row per run) and `routes.csv` (one row per `Stop` from `trace`, keyed by `run_id`). Every plot is drawn only from those CSV files, never from in-memory results. The map plot (worktree `graph-map/`) reads `routes.csv`. Decision (user): "yes". Doc delta: `docs/CONTRACTS.md`.
  - Output files go in `experiments/<folder>/out/` (`runs.csv`, `routes.csv`, `plot.png`) and are committed. Decision (user): "yes". Doc delta: `README.md` (Running the experiments).
  - Run time is wall-clock `time.perf_counter()` around the solver call only (not `trace`, not CSV writing); best of 3 repeats in experiments 1 and 2, 1 run elsewhere. Decision (user): "yes". Doc delta: `docs/CONTRACTS.md` (`time_s`).
  - Approach A is `a_heap` in experiments 2–4; experiments 1 and 2 also run `a_scan`. Decision (user): "yes". Doc delta: `docs/EXPERIMENT.md`.
  - `"a_heap"` is `greedy_insertion(inst, "heap")`, `"a_scan"` is `greedy_insertion(inst, "scan")`, `"nn"` is `nearest_neighbour(inst)`, `"b"` is `local_search(inst)`, `"b_on_a"` is `local_search(inst, initial=a_route)`, `"dp"` is `exact_dp(inst)`. Doc delta: `docs/CONTRACTS.md`.
  - `matplotlib` in `requirements.txt`, no pandas: CSV via the `csv` module. Decision (user): "yes". Doc delta: `README.md`.
- **Acceptance criteria:**
  - [x] On a small hand-built instance, `solve` for each name in `ALGORITHMS` returns the same route as the direct solver call. An unknown name, and `"b_on_a"` without `a_route`, raise `ValueError`. `tests/test_experiments.py::test_solve_dispatch`
  - [x] `write_outputs` writes `runs.csv` and `routes.csv` with exactly the section 4 headers, in order. `tests/test_experiments.py::test_output_headers`
  - [x] Each run has `len(route) + 2` rows in `routes.csv`, in `step` order, equal to `trace(inst, route)` field by field. The `runs.csv` values `population`, `distance_km`, `fuel_needed_kg` and `feasible` equal `evaluate(inst, route)`. `tests/test_experiments.py::test_outputs_match_trace`
  - [x] `read_runs` round-trips `stats` (JSON) and `sample` (empty for `None`). `tests/test_experiments.py::test_read_runs`
  - [x] Full suite passes: `python -m pytest`.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: new "Experiment output" section (section 4), including the algorithm names and what each one calls.
  - `README.md`: folder structure line for `experiments/`; a "Running the experiments" section; matplotlib in the dependencies line.
  - Decisions made during S1:
    - `read_runs` also casts the numeric columns (`run_id`, `n_towns`, `F`, `population`, `towns_visited`, `distance_km`, `fuel_needed_kg`, `time_s`) to `int`/`float` and `feasible` to `bool`, so plots need no casting. Doc: `docs/CONTRACTS.md` (Experiment output).
    - The CSV columns are derived from the `Run` and `Stop` dataclass fields (`routes.csv` is the 4 key columns then every `Stop` field), so the files cannot drift from the dataclasses. Doc: `docs/CONTRACTS.md`.
    - `routes.csv` rows follow the order of `runs`, then `step`. Doc: `docs/CONTRACTS.md`.
    - With `repeats > 1`, `run` returns the last call's `SolveResult` (the solvers are deterministic) and `time_s` is the minimum. Doc: `docs/CONTRACTS.md` (`time_s`).

### S2 Fixed fuel cap in the experiment plan (docs only)

- **Goal:** the docs plan no fuel sweep and no `F` sweep, every experiment uses `F = 21,100 kg` except the optimality gap, and the docs say why.
- **Blocked by:** none
- **Files:** `docs/EXPERIMENT.md`, `docs/PROBLEM.md`, `docs/DOMAIN-RESEARCH.md`, `docs/DECISIONS.md`, `docs/TODO.md` (only if it names experiment numbers).
- **Seams:** none (docs only).
- **Decisions:**
  - The fuel sweep experiment (population against `F`, NN/A/B, from 3,000 to 20,000 kg) is removed. `docs/DOMAIN-RESEARCH.md` justifies the default `F = 21,100 kg` as the C-130H internal tank, and experiment 3 (bases) compares the algorithms on 6 instances. Decision (user): "yes" to dropping it. Doc delta: `docs/DECISIONS.md`, new entry "No fuel sweep", in the style of "No control experiment".
  - "change everything to 21100. the bases exp aslo" (user). Experiments 1–3 use default `Params` (`F = 21,100 kg`). Experiment 1 varies the number of towns, not `F`. The bases experiment moves from `F = 20,000` to `21,100 kg`. Doc delta: `docs/DECISIONS.md` (same entry), `docs/EXPERIMENT.md`, `docs/PROBLEM.md` (Evaluation plan "Base comparison", Parameters rows `base` and `F`: "Swept from about 3 t to 20 t" and "compared at `F = 20 t`" become 21,100 kg), `docs/DOMAIN-RESEARCH.md` (remove the Summary row "`F` sweep" and the "Experiment ranges" row "`F` sweep"; the "Base comparison" row becomes `F = 21,100 kg`, the full internal tank; remove the sentence "`F` is also swept in the experiments, so the exact default matters less than the range").
  - The optimality gap uses two lower fixed `F` values, each the same for all 10 samples and each stated as an assumption (a partial fuel load for a short-range sortie). Decision (user): "have 2 Fs for optimality. like one should be enuf to cover all the nodes in most cases. and the other mayb only can cover like 70-90%".
    - `F_full`: the smallest multiple of 10 kg in `[R, 21,100]` at which the exact DP route visits all 12 towns in at least 8 of the 10 samples ("most cases" = 8 of 10; user: "yes").
    - `F_tight`: the smallest multiple of 10 kg in `[R, 21,100]` at which the exact DP routes over the 10 samples visit on average at least 80% of the 12 towns (9.6 towns) (80%, the middle of 70–90%; user: "yes").
    - Both are found by binary search over multiples of 10 kg.
    - Reason for a lower `F` at all: at `F = 21,100 kg` every 12-town sample fits whole, so NN, A and B all score exactly the optimum (checked on 10 samples from all towns and from Peninsular towns: every gap 1.000).
    - This replaces the earlier rule "`F` set so about half the towns fit" and the user's choice "do 1" (one fixed `F` where half fit).
    - Doc delta: `docs/DECISIONS.md` (same entry), `docs/PROBLEM.md` (Evaluation plan "Optimality gap": replaces "with `F` set so about half the towns fit"), `docs/EXPERIMENT.md`.
  - The optimality gap's 12-town samples are drawn from Peninsular towns only (`region == "Peninsular"`), from the Perak base. Decision (user): "write in DECISION why chose Peninsular". Reason, measured during planning on seeds 0–9: drawn from all 745 towns, 18 of the 120 sampled towns are in East Malaysia, over 1,000 km from Perak. At the gap's `F` values (about 4,900 and 5,640 kg, so at most about 3,940 kg above the reserve, under 1,000 km of flight at 4.2 kg/km) no route can reach them and fly back. They are candidates that every algorithm and the DP skip, so a sample has fewer than 12 real choices, and the count differs between samples. Peninsular samples keep all 12 towns reachable. The base is rural Perak, which is on the Peninsula, and 642 of the 745 towns are Peninsular. Doc delta: `docs/DECISIONS.md` (in the "No fuel sweep" entry, or its own entry), `docs/PROBLEM.md` Evaluation plan "Optimality gap", `docs/EXPERIMENT.md`.
  - B on A (`local_search(inst, initial=a.route)`) moves to the bases experiment, as its own row kept off the main chart. Decision (user): "yes". Doc delta: `docs/EXPERIMENT.md`, `docs/PROBLEM.md` Evaluation plan.
  - The experiments are renumbered 1–4: heap vs scan, run time, bases, optimality gap, with folders `e1_heap_vs_scan`, `e2_run_time`, `e3_bases`, `e4_optimality_gap`. Decision (user): "yes". Doc delta: `docs/EXPERIMENT.md`.
  - `docs/EXPERIMENT.md` keeps the 2026-10-21 trial result for heap vs scan (at 21,100 and 8,000 kg) as historical, labelled as a trial with a varied `F`. `transient` choice of wording.
- **Acceptance criteria:**
  - [x] `docs/EXPERIMENT.md` lists exactly 4 experiments, numbered 1–4, and no "Fuel sweep" row. `grep -n "Fuel sweep" docs/EXPERIMENT.md` finds no table row.
  - [x] `docs/DECISIONS.md` has a "No fuel sweep" entry with **Change**, **Why** and **Consequence**, covering the fixed 21,100 kg, the optimality gap's `F_full` and `F_tight` rules, and why its samples are Peninsular.
  - [x] `grep -n "20,000\|20 t\|3 t\|Swept\|swept" docs/PROBLEM.md docs/DOMAIN-RESEARCH.md docs/EXPERIMENT.md` finds no `F` value or sweep for an experiment (the trial result and unrelated values such as weights excepted).
  - [x] Full suite passes: `python -m pytest`.
- **Doc deltas:** the files above (this subtask is the doc change).
  - Decisions made during S2:
    - `docs/DECISIONS.md` entry "Three rural and three non-rural bases": its Consequence now points to experiment 3 (bases), not experiment 4, to match the renumbering. Recorded in that doc.
    - `docs/PROBLEM.md` Parameters intro: "experiments sweep some of them" became "experiments vary some of them", since no parameter is swept. Recorded in that doc.
    - `docs/TODO.md` left unchanged: its only experiment number is experiment 1 (heap vs scan), which keeps its number. No doc needed.
    - The optimality gap's `F_full`/`F_tight` values (about 5,640 and 4,900 kg) appear in `docs/DECISIONS.md` only as the planning measurement behind the Peninsular reason; S6 records the values its run finds in `docs/EXPERIMENT.md`. Recorded in `docs/DECISIONS.md`.

### S3 Experiment 1: heap vs scan

- **Goal:** `experiments/e1_heap_vs_scan/` shows how much work A's heap saves, and how often it picks a different town than the re-scan, as the number of towns grows.
- **Blocked by:** S1, S2
- **Files:** `experiments/e1_heap_vs_scan/__init__.py`, `experiments/e1_heap_vs_scan/run.py`, `experiments/e1_heap_vs_scan/out/*`, `tests/test_experiments.py`.
- **Seams:** `run_experiment`, `plot`.
- **Decisions:**
  - Default `Params` (`F = 21,100 kg`), Perak base (user: "change everything to 21100"). Population thresholds 100,000 / 50,000 / 15,000 / 0, which give 86 / 148 / 358 / 745 towns with the current CSV (user: "yes"). For each threshold: one `a_heap` and one `a_scan` run (timed, best of 3, user). Mismatches come from a separate `greedy_insertion(inst, "heap", audit=True)` call and are stored in the `a_heap` row's `stats` as `mismatches`. Doc delta: via S2 (`docs/EXPERIMENT.md`).
  - Plot: two panels against `n_towns`: score evals per selector (log y), and mismatches ÷ insertions. Decision (user): "yes". `transient`.
- **Acceptance criteria:**
  - [ ] On a small hand-built town list and 2 thresholds, `run_experiment` writes contract-conforming outputs with one `a_heap` and one `a_scan` row per threshold, every row has `F == 21100`, and each `a_heap` row's `stats` has `mismatches`. `tests/test_experiments.py::test_e1`
  - [ ] `plot` writes a non-empty `plot.png` from `runs.csv` alone (no other input). `tests/test_experiments.py::test_e1`
  - [ ] `python -m experiments.e1_heap_vs_scan.run` exits 0 and writes `experiments/e1_heap_vs_scan/out/{runs.csv,routes.csv,plot.png}`.
- **Doc deltas:** `docs/EXPERIMENT.md`: the results table for experiment 1, added below the trial result.

### S4 Experiment 2: run time

- **Goal:** `experiments/e2_run_time/` shows how each algorithm's run time grows with the number of towns.
- **Blocked by:** S1, S2
- **Files:** `experiments/e2_run_time/__init__.py`, `experiments/e2_run_time/run.py`, `experiments/e2_run_time/out/*`, `tests/test_experiments.py`.
- **Seams:** `run_experiment`, `plot`.
- **Decisions:**
  - Default `Params` (`F = 21,100 kg`, user), Perak base; thresholds 100,000 / 50,000 / 15,000 / 0; algorithms `nn`, `a_heap`, `a_scan`, `b`; timing best of 3. Decision (user): "yes". EXPERIMENT.md's 83 / 144 / 355 come from an older cleaning. Doc delta: `docs/EXPERIMENT.md` (actual town counts 86 / 148 / 358 / 745).
  - Plot: time against `n_towns`, one line per algorithm, log y axis. Decision (user): "yes". `transient`.
- **Acceptance criteria:**
  - [ ] On a small town list and 2 thresholds, outputs conform with one row per (threshold, algorithm), every row has `F == 21100`, and `n_towns` equals the towns kept. `tests/test_experiments.py::test_e2`
  - [ ] `plot` writes `plot.png` from `runs.csv` alone. `tests/test_experiments.py::test_e2`
  - [ ] `python -m experiments.e2_run_time.run` exits 0 and writes the three output files.
- **Doc deltas:** `docs/EXPERIMENT.md`: experiment 2 town counts.

### S5 Experiment 3: bases

- **Goal:** `experiments/e3_bases/` compares the population reached from each of the 6 bases, rural against non-rural per region, for each algorithm, with B on A as a separate row.
- **Blocked by:** S1, S2
- **Files:** `experiments/e3_bases/__init__.py`, `experiments/e3_bases/run.py`, `experiments/e3_bases/out/*`, `tests/test_experiments.py`.
- **Seams:** `run_experiment`, `plot`.
- **Decisions:**
  - All 6 bases (`RURAL_BASES`, `URBAN_BASES`), default `Params` (`F = 21,100 kg`; user: "the bases exp aslo"), 745 towns, algorithms `nn`, `a_heap`, `b`, `b_on_a` (user: "yes"). `b_on_a` is seeded with the same base's `a_heap` route. Regions: `perak`/`klia` Peninsula, `sarawak`/`kuching` Sarawak, `sabah`/`kota_kinabalu` Sabah (docs: `DECISIONS.md` 2026-10-27). Doc delta: via S2.
  - B on A is kept off the main chart (user, via S2). Plot: bars grouped by region, rural and non-rural side by side, one bar per algorithm; B on A in a separate panel. Decision (user): "yes". `transient`.
- **Acceptance criteria:**
  - [ ] On a small town list, outputs conform with one row per (base, algorithm) for all 6 bases, and every row has `F == 21100`. Each `b_on_a` population ≥ the `a_heap` population from the same base. `tests/test_experiments.py::test_e3`
  - [ ] `plot` writes `plot.png` from `runs.csv` alone. `tests/test_experiments.py::test_e3`
  - [ ] `python -m experiments.e3_bases.run` exits 0 and writes the three output files.
- **Doc deltas:** none beyond S2.

### S6 Experiment 4: optimality gap

- **Goal:** `experiments/e4_optimality_gap/` reports how close the heuristics come to the exact DP on 10 random 12-town samples, at `F_full` (almost every town fits) and at `F_tight` (about 80% of towns fit).
- **Blocked by:** S1, S2
- **Files:** `experiments/e4_optimality_gap/__init__.py`, `experiments/e4_optimality_gap/run.py`, `experiments/e4_optimality_gap/out/*`, `tests/test_experiments.py`.
- **Seams:** `run_experiment`, `plot`, and these public functions in `experiments/e4_optimality_gap/run.py`:
  ```python
  def full_fit_F(samples: Sequence[Sequence[Town]], base: Base, min_samples: int = 8) -> float
  def coverage_F(samples: Sequence[Sequence[Town]], base: Base, share: float = 0.8) -> float
  ```
- **Decisions:**
  - `F_full = full_fit_F(...)`, `F_tight = coverage_F(...)`, rules as in S2 (user). Both are computed once in the run, over the 10 samples. Every sample is solved at both values, and each row's `F` holds the value used. `transient` (S2 records the rules).
  - Peninsular towns (see S2), Perak base, seeds 0–9 (`random.Random(seed).sample(pool, 12)`), algorithms `nn`, `a_heap`, `b`, `b_on_a`, each compared against `dp`. Decision (user): "yes". Gap = heuristic population ÷ optimal population (docs: `PROBLEM.md`). Report the average and worst per algorithm, per `F`.
  - Measured during planning (transient, for reference only), with Peninsular samples, seeds 0–9 and the Perak base:

    | `F` | Value | DP towns per sample | Coverage | NN avg / worst | A avg / worst | B avg / worst | B on A avg / worst |
    |---|---|---|---|---|---|---|---|
    | `F_full` | 5,640 kg | 12 in 8 samples, 11 in 2 | 98% | 0.963 / 0.656 | 0.998 / 0.995 | 0.999 / 0.996 | 0.999 / 0.996 |
    | `F_tight` | 4,900 kg | 7–11 | 81% | 0.742 / 0.236 | 0.997 / 0.970 | 0.916 / 0.497 | 0.997 / 0.970 |
  - Plot: two panels, one per `F` value, each showing the gap per algorithm, one dot per sample plus the average. Decision (user): "yes". `transient`.
- **Acceptance criteria:**
  - [ ] `full_fit_F` returns a multiple of 10 in `[R, 21,100]`; at that `F` the DP route visits every town in at least `min_samples` samples. `tests/test_experiments.py::test_full_fit_F`
  - [ ] `coverage_F` returns a multiple of 10 in `[R, 21,100]`; at that `F` the mean DP route length over the samples is ≥ `share` × sample size. `tests/test_experiments.py::test_coverage_F`
  - [ ] On a small town list with 2 samples of 6 towns, outputs conform, with one `dp` row and one row per heuristic per (sample, `F` value), 2 distinct `F` values in all. Every heuristic population ≤ the `dp` population of its sample at the same `F`. `tests/test_experiments.py::test_e4`
  - [ ] The same seeds give the same samples and the same `F_full` and `F_tight` on two calls. `tests/test_experiments.py::test_e4_deterministic`
  - [ ] `plot` writes `plot.png` from `runs.csv` alone. `tests/test_experiments.py::test_e4`
  - [ ] `python -m experiments.e4_optimality_gap.run` exits 0 and writes the three output files.
- **Doc deltas:** `docs/EXPERIMENT.md`: experiment 4 sampling, and the `F_full` and `F_tight` values the run found.

## 6. Human checks

- [ ] S3–S6: open each `experiments/eN_*/out/plot.png`. Expected: axes labelled with units, a legend, values readable at slide size.
- [ ] S5: in the bases plot, B on A is not on the main NN/A/B chart. Expected: a separate panel.
