#!/usr/bin/env python3
"""Refresh Don Edwards NWR species CSVs.

Primary source (no API key): iNaturalist verifiable observation species counts
for place_id 50136 (Don Edwards SF Bay NWR, Alviso unit polygon).

Fallback: restore EcoData-era USFWS-derived lists from data/bundled/.

Optional: set INATURALIST_PLACE_ID to override the place id.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"
BUNDLED_DIR = DATA_DIR / "bundled"
DEFAULT_PLACE_ID = 50136
USER_AGENT = "DESFB-Climate-Modeler/1.0 (+https://github.com/aksheyd/Don-Edwards-San-Fransisco-Bay-Wildlife-Refuge-Climate-Modeler; educational)"

# Map iNaturalist iconic taxa → our sheet files. Herps are merged.
INAT_GROUPS = {
    "Aves": "BirdSheet.csv",
    "Mammalia": "MammalsSheet.csv",
    "Amphibia": "AmphibianReptilesSheet.csv",
    "Reptilia": "AmphibianReptilesSheet.csv",
    "Actinopterygii": "FishsSheet.csv",
}

COLUMNS = [
    "Common Name",
    "Scientific Name",
    "Occurrence",
    "Classification",
    "Federal",
    "State",
    "Source",
    "Obs Count",
]


def _request_json(url: str, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def fetch_inat_species_counts(place_id: int, iconic: str) -> list[dict]:
    """Return species_counts results for one iconic taxon (paginated)."""
    all_rows: list[dict] = []
    page = 1
    while page <= 25:
        q = urllib.parse.urlencode(
            {
                "place_id": place_id,
                "iconic_taxa": iconic,
                "per_page": 200,
                "page": page,
                "verifiable": "true",
            }
        )
        url = f"https://api.inaturalist.org/v1/observations/species_counts?{q}"
        data = _request_json(url)
        results = data.get("results") or []
        all_rows.extend(results)
        total = int(data.get("total_results") or 0)
        if len(all_rows) >= total or not results:
            break
        page += 1
        time.sleep(0.35)  # be polite
    return all_rows


def load_prior_lookup(data_dir: Path) -> dict[str, dict]:
    """Scientific-name → prior listing fields from existing/bundled CSVs."""
    lookup: dict[str, dict] = {}
    candidates = list(data_dir.glob("*Sheet.csv")) + list(BUNDLED_DIR.glob("*Sheet.csv"))
    for path in candidates:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        for _, row in df.iterrows():
            sci = str(row.get("Scientific Name", "")).strip()
            if not sci or sci == "nan":
                continue
            key = sci.casefold()
            if key in lookup:
                continue
            lookup[key] = {
                "Classification": _clean(row.get("Classification")),
                "Federal": _clean(row.get("Federal")),
                "State": _clean(row.get("State")),
                "Occurrence": _clean(row.get("Occurrence")),
            }
    return lookup


def _clean(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none") else s


def rows_from_inat(results: list[dict], prior: dict[str, dict], source_label: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for item in results:
        taxon = item.get("taxon") or {}
        if taxon.get("rank") not in ("species", "subspecies", "variety"):
            continue
        sci = (taxon.get("name") or "").strip()
        if not sci:
            continue
        key = sci.casefold()
        if key in seen:
            continue
        seen.add(key)
        common = (taxon.get("preferred_common_name") or taxon.get("english_common_name") or sci).strip()
        prior_row = prior.get(key, {})
        obs = int(item.get("count") or 0)
        occurrence = prior_row.get("Occurrence") or f"iNaturalist observations: {obs}"
        out.append(
            {
                "Common Name": common,
                "Scientific Name": sci,
                "Occurrence": occurrence,
                "Classification": prior_row.get("Classification", ""),
                "Federal": prior_row.get("Federal", ""),
                "State": prior_row.get("State", ""),
                "Source": source_label,
                "Obs Count": obs,
            }
        )
    out.sort(key=lambda r: (-int(r["Obs Count"]), r["Common Name"].casefold()))
    return out


def write_sheet(path: Path, rows: list[dict]) -> None:
    df = pd.DataFrame(rows, columns=COLUMNS)
    # Keep legacy column order first for climate_modeler compatibility; extra cols OK
    legacy = ["Common Name", "Scientific Name", "Occurrence", "Classification", "Federal", "State"]
    extras = [c for c in COLUMNS if c not in legacy]
    df = df[legacy + extras]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def restore_bundled(data_dir: Path) -> dict:
    if not BUNDLED_DIR.is_dir():
        raise FileNotFoundError(f"Missing bundled fallback directory: {BUNDLED_DIR}")
    copied = []
    for name in (
        "BirdSheet.csv",
        "MammalsSheet.csv",
        "AmphibianReptilesSheet.csv",
        "FishsSheet.csv",
    ):
        src = BUNDLED_DIR / name
        if not src.is_file():
            raise FileNotFoundError(f"Missing bundled file: {src}")
        dest = data_dir / name
        shutil.copy2(src, dest)
        copied.append(name)
    meta = {
        "ok": True,
        "mode": "bundled_fallback",
        "files": copied,
        "message": "Restored EcoData-era USFWS-derived lists from data/bundled/.",
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
    (data_dir / "refresh_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def refresh_from_inaturalist(place_id: int, data_dir: Path) -> dict:
    prior = load_prior_lookup(data_dir)
    source_label = f"iNaturalist species_counts place_id={place_id}"
    by_file: dict[str, list[dict]] = {
        "BirdSheet.csv": [],
        "MammalsSheet.csv": [],
        "AmphibianReptilesSheet.csv": [],
        "FishsSheet.csv": [],
    }
    group_stats = {}
    for iconic, filename in INAT_GROUPS.items():
        results = fetch_inat_species_counts(place_id, iconic)
        rows = rows_from_inat(results, prior, source_label)
        by_file[filename].extend(rows)
        group_stats[iconic] = {"raw_taxa": len(results), "species_rows": len(rows)}
        print(f"  {iconic}: {len(rows)} species rows from {len(results)} taxa")

    # Deduplicate herps if Amphibia+Reptilia overlap (unlikely)
    herp = by_file["AmphibianReptilesSheet.csv"]
    seen: set[str] = set()
    deduped = []
    for row in herp:
        k = row["Scientific Name"].casefold()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(row)
    by_file["AmphibianReptilesSheet.csv"] = deduped

    for filename, rows in by_file.items():
        if not rows:
            raise RuntimeError(f"No rows produced for {filename}; aborting refresh.")
        write_sheet(data_dir / filename, rows)

    meta = {
        "ok": True,
        "mode": "inaturalist",
        "place_id": place_id,
        "place_url": f"https://www.inaturalist.org/places/{place_id}",
        "api": "https://api.inaturalist.org/v1/observations/species_counts",
        "group_stats": group_stats,
        "counts": {fn: len(rows) for fn, rows in by_file.items()},
        "note": (
            "Live list is observation-based (iNaturalist), not a complete USFWS "
            "inventory. Federal/State/Classification carried over from prior CSVs "
            "when scientific names match. Danger scoring remains a toy heuristic."
        ),
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
    (data_dir / "refresh_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def refresh(prefer_live: bool = True, place_id: int | None = None, data_dir: Path | None = None) -> dict:
    data_dir = data_dir or DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    place_id = place_id or int(
        __import__("os").environ.get("INATURALIST_PLACE_ID", DEFAULT_PLACE_ID)
    )

    if prefer_live:
        try:
            print(f"Fetching iNaturalist species counts for place_id={place_id} …")
            return refresh_from_inaturalist(place_id, data_dir)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"Live refresh failed ({exc!r}); falling back to bundled CSVs.", file=sys.stderr)
            meta = restore_bundled(data_dir)
            meta["live_error"] = str(exc)
            (data_dir / "refresh_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
            return meta
    return restore_bundled(data_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh Don Edwards species CSVs.")
    parser.add_argument(
        "--bundled-only",
        action="store_true",
        help="Skip network; restore data/bundled/ into data/.",
    )
    parser.add_argument(
        "--place-id",
        type=int,
        default=None,
        help=f"iNaturalist place id (default: {DEFAULT_PLACE_ID} or $INATURALIST_PLACE_ID).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Output directory for active CSVs (default: data/).",
    )
    args = parser.parse_args(argv)
    meta = refresh(
        prefer_live=not args.bundled_only,
        place_id=args.place_id,
        data_dir=args.data_dir,
    )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
