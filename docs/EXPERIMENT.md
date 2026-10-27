# Experiments

What to run for the presentation. Each experiment gets a folder under `experiments/` with a script that saves a CSV and a plot.
Algorithms: nearest neighbour (NN), Approach A, Approach B. Approach A is the heap selector (`a_heap`) in experiments 2–4; experiments 1 and 2 also run the re-scan (`a_scan`).
Default: all 745 towns, Perak base, default `Params` (`F = 21,100 kg`, the full internal tank). Every experiment uses `F = 21,100 kg` except the optimality gap. There is no fuel sweep (see [DECISIONS.md](DECISIONS.md), "No fuel sweep").

| # | Folder | Experiment | Question | Plot |
|---|---|---|---|---|
| 1 | `e1_heap_vs_scan` | Heap vs scan | How much work does A's lazy heap save, and how often does it pick a different town than the re-scan? Population thresholds 100,000 / 50,000 / 15,000 / 0. Mismatches from `audit=True`. | Score evals per selector, and mismatches ÷ insertions, against number of towns |
| 2 | `e2_run_time` | Run time | How does each algorithm's run time grow with the number of towns? NN, A (heap and scan), B, same thresholds. | Time against number of towns, one line per algorithm |
| 3 | `e3_bases` | Bases | Which of the 6 bases reaches the most people, and how much does a non-rural base gain over the rural one in its region? NN, A, B, and B on A. | Bars grouped by region, rural and non-rural side by side; B on A in a separate panel |
| 4 | `e4_optimality_gap` | Optimality gap | How close do NN, A, B and B on A come to the exact DP? 10 random 12-town samples of Peninsular towns, Perak base, at two lower fixed fuel caps `F_full` and `F_tight`. | Gap per algorithm, one panel per `F` |

B on A is local search started from A's route (`local_search(inst, initial=a.route)`). It is reported in experiment 3 as its own row, kept off the main NN/A/B chart.

Experiment 4's two fuel caps are each the same for all 10 samples, and each is an assumption: a partial fuel load for a short-range sortie. At `F = 21,100 kg` every 12-town sample fits whole, so every heuristic scores exactly the optimum.

- `F_full`: the smallest multiple of 10 kg in `[R, 21,100]` at which the exact DP route visits all 12 towns in at least 8 of the 10 samples.
- `F_tight`: the smallest multiple of 10 kg in `[R, 21,100]` at which the exact DP routes visit on average at least 80% of the 12 towns (9.6 towns).
- Both are found by binary search over multiples of 10 kg.

The samples are drawn from Peninsular towns only, so all 12 towns of a sample are within reach of the Perak base at these fuel caps (see [DECISIONS.md](DECISIONS.md), "No fuel sweep").

## Trial result for experiment 1

A trial run with a varied `F`, before the fuel cap was fixed at 21,100 kg. Kept as history.

86 towns (population ≥ 100,000), Perak base, 2026-10-21:

| `F` (kg) | Selector | Population | Score evals | Mismatches |
|---|---|---|---|---|
| 21,100 | scan | 25.94 M | 3,725 | n/a |
| 21,100 | heap | 26.23 M | 172 | 72 of 81 |
| 8,000 | scan | 23.80 M | 3,085 | n/a |
| 8,000 | heap | 21.16 M | 165 | 50 of 54 |

The heap never pushed a town back. Scores rise as the route grows: a town's first score prices a round trip from the base, later scores only a short detour. So the heap ends up sorting by first score.
