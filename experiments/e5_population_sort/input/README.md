# Experiment 5 input

`cities_clean.csv` is the 745-town GeoNames Malaysia snapshot used by this experiment.
It was regenerated from the project's GeoNames `MY.txt` source using the cleaning steps
in `eda.ipynb`: select populated places with recorded population and coordinates,
remove historic/abandoned and duplicate-coordinate entries, then sort by population.
The source is [GeoNames](https://www.geonames.org/), downloaded from its
[Malaysia export](https://download.geonames.org/export/dump/MY.zip).

The experiment validates this snapshot against the committed Experiment 3 results:
all six Approach A routes and population totals must match before it reuses B's routes.
`out/provenance.json` records the file checksum.
