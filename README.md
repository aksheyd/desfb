# Don Edwards San Francisco Bay Wildlife Refuge Climate Modeler

Michigan EcoData project by Akshey Deokule. Loads species lists for
[Don Edwards SF Bay NWR](https://www.fws.gov/refuge/don-edwards-san-francisco-bay)
and assigns each species a **Danger Level** from a simple temperature-delta
heuristic plus listing/occurrence rules. When Danger Level reaches 100, the
scenario treats that species as “extinct.”

**This is a toy heuristic, not a scientific climate or extinction model.**

## Data sources

| Layer | What it is |
|-------|------------|
| `data/bundled/*.csv` | EcoData-era refuge species tables (originally transcribed from USFWS Don Edwards lists / refuge materials). Kept as the offline fallback. Historical copies also remain at the repo root. |
| `data/*.csv` (active) | Working tables used by the CLI and dashboard. |
| Live refresh | [iNaturalist](https://www.inaturalist.org/places/50136) verifiable **observation species counts** for place_id `50136` (Alviso-area Don Edwards polygon). No API key. Federal/State/Classification are carried over from prior/bundled rows when scientific names match. |

The USFWS NWRSpecies API (`iris.fws.gov/.../SpeciesAPI`) previously documented for refuge downloads returned HTTP 404 from this environment (Sept 2026), so the default live path is iNaturalist. Observation-based lists are **not** a complete refuge inventory (fewer fish/herps than the bundled USFWS-derived tables).

Optional env vars:

- `DATA_DIR` — override active CSV directory (default `data/`)
- `INATURALIST_PLACE_ID` — override place id (default `50136`)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Score bundled/active data
python climate_modeler.py --temp 60

# Refresh active CSVs (iNaturalist → fallback to data/bundled/)
python refresh_data.py
python refresh_data.py --bundled-only   # offline restore

# Explore dashboard (scrollable tables, temp slider, refresh button)
python dashboard.py
# open http://127.0.0.1:5050
```

## Inputs / outputs

| Input | Description |
|-------|-------------|
| `data/BirdSheet.csv` (etc.) | Active species tables |
| `--temp` / `-t` | Hypothetical °F (baseline **60**) |

| Output | Description |
|--------|-------------|
| stdout / dashboard | Per-taxa summaries + Danger Levels |
| `data/refresh_meta.json` | Last refresh mode, counts, timestamp |

## Layout

- `climate_modeler.py` — scoring CLI
- `refresh_data.py` — pull/update CSVs
- `dashboard.py` — local Flask explore UI
- `data/bundled/` — offline sample
- Optional C++ menu (`make main.exe`) — thin shell-out only; no Boost

## Known limitations

- Toy Danger Level curve; mainly reacts when temperature **falls below** 60 °F.
- iNaturalist refresh is observation-biased; use **Restore bundled** for the fuller EcoData/USFWS-derived lists.
- Flora not scored. `pyqt_test.py` is unused.

Sample CLI capture: [docs/SAMPLE_RUN.md](docs/SAMPLE_RUN.md).  
Dashboard walkthrough: [docs/DASHBOARD.md](docs/DASHBOARD.md).
