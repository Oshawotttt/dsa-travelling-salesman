# Problem Definition: Payload-Aware Aid Airdrop

## Use case

An aid plane takes off from a base carrying relief supplies and airdrops them over towns in Malaysia.
It does not land, so any town can be served directly from the air.
Each town gets one drop, and one drop serves the whole town.
Fuel is limited, so the plane cannot reach every town.
The goal is to reach as many people as possible and return to base with a safe fuel reserve.

Because the plane flies straight between drops, great-circle (haversine) distance is a realistic travel distance.
The sea between Peninsular and East Malaysia is not an obstacle.

## Why the classic TSP is not enough

| # | Classic assumption | What changes in our use case |
|---|---|---|
| 1 | Every city must be visited | The fuel limit makes visits optional. We choose a subset of towns. |
| 2 | All cities are equal | Each town has a prize: its population (people reached by the drop). |
| 3 | Single objective: minimize distance | Maximize total population reached, with fuel as a hard constraint. |
| 4 | Edge cost is fixed | Fuel burn depends on the plane's current weight (cargo + fuel on board). The plane gets lighter after each drop and as it burns fuel, so the cost of a leg depends on everything flown before it. |

Assumptions 1–3 alone give the **Orienteering Problem** (also called the selective TSP).
Assumption 4 adds a weight-dependent, history-dependent cost, which makes our formulation an extension of it.

## TSP variant

**Input**

