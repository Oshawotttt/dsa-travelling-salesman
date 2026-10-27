# Approach A (greedy insertion with a lazy heap) and Approach B (local search)

**Status:** approved
**Repo:** `D:\SMU\CS201\proj\dsa-travelling-salesman`
**Context file to update:** none named
**Source docs:** `PROBLEM.md` (source of truth for the variant, fuel model and both approaches), `docs/Project_2627T1.pdf`. The repo has no CLAUDE.md, no ADRs, no glossary. Terms follow PROBLEM.md: *town*, *base*, *drop*, *route*, *fuel needed* (`F₀_needed`).

**Commands** (pytest installed via `pip install -r requirements.txt`):
- Full test suite: `python -m pytest`
- Single test file: `python -m pytest tests/test_model.py`
- Typecheck: none
- Lint: none

## 1. Dependencies and blockers

| Subtask | Blocked by |
|---|---|
| S1 Model, bases and route evaluator | none |
| S2 Route prefix sums (O(1) move costs) | S1 |
| S3 Approach A, full re-scan selector | S2 |
| S4 Approach A, lazy heap selector | S3 |
| S5 Nearest-neighbour seed for B | S1 |
| S6 Approach B, local search | S2, S5 |
| S7 README run instructions | S4, S6 |

Run order: S1, S2, S3, S4, S5, S6, S7.

Doc deltas: every subtask's **Doc deltas** (including edits to `PROBLEM.md`) are applied in one docs update after the last subtask and the final code review, not inside the subtask. A subtask is complete without them. Decision (user, 2026-10-21): "Defer to step 6".

External blockers:
- `PROBLEM.md` has the user's uncommitted edits. The user commits them before `/loopeng-auto` runs, because S1, S5 and S6 doc deltas edit `PROBLEM.md`.
- `.gitignore` ignores `docs/` and `data/`. Decision (user): "unignore docs". The `docs/` line is removed from `.gitignore` and that change is committed together with this spec, before S1. This also puts `docs/Project_2627T1.pdf` under git.
- `data/` stays ignored, so `data/cities_clean.csv` is not in git. Decision (user, A5): unit tests use small hand-built instances; tests that read `data/cities_clean.csv` are skipped when the file is missing.

Uncommitted changes: `PROBLEM.md` (see above). If it is still uncommitted when the run starts, stop and ask the user.
Branch: current branch `experiments`, no new branch. Decision (user): yes to A4.

## 2. Suggested splits

No split: all subtasks are connected. A (S3, S4) and B (S5, S6) both depend on the prefix-sum structure in S2.

## 3. Out of scope

- Population greedy baseline, exact DP, experiment scripts and plots. Decision (user): "just implement the two approaches". Nearest neighbour is in scope only because PROBLEM.md makes it Approach B's starting route.
- The "state-aware ratio greedy" (rejected in PROBLEM.md, Other approaches).
- Changes to `eda.ipynb`, the data cleaning or `PROBLEM.md` content beyond the doc deltas listed.
- Wind, climb, descent, airspace (PROBLEM.md, Limitations).

## 4. Interfaces

Decision (user, A2): Python package `airdrop/` at repo root, tests in `tests/`, dependencies numpy and pytest in `requirements.txt`.

All in package `airdrop`. Units: km, kg. Index `0` is the base; towns are `1..n`. A route is a list of town indices, base excluded: `base → route[0] → … → route[-1] → base`.

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

BASES: dict[str, Base]   # keys: "perak", "kelantan", "johor", "sarawak", "sabah" (PROBLEM.md, Bases table)

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

M_REF: float = 60_000.0      # representative mid-mission mass, kg

def control_params(p: Params) -> Params   # copy of p with b = 0 and a = p.c * M_REF (≈ 4.2 kg/km)

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float  # R_earth = 6371.0088 km
def load_towns(path: str | Path, min_population: int = 0) -> list[Town]       # reads cities_clean.csv

