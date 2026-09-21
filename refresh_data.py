#!/usr/bin/env python3
"""Refresh Don Edwards NWR species CSVs.

Default (USFWS official inventory path):
  1. Download ServCat 2008 bird checklist PDF
  2. Parse -> data/BirdSheet.csv (scientific names merged from bundled)
  3. Copy mammals / herps / fish from data/bundled/
  4. Optionally parse Plant_List.pdf -> PlantSheet.csv (unscored)

Flags:
  --inat           Optional iNaturalist observation species counts
  --bundled-only   Offline restore of data/bundled/
  --skip-download  Reuse existing data/official PDF

The USFWS IRIS NWRSpecies API returned HTTP 404 in 2026 (retired) and is
not used: https://iris.fws.gov/APPS/PubData/NWRSpecies/SpeciesAPI
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from usfws_parse import (
    BUNDLED_DIR,
    DATA_DIR,
    LEGACY_COLUMNS,
    OFFICIAL_DIR,
    REPO_ROOT,
    build_bird_sheet,
    copy_bundled_sheet,
    parse_plant_list_pdf,
)

SERVCAT_BIRD_URL = "https://ecos.fws.gov/ServCat/DownloadFile/800?Reference=721"
BIRD_PDF_NAME = "SFB_2008_BirdList.pdf"

IRIS_API_URL = "https://iris.fws.gov/APPS/PubData/NWRSpecies/SpeciesAPI"
IRIS_NOTE = (
    "USFWS IRIS NWRSpecies API "
    f"({IRIS_API_URL}) returned HTTP 404 as of 2026 (retired) and is not used. "
    "Default refresh downloads the ServCat bird checklist PDF and uses bundled "
    "EcoData mammals/herps/fish."
)

DEFAULT_PLACE_ID = 50136
USER_AGENT = (
    "DESFB-Climate-Modeler/1.1 "
    "(+https://github.com/aksheyd/Don-Edwards-San-Fransisco-Bay-Wildlife-Refuge-Climate-Modeler; "
    "educational)"
)

SHEET_FILES = (
    "BirdSheet.csv",
    "MammalsSheet.csv",
    "AmphibianReptilesSheet.csv",
    "FishsSheet.csv",
)

INAT_GROUPS = {
    "Aves": "BirdSheet.csv",
    "Mammalia": "MammalsSheet.csv",
    "Amphibia": "AmphibianReptilesSheet.csv",
    "Reptilia": "AmphibianReptilesSheet.csv",
    "Actinopterygii": "FishsSheet.csv",
}

INAT_COLUMNS = LEGACY_COLUMNS + ["Source", "Obs Count"]


def _request_json(url: str, timeout: float = 60.0) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def download_servcat_bird_pdf(dest: Path, url: str = SERVCAT_BIRD_URL) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    if len(data) < 10_000 or data[:4] != b"%PDF":
        raise RuntimeError(
            f"ServCat download does not look like a PDF ({len(data)} bytes)."
        )
    dest.write_bytes(data)
    return dest


def fetch_inat_species_counts(place_id: int, iconic: str) -> list[dict]:
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
        time.sleep(0.35)
    return all_rows


def _clean(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none") else s


def load_prior_by_scientific(data_dir: Path) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    candidates = list(data_dir.glob("*Sheet.csv")) + list(BUNDLED_DIR.glob("*Sheet.csv"))
    for path in candidates:
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        df.columns = [str(c).lstrip("\ufeff").strip() for c in df.columns]
        for _, row in df.iterrows():
            sci = str(row.get("Scientific Name", "")).strip()
            if not sci or sci.lower() == "nan":
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


def rows_from_inat(
    results: list[dict], prior: dict[str, dict], source_label: str
) -> list[dict]:
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
        common = (
            taxon.get("preferred_common_name")
            or taxon.get("english_common_name")
            or sci
        ).strip()
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


def write_inat_sheet(path: Path, rows: list[dict]) -> None:
    df = pd.DataFrame(rows, columns=INAT_COLUMNS)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_meta(data_dir: Path, meta: dict) -> None:
    meta = dict(meta)
    meta.setdefault("iris_api", IRIS_API_URL)
    meta.setdefault("iris_status", "HTTP 404 (retired as of 2026)")
    meta.setdefault("iris_note", IRIS_NOTE)
    meta["refreshed_at"] = datetime.now(timezone.utc).isoformat()
    (data_dir / "refresh_meta.json").write_text(json.dumps(meta, indent=2) + "\n")


def restore_bundled(data_dir: Path) -> dict:
    if not BUNDLED_DIR.is_dir():
        raise FileNotFoundError(f"Missing bundled fallback directory: {BUNDLED_DIR}")
    copied = []
    counts = {}
    for name in SHEET_FILES:
        dest = copy_bundled_sheet(name, data_dir)
        copied.append(name)
        counts[name] = int(pd.read_csv(dest).shape[0])
    meta = {
        "ok": True,
        "mode": "bundled",
        "files": copied,
        "counts": counts,
        "message": "Restored EcoData-era USFWS-derived lists from data/bundled/.",
        "sources": {name: f"data/bundled/{name}" for name in copied},
    }
    write_meta(data_dir, meta)
    return meta


def refresh_from_usfws(data_dir: Path, *, skip_download: bool = False) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    OFFICIAL_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = OFFICIAL_DIR / BIRD_PDF_NAME

    if not skip_download or not pdf_path.is_file():
        print(f"Downloading ServCat bird checklist -> {pdf_path} ...")
        download_servcat_bird_pdf(pdf_path)
        print(f"  saved {pdf_path.stat().st_size} bytes")
    else:
        print(f"Using existing PDF {pdf_path}")

    print("Parsing bird checklist PDF ...")
    birds = build_bird_sheet(pdf_path)
    bird_out = data_dir / "BirdSheet.csv"
    birds.to_csv(bird_out, index=False)
    print(f"  birds: {len(birds)} -> {bird_out}")

    sources: dict = {
        "BirdSheet.csv": {
            "type": "USFWS ServCat PDF",
            "url": SERVCAT_BIRD_URL,
            "file": str(pdf_path.relative_to(REPO_ROOT)),
            "rows": int(len(birds)),
        }
    }
    counts = {"BirdSheet.csv": int(len(birds))}

    for name in ("MammalsSheet.csv", "AmphibianReptilesSheet.csv", "FishsSheet.csv"):
        dest = copy_bundled_sheet(name, data_dir)
        n = int(pd.read_csv(dest).shape[0])
        counts[name] = n
        sources[name] = {
            "type": "bundled EcoData / USFWS-derived",
            "file": f"data/bundled/{name}",
            "rows": n,
        }
        print(f"  {name}: {n} from bundled")

    plant_pdf = REPO_ROOT / "Plant_List.pdf"
    if plant_pdf.is_file():
        plants = parse_plant_list_pdf(plant_pdf)
        if plants is not None and len(plants):
            plant_out = data_dir / "PlantSheet.csv"
            plants.to_csv(plant_out, index=False)
            counts["PlantSheet.csv"] = int(len(plants))
            sources["PlantSheet.csv"] = {
                "type": "EcoData Plant_List.pdf (unscored)",
                "file": "Plant_List.pdf",
                "rows": int(len(plants)),
            }
            print(f"  plants (unscored): {len(plants)}")

    meta = {
        "ok": True,
        "mode": "usfws_official",
        "message": (
            "Birds from USFWS ServCat 2008 checklist PDF; "
            "mammals/herps/fish from bundled EcoData USFWS-derived CSVs."
        ),
        "counts": counts,
        "sources": sources,
        "files": list(counts.keys()),
    }
    write_meta(data_dir, meta)
    return meta


def refresh_from_inaturalist(place_id: int, data_dir: Path) -> dict:
    prior = load_prior_by_scientific(data_dir)
    source_label = f"iNaturalist species_counts place_id={place_id}"
    by_file: dict[str, list[dict]] = {name: [] for name in SHEET_FILES}
    group_stats = {}
    for iconic, filename in INAT_GROUPS.items():
        results = fetch_inat_species_counts(place_id, iconic)
        rows = rows_from_inat(results, prior, source_label)
        by_file[filename].extend(rows)
        group_stats[iconic] = {"raw_taxa": len(results), "species_rows": len(rows)}
        print(f"  {iconic}: {len(rows)} species rows from {len(results)} taxa")

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
        write_inat_sheet(data_dir / filename, rows)

    meta = {
        "ok": True,
        "mode": "inaturalist",
        "place_id": place_id,
        "place_url": f"https://www.inaturalist.org/places/{place_id}",
        "api": "https://api.inaturalist.org/v1/observations/species_counts",
        "group_stats": group_stats,
        "counts": {fn: len(rows) for fn, rows in by_file.items()},
        "message": (
            "Optional observation-based iNaturalist list — not a complete "
            "USFWS inventory."
        ),
        "sources": {
            fn: {"type": "iNaturalist", "place_id": place_id, "rows": len(rows)}
            for fn, rows in by_file.items()
        },
        "files": list(by_file.keys()),
    }
    write_meta(data_dir, meta)
    return meta


def refresh(
    prefer_live: bool = True,
    place_id: int | None = None,
    data_dir: Path | None = None,
    *,
    use_inat: bool = False,
    bundled_only: bool = False,
    skip_download: bool = False,
) -> dict:
    """Entry point used by CLI and dashboard.

    Default live path is USFWS ServCat (not iNaturalist). Pass use_inat=True
    or CLI --inat for the optional observation-based path. prefer_live=False
    restores bundled CSVs (dashboard "Restore bundled").
    """
    data_dir = data_dir or DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    place_id = place_id or int(
        os.environ.get("INATURALIST_PLACE_ID", DEFAULT_PLACE_ID)
    )

    if bundled_only or not prefer_live:
        return restore_bundled(data_dir)

    if use_inat:
        try:
            print(f"Fetching iNaturalist species counts for place_id={place_id} ...")
            return refresh_from_inaturalist(place_id, data_dir)
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            RuntimeError,
            json.JSONDecodeError,
        ) as exc:
            print(
                f"iNaturalist refresh failed ({exc!r}); falling back to bundled.",
                file=sys.stderr,
            )
            meta = restore_bundled(data_dir)
            meta["live_error"] = str(exc)
            write_meta(data_dir, meta)
            return meta

    try:
        return refresh_from_usfws(data_dir, skip_download=skip_download)
    except Exception as exc:
        print(
            f"USFWS official refresh failed ({exc!r}); falling back to bundled.",
            file=sys.stderr,
        )
        meta = restore_bundled(data_dir)
        meta["live_error"] = str(exc)
        write_meta(data_dir, meta)
        return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh Don Edwards species CSVs. "
            "Default: USFWS ServCat bird PDF + bundled mammals/herps/fish."
        )
    )
    parser.add_argument(
        "--bundled-only",
        action="store_true",
        help="Skip network; restore data/bundled/ into data/.",
    )
    parser.add_argument(
        "--inat",
        action="store_true",
        help="Use iNaturalist observation species counts instead of USFWS default.",
    )
    parser.add_argument(
        "--place-id",
        type=int,
        default=None,
        help=f"iNaturalist place id (default: {DEFAULT_PLACE_ID}).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Output directory for active CSVs (default: data/).",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Reuse existing data/official bird PDF if present.",
    )
    args = parser.parse_args(argv)

    meta = refresh(
        prefer_live=not args.bundled_only,
        place_id=args.place_id,
        data_dir=args.data_dir,
        use_inat=args.inat,
        bundled_only=args.bundled_only,
        skip_download=args.skip_download,
    )
    print(json.dumps(meta, indent=2))
    return 0 if meta.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
