# desfb — Don Edwards SF Bay NWR visitor companion

Static [GitHub Pages](https://aksheyd.github.io/desfb/) site for
[Don Edwards San Francisco Bay National Wildlife Refuge](https://www.fws.gov/refuge/don-edwards-san-francisco-bay)
(South Bay tidal marsh & salt ponds). Unofficial visit companion — not an FWS product.

**Live:** [https://aksheyd.github.io/desfb/](https://aksheyd.github.io/desfb/)

## What the site shows

1. **Today** — Alviso tides (NOAA CO-OPS `9414551`) + NWS forecast near `37.46, −121.97`
2. **About the park** — short visitor intro + official FWS link
3. **Seasonal highlights** — birds from the USFWS 2008 checklist by rough season
4. **Featured species** — Ridgway’s rail, salt-marsh harvest mouse, western snowy plover
5. **How to visit** — Alviso pointer + refuge page

## Layout

```
site/                 # static Pages UI (index.html, app.js, styles.css, logo.jpg)
data/public/          # committed JSON the site loads (relative data/public/*.json)
data/source/          # slim bird/mammal CSVs used to rebuild season & featured
scripts/sync_today.py # stdlib-only: CO-OPS + NWS + season/featured builders
.github/workflows/
  pages.yml           # assemble site + data/public → GitHub Pages
  sync-data.yml       # daily cron + workflow_dispatch
```

No pip packages: `sync_today.py` uses the Python 3 standard library only.

## Daily sync

- Workflow: `.github/workflows/sync-data.yml`
- Schedule: `0 14 * * *` (14:00 UTC ≈ 07:00 PT) plus **workflow_dispatch**
- Writes `data/public/*.json`; commits only when content changes

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