- A base (start and end of the route): one of five candidate airport sites (see [Bases](#bases)).
- A set of candidate towns, each with latitude, longitude and population (from `data/cities_clean.csv`).
- Haversine distance `d(i, j)` between every pair of locations.
- Aircraft constants (C-130H, see [Parameters](#parameters)): empty weight `E`, maximum payload `C`, maximum takeoff weight `MTOW`, fuel cap `F` (tank size).
- Drop weight `w = 200 kg` per town.
- Fuel reserve `R`: fuel that must remain after landing.
- Fuel burn coefficient `c`: fuel burnt per km per kg of total aircraft mass.

**Output**

- A route `base → t1 → t2 → … → tk → base` that visits a subset of `k` towns, with one drop per town.
- The cargo and fuel to load, both derived from the route.

**Loading**

- Cargo: the plane carries only what it will drop, `W₀ = w × k`.
- Fuel: the plane carries only what the route needs, `F₀` (see the fuel model below).

**Constraints**

- Each town is visited at most once.
- The route starts and ends at the base.
- Payload: `w × k ≤ C`.
- Fuel fits the tank and the takeoff weight: `F₀ ≤ min(F, MTOW − E − w × k)`.
- Fuel left after the return leg is at least `R`.

**Objective**

- Maximize the total population of the visited towns.
- Ties are broken by the least fuel needed.

## Fuel model

Fuel burn per km is proportional to the plane's total mass:

```
burn rate u = a + b × (cargo + fuel on board),   where a = c × E and b = c
```

Fuel is burnt continuously, so in flight `du/dx = −b × u`:

- Over a leg of length `d`, `u` shrinks by the factor `e^(−b·d)`.
- At a drop, `u` falls by `b × w`.

For a whole route, with `D` = total distance and `Rᵢ` = distance flown after the drop at town `i`:

```
u₀       = a + b × (W₀ + F₀)
fuel_end = ( u₀ × e^(−b·D) − b × Σ w × e^(−b·Rᵢ) − a ) / b
```

Fuel on board only goes down, so checking `fuel_end ≥ R` at the end is enough.
`fuel_end` is linear in `F₀`, so the fuel a route needs has a closed form:

```
fuel_end  = F₀ × e^(−b·D) + K          (K depends only on the route)
F₀_needed = (R − K) × e^(b·D)
```

We checked this formula against a step-by-step numerical simulation; the two agree to within 0.01 kg.
On a 2,572 km test route, counting fuel weight raised the burn from 7,905 kg to 10,410 kg (about 30%).

## Design consequences of the weight-dependent cost

- **No fixed cost matrix.** We can still store distances, but fuel must be computed from the cargo and fuel on board.
- **History-dependent cost.** A leg's cost depends on what was dropped and burnt before it, not only on its two endpoints.
- **Greedy scores go stale.** Every insertion makes the route longer and heavier, so all stored scores become out of date.
- **Local search can still be cheap.** Reversing a segment in 2-opt changes leg weights only inside the segment, and the drop terms `w × e^(−b·Rᵢ)` can be kept in prefix sums. This gives O(1) move evaluation (see Approach B).
- **New trade-offs.**
  - Long legs are cheaper late in the flight, when the plane is lighter.
  - Under the takeoff-weight limit, each extra town costs 200 kg of fuel capacity, so cargo and fuel compete.

## Approaches

Each approach solves the whole variant: all four broken assumptions at once.

### Baselines

- **Nearest neighbour with fuel cutoff:** classic nearest neighbour. Before flying to the next town, it checks that the plane could still fly home from there with the reserve.
- **Population greedy:** always fly to the most populous town that still fits the fuel check.

### Approach A: Greedy insertion with a lazy heap

- Keep a complete route, starting with `base → base`.
- Score each unvisited town by `population / marginal fuel`, where marginal fuel is the extra fuel needed to insert it at its cheapest position.
- Marginal fuel includes the cost of carrying the town's 200 kg from the base to its drop point, so the weight model drives the choices.
- Insert the best town if the route stays feasible, and repeat until no town fits.
- Each insertion cost is evaluated in O(1) per position, using the same prefix sums as Approach B.
- **Data structure: max-heap with lazy re-evaluation.**
  1. Pop the top town and recompute its true score against the current route.
  2. If it still beats the next key in the heap, insert it.
  3. Otherwise push it back with the new score.

  Re-scoring every town after each insertion would make the heap pointless, because a linear scan would do the same job.
  Lazy re-evaluation is exact only if scores never rise. They mostly fall as the route grows, but a new town can open a cheaper slot nearby.
- **Comparison:** lazy heap against a full re-scan, measuring run time and how often the lazy heap picks a different town.

### Approach B: Local search

- Start from the nearest-neighbour baseline route. It knows nothing about the weight model, so any weight awareness in B's result comes from B's moves.
- Moves, all evaluated under the full fuel model:

  | Move | What it does | Accepted when |
  |---|---|---|
  | 2-opt | Reverses a segment of the route | Same population, less fuel needed |
  | Add | Inserts an unvisited town at its cheapest position | Route stays feasible (population rises) |
  | Swap | Replaces a visited town with a more populous unvisited one | Route stays feasible, population rises |
  | Replace 1 with 2 | Removes one visited town and inserts two unvisited ones | Route stays feasible, population rises |

- Each round, apply the move with the largest population gain. Ties go to the move that needs the least fuel.
- Repeat until no move improves the route.
- A plain "drop a town" move is not used: on its own it always lowers population, so it would never be accepted.
- **Data structure: exponential-weighted prefix sums** over the route.
  - Store prefix sums of distance and of `w × e^(b × distance so far)`.
  - Reversing segment `i..j` changes `D` by the change in the two boundary edges. It shifts `Rᵢ` for every town before the segment by the same amount, which scales their sum by one factor. Towns inside the segment are covered by the prefix sum.
  - This gives O(1) evaluation per move and an O(n) rebuild after each accepted move.
  - To avoid overflow in `e^(b·x)`, rescale the sums or work in log space.

### Other approaches considered

- **State-aware ratio greedy** (score `population / fuel(current, town, W)`): rejected. At each step `(a + bW)` is the same for every candidate, so the ranking reduces to `population / distance` and the weight model never changes the choices. A heap is also no help here, because every key changes when the current town changes.
- Cluster first, route second (k-means or DBSCAN on town locations).
- Select then route (knapsack-style selection with estimated fuel, then classic TSP on the chosen set).
- Metaheuristics (simulated annealing, genetic algorithm, ant colony optimisation).

## Evaluation plan

- **Main comparison:** population reached against the fuel cap `F`, swept from about 3 t to 20 t, for:
  - nearest neighbour, population greedy, Approach A, and Approach B (seeded from nearest neighbour);
  - an extra row, **B on A's route**, labelled as a combined result and kept off the main A-vs-B chart. It shows how much local search still adds on top of a good route.
- **Run time:** against number of towns `n`, using population thresholds from `eda.ipynb` (for example 83, 144, 355 and 745 towns).
- **Optimality gap:** exact DP (below) on 10 random 12-town samples, with `F` set so about half the towns fit. Report the average and worst gap: heuristic population ÷ optimal population.
- **Data-structure comparison:** lazy heap against full re-scan in Approach A.
- **Base comparison:** population reached from each of the five bases at `F = 20 t`.
- **Control:** `c = 0` switches off the weight model and reduces the problem to the plain Orienteering Problem. It isolates the effect of the weight-dependent cost.
- **Complexity analysis** of each approach, including the O(1) move evaluation with prefix sums.

### Exact DP

Exact DP finds the true best route on small inputs. It covers every route, like brute force, but only does work on a fraction of them.

- Two partial routes that have visited the same towns, are at the same town and carry the same cargo have identical futures. The one with more fuel left is at least as good, so the other is discarded.
- Table: `best[towns visited][current town]` = the most fuel left at that point.
  1. Start: for each town `X`, `best[{X}][X]` = fuel left after flying base → `X`.
  2. Extend: from each entry, try each unvisited town `Y`, and keep the larger fuel in `best[visited + Y][Y]`.
  3. Finish: an entry is a valid route if the plane can still fly home with the reserve. Its score is the population of the visited towns.
  4. Answer: the highest score.
- Starting cargo depends on how many towns the route has. Because every drop is 200 kg, it depends only on the count `k`. So the table is run once for each `k = 1…n`, starting with `200 × k` kg of cargo and the matching fuel, and only routes with exactly `k` towns are accepted.
- Cost: O(n × 2ⁿ × n²). For `n = 12` this is about 7M steps, which takes seconds in Python.

## Bases

The bases are sites for a new airport, chosen from `MY.txt` and treated as already built.
Each is far from all towns in `cities_clean.csv`.

| Region | GeoNames ID | Name | Coordinates | Elevation | Nearest town |
|---|---|---|---|---|---|
| Peninsula north (Perak) | 1734611 | Kampung Sungai Semaliang | 4.9833, 101.2167 | 104 m | 30.8 km |
| Peninsula east (Kelantan) | 7609811 | Kemajuan Tanah Gugusan Aring | 4.8811, 102.3238 | 105 m | 39.4 km |
| Peninsula south (Johor) | 7567448 | Kampung Ponjot | 2.2366, 103.5823 | 24 m | 35.9 km |
| Sarawak | 1737158 | Long Geng | 2.6167, 114.1333 | 121 m | 40.0 km |
| Sabah | 1733926 | Kampung Balat | 5.3222, 117.6087 | 39 m | 39.7 km |

Selection filters:

- No recorded population (`population == 0`).
- Feature class `P` (place) or `L` (area), so no hills, caves or islands.
- Elevation (`dem`) between 1 and 150 m, so the ground is flat enough for a runway.
- 20–40 km from the nearest town: remote, but not deep jungle.
- Within that, the site farthest from towns in each region.

Long Geng already has an airstrip (`S.AIRF` row at the same point).
Gugusan Aring is cleared plantation land.

## Data

- Towns: `data/cities_clean.csv`, built from `MY.txt` in `eda.ipynb` (section 9).
  It keeps populated places (`feature_class == "P"`) with a recorded population, drops historical and abandoned places, removes duplicate coordinates, and adds the derived `state` and `region` columns.
- Bases: five rows from `MY.txt`, chosen with the filters above.
- Derived values: drop weight `w = 200 kg` per town, cargo `W₀ = w × k`, and the fuel needed per route `F₀_needed`.

## Parameters

The constants are inputs to the problem, not fixed values.
Every solver takes them as arguments, and experiments sweep some of them.
The C-130H figures are approximate and must be checked against a cited source.

| Parameter | Meaning | Value / experiment |
|---|---|---|
| `base` | Start and end location | Five candidate sites; compared at `F = 20 t` |
| `F` | Fuel cap (tank size) | Swept from about 3 t to 20 t; default 20 t |
| `E` | Empty weight | About 34,400 kg |
| `C` | Maximum payload | About 19,000 kg (95 drops) |
| `MTOW` | Maximum takeoff weight | About 70,300 kg (cargo + fuel ≤ about 36 t) |
| `c` | Fuel per km per kg of total mass | About 7.8e-5, from about 2,300 kg/h at 540 km/h; `c = 0` is the control |
| `a = c × E` | Fuel per km for the empty plane | About 2.7 kg/km |
| `w` | Weight of one drop | 200 kg |
| `R` | Fuel reserve after landing | About 1,700 kg (45 minutes of flight) |
| `n` | Number of candidate towns (set by a population threshold) | 83, 144, 355, 745 for run time; 12 for the exact DP |

## Limitations

- **Population overlap:** suburbs sit inside larger cities (for example Subang Jaya inside the KL urban area), so summed population overstates people reached. We treat population reached as a relative score, not a head count.
- **One drop serves a whole town:** a 200 kg drop cannot feed a large town. Population is a priority score, not a count of people fed.
- **Fuel model:** burn is linear in total mass. Wind, altitude changes, climb and descent are ignored.
- **Straight-line flight:** no airspace restrictions or terrain avoidance.
- **No recorded population:** GeoNames uses 0 for "not recorded", so the base sites are not truly empty. They are small villages or plantation land outside the town list.
- **Aircraft constants** are approximate public figures for the C-130H.
