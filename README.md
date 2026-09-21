# Don Edwards San Francisco Bay Wildlife Refuge Climate Modeler

Michigan EcoData project by Akshey Deokule. Loads species lists for
[Don Edwards SF Bay NWR](https://www.fws.gov/refuge/don-edwards-san-francisco-bay)
and assigns each species a **Danger Level** from a simple temperature-delta
heuristic plus listing/occurrence rules. When Danger Level reaches 100, the
scenario treats that species as "extinct."

**This is a toy heuristic, not a scientific climate or extinction model.**

## Data sources

| Layer | What it is |
|-------|------------|
| **Default live refresh** | USFWS ServCat **2008 bird checklist PDF** ([ServCat DownloadFile/800](https://ecos.fws.gov/ServCat/DownloadFile/800?Reference=721)) parsed with `pdftotext -bbox`, plus mammals / amphibians-reptiles / fish from `data/bundled/` (EcoData-era USFWS-derived inventories). |
| `data/official/SFB_2008_BirdList.pdf` | Cached ServCat PDF (downloaded by `refresh_data.py`). |
| `data/bundled/*.csv` | Offline EcoData-era refuge tables. Used for non-bird taxa and as full offline fallback. |
| `data/*.csv` (active) | Working tables used by the CLI and dashboard. |
| Optional `--inat` | [iNaturalist](https://www.inaturalist.org/places/50136) verifiable observation species counts for place_id `50136`. Observation-based — **not** a complete USFWS inventory. |
| Plants (optional, unscored) | `Plant_List.pdf` → `data/PlantSheet.csv` when present. Not scored by `climate_modeler.py`. |

### Why not the IRIS Species API?

The USFWS IRIS NWRSpecies API previously documented for refuge downloads:

`https://iris.fws.gov/APPS/PubData/NWRSpecies/SpeciesAPI`

returns **HTTP 404** as of 2026 (retired). This project does **not** call it.
The default path uses the ServCat bird checklist PDF instead.

Optional env vars:

- `DATA_DIR` — override active CSV directory (default `data/`)
- `INATURALIST_PLACE_ID` — override place id for `--inat` (default `50136`)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Default: download/parse USFWS ServCat birds + bundled other taxa
python refresh_data.py
python climate_modeler.py --temp 60

# Offline restore of bundled EcoData tables
python refresh_data.py --bundled-only

# Optional observation-based refresh
python refresh_data.py --inat

# Explore dashboard (scrollable tables, temp slider, refresh controls)
python dashboard.py
# open http://127.0.0.1:5050
```

### How refresh works

1. **USFWS (default):** download ServCat PDF → `usfws_parse.py` extracts common
   names, abundance codes (`a/c/u/o/r`), nesting (`*`), and accidentals → write
   `data/BirdSheet.csv`. Scientific Name / Federal / State / Classification are
   merged from bundled EcoData rows by common-name match. Mammals, herps, and
   fish are copied from `data/bundled/`.
2. **`--bundled-only`:** copy all four taxon sheets from `data/bundled/`.
3. **`--inat`:** pull iNaturalist species counts (optional; falls back to bundled
   on network failure).

`data/refresh_meta.json` records mode, counts, source URLs, and the IRIS 404 note.

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
- `refresh_data.py` — pull/update CSVs (USFWS default)
- `usfws_parse.py` — ServCat bird PDF (+ optional plant PDF) parser
- `dashboard.py` — local Flask explore UI
- `data/bundled/` — offline EcoData / USFWS-derived sample
- `data/official/` — downloaded ServCat PDF cache
- Optional C++ menu (`make`) — thin shell-out only; no Boost

## Known limitations

- Toy Danger Level curve; mainly reacts when temperature **falls below** 60 °F.
- Bird scientific names / listing codes depend on common-name matches against
  bundled EcoData sheets (AOU/name drift may leave gaps).
- iNaturalist refresh is observation-biased; prefer the USFWS default for an
  inventory-style bird list.
- Flora may be exported to `PlantSheet.csv` but is **not** scored.
- `pyqt_test.py` is unused.

Sample CLI capture: [docs/SAMPLE_RUN.md](docs/SAMPLE_RUN.md).
Dashboard walkthrough: [docs/DASHBOARD.md](docs/DASHBOARD.md).
