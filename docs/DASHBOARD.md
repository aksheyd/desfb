# Dashboard walkthrough

## Launch

```bash
source .venv/bin/activate
python dashboard.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

## What you should see

1. **Summary cards** — species counts per taxa, average Danger Level, and count with Danger ≥ 100 at the current temperature.
2. **Temperature slider (0–99 °F)** — release the slider to re-score live (toy heuristic; baseline 60 °F).
3. **Bar chart** — average Danger by taxa; **histogram** — Danger distribution for the active table filter.
4. **Taxa tabs + search** — scroll the full birds / mammals / herps / fish tables; click column headers to sort.
5. **Refresh data** — POST `/api/refresh` runs `refresh_data.py` logic (iNaturalist live pull, bundled fallback on failure). Status text and `refresh_meta` JSON update at the bottom.
6. **Restore bundled** — force-copy `data/bundled/` into `data/` without hitting the network.

## Screenshot stand-in (text)

After a successful iNaturalist refresh (example counts from a live pull):

```
Cards: Birds ~186 · Mammals ~20 · Amphibians/Reptiles ~7 · Fish ~17
Temp 60 °F → changeVal 0; Temp 45 °F → changeVal 25 (averages rise)
Table: scrollable; search “pelican” filters Common/Scientific Name
Refresh status: Refresh OK (inaturalist). …
```

If the network is blocked, Refresh still succeeds via `bundled_fallback` and restores the EcoData CSVs (~269 birds, ~27 mammals, ~12 herps, ~56 fish).