class Instance:
    def __init__(self, base: Base, towns: Sequence[Town], params: Params): ...
    n: int
    towns: tuple[Town, ...]           # towns[i-1] is town i
    params: Params
    a: float; b: float                # resolved
    def dist(self, i: int, j: int) -> float   # precomputed (n+1)x(n+1)
    def population(self, i: int) -> int
    def fuel_limit(self, k: int) -> float     # min(F, MTOW - E - w*k)
    def fits(self, k: int, fuel: float) -> bool  # added in code review: w*k <= C and fuel <= fuel_limit(k)

@dataclass(frozen=True)
class RouteEval:
    population: int
    distance: float          # D
    cargo: float             # W0 = w * k
    fuel_needed: float       # F0_needed = (R - K) * e^(b*D); b == 0 -> R + a*D
    feasible: bool
    reason: str | None       # None, or first failing check in this order:
                             # "bad_index", "duplicate", "payload", "fuel_cap", "takeoff_weight"

def evaluate(inst: Instance, route: Sequence[int]) -> RouteEval
def fuel_end(inst: Instance, route: Sequence[int], F0: float) -> float   # closed form, PROBLEM.md Fuel model
```

Feasible iff indices valid, no duplicates, `w·k ≤ C` ("payload"), `F₀_needed ≤ F` ("fuel_cap"), `F₀_needed ≤ MTOW − E − w·k` ("takeoff_weight").

```python
# airdrop/prefix.py
class RouteState:
    """Prefix sums over one route. Build O(k); every query O(1) except best_insertion O(k)."""
    def __init__(self, inst: Instance, route: Sequence[int]): ...
    route: tuple[int, ...]
    fuel_needed: float                                   # equals evaluate(...).fuel_needed
    def insert_fuel(self, t: int, pos: int) -> float     # fuel_needed after inserting t before route[pos], pos in 0..k
    def best_insertion(self, t: int) -> tuple[int, float]  # (pos, fuel_needed); ties -> smallest pos
    def remove_fuel(self, pos: int) -> float             # fuel_needed after removing route[pos]
    def two_opt_fuel(self, i: int, j: int) -> float      # fuel_needed after reversing route[i..j] inclusive, 0 <= i < j < k
    def best_insertions(self, towns: Sequence[int]) -> tuple[list[int], list[float]]
        # added in S6: best_insertion for many towns at once, numpy-vectorised; (positions, fuels)
```

Spec change (S6): `RouteState.best_insertions` and `Instance.dist_matrix` (the numpy distance matrix behind `dist`) were added to the interfaces during S6. Local search needs the cheapest insertion of every unvisited town into the route without each visited town, every round; the scalar loop measured at tens of seconds per round on 745 towns.

```python
# airdrop/approach_a.py
@dataclass
class SolveResult:
    route: list[int]
    eval: RouteEval
    stats: dict[str, int]

def greedy_insertion(inst: Instance, selector: Literal["heap", "scan"] = "heap",
                     audit: bool = False) -> SolveResult
# stats: "score_evals", "insertions"; heap adds "heap_pops", "heap_pushes";
# audit=True (heap only) adds "mismatches": steps where the heap's pick differs from the full re-scan's argmax.

# airdrop/baseline.py
def nearest_neighbour(inst: Instance) -> SolveResult

# airdrop/approach_b.py
def local_search(inst: Instance, initial: Sequence[int] | None = None,
                 L: int = 20, max_rounds: int = 10_000) -> SolveResult
