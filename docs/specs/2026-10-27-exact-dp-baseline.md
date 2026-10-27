# Exact DP baseline and route trace

**Status:** approved
**Repo:** `D:\SMU\CS201\proj\dsa-travelling-salesman`
**Context file to update:** none named
**Source docs:** `PROBLEM.md` (Exact DP, Evaluation plan, Bases), `EXPERIMENT.md` (experiment 6), `DECISIONS.md`, `README.md`, `TODO.md`, in `docs/` except `README.md`. The repo has no CLAUDE.md, no ADRs, no glossary. Terms follow PROBLEM.md: *town*, *base*, *drop*, *route*, *fuel needed* (`F₀_needed`).

**Commands** (from the repo root, after `pip install -r requirements.txt`):
- Full test suite: `python -m pytest`
- Single test file: `python -m pytest tests/test_exact_dp.py`
- Typecheck: none
- Lint: none

## 1. Dependencies and blockers

| Subtask | Blocked by |
|---|---|
| S1 Exact DP solver | none |
| S2 Route trace (per-stop record) | none |

Run order: S1, S2.

External blockers:
- The worktree `D:/SMU/CS201/proj/experiments` (branch `feat/experiments`) is for the experiment scripts, which will use `exact_dp` and `trace`. S2 changes `airdrop/model.py`.

Uncommitted changes: if anything other than this spec is uncommitted when the run starts, stop and ask the user.
Branch: current branch `feat/dp-baseline`, no new branch.

## 2. Suggested splits

S1 and S2 have no dependency between them and change different files (`airdrop/exact_dp.py` vs `airdrop/model.py`, `airdrop/__init__.py`). Both also edit `docs/CONTRACTS.md` and `README.md` in the final docs update. Split possible; decision (user): one spec.

## 3. Out of scope

- All experiment scripts, including experiment 6 (optimality gap) on the six bases. Decision (user): "i rather do all the experiments at once". `transient`.
- Plotting. Decision (user): "for now don't need to plot". `transient`.
- New algorithm-specific instrumentation in NN, A or B (user). `transient`.
- Speeding up the DP beyond the fuel-limit pruning in S1. `transient`.
- Changes to NN, A, B, the fuel model or `eda.ipynb`. `transient`.

## 4. Interfaces

Each interface below is a doc delta to `docs/CONTRACTS.md` on the subtask that introduces it.

