# Problem Definition: Payload-Aware Aid Airdrop

## Use case

An aid plane leaves a base carrying relief supplies and airdrops them over towns in Malaysia.
It does not land, so any town can be served directly from the air.
Fuel is limited, so the plane cannot reach every town.
The goal is to reach as many people as possible before the plane must return to base.

Because the plane flies straight between drops, great-circle (haversine) distance is a realistic travel distance.
The sea between Peninsular and East Malaysia is not an obstacle.

## Why the classic TSP is not enough

| # | Classic assumption | What changes in our use case |
|---|---|---|
| 1 | Every city must be visited | The fuel budget makes visits optional. We choose a subset of cities. |
| 2 | All cities are equal | Each city has a prize: its population (people reached by the drop). |
| 3 | Single objective: minimize distance | Maximize total population reached, with fuel as a hard constraint. |
| 4 | Edge cost is fixed | Fuel burn depends on the plane's current weight. The plane gets lighter after each drop, so the cost of a leg depends on visit order. |

Assumptions 1–3 alone give the **Orienteering Problem** (also called the prize-collecting TSP).
Assumption 4 adds a payload-dependent, order-dependent cost, which makes our formulation an extension of it.

## TSP variant

**Input**

- A base location (start and end of the route).
- A set of candidate cities, each with latitude, longitude and population (from `data/cities_clean.csv`).
- Haversine distance `d(i, j)` between every pair of locations.
- A fuel budget `F`.
- Package size `N`: one aid package serves `N` people.
  City `i` needs `k(i) = ⌈population(i) / N⌉` packages.
- Package weight `w`; the aid for city `i` weighs `w × k(i)`.
- A fuel model, for example `fuel(i, j, W) = d(i, j) × (a + b × W)`, where `W` is the plane's current total weight.

**Output**

- A route `base → c1 → c2 → … → ck → base` that visits a subset of cities, with one airdrop per city.

**Constraints**

- Total fuel used, including the return to base, is at most `F`.
- Each city is visited at most once.
- The plane's weight decreases by `w × k(i)` after the drop at city `i`.

**Objective**

- Maximize the total population of the visited cities.

## Design consequences of the payload-dependent cost

- **No fixed cost matrix.** We can still store distances, but fuel must be computed from the current payload.
- **Asymmetric cost.** A → B costs more than B → A if cargo is dropped at A first.
- **Greedy scores go stale.** A score such as `population / fuel_to_reach` changes as the plane gets lighter, so a plain priority queue becomes invalid after each drop. This needs lazy re-scoring or rebuilding the queue.
- **Local search gets more expensive.** In 2-opt, reversing a segment changes the weight carried on every later leg. Checking one move costs O(n) instead of O(1).
- **New trade-off.** Dropping heavy loads early makes the rest of the flight cheaper, but this can conflict with travelling short distances.

## Approaches

Each approach solves the whole variant: all four broken assumptions at once.

### Baselines

- **Nearest neighbour with fuel cutoff:** classic nearest neighbour, stopping when the next city and the return to base no longer fit the budget.
- **Population greedy:** always fly to the most populous reachable city.

### Approach A: State-aware ratio greedy

- At each step, score each reachable city by `population / fuel(current, city, W)`.
- Only consider a city if the plane can still fly back to base after visiting it.
- Data structure: a priority queue with lazy invalidation (re-score an entry when it is popped if the weight has changed). Compare it with a linear scan per step.

### Approach B: Greedy + local search

- Build an initial route with Approach A.
- Improve it with moves evaluated under the payload-aware fuel model:
  - 2-opt to shorten the route and free fuel,
  - add a city when fuel allows,
  - drop or swap low-value cities for higher-value ones.
- Repeat until no move improves the population reached.

### Other approaches considered

- Greedy insertion (insert the city with the best `population / extra fuel` at its cheapest position).
- Cluster first, route second (k-means or DBSCAN on town locations).
- Select then route (knapsack-style selection with estimated fuel, then classic TSP on the chosen set).
- Metaheuristics (simulated annealing, genetic algorithm, ant colony optimisation).

## Evaluation plan

- **Main comparison:** population reached against fuel budget `F`, for each method.
- **Run time:** against number of cities `n`, using population thresholds from `eda.ipynb` (for example 83, 144, 355 and 745 cities).
- **Optimality gap:** exact bitmask DP on small inputs (n ≤ ~15) gives the true optimum to compare with the heuristics.
- **Data-structure comparison:** heap with lazy invalidation against linear scan in Approach A.
- **Complexity analysis** of each approach, including the O(n) move evaluation caused by the payload-dependent cost.

## Parameters

The constants are inputs to the problem, not fixed values.
Every solver takes them as arguments, and experiments sweep them to show how each method responds.

| Parameter | Meaning | Example experiment |
|---|---|---|
| `base` | Start and end location | KL vs Kota Kinabalu: central vs edge base |
| `F` | Fuel budget | Population reached as `F` grows |
| `a` | Fuel per km for the empty plane | Fixed per run |
| `b` | Extra fuel per km per unit of weight | `b = 0` reduces to the plain Orienteering Problem; larger `b` makes visit order matter more |
| `N` | People served by one package | Small `N` means more packages per city and a heavier load |
| `w` | Weight of one package | Heavier packages make early heavy drops more valuable |
| `load_policy` | `planned`: carry only the aid for the chosen cities; `full`: carry a fixed full load | Effect of the starting load on the route |
| `n` | Number of candidate cities (set by a population threshold) | Run time and solution quality as `n` grows |

The `b = 0` case is a useful control: it isolates the effect of the payload-dependent cost.

## Limitations

- **Population overlap:** suburbs sit inside larger cities (for example Subang Jaya inside the KL urban area), so summed population overstates people reached. We treat population reached as a relative score, not a head count.
