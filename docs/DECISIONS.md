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
