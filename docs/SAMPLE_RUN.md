# Sample run

## CLI (active `data/` after iNaturalist refresh)

```text
$ python climate_modeler.py --temp 60
Don Edwards SF Bay NWR Climate Modeler (toy heuristic)
Temperature: 60 °F (baseline 60 °F) → base changeVal=0
Data dir: .../data

Birds: Amount ≈ 186 · avg Danger ≈ 3.51 · max 52
Mammals: Amount ≈ 20 · avg ≈ 3.65
Amphibians/Reptiles: Amount ≈ 7 · avg ≈ 0.71
Fish: Amount ≈ 17 · avg ≈ 8.59
Species with Danger Level ≥ 100: 0
```

## Bundled EcoData fallback

```text
$ python refresh_data.py --bundled-only
$ python climate_modeler.py --temp 60
# Birds ≈ 269, Mammals ≈ 27, A/R ≈ 12, Fish ≈ 56
```

## Cooler scenario (45 °F)

`changeVal=25`; search “pelican” on the dashboard at 45 °F shows American White Pelican Danger 76 (carried State SSC + toy delta).

See also [DASHBOARD.md](DASHBOARD.md).
