# Dashboard

```bash
python dashboard.py
# http://127.0.0.1:5050
```

## Controls

- **Temperature slider** — re-scores all taxa with the toy Danger Level heuristic.
- **Refresh (USFWS)** — downloads the ServCat 2008 bird checklist PDF, parses it,
  and restores mammals/herps/fish from `data/bundled/`.
- **Refresh (iNat)** — optional iNaturalist observation species counts.
- **Restore bundled** — offline copy of `data/bundled/` into `data/`.
- **Source badge** — shows the active refresh mode (`usfws_official`,
  `inaturalist`, or `bundled`).

## API

| Endpoint | Notes |
|----------|-------|
| `GET /api/summary?temp=` | Group stats + `refresh_meta` |
| `GET /api/taxa/<key>?temp=&q=` | Scrollable/searchable rows |
| `POST /api/refresh` | Body: `{ "bundled_only": false, "use_inat": false }` |
| `GET /api/health` | CSV presence + meta |

Danger Level remains a **toy** EcoData heuristic.
