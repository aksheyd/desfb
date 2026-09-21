# desfb — Don Edwards SF Bay NWR companion

Small visit-oriented site and data sync for
[Don Edwards San Francisco Bay National Wildlife Refuge](https://www.fws.gov/refuge/don-edwards-san-francisco-bay)
(the nation’s first urban NWR, South Bay tidal marsh & salt ponds).

**Live site:** [https://aksheyd.github.io/desfb/](https://aksheyd.github.io/desfb/)

Built by Akshey Deokule (Michigan EcoData roots). The repo is public so GitHub Pages can serve the site.

## What’s on the site

1. **About the park** — short visitor intro + FWS link  
2. **Today strip** — Alviso tides (NOAA CO-OPS `9414551`) + NWS forecast near `37.46, -121.97`  
3. **Seasonal highlights** — ~15–20 birds from the USFWS checklist by rough season  
4. **Featured species** — Ridgway’s / Clapper rail, salt-marsh harvest mouse, western snowy plover  
5. **How to visit** — Alviso pointer + official refuge page  

## Layout

```
site/                      # static Pages app
  index.html
  styles.css
  app.js                   # fetches data/public/*.json
data/public/               # committed JSON consumed by the site
  today.json
  season.json
  featured.json
  meta.json
scripts/sync_today.py      # CO-OPS + NWS + season/featured builders
.github/workflows/
  pages.yml                # assemble site + data/public → GitHub Pages
  sync-data.yml            # daily cron + manual dispatch
```

## Daily sync

- Workflow: `.github/workflows/sync-data.yml`
- Schedule: `0 14 * * *` (14:00 UTC) plus **workflow_dispatch**
- Writes `data/public/*.json`; commits only when content changes (`chore(data): daily public JSON sync`)
- NWS requests use User-Agent `desfb (https://github.com/aksheyd/desfb)`

Re-run manually:

```bash
gh workflow run sync-data.yml --repo aksheyd/desfb
# or locally:
python3 scripts/sync_today.py
```

## Local preview

```bash
python3 scripts/sync_today.py
mkdir -p /tmp/desfb-site/data && cp -a site/. /tmp/desfb-site/ && cp -a data/public /tmp/desfb-site/data/
python3 -m http.server 8080 --directory /tmp/desfb-site
# open http://127.0.0.1:8080/
```

## Optional: climate modeler & explore dashboard

This repo still contains the original EcoData **toy** climate / Danger Level heuristic and a local Flask explore UI. They are **not** part of the public Pages site.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python refresh_data.py          # USFWS ServCat birds + bundled taxa
python climate_modeler.py --temp 60
python dashboard.py             # http://127.0.0.1:5050
```

**This is a toy heuristic, not a scientific climate or extinction model.**

### Data sources (inventory tooling)

| Layer | What it is |
|-------|------------|
| **Default live refresh** | USFWS ServCat **2008 bird checklist PDF** ([ServCat DownloadFile/800](https://ecos.fws.gov/ServCat/DownloadFile/800?Reference=721)) parsed with `pdftotext -bbox`, plus mammals / amphibians-reptiles / fish from `data/bundled/` |
| `data/bundled/*.csv` | Offline EcoData-era refuge tables |
| `data/*.csv` (active) | Working tables used by CLI / dashboard / public JSON builders |
| Optional `--inat` | iNaturalist place `50136` (observation-based, incomplete) |

The USFWS IRIS NWRSpecies API returns **HTTP 404** as of 2026 (retired). This project does not call it.

See [docs/SAMPLE_RUN.md](docs/SAMPLE_RUN.md) and [docs/DASHBOARD.md](docs/DASHBOARD.md).
