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

## Running

`python -m experiments.eN_<name>.run` from the repo root. It writes `runs.csv`, `routes.csv` and `plot.png` to `experiments/eN_<name>/out/`, which are committed. Output format: [CONTRACTS.md](CONTRACTS.md#experiment-output).

- Experiments 1 and 2 time each solver call best of 3; experiments 3 and 4 run once. Timing covers the solver call only.
- Experiment 3 runs `nn`, `a_heap`, `b`, `b_on_a` in that order for each base, with `b_on_a` seeded by the `a_heap` route of the same base. The region pairing (`perak`/`klia` Peninsula, `sarawak`/`kuching` Sarawak, `sabah`/`kota_kinabalu` Sabah) is `REGIONS` in `e3_bases/run.py`.
- Experiment 4 draws `random.Random(seed).sample(pool, 12)` for seeds 0-9 from the Peninsular towns (`region` column of the CSV). It runs `F_full` first, then `F_tight`; for each sample `dp`, `nn`, `a_heap`, `b`, `b_on_a`, with `b_on_a` seeded by that sample's `a_heap` route at the same `F`. Gap = heuristic population / optimal population.

## Results

Population thresholds 100,000 / 50,000 / 15,000 / 0 give 86 / 148 / 358 / 745 towns (the 83 / 144 / 355 of earlier notes came from an older cleaning). All at `F = 21,100 kg`, Perak base, except experiment 4.

**Experiment 1** (score evals; mismatches are heap picks that differ from the re-scan):

| Towns | Heap evals | Scan evals | Mismatches |
|---|---|---|---|
| 86 | 172 | 3,725 | 72 of 81 |
| 148 | 296 | 9,751 | 91 of 98 |
| 358 | 716 | 30,591 | 93 of 98 |
| 745 | 1,490 | 68,904 | 93 of 98 |

**Experiment 2** (best of 3, seconds):

| Towns | NN | A heap | A scan | B |
|---|---|---|---|---|
| 86 | 0.004 | 0.01 | 0.20 | 1.2 |
| 148 | 0.006 | 0.013 | 0.49 | 11.3 |
| 358 | 0.019 | 0.041 | 1.97 | 33.6 |
| 745 | 0.074 | 0.142 | 4.20 | 94.1 |

The full run takes about 8.5 minutes, almost all of it B on 358 and 745 towns timed 3 times.

**Experiment 3** (population, millions; the full run takes about 8.5 minutes, mostly B at 30-115 s per base):

| Base | NN | A | B | B on A |
|---|---|---|---|---|
| perak | 3.31 | 25.38 | 27.58 | 27.10 |
| klia | 4.60 | 24.02 | 27.35 | 27.02 |
| sarawak | 3.94 | 24.97 | 4.41 | 27.28 |
| kuching | 3.78 | 25.05 | 4.41 | 27.51 |
| sabah | 3.97 | 22.58 | 4.41 | 27.04 |
| kota_kinabalu | 3.97 | 23.34 | 4.41 | 27.13 |

From the East Malaysian bases, B started from the NN route stays at 4.41 M, while B on A reaches 27 M.

**Experiment 4** (gap to the DP, average / worst over the 10 samples):

| `F` | Value | DP towns per sample | Coverage | NN | A | B | B on A |
|---|---|---|---|---|---|---|---|
| `F_full` | 5,640 kg | 12 in 8 samples, 11 in 2 | 98.3% | 0.963 / 0.656 | 0.998 / 0.995 | 0.999 / 0.996 | 0.999 / 0.996 |
| `F_tight` | 4,890 kg | 7-11 (96 of 120) | 80.0% | 0.742 / 0.236 | 0.997 / 0.970 | 0.916 / 0.497 | 0.997 / 0.970 |

`F_tight` is 4,890 kg, not the 4,900 kg of the planning estimate: `0.8 * 12` is `9.600000000000001` in floating point, so `coverage_F` compares the town totals with a `1e-9` tolerance. The plot writes the average and worst gap under each algorithm in each panel.

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
