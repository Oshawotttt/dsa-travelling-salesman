# Exact DP baseline on small instances, all six bases

**Status:** draft
**Repo:** `D:\SMU\CS201\proj\dsa-travelling-salesman`
**Context file to update:** none named
**Source docs:** `PROBLEM.md` (Exact DP, Evaluation plan, Bases), `EXPERIMENT.md` (experiment 6), `DECISIONS.md`, `README.md`, `TODO.md`, in `docs/` except `README.md` (moved by S0). The repo has no CLAUDE.md, no ADRs, no glossary. Terms follow PROBLEM.md: *town*, *base*, *drop*, *route*, *fuel needed* (`F₀_needed`).

**Commands** (from the repo root, after `pip install -r requirements.txt`):
- Full test suite: `python -m pytest`
- Single test file: `python -m pytest tests/test_exact_dp.py`
- Typecheck: none
- Lint: none

## 1. Dependencies and blockers

| Subtask | Blocked by |
|---|---|
| S0 Move docs into `docs/`, add `docs/CONTRACTS.md` | done 2026-10-27, committed by the user before the run |
| S1 Exact DP solver | none |
| S2 Route trace (per-stop record) | none |
| S3 Optimality-gap experiment on all six bases | S1, S2 |

Run order: S1, S2, S3. S0 is already done; the run skips it.

External blockers:
- The ASSUMED points in section 2.
- S3 reads `data/cities_clean.csv` (git-ignored, present locally).
- The user commits S0 before the run. The worktree `D:/SMU/CS201/proj/experiments` (branch `feat/experiments`) is for the other experiment scripts; S2 changes `airdrop/model.py`.

Uncommitted changes: S0's changes until the user commits them. If anything other than this spec is uncommitted when the run starts, stop and ask the user.
Branch: current branch `feat/dp-baseline`, no new branch.

## 2. Open questions