# initial=None -> nearest_neighbour(inst).route
# stats: "rounds", "two_opt", "add", "swap", "replace_1_2", "hit_max_rounds"
```

Score in Approach A: `population(t) / (best_insertion(t).fuel − fuel_needed)`. Marginal ≤ 0 gives score `+inf`. Score ties break by larger population, then smaller index.

## 5. Subtasks

### S1 Model, bases and route evaluator

- **Goal:** towns load from CSV, the five bases are defined, and `evaluate` computes `F₀_needed` and feasibility of any route with the closed-form fuel model.
- **Blocked by:** none
- **Files:** `airdrop/__init__.py`, `airdrop/model.py`, `tests/test_model.py`, `requirements.txt`, `pyproject.toml` (pytest config only: `testpaths = ["tests"]`), `.gitignore` is not touched here (see section 1)
- **Seams:** `haversine_km`, `load_towns`, `BASES`, `Instance`, `evaluate`, `fuel_end`
- **Decisions:**
  - Burn rate `u = a + b × (cargo + fuel on board)`, `a = c × E`, `b = c`; over a leg `u` shrinks by `e^(−b·d)`; at a drop `u` falls by `b × w` (docs: PROBLEM.md, Fuel model).
  - `fuel_end = (u₀·e^(−b·D) − b·Σ w·e^(−b·Rᵢ) − a) / b`, `u₀ = a + b(W₀ + F₀)`; `F₀_needed = (R − K)·e^(b·D)` (docs: PROBLEM.md).
  - Cargo `W₀ = w × k`; fuel loaded is exactly `F₀_needed` (docs: PROBLEM.md, Loading).
  - Constraints: each town at most once; `w·k ≤ C`; `F₀ ≤ min(F, MTOW − E − w·k)`; fuel left ≥ `R` (docs: PROBLEM.md).
  - Objective: max population; ties by least fuel needed (docs: PROBLEM.md).
  - Bases: the five sites in the PROBLEM.md Bases table, with those GeoNames IDs and coordinates (docs: PROBLEM.md).
  - All constants are arguments (docs: PROBLEM.md).
  - Default constants (user: "yes" to the proposal from research): `E = 33,600`, `C = 19,630`, `MTOW = 70,300`, `F = 21,100`, `R = 1,700`, `w = 200`, `c = 7.0e-5`.
  - `Params` takes `a` and `b` separately; defaults `a = c × E`, `b = c` (user).
  - Control: `b = 0` and `a = c × 60,000 ≈ 4.2 kg/km`, so the average burn per km stays the same and only the weight effect is removed (user). Provided by `control_params`.
  - With `b = 0` the closed form becomes `F₀_needed = R + a × D`.
- **Acceptance criteria:**
  - [x] `haversine_km` is 0 for identical points; KL (3.1412, 101.68653) to Johor Bahru (1.4655, 103.7578) is 296 ± 2 km. `tests/test_model.py::test_haversine`
  - [x] `Instance.dist` is symmetric, zero on the diagonal, equal to `haversine_km`. `test_distance_matrix`
  - [x] `evaluate([])` gives population 0, distance 0, `fuel_needed == R`, feasible. `test_empty_route`
  - [x] For 3 random routes, `fuel_end(route, evaluate(route).fuel_needed) == R` within 1e-6 kg. `test_fuel_needed_closes`
  - [x] Closed form matches a step-by-step simulation (step 0.01 km, burn `u` per km, cargo drop at each town) within 0.1 kg on a ~500 km 3-town route. `test_matches_simulation`
  - [x] With `b > 0`, reversing a route changes `fuel_needed`. `test_order_dependent`
  - [x] With `b = 0`, `fuel_needed == R + a·D` and reversal does not change it; `b = 1e-12` is within 1e-3 kg of the `b = 0` value. `test_b_zero_control`
  - [x] `Params()` resolves to `a = 7.0e-5 × 33,600 = 2.352`, `b = 7.0e-5`; explicit `a`, `b` override; `control_params(Params())` has `b == 0`, `a == 4.2` (to 1e-9), other fields unchanged. `test_params_defaults_and_control`
  - [x] Each failure reason is produced by a minimal case: bad index, duplicate, payload (`w·k > C`), fuel_cap, takeoff_weight. `test_infeasible_reasons`
  - [x] `BASES` has 5 entries with the IDs 1734611, 7609811, 7567448, 1737158, 1733926. `test_bases`
  - [x] With the CSV present: 745 towns at `min_population=0`; each base's nearest town distance matches the PROBLEM.md table (30.8, 39.4, 35.9, 40.0, 39.7 km) within 0.5 km. Skipped if file missing. `test_data_smoke`
- **Doc deltas:** PROBLEM.md Parameters and Evaluation plan:
  - New defaults `E = 33,600`, `C = 19,630` (98 drops), `F = 21,100`, `c = 7.0e-5`, with sources: Lockheed Service News V16N1 (weights, fuel), SKYbrary and NCAR C-130 handbook (cruise ≈ 2,270 kg/h at 537 km/h ≈ 4.2 kg/km), AFI 11-202 Vol 3 (reserve).
  - `a` and `b` are separate inputs, defaults `a = c × E`, `b = c`.
  - Control is `b = 0`, `a = c × 60,000 ≈ 4.2 kg/km`, replacing "`c = 0` is the control" (with `a = c × E`, `c = 0` would burn no fuel at all).
  - Decisions made during implementation:
    - Base coordinates use the full precision of `data/MY.txt` (the PROBLEM.md table rounds them); the table stays as is.
    - `load_towns` keeps towns with `population >= min_population`, so `min_population=0` keeps all 745 (code docstring).
    - The closed form is computed as `F₀_needed = R·e^(bD) + a·(e^(bD) − 1)/b + w·Σ(e^(b·sᵢ) − 1)`, `sᵢ` = distance flown before drop `i`, using `expm1`; it equals `(R − K)·e^(bD)` and gives `R + a·D` at `b = 0` without a special case in `evaluate` (`fuel_end` keeps a `b = 0` branch, since its form divides by `b`). PROBLEM.md Fuel model: add this form.
    - An `e^x` that would overflow returns `inf` instead of raising, and a resulting `0 × inf = NaN` is mapped to `inf`, so such routes are infeasible with reason `fuel_cap` (code comment; `test_overflow_is_infeasible`).
    - A route with a bad index evaluates to population 0, distance 0, `fuel_needed = inf` (code; no doc needed).
    - Route indices accept any integer type (`operator.index`), so numpy integers work (code; no doc needed).
    - The distance matrix is computed once with numpy and stored as nested Python lists, because scalar lookups on lists are faster than on numpy arrays (code; no doc needed).
    - Code-review fixes (no behaviour change: routes and stats identical before and after; fuel values equal to floating-point rounding, about 1e-14 relative):
      - `haversine_km` is the one haversine implementation; it takes floats or numpy arrays, and `Instance` builds its matrix with it (code docstring; no doc needed).
      - `Instance.fits(k, fuel)` holds the payload, tank and takeoff check used by both solvers, next to `fuel_limit` (spec change under Interfaces; code docstring).
      - The overflow-safe `e^x` is named `safe_exp`, so it is not mistaken for `math.exp` (code; no doc needed).
      - The numpy form of the fuel formula (`fuel_needed_array`, `phi_array`) sits in `model.py` beside the scalar `fuel_needed_from`, so a change to the fuel model is made in one module (code docstring; no doc needed).

### S2 Route prefix sums (O(1) move costs)

- **Goal:** `RouteState` gives the fuel needed after an insertion, a removal or a 2-opt reversal in O(1), matching `evaluate`.
- **Blocked by:** S1
- **Files:** `airdrop/prefix.py`, `tests/test_prefix.py`
- **Seams:** `RouteState`, `evaluate`
- **Decisions:**
  - Store prefix sums of distance and of `w × e^(b × distance so far)`; reversal of `i..j` changes `D` by the two boundary edges, scales the terms of towns before the segment by one factor, and covers towns inside the segment with the prefix sum; O(1) per move, O(n) rebuild after an accepted move (docs: PROBLEM.md, Approach B data structure).
  - Avoid overflow in `e^(b·x)` by rescaling or log space (docs: PROBLEM.md).
  - `b = 0` uses the limit form (no division by `b`).
- **Acceptance criteria:**
  - [x] On 50 random routes (fixed seeds, k up to 30), `insert_fuel`, `remove_fuel` and `two_opt_fuel` equal `evaluate` on the modified route within 1e-6 relative, for every valid position. `tests/test_prefix.py::test_matches_evaluate`
  - [x] Same check with `b = 0`. `test_matches_evaluate_b_zero`
  - [x] `best_insertion` returns the minimum over all positions, smallest position on ties. `test_best_insertion`
  - [x] Works on the empty route (insert at pos 0) and single-town route. `test_small_routes`
  - [x] With `b = 1e-3` and a 20,000 km route, results are finite and match `evaluate`. `test_no_overflow`
- **Doc deltas:** none from the spec. Decisions made during implementation:
  - The prefix sums hold `φ(Sₘ) = (e^(b·Sₘ) − 1)/b` (with `φ = Sₘ` at `b = 0`) rather than `w·e^(b·Sₘ)`, `Sₘ` = distance flown to drop `m`. It carries the same information, has the `b = 0` limit without dividing by `b`, and avoids subtracting `w·k` from a large sum. PROBLEM.md Approach B data structure: say the sums use this form.
  - The shift rule `φ(x + δ) = e^(b·δ)·φ(x) + φ(δ)` moves all drops after a move by `δ` in O(1). A reversed segment `i..j` (with `B = S_(j+1)`) uses suffix sums of `φ(D − Sₘ)`: `φ(A − Sₘ) = e^(b·(B − Sₘ))·φ(A − B) + φ(B − Sₘ)`, and `φ(B − Sₘ)` is `φ(D − Sₘ)` shifted by `−(D − B)` (module docstring of `airdrop/prefix.py`).
  - Overflow and precision (rescaling): every stored term is `φ` of a distance in `[0, D]`; each range sum subtracts the smaller terms (prefix sums of the growing `φ(Sₘ)`, suffix sums of the shrinking `φ(D − Sₘ)`); the reversed segment is rescaled to its last drop `B`, so no product is larger than a term of the answer. Nothing overflows before the answer does, and an overflowing `e^x` gives `inf` (S1). A first version computed the segment through `φ(A)` with `A ≈ 2D` and lost all precision once `b·D ≳ 30` (module docstring; `test_no_overflow`, `test_large_exponent_out_and_back`).
  - `evaluate` and `RouteState` share one helper, `model.fuel_needed_from(inst, D, Σφ)`, so they cannot drift apart (code; no doc needed).

### S3 Approach A, full re-scan selector

- **Goal:** `greedy_insertion(inst, "scan")` grows the route from `base → base` by inserting, each step, the town with the best `population / marginal fuel` at its cheapest position, while the route stays feasible.
- **Blocked by:** S2
- **Files:** `airdrop/approach_a.py`, `tests/test_approach_a.py`
- **Seams:** `greedy_insertion`, `evaluate`
- **Decisions:**
  - Start `base → base`; score `population / marginal fuel` where marginal fuel is the extra fuel needed to insert at the cheapest position; insert the best town if the route stays feasible; repeat until no town fits (docs: PROBLEM.md, Approach A).
  - A town whose cheapest insertion is infeasible is discarded for the rest of the run (removing a town never raises fuel needed, so it cannot become feasible later).
  - Marginal ≤ 0 → score `+inf`; ties by larger population, then smaller index.
- **Acceptance criteria:**
  - [x] Result is feasible on random instances (fixed seeds). `tests/test_approach_a.py::test_scan_feasible`
  - [x] `result.eval == evaluate(inst, result.route)`. `test_result_matches_evaluate`
  - [x] Each step inserts the argmax town at its cheapest position, checked by a brute-force oracle in the test that uses only `evaluate`. `test_scan_is_argmax`
  - [x] `F` below `R` + any one town's need gives empty route; huge `F`, `C` and `MTOW` visit all towns. `test_budget_extremes`
  - [x] Hand-built case: a heavy-route town far from base loses to one near base with equal population (weight carried from base counts). `test_weight_drives_choice`
  - [x] Deterministic across runs. `test_scan_deterministic`
  - [x] `stats` has `score_evals` and `insertions`. `test_scan_stats`
- **Doc deltas:** none from the spec. Decisions made during implementation:
  - A town fits when `w·(k+1) ≤ C` and its cheapest-insertion fuel is `≤ fuel_limit(k+1)`; the cheapest position is the only one checked, since feasibility is monotone in fuel (`Instance.fits`, moved there from `approach_a` in code review; code docstring; no doc needed).
  - `score_evals` counts one per `best_insertion` call (one candidate scored against the current route) (code; README can mention it with the stats).
  - The scan visits candidates in index order and drops a town as soon as its cheapest insertion does not fit (code comment; no doc needed).
  - `RouteState` is rebuilt (O(k)) after every insertion (PROBLEM.md already says O(n) rebuild after an accepted move; no doc needed).

### S4 Approach A, lazy heap selector

- **Goal:** `greedy_insertion(inst, "heap")` selects with a max-heap and lazy re-evaluation, and can report how often it differs from the full re-scan.
- **Blocked by:** S3
- **Files:** `airdrop/approach_a.py`, `tests/test_approach_a.py`
- **Seams:** `greedy_insertion`, `evaluate`
- **Decisions:**
  - Max-heap with lazy re-evaluation: pop the top, recompute its true score against the current route; if it still beats the next key, insert it; otherwise push it back with the new score (docs: PROBLEM.md, Approach A).
  - Lazy re-evaluation is exact only if scores never rise; comparison is lazy heap vs full re-scan, measuring run time and how often the heap picks a different town (docs: PROBLEM.md).
  - Infeasible popped towns are discarded (same rule as S3).
  - `heapq` with negated keys; tie keys use the S3 tie order.
  - `audit=True` computes the re-scan argmax at each step without changing the heap's pick.
- **Acceptance criteria:**
  - [x] Heap result is feasible on the S3 random instances. `test_heap_feasible`
  - [x] First insertion equals the scan's first insertion. `test_heap_first_pick_matches_scan`
  - [x] With `audit=True`, `mismatches == 0` implies the heap route equals the scan route on the same instance. `test_audit_consistent`
  - [x] Hand-built case where inserting a town opens a cheaper slot for another town (score rises): the audit reports ≥ 1 mismatch. `test_audit_detects_rise`
  - [x] `stats` has `score_evals`, `insertions`, `heap_pops`, `heap_pushes`; `mismatches` only with audit. `test_heap_stats`
  - [x] Deterministic. `test_heap_deterministic`
- **Doc deltas:** none from the spec. Decisions made during implementation:
  - Heap entries are `(−score, −population, index)`, so `heapq`'s min order is the S3 tie order and each town has exactly one entry at a time (code docstring; no doc needed).
  - Towns that do not fit into the empty route are never pushed; `heap_pushes` counts the initial pushes as well as the push-backs (code; README stats description).
  - "Still beats the next key" compares the fresh full key with the current top entry; an empty heap counts as beaten (code docstring; no doc needed).
  - The audit's re-scan argmax covers the popped town plus every town still in the heap, feasible ones only, and its score evaluations are not added to `score_evals`, so stats match with and without audit (code; README stats description).
  - The scan and the audit share one argmax helper (`approach_a._argmax`) (code; no doc needed).

### S5 Nearest-neighbour seed for B

- **Goal:** `nearest_neighbour` builds a feasible route by flying to the nearest town that still lets the plane get home with the reserve.
- **Blocked by:** S1
- **Files:** `airdrop/baseline.py`, `tests/test_baseline.py`
- **Seams:** `nearest_neighbour`, `evaluate`
- **Decisions:**
  - Classic nearest neighbour; before flying to the next town, check the plane could still fly home from there with the reserve (docs: PROBLEM.md, Baselines). The check is `evaluate(route + [t]).feasible`.
  - When the nearest town does not fit, skip it and take the nearest town that fits; stop when no town fits. Decision (user): "yes" to this proposal.
  - Distance ties: smaller index.
- **Acceptance criteria:**
  - [x] Result is feasible; deterministic. `tests/test_baseline.py::test_nn_feasible`
  - [x] Each step goes to the nearest town that passes the check, skipping nearer towns that fail it, verified by an oracle in the test. `test_nn_is_nearest`
  - [x] Hand-built case where the nearest town fails the check and a farther one passes: the farther one is taken. `test_nn_skips_unfit`
  - [x] `result.eval == evaluate(inst, result.route)`. `test_nn_consistent`
- **Doc deltas:** PROBLEM.md Baselines: nearest neighbour skips towns that do not fit and stops when none fits.
  - Decisions made during implementation:
    - A town that fails the check is dropped for the rest of the run: appending to a longer route never needs less fuel and the payload and takeoff limits only tighten, so it cannot pass later. The result is the same, with fewer checks (code comment; PROBLEM.md Baselines can note it).
    - `stats` for `nearest_neighbour` are `"checks"` (calls to `evaluate` for a candidate) and `"steps"` (towns added); the spec left them open (code; README stats description).
    - `nearest_neighbour` returns the `SolveResult` type defined in `approach_a` (code; no doc needed).

### S6 Approach B, local search

- **Goal:** `local_search` starts from the nearest-neighbour route (or a given route) and applies the best improving move each round until none improves.
- **Blocked by:** S2, S5
- **Files:** `airdrop/approach_b.py`, `tests/test_approach_b.py`
- **Seams:** `local_search`, `nearest_neighbour`, `evaluate`
- **Decisions:**
  - Start from the nearest-neighbour route (docs: PROBLEM.md, Approach B). `initial` allows "B on A's route" (docs: PROBLEM.md, Evaluation plan).
  - Moves, all under the full fuel model (docs: PROBLEM.md):
    - 2-opt: reverses a segment; accepted when same population, less fuel needed.
    - Add: inserts an unvisited town at its cheapest position; accepted when the route stays feasible.
    - Swap: replaces a visited town with a more populous unvisited one; accepted when feasible and population rises.
    - Replace 1 with 2: removes one visited town and inserts two unvisited ones; accepted when feasible and population rises.
    - Replace 1 with 2 neighbourhood. Decision (user): "yes" to this proposal: for each removed town `r`, take the `L = 20` unvisited towns with the best single-insertion score into the route without `r`; try each pair `(u, v)` from them, inserting `u` at its cheapest position, then `v` at its cheapest position. `L` is a `local_search` argument.
  - Each round, apply the move with the largest population gain; ties go to the move that needs the least fuel; repeat until no move improves (docs: PROBLEM.md).
  - No plain "drop a town" move (docs: PROBLEM.md).
  - Move costs via `RouteState`; rebuild after each accepted move (docs: PROBLEM.md).
  - Remaining ties (same gain, same fuel): move type order 2-opt, add, swap, replace 1 with 2, then smallest indices.
  - `max_rounds` cap; `stats["hit_max_rounds"] = 1` if reached.
- **Acceptance criteria:**
  - [x] Result is feasible; population ≥ the initial route's; if equal, fuel needed ≤ initial. `tests/test_approach_b.py::test_not_worse_than_seed`
  - [x] Hand-built crossing route: 2-opt removes the crossing and lowers fuel needed. `test_two_opt_uncrosses`
  - [x] Hand-built case where add applies. `test_add`
  - [x] Hand-built case where swap applies. `test_swap`
  - [x] Hand-built case where only replace 1 with 2 improves. `test_replace_1_2`
  - [x] With `L = 1`, replace 1 with 2 tries no pair; with `L ≥ n` it matches the unrestricted brute force on n ≤ 8. `test_replace_neighbourhood_L`
  - [x] Each round picks the largest population gain, then least fuel, checked by a brute-force oracle over all moves on a small instance (n ≤ 8). `test_best_move_chosen`
  - [x] On the result, no move of the four types improves (brute-force check, n ≤ 8). `test_local_optimum`
  - [x] `initial=` a given route is used as the seed. `test_custom_seed`
  - [x] `result.eval == evaluate(inst, result.route)`; deterministic; stats keys present. `test_consistent_and_stats`
- **Doc deltas:** PROBLEM.md Approach B: move tie order, and the `L = 20` candidate restriction for replace 1 with 2.
  - Decisions made during implementation:
    - Swap inserts the new town `u` at its cheapest position in the route without `r` (the spec did not fix the position; this matches add and replace 1 with 2). PROBLEM.md Approach B moves table.
    - Replace 1 with 2 tries ordered pairs, so both `(u, v)` and `(v, u)` are tried; pairs with `pop(u) + pop(v) ≤ pop(r)` are skipped before any fuel is computed. PROBLEM.md Approach B.
    - The `L` candidates are ranked with Approach A's key (`approach_a.insertion_key`: population / marginal fuel into the route without `r`, then population, then index), with no feasibility filter. PROBLEM.md Approach B.
    - Add is offered only for towns with population > 0, since a move must raise population or, for 2-opt, lower fuel (code docstring; no doc needed).
    - The "smallest indices" tie-break uses positions `(i, j)` for 2-opt and town indices `(t)`, `(r, u)`, `(r, u, v)` for the others (module docstring of `approach_b.py`).
    - `stats["rounds"]` counts applied moves. `hit_max_rounds = 1` only when the cap stopped the search while an improving move was left, so `max_rounds=0` on a local optimum reports 0 (code; README stats description).
    - An infeasible `initial` route raises `ValueError` (code docstring; README).
    - Each round builds a `RouteState` for the route without each visited town, and one for each candidate `u` in replace 1 with 2, then scores insertions with the vectorised `best_insertions` (see the spec change under Interfaces). README: run time note.
    - Tests seed the brute-force oracles from both the nearest-neighbour route and the empty route, because nearest neighbour alone leaves no room for add or replace 1 with 2; `test_best_move_chosen` asserts that all four move types are exercised (tests; no doc needed).

### S7 README run instructions

- **Goal:** README describes the folder structure, setup, how to run tests, and how to call both approaches.
- **Blocked by:** S4, S6
- **Files:** `README.md`
- **Seams:** none (docs only)
- **Decisions:** README must describe folder structure and run instructions (docs: Project_2627T1.pdf §6a).
- **Acceptance criteria:**
  - [x] The README example snippet, saved to a script and run with `python` from repo root, exits 0.
  - [x] `python -m pytest` passes.
- **Doc deltas:** README.md itself.
  - Decisions made during implementation:
    - The example loads towns with `population >= 100,000` (86 towns), so it runs in about 2 s; the 745-town run time is stated in prose instead (README).
    - The README documents each solver's `stats` keys, since the spec left `nearest_neighbour`'s open and several counting rules were decided in S4–S6 (README).
    - Proved by saving the README's `python` block to a file and running `python - < <file>` from the repo root (stdin keeps the repo root on `sys.path`); exit code 0 (no doc needed).

## 6. Human checks

- [ ] S1: cruise burn (≈ 2,270 kg/h, no gross weight stated) and the reserve rule come from medium/low-trust sources. Expected: you accept them as cited in PROBLEM.md, or replace them with a better source.
- [ ] S4: run `greedy_insertion` with `"heap"` and `"scan"` on all 745 towns from one base. Expected: both finish; you can explain the run-time gap and the mismatch count.
- [ ] S6: run `local_search` on all 745 towns at default params. Expected: it finishes in a time you can live with for the experiments; if not, lower `L`.
- [ ] S3/S6: plot A's and B's routes on a map for one base. Expected: routes look plausible, no obvious crossings after B.