```python
# airdrop/exact_dp.py  (S1)
def exact_dp(inst: Instance, max_n: int = 15) -> SolveResult
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

## 5. Subtasks

### S1 Exact DP solver

- **Goal:** `airdrop.exact_dp.exact_dp` returns the provably best route for instances up to `max_n` towns, under the full fuel model and all constraints.
- **Blocked by:** none
- **Files:** `airdrop/exact_dp.py` (new), `tests/test_exact_dp.py` (new).
- **Seams:** `exact_dp(inst, max_n)`, `evaluate(inst, route)`, `nearest_neighbour`, `greedy_insertion`, `local_search`.
- **Decisions:**
  - Decision (user, recorded in `docs/DECISIONS.md` on 2026-10-27): backward DP. `need[U][j]` = least fuel on board on arrival at town `j` (before its drop, cargo `w·|U|`) that lets the plane drop at every town of `U` with `j` first, return to base and land with `R`.
    - `|U| = 1`: `need[{j}][j] = before(R, d(j, 0), 0)`.
    - Otherwise `need[U][j] = min over i in U∖{j} of before(need[U∖{j}][i], d(j, i), w·(|U|−1))`.
    - `before(f, d, cargo) = f + (f + cargo)·expm1(b·d) + a·φ(b, d)` (fuel needed before a leg of length `d` to have `f` after it; exact at `b = 0`).
    - Fuel needed for set `U`: `F₀(U) = min over j in U of before(need[U][j], d(0, j), w·|U|)`; keep the `j` that gives it. `U` is feasible when `inst.fits(|U|, F₀(U))`.
    - Store `next[U][j]` = the town `i` that gave `need[U][j]`. The route is rebuilt from the winning `j`, following `next`.
    - `before` is increasing in `f`, so the least `need` dominates. Cargo on every leg is fixed by `|U|`, so one pass covers every `k`, and the least fuel needed is exact.
    - Pruning: drop an entry when `need[U][j] > inst.fuel_limit(|U|)` or `w·|U| > C`.
    - Doc delta: `docs/PROBLEM.md`, Exact DP section. (`docs/DECISIONS.md` entry already written.)
  - Cost: `O(n² · 2ⁿ)` time, `O(n · 2ⁿ)` memory. Doc delta: `docs/PROBLEM.md`.
  - `max_n` default 15. Decision (user): "just max 15". Doc delta: `docs/CONTRACTS.md`.
- **Acceptance criteria:**
  - [x] On 20 random instances of 1–7 towns (tight and loose `F`, and `control_params`), `exact_dp` population and fuel needed equal a brute force over every ordered subset (fuel within `1e-6` relative). `tests/test_exact_dp.py::test_matches_brute_force`
  - [x] `result.eval == evaluate(inst, result.route)` and `result.eval.feasible` (or `route == []`). `tests/test_exact_dp.py::test_consistent`
  - [x] DP population ≥ NN, A (heap and scan), B and B on A on 10 random 12-town instances. `tests/test_exact_dp.py::test_beats_heuristics`
  - [x] Instance where no town fits returns `route == []`, population 0. `tests/test_exact_dp.py::test_nothing_fits`
  - [x] `inst.n > max_n` raises `ValueError`. `tests/test_exact_dp.py::test_max_n`
  - [x] Two calls on the same instance return equal results. `tests/test_exact_dp.py::test_deterministic`
  - [x] Full suite passes: `python -m pytest`.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: `exact_dp` section (section 4 of this spec).
  - `docs/PROBLEM.md`, Exact DP: replace the forward per-`k` table with the backward DP above, its exactness argument, pruning and cost `O(n²·2ⁿ)`.
  - `README.md`: folder structure line for `exact_dp.py`; usage `exact_dp(inst)`; remove "the exact DP" from "Not implemented".
  - Decisions made during implementation:
    - `before` is computed as `f + (b·(f + cargo) + a)·φ(b, d)`, the same formula as above, reusing `model.phi` so `b = 0` is exact and an overflow gives `inf` (NaN mapped to `inf`). Needs no doc: the code comment states it.
    - `stats["transitions"]` counts every `before` call that computes a candidate `need` entry, including the landing leg of `|U| = 1`; takeoff legs are not counted. Doc: `docs/CONTRACTS.md`.
    - Ties in `need` and in the takeoff choice keep the smallest town index (towns scanned in ascending order, strict `<`), so among routes with exactly equal fuel the rebuilt route is the smallest tuple. The fuel and tie rules (and `fits`) are applied to the DP's own float fuel, not `evaluate`'s, so routes whose fuel differs only by rounding (e.g. a route and its reverse at `b = 0`) may not follow the tuple rule. Doc: `docs/PROBLEM.md`, Exact DP, and `docs/CONTRACTS.md`.
    - A set with `w·|U| > C` is skipped whole, before any entry is computed. Doc: `docs/PROBLEM.md`, Exact DP (pruning).

### S2 Route trace (per-stop record)

- **Goal:** `airdrop.trace(inst, route)` gives, for any feasible route from any solver, the position, distance, fuel, cargo, weight and population reached at takeoff, each drop and landing.
- **Blocked by:** none
- **Files:** `airdrop/model.py`, `airdrop/__init__.py` (export `Stop`, `trace`), `tests/test_model.py`.
- **Seams:** `trace(inst, route)`, `evaluate(inst, route)`, `fuel_end(inst, route, F0)`.
- **Decisions:**
  - Decision (user): one model-level `trace(inst, route)` for every algorithm; no new algorithm-specific instrumentation; no solver changes. Doc delta: `docs/CONTRACTS.md`.
  - Decision (user): fuel on board assumes the plane loads exactly `F₀_needed`, so it lands with exactly the fixed reserve `R` (1,700 kg); no percentage reserve. Doc delta: `docs/CONTRACTS.md`.
- **Acceptance criteria:**
  - [x] Takeoff stop has `fuel_kg == evaluate(...).fuel_needed`, `cargo_kg == w·k`; landing stop has `fuel_kg ≈ R` (`1e-6` relative), `distance_km ≈ evaluate(...).distance`, `population_reached == evaluate(...).population`. `tests/test_model.py::test_trace_endpoints`
  - [x] Landing fuel equals `fuel_end(inst, route, F0_needed)`, and each stop's `fuel_kg` equals `fuel_end`-style forward simulation of the prefix, on random routes with default `Params` and `control_params`. `tests/test_model.py::test_trace_matches_fuel_end`
  - [x] Cargo falls by `w` after each drop; `fuel_kg` never rises; `weight_kg == E + cargo_kg + fuel_kg`; `leg_fuel_kg` = previous `fuel_kg` − this `fuel_kg`. `tests/test_model.py::test_trace_invariants`
  - [x] Empty route gives 2 stops (takeoff, landing at base, `fuel_kg == R`). `tests/test_model.py::test_trace_empty`
  - [x] Bad index or `fuel_needed == inf` raises `ValueError`. `tests/test_model.py::test_trace_errors`
  - [x] Full suite passes: `python -m pytest`.
- **Doc deltas:**
  - `docs/CONTRACTS.md`: `Stop` and `trace` section (section 4 of this spec), including that fuel assumes `F₀_needed` loaded.
  - `README.md`: one usage line for `trace(inst, route)`.
  - Decisions made during implementation:
    - `trace` raises only on a bad index or infinite fuel needed, as the interface says; a route that is infeasible with finite fuel (duplicate, payload, fuel cap, takeoff weight) is still traced. Doc: `docs/CONTRACTS.md`.
    - The landing stop's `fuel_kg` is the forward-flown value (equal to `R` within rounding), not set to `R`, so the `leg_fuel_kg` values add up to `F₀_needed − fuel_kg` at landing. Doc: `docs/CONTRACTS.md`.
    - Takeoff and landing stops carry the base's `geonameid`, `name`, `lat`, `lon`. Doc: `docs/CONTRACTS.md`.
    - Added `tests/test_model.py::test_trace_exported` to check `Stop` and `trace` are exported from `airdrop`. Needs no doc.

## 6. Human checks

none