1. **ASSUMED A1** (S1): Backward DP (state = towns still to visit and current town, value = least fuel needed on board on arrival), one pass, instead of PROBLEM.md's forward DP run once per `k`. Reason in S1 Decisions. Contradicts no ADR (repo has none); it changes the PROBLEM.md Exact DP section.
2. **ASSUMED A2** (S1, S3): Node number `n = 15` towns per sample, not PROBLEM.md's 12. Transition counts (`n(n−1)·2ⁿ⁻²`): `n = 12` → 135,168; `n = 15` → 1,720,320; `n = 16` → 3,932,160; `n = 18` → 20,054,016. Solver guard `max_n = 18`.
3. **ASSUMED A3** (S3): Towns per sample: 15 drawn at random (seeded) from the 40 towns nearest the base by haversine distance. `cities_clean.csv` has only two regions (`Peninsular`, `East Malaysia`).
4. **ASSUMED A4** (S3): Fuel cap per sample: `F` = the least fuel needed by any route of `⌈n/2⌉` = 8 towns from the sample, computed by the DP with no tank limit. Other `Params` stay at defaults.
5. **ASSUMED A5** (S3): Algorithms: `dp`, `nn`, `a_heap`, `a_scan`, `b`, `b_on_a` (B on A's route, labelled combined). Gap = population ÷ optimal population.
6. **ASSUMED A6** (S2, S3): Per-stop analysis comes from one model-level `trace(inst, route)` used for every algorithm. No new algorithm-specific instrumentation; the existing `SolveResult.stats` are saved as a JSON column.
7. **ASSUMED A7** (S2): Fuel on board in the trace assumes the plane loads exactly `F₀_needed` (so it lands with exactly `R`).
8. **ASSUMED A8** (S3): Output is three CSV files in long format (`runs.csv`, `stops.csv`, `candidates.csv`), columns in section 5.

## 3. Suggested splits

No split: S3 calls S1's `exact_dp` and S2's `trace`.

## 4. Out of scope

- Plotting, including the map and the gap chart. Decision (user): "for now don't need to plot". The output must have "enough information to then plot the map". Recorded in S3's doc delta to `docs/EXPERIMENT.md`.
- Other experiments (1–5): branch `feat/experiments`. `transient`.
- New algorithm-specific instrumentation in NN, A or B (ASSUMED A6). `transient`.
- Speeding up the DP beyond the fuel-limit pruning in S1. `transient`.
- Changes to NN, A, B, the fuel model or `eda.ipynb`. `transient`.

## 5. Interfaces

Each interface below is a doc delta to `docs/CONTRACTS.md` on the subtask that introduces it.

```python
# airdrop/exact_dp.py  (S1)
def exact_dp(inst: Instance, max_n: int = 18) -> SolveResult
```

- Returns the optimal route: largest population; ties go to the least fuel needed; remaining ties go to the smallest route as a tuple.
- `route`, `eval` as for every solver (`SolveResult` from `airdrop.approach_a`). `eval == evaluate(inst, route)`.
- `stats`: `states` (table entries kept), `transitions` (extensions computed).
- Raises `ValueError` when `inst.n > max_n`.
- No town fits: `route == []`.

```python
# airdrop/model.py  (S2)
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

- Length `len(route) + 2`. Raises `ValueError` when `evaluate(inst, route).fuel_needed` is `inf` or the route has a bad index.
- Fuel on a leg of length `d` with cargo `W`: `fuel_after = f + (f + W)·expm1(−b·d) + a·expm1(−b·d)/b` (`f − a·d` at `b = 0`).

CSV files in `experiments/06_optimality_gap/` (S3; one row per line, header row first). With these three files a map of any run can be drawn without `data/cities_clean.csv`.

| File | One row per | Columns |
|---|---|---|
| `runs.csv` | base × sample × algorithm | `run_id, base, type, region, sample, seed, n, F, algorithm, population, optimal, gap, towns, distance_km, cargo_kg, fuel_needed_kg, feasible, seconds, stats` (`stats` = JSON of `SolveResult.stats`) |
| `stops.csv` | stop of each run | `run_id` + every `Stop` field |
| `candidates.csv` | town of each sample | `base, sample, index, geonameid, name, lat, lon, population, visited_by` (`visited_by` = `;`-joined algorithm names) |

- `run_id` = `<base>-<sample>-<algorithm>`. `type` is `rural` or `non-rural`. `region` is `Peninsula`, `Sarawak` or `Sabah` (DECISIONS.md table).

## 6. Subtasks

### S0 Move docs into `docs/`, add `docs/CONTRACTS.md`

**Done** on 2026-10-27, outside the run. Kept for the record; the run does not execute it.


- **Goal:** the project docs live in `docs/`, all links and references point at the new paths, and `docs/CONTRACTS.md` holds the current public contracts. No code behaviour changes.
- **Blocked by:** none
- **Files:** `PROBLEM.md` → `docs/PROBLEM.md`, `DECISIONS.md` → `docs/DECISIONS.md`, `EXPERIMENT.md` → `docs/EXPERIMENT.md`, `TODO.md` → `docs/TODO.md` (moved; git detects the renames on commit); `docs/CONTRACTS.md` (new); `README.md`; docstrings and comments that name `PROBLEM.md` in `airdrop/__init__.py`, `airdrop/model.py`, `airdrop/prefix.py`, `airdrop/approach_a.py`, `airdrop/approach_b.py`, `airdrop/baseline.py`.
- **Seams:** the file tree; `python -m pytest`.
- **Decisions:**
  - Decision (user): "write into CONTRACTS.md and move all the docs into docs/". Doc delta: README folder structure.
  - Decision (user, by asking S0 to be done): README stays at root; `PROBLEM.md`, `DECISIONS.md`, `EXPERIMENT.md`, `TODO.md` move. Doc delta: README folder structure.
  - Decision (user): CONTRACTS.md holds the public contracts; README "Using the solvers" keeps the example and links to `docs/CONTRACTS.md` for return types, stats and arguments. Doc delta: README, CONTRACTS.md.
  - Code references become `docs/PROBLEM.md` (e.g. `(docs/PROBLEM.md, Fuel model)`). `transient`.
- **Acceptance criteria:**
  - [ ] `PROBLEM.md`, `DECISIONS.md`, `EXPERIMENT.md`, `TODO.md` exist under `docs/` and not at the root; `README.md` exists at the root. Command: `git ls-files PROBLEM.md DECISIONS.md EXPERIMENT.md TODO.md docs/PROBLEM.md docs/DECISIONS.md docs/EXPERIMENT.md docs/TODO.md docs/CONTRACTS.md README.md` lists only the `docs/` paths and `README.md`.
  - [ ] `git log --follow docs/PROBLEM.md` shows commits from before the move.
  - [ ] Every relative markdown link in `README.md` and `docs/*.md` resolves to an existing file. Command: a one-off check that extracts `](path)` targets (ignoring `http` and `#` anchors) and tests each path exists, exits 0.
  - [ ] No file outside `docs/specs/` names a root-level path to a moved doc: `git grep -nE "\]\((PROBLEM|DECISIONS|EXPERIMENT|TODO)\.md" -- README.md` and `git grep -n "PROBLEM.md" -- airdrop` show only `docs/`-relative references.
  - [ ] `docs/CONTRACTS.md` contains sections for the route convention, `Params`, `Instance`, `RouteEval`/`evaluate`, `SolveResult`, `greedy_insertion`, `nearest_neighbour`, `local_search`, matching the signatures in `airdrop/`. Command: `git grep -n "def greedy_insertion\|def nearest_neighbour\|def local_search\|def evaluate" -- airdrop` compared with the headings in `docs/CONTRACTS.md`.
  - [ ] Existing tests pass unchanged: `python -m pytest`.
- **Doc deltas:**
  - `README.md`: folder structure lists `docs/` with `PROBLEM.md`, `DECISIONS.md`, `EXPERIMENT.md`, `TODO.md`, `CONTRACTS.md`, `specs/`; links updated.

### S1 Exact DP solver

- **Goal:** `airdrop.exact_dp.exact_dp` returns the provably best route for instances up to `max_n` towns, under the full fuel model and all constraints.
- **Blocked by:** none
- **Files:** `airdrop/exact_dp.py` (new), `tests/test_exact_dp.py` (new).
- **Seams:** `exact_dp(inst, max_n)`, `evaluate(inst, route)`, `nearest_neighbour`, `greedy_insertion`, `local_search`.
- **Decisions:**
  - ASSUMED A1: backward DP. `need[U][j]` = least fuel on board on arrival at town `j` (before its drop, cargo `w·|U|`) that lets the plane drop at every town of `U` with `j` first, return to base and land with `R`.
    - `|U| = 1`: `need[{j}][j] = before(R, d(j, 0), 0)`.
    - Otherwise `need[U][j] = min over i in U∖{j} of before(need[U∖{j}][i], d(j, i), w·(|U|−1))`.
    - `before(f, d, cargo) = f + (f + cargo)·expm1(b·d) + a·φ(b, d)` (fuel needed before a leg of length `d` to have `f` after it; exact at `b = 0`).
    - Fuel needed for set `U`: `F₀(U) = min over j in U of before(need[U][j], d(0, j), w·|U|)`. `U` is feasible when `inst.fits(|U|, F₀(U))`.
    - `before` is increasing in `f`, so the least `need` dominates. Cargo on every leg is fixed by `|U|`, so one pass covers every `k`, and the least fuel needed is exact.
    - Pruning: drop an entry when `need[U][j] > inst.fuel_limit(|U|)` or `w·|U| > C`.
    - Doc delta: `docs/PROBLEM.md`, Exact DP section; `docs/DECISIONS.md`.
  - Cost: `O(n² · 2ⁿ)` time, `O(n · 2ⁿ)` memory. Doc delta: `docs/PROBLEM.md`.
  - `max_n` default 18 (ASSUMED A2). Doc delta: `docs/CONTRACTS.md`.
- **Acceptance criteria:**
  - [ ] On 20 random instances of 1–7 towns (tight and loose `F`, and `control_params`), `exact_dp` population and fuel needed equal a brute force over every ordered subset (fuel within `1e-6` relative). `tests/test_exact_dp.py::test_matches_brute_force`
  - [ ] `result.eval == evaluate(inst, result.route)` and `result.eval.feasible` (or `route == []`). `tests/test_exact_dp.py::test_consistent`
  - [ ] DP population ≥ NN, A (heap and scan), B and B on A on 10 random 12-town instances. `tests/test_exact_dp.py::test_beats_heuristics`
  - [ ] Instance where no town fits returns `route == []`, population 0. `tests/test_exact_dp.py::test_nothing_fits`
  - [ ] `inst.n > max_n` raises `ValueError`. `tests/test_exact_dp.py::test_max_n`
  - [ ] Two calls on the same instance return equal results. `tests/test_exact_dp.py::test_deterministic`
  - [ ] Full suite passes: `python -m pytest`.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: `exact_dp` section (section 5 of this spec).
  - `docs/PROBLEM.md`, Exact DP: replace the forward per-`k` table with the backward DP above, its exactness argument, pruning and cost `O(n²·2ⁿ)`.
  - `README.md`: folder structure line for `exact_dp.py`; usage `exact_dp(inst)`; remove "the exact DP" from "Not implemented".
  - `docs/DECISIONS.md`: entry "Backward exact DP" with why (exact least-fuel tie-break, one pass instead of `n`).

### S2 Route trace (per-stop record)

- **Goal:** `airdrop.trace(inst, route)` gives, for any feasible route from any solver, the position, distance, fuel, cargo, weight and population reached at takeoff, each drop and landing.
- **Blocked by:** none
- **Files:** `airdrop/model.py`, `airdrop/__init__.py` (export `Stop`, `trace`), `tests/test_model.py`.
- **Seams:** `trace(inst, route)`, `evaluate(inst, route)`, `fuel_end(inst, route, F0)`.
- **Decisions:**
  - ASSUMED A6: one model-level trace for every algorithm; no solver changes. Doc delta: `docs/CONTRACTS.md`.
  - ASSUMED A7: fuel on board assumes `F₀_needed` loaded. Doc delta: `docs/CONTRACTS.md`.
- **Acceptance criteria:**
  - [ ] Takeoff stop has `fuel_kg == evaluate(...).fuel_needed`, `cargo_kg == w·k`; landing stop has `fuel_kg ≈ R` (`1e-6` relative), `distance_km ≈ evaluate(...).distance`, `population_reached == evaluate(...).population`. `tests/test_model.py::test_trace_endpoints`
  - [ ] Landing fuel equals `fuel_end(inst, route, F0_needed)`, and each stop's `fuel_kg` equals `fuel_end`-style forward simulation of the prefix, on random routes with default `Params` and `control_params`. `tests/test_model.py::test_trace_matches_fuel_end`
  - [ ] Cargo falls by `w` after each drop; `fuel_kg` never rises; `weight_kg == E + cargo_kg + fuel_kg`; `leg_fuel_kg` = previous `fuel_kg` − this `fuel_kg`. `tests/test_model.py::test_trace_invariants`
  - [ ] Empty route gives 2 stops (takeoff, landing at base, `fuel_kg == R`). `tests/test_model.py::test_trace_empty`
  - [ ] Bad index or `fuel_needed == inf` raises `ValueError`. `tests/test_model.py::test_trace_errors`
  - [ ] Full suite passes: `python -m pytest`.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: `Stop` and `trace` section (section 5 of this spec), including that fuel assumes `F₀_needed` loaded.
  - `README.md`: one usage line for `trace(inst, route)`.

### S3 Optimality-gap experiment on all six bases

- **Goal:** one script runs experiment 6 on all six bases and saves `runs.csv`, `stops.csv` and `candidates.csv`, with enough data to plot the map of every run later. No plot.
- **Blocked by:** S1, S2
- **Files:** `experiments/06_optimality_gap/run.py` (new), `experiments/06_optimality_gap/runs.csv`, `stops.csv`, `candidates.csv` (outputs, committed), `tests/test_experiment_gap.py` (new).
- **Seams:** `python experiments/06_optimality_gap/run.py`; function `run(towns, bases, samples, n, pool, seed0) -> tuple[list[dict], list[dict], list[dict]]` (runs, stops, candidates rows) in that file, tested on hand-built towns.
- **Decisions:**
  - No plot. Decision (user): "for now don't need to plot. i just need some sort of format for the output of each algorithm. each output should have enough information to then plot the map". Doc delta: `docs/EXPERIMENT.md`.
  - Output format: the three CSVs in section 5 (ASSUMED A8). Doc delta: `docs/CONTRACTS.md`.
  - Bases: all six in `BASES`, order `RURAL_BASES` then `URBAN_BASES`. Doc delta: `docs/EXPERIMENT.md`.
  - `n = 15`, 10 samples per base, seeds `0..9` (ASSUMED A2). Doc delta: `docs/EXPERIMENT.md`, `docs/PROBLEM.md` (Evaluation plan, Parameters `n`).
  - Sample pool: 40 nearest towns to the base (ASSUMED A3). Doc delta: `docs/EXPERIMENT.md`.
  - `F` per sample: least fuel needed by any 8-town route (ASSUMED A4). Doc delta: `docs/EXPERIMENT.md`.
  - Algorithms and gap (ASSUMED A5). Doc delta: `docs/EXPERIMENT.md`.
- **Acceptance criteria:**
  - [ ] `run` on hand-built towns returns runs rows with every `runs.csv` column, `gap ≤ 1` for every row and `gap == 1` for `dp`; stops rows per run number `towns + 2`; candidates rows per sample number `n`. `tests/test_experiment_gap.py::test_rows`
  - [ ] Every `stops` row's `index` is 0 or appears in that sample's `candidates` rows. `tests/test_experiment_gap.py::test_stops_in_candidates`
  - [ ] `python experiments/06_optimality_gap/run.py` exits 0 and writes `runs.csv` with 6 × 10 × 6 = 360 rows, `candidates.csv` with 6 × 10 × 15 = 900 rows, and `stops.csv`.
  - [ ] Full suite passes: `python -m pytest`.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: the three CSV files and their columns (section 5 of this spec).
  - `docs/EXPERIMENT.md`, row 6: all six bases, `n = 15`, pool, `F` rule, algorithms, output files (link to CONTRACTS.md), how to run; no plot yet.
  - `docs/PROBLEM.md`, Evaluation plan and Parameters: `n = 15` for the exact DP, six bases.
  - `README.md`: how to run experiment 6.
  - `docs/TODO.md`: tick "Exact DP".

## 7. Human checks

- [ ] S3: open `runs.csv`. Expected: mean `gap` per base between 0 and 1; `b_on_a` ≥ `a_heap` for most samples.
- [ ] S3: pick one run in `stops.csv`. Expected: `fuel_kg` falls each step, `cargo_kg` falls by 200 per drop, landing `fuel_kg` ≈ 1,700.
