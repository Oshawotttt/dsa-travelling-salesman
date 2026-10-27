"""Route maps for an experiment output folder (runs.csv and routes.csv), drawn from the CSVs
alone, so nothing is re-solved.

Run from the repo root: python -m experiments.maps experiments/e3_bases/out [more folders]

One map per instance: runs sharing (base, n_towns, sample, F). Each writes
<folder>/maps/<base>_n<n_towns>[_s<sample>]_F<F>.html with one layer per run. The small grey
circles are the towns any route on that map visits; towns no route visits are not in the CSVs.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from airdrop.model import Base, Stop
from airdrop.plot import plot_stops_html
from experiments.common import read_routes, read_runs

LABELS = {"nn": "NN", "a_heap": "A", "a_scan": "A scan", "b": "B", "b_on_a": "B on A", "dp": "DP"}


def map_name(base: str, n_towns: int, sample: int | None, F: float) -> str:
    sample_part = "" if sample is None else f"_s{sample}"
    return f"{base}_n{n_towns}{sample_part}_F{F:g}.html"


def write_maps(out_dir: Path, maps_dir: Path | None = None) -> list[Path]:
    """Write one HTML map per instance in out_dir's runs.csv; return their paths in run order."""
    out_dir = Path(out_dir)
    maps_dir = out_dir / "maps" if maps_dir is None else Path(maps_dir)
    stops = read_routes(out_dir / "routes.csv")
    groups: dict[tuple, list[dict]] = {}
    for r in read_runs(out_dir / "runs.csv"):
        groups.setdefault((r["base"], r["n_towns"], r["sample"], r["F"]), []).append(r)
    paths = []
    for (base, n_towns, sample, F), runs in groups.items():
        routes: dict[str, list[Stop]] = {LABELS.get(r["algorithm"], r["algorithm"]): stops[r["run_id"]]
                                         for r in runs}
        visited = {s.geonameid: s for route in routes.values() for s in route[1:-1]}
        sample_part = "" if sample is None else f", sample {sample}"
        title = f"{runs[0]['experiment']}: {base}, {n_towns} towns{sample_part}, F {F:,.0f} kg"
        takeoff = next(iter(routes.values()))[0]
        home = Base(takeoff.geonameid, takeoff.name, takeoff.lat, takeoff.lon)
        paths.append(plot_stops_html(home, list(visited.values()), routes,
                                     maps_dir / map_name(base, n_towns, sample, F), title=title))
    return paths


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m experiments.maps",
                                     description="Write HTML route maps from experiment output folders.")
    parser.add_argument("folders", nargs="+", type=Path,
                        help="folders holding runs.csv and routes.csv, e.g. experiments/e3_bases/out")
    parser.add_argument("--out", type=Path,
                        help="where to write the maps (default: <folder>/maps); one folder only")
    args = parser.parse_args(argv)
    if args.out is not None and len(args.folders) > 1:
        parser.error("--out takes one folder only")
    for folder in args.folders:
        for name in ("runs.csv", "routes.csv"):
            if not (folder / name).is_file():
                parser.error(f"{folder / name} not found")
        for path in write_maps(folder, args.out):
            print(path)


if __name__ == "__main__":
    main()
