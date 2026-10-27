# Experiments

What to run for the presentation. Each experiment gets a folder under `experiments/` with a script that saves a CSV and a plot.
Algorithms: nearest neighbour (NN), Approach A, Approach B. Default: all 745 towns, Perak base, default `Params`.

| # | Experiment | Question | Plot |
|---|---|---|---|
| 1 | Heap vs scan | Is A's lazy heap faster, and how often does it pick a different town? Use `audit=True`. Run first: it picks A's selector for the other experiments. | Time and mismatches vs `F` |
| 2 | Fuel sweep | Who reaches the most people as fuel gets tighter? Sweep `F` from 3,000 to 20,000 kg. | Population vs `F`, one line per algorithm |
| 3 | Run time | How does each algorithm scale? Use about 83, 144, 355, 745 towns. | Time vs number of towns |
| 4 | Bases | Which of the 6 bases reaches the most people at `F = 20,000 kg`, and how much does a non-rural base gain over the rural one in its region? | Bar per base, grouped by region |
| 5 | Optimality gap | How close are A and B to the best route? Exact DP on 10 random 12-town samples. | Gap per algorithm |

Also report B on A's route (`local_search(inst, initial=a.route)`) as a separate row in experiment 2.

## Trial result for experiment 1

86 towns (population ≥ 100,000), Perak base, 2026-10-21:

| `F` (kg) | Selector | Population | Score evals | Mismatches |
|---|---|---|---|---|
| 21,100 | scan | 25.94 M | 3,725 | n/a |
| 21,100 | heap | 26.23 M | 172 | 72 of 81 |
| 8,000 | scan | 23.80 M | 3,085 | n/a |
| 8,000 | heap | 21.16 M | 165 | 50 of 54 |

The heap never pushed a town back. Scores rise as the route grows: a town's first score prices a round trip from the base, later scores only a short detour. So the heap ends up sorting by first score.
