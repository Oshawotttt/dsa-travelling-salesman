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

**Consequence:** experiment 4 in [EXPERIMENT.md](EXPERIMENT.md) compares the rural and non-rural base within each region.

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
