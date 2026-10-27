# Decisions

## 2026-10-27: Three rural and three non-rural bases

**Change:** the five rural bases became six bases: one rural site and one existing airport in each region (Peninsula, Sarawak, Sabah). See the Bases table in [PROBLEM.md](PROBLEM.md#bases).

| Region | Rural (new airbase) | Non-rural (existing airport) |
|---|---|---|
| Peninsula | Kampung Sungai Semaliang (`perak`) | Kuala Lumpur International Airport (`klia`) |
| Sarawak | Long Geng (`sarawak`) | Kuching International Airport (`kuching`) |
| Sabah | Kampung Balat (`sabah`) | Kota Kinabalu International Airport (`kota_kinabalu`) |

The Kelantan and Johor rural sites were dropped, so each region has one base of each type.

**Why:** we want to weigh the cost of building a new airbase against costs that the model does not count.
Running the same solver from both bases in a region gives a measured difference in population reached and fuel used.
That difference is what a new rural airbase buys.
We can then set it against the costs that have no number in our model, for example:

- building the runway, fuel storage and access roads at a remote site;
- clearing land, and the effect on forest, plantations and nearby villages;
- the time before the base can operate;
- crew, maintenance and supply lines far from a city;
- sharing a busy civilian airport: slots, congestion and priority for aid flights.

If the existing airport reaches almost as many people, a new airbase is hard to justify.
If the rural site reaches many more, the non-numerical costs may be worth paying.

**Consequence:** experiment 3 (bases) in [EXPERIMENT.md](EXPERIMENT.md) compares the rural and non-rural base within each region.

## 2026-10-27: Exact DP runs backward, from landing to takeoff

**Change:** the exact DP builds routes from the landing back to the takeoff, instead of forward from the base as first planned in [PROBLEM.md](PROBLEM.md#exact-dp).

- State: the set `U` of towns still to drop and the town `j` the plane is arriving at (the first town of `U`).
- Value: the least fuel on board on arrival at `j` that lets the plane drop at every town of `U` and land with the reserve `R`.
- Start: for each town, the fuel needed to drop there, fly home and land with `R`.
- Step: put one more town in front of a set, try every next town, and keep the least fuel.
- Finish: add the leg from the base to the first town. This gives the exact fuel to load, `F₀`. Keep the sets that fit the payload, tank and takeoff limits, and pick the most population, then the least `F₀`.

**Why:** cargo on a leg is 200 kg for each drop still to come.

- Forward, the takeoff cargo depends on how many towns the route ends up with, which is not known yet. The forward DP has to be run once for each route length `k`, with the fuel loaded fixed in advance.
- Backward, the set `U` already says how many drops are left, so the cargo on every leg is known. One pass covers every route length, so it is about `n` times less work: `O(n²·2ⁿ)` instead of `O(n³·2ⁿ)`.
- With the fuel fixed in advance, the forward DP can only say whether a route fits. Two routes over the same towns can leave different amounts of fuel at the end, and the one with more left is not always the one that needs less fuel to load. The backward DP computes the least fuel to load directly, so the tie-break "least fuel needed" is exact.
- Needing less fuel later always means needing less fuel earlier, so keeping only the least fuel per state loses no route. The answer is still exact.

**Consequence:** the Exact DP section of [PROBLEM.md](PROBLEM.md#exact-dp) is rewritten to the backward version when the DP is implemented.

## 2026-10-27: No control experiment

**Change:** the control experiment (rerun the fuel sweep with `control_params`, `b = 0`) was dropped from [EXPERIMENT.md](EXPERIMENT.md) and the evaluation plan in [PROBLEM.md](PROBLEM.md#evaluation-plan).
`control_params` stays in the code.

**Why:** the weight effect is large enough to argue without running it.
Burn per km is `c × total mass`, and total mass ranges from 33,600 kg (empty) to 70,300 kg (MTOW), so a full plane burns about twice as much per km as an empty one.

**Consequence:** the slides justify the weight model with this calculation instead of a plot.

## 2026-10-27: No fuel sweep

**Change:** the fuel sweep experiment (population against `F` for NN, A and B, from 3,000 to 20,000 kg) was dropped from [EXPERIMENT.md](EXPERIMENT.md) and the evaluation plan in [PROBLEM.md](PROBLEM.md#evaluation-plan). No experiment sweeps `F`.

- Experiments 1–3 (heap vs scan, run time, bases) use the default `Params`, `F = 21,100 kg`. Experiment 1 varies the number of towns, not `F`. The bases experiment moves from `F = 20,000 kg` to 21,100 kg.
- B on A moves from the fuel sweep to the bases experiment, as its own row kept off the main chart.
- The experiments are renumbered 1–4: heap vs scan, run time, bases, optimality gap.
- The optimality gap uses two lower fixed fuel caps, each the same for all 10 samples and each stated as an assumption (a partial fuel load for a short-range sortie):
  - `F_full`: the smallest multiple of 10 kg in `[R, 21,100]` at which the exact DP route visits all 12 towns in at least 8 of the 10 samples ("most cases").
  - `F_tight`: the smallest multiple of 10 kg in `[R, 21,100]` at which the exact DP routes visit on average at least 80% of the 12 towns, 9.6 towns (the middle of 70–90%).
  - Both are found by binary search over multiples of 10 kg. They replace the earlier rule "`F` set so about half the towns fit".
- The optimality gap's 12-town samples are drawn from Peninsular towns only (`region == "Peninsular"`), from the Perak base.

**Why:**

- [DOMAIN-RESEARCH.md](DOMAIN-RESEARCH.md) justifies `F = 21,100 kg` as the C-130H internal tank, so a sweep is not needed to defend the value. The bases experiment already compares the algorithms on 6 instances.
- The optimality gap needs a lower `F`: at 21,100 kg every 12-town sample fits whole, so NN, A and B all score exactly the optimum (checked on 10 samples from all towns and from Peninsular towns: every gap 1.000). Two values show the gap when almost every town fits and when about a fifth must be left out.
- Peninsular samples, measured on seeds 0–9: drawn from all 745 towns, 18 of the 120 sampled towns are in East Malaysia, over 1,000 km from Perak. At the gap's fuel caps (about 4,900 and 5,640 kg, so at most about 3,940 kg above the reserve, under 1,000 km of flight at 4.2 kg/km) no route can reach them and fly back. Every algorithm and the DP skip them, so a sample has fewer than 12 real choices, and the count differs between samples. Peninsular samples keep all 12 towns reachable. The Perak base is on the Peninsula, and 642 of the 745 towns are Peninsular.

**Consequence:** each experiment's plan in [EXPERIMENT.md](EXPERIMENT.md) states its fuel cap. Experiment 4 reports the `F_full` and `F_tight` values its run finds.
