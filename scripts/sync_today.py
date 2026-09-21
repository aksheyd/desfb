#!/usr/bin/env python3
"""Fetch Alviso tides + NWS forecast; refresh public JSON for the desfb site."""

from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"
SOURCE = ROOT / "data" / "source"

STATION = "9414551"  # Alviso Slough / Coyote Creek area (CO-OPS)
LAT, LON = 37.46, -121.97
UA = "desfb (https://github.com/aksheyd/desfb)"
PT = ZoneInfo("America/Los_Angeles")

# USFWS 2008 checklist columns: Spring Summer Fall Winter
SEASON_KEYS = ("spring", "summer", "fall", "winter")
CODE_RANK = {"a": 5, "c": 4, "u": 3, "o": 2, "r": 1}

FEATURED_SPECS = [
    {
        "id": "ridgways-rail",
        "common_name": "Ridgway's Rail (California Clapper Rail)",
        "match_names": ("Clapper Rail", "California Clapper rail", "Ridgway"),
        "sheet": "BirdSheet.csv",
        "blurb": (
            "A secretive marsh bird that calls from pickleweed and cordgrass. "
            "Once called California Clapper Rail; still one of the refuge's "
            "signature endangered shorebirds."
        ),
    },
    {
        "id": "salt-marsh-harvest-mouse",
        "common_name": "Salt Marsh Harvest Mouse",
        "match_names": ("Salt marsh harvest mouse", "salt marsh harvest mouse"),
        "sheet": "MammalsSheet.csv",
        "blurb": (
            "A tiny endemic rodent that lives only in Bay Area tidal marshes. "
            "Don Edwards protects critical pickleweed habitat for this "
            "federally endangered species."
        ),
    },
    {
        "id": "western-snowy-plover",
        "common_name": "Western Snowy Plover",
        "match_names": ("Snowy Plover", "Western Snowy Plover"),
        "sheet": "BirdSheet.csv",
        "blurb": (
            "A small shorebird that nests on salt-pond levees and open flats. "
            "Look for them quietly running along pale shorelines — please keep "
            "distance from nesting areas."
        ),
    },
]


def _get(url: str, accept: str = "application/json") -> dict | list:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": accept},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def current_season(now: datetime | None = None) -> str:
    now = now or datetime.now(PT)
    m = now.month
    if m in (3, 4, 5):
        return "spring"
    if m in (6, 7, 8):
        return "summer"
    if m in (9, 10, 11):
        return "fall"
    return "winter"


def fetch_tides() -> dict:
    url = (
        "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
        f"?date=today&station={STATION}&product=predictions"
        "&datum=MLLW&time_zone=lst_ldt&interval=hilo"
        "&units=english&format=json"
    )
    raw = _get(url)
    preds = raw.get("predictions") or []
    tides = []
    for p in preds:
        tides.append(
            {
                "time": p.get("t"),
                "height_ft": round(float(p["v"]), 2) if p.get("v") is not None else None,
                "type": "high" if p.get("type") == "H" else "low",
            }
        )
    return {
        "station_id": STATION,
        "station_name": "Alviso (CO-OPS 9414551)",
        "datum": "MLLW",
        "units": "ft",
        "predictions": tides,
        "source": "https://api.tidesandcurrents.noaa.gov/",
    }


def fetch_forecast() -> dict:
    points = _get(
        f"https://api.weather.gov/points/{LAT},{LON}",
        accept="application/geo+json",
    )
    props = points.get("properties") or {}
    forecast_url = props.get("forecast")
    if not forecast_url:
        raise RuntimeError("NWS points response missing forecast URL")
    forecast = _get(forecast_url, accept="application/geo+json")
    periods_in = (forecast.get("properties") or {}).get("periods") or []
    periods = []
    for p in periods_in[:6]:
        periods.append(
            {
                "name": p.get("name"),
                "startTime": p.get("startTime"),
                "isDaytime": p.get("isDaytime"),
                "temperature": p.get("temperature"),
                "temperatureUnit": p.get("temperatureUnit"),
                "windSpeed": p.get("windSpeed"),
                "windDirection": p.get("windDirection"),
                "shortForecast": p.get("shortForecast"),
                "detailedForecast": p.get("detailedForecast"),
            }
        )
    loc = ((props.get("relativeLocation") or {}).get("properties")) or {}
    return {
        "lat": LAT,
        "lon": LON,
        "office": props.get("cwa"),
        "city": loc.get("city"),
        "state": loc.get("state"),
        "periods": periods,
        "source": "https://www.weather.gov/",
    }


def _read_csv(name: str) -> list[dict]:
    path = SOURCE / name
    if not path.is_file():
        raise FileNotFoundError(f"Missing species source CSV: {path}")
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {
                (k or "").lstrip("\ufeff").strip(): (v or "").strip()
                for k, v in row.items()
                if k is not None
            }
            # Mammals sheet sometimes wraps scientific name across lines in field
            if "Scientific Name" in cleaned:
                cleaned["Scientific Name"] = re.sub(
                    r"\s+", " ", cleaned["Scientific Name"]
                ).strip()
            if "Common Name" in cleaned:
                cleaned["Common Name"] = re.sub(
                    r"\s+", " ", cleaned["Common Name"]
                ).strip()
            rows.append(cleaned)
    return rows


def _season_code(codes: str, season: str) -> str | None:
    parts = codes.split()
    if not parts:
        return None
    idx = SEASON_KEYS.index(season)
    if len(parts) == 4:
        return parts[idx].lower()
    if len(parts) == 3:
        # Often Sp Fa Wi (no summer) or Sp Su Fa — treat as Sp Su/Fa Wi stretch
        # Prefer mapping: 0=spring, 1=fall-ish mid, 2=winter when summer missing
        mapping_3 = {
            "spring": 0,
            "summer": 1,
            "fall": 1,
            "winter": 2,
        }
        return parts[mapping_3[season]].lower()
    if len(parts) == 2:
        mapping_2 = {"spring": 0, "summer": 0, "fall": 1, "winter": 1}
        return parts[mapping_2[season]].lower()
    if len(parts) == 1:
        return parts[0].lower()
    return None


def build_season(season: str | None = None) -> dict:
    season = season or current_season()
    birds = _read_csv("BirdSheet.csv")
    scored: list[tuple[int, dict]] = []
    for row in birds:
        name = row.get("Common Name") or ""
        if not name:
            continue
        code = _season_code(row.get("Abundance Codes") or "", season)
        if not code or code not in CODE_RANK:
            continue
        rank = CODE_RANK[code]
        if rank < 3:  # skip rare/occasional for highlights
            continue
        scored.append(
            (
                rank,
                {
                    "common_name": name,
                    "scientific_name": row.get("Scientific Name") or "",
                    "abundance": code,
                    "nests_locally": (row.get("Nests Locally") or "").lower()
                    == "yes",
                    "federal": row.get("Federal") or "",
                    "state": row.get("State") or "",
                },
            )
        )
    scored.sort(key=lambda x: (-x[0], x[1]["common_name"]))
    # Prefer diversity: take top ~18
    highlights = [item for _, item in scored[:18]]
    return {
        "season": season,
        "label": season.title(),
        "note": (
            "Rough seasonal picks from the USFWS 2008 Don Edwards bird checklist "
            "(abundance codes a/c/u by Spring–Summer–Fall–Winter). Not a live eBird feed."
        ),
        "highlights": highlights,
        "source": "data/source/BirdSheet.csv (USFWS ServCat bird checklist 2008)",
    }


def _find_row(sheet: str, match_names: tuple[str, ...]) -> dict | None:
    rows = _read_csv(sheet)

    def match(row: dict) -> bool:
        cn = (row.get("Common Name") or "").lower()
        return any(m.lower() in cn or cn in m.lower() for m in match_names)

    return next((r for r in rows if match(r)), None)


def build_featured() -> dict:
    species = []
    for spec in FEATURED_SPECS:
        row = _find_row(spec["sheet"], spec["match_names"]) or {}
        species.append(
            {
                "id": spec["id"],
                "common_name": spec["common_name"],
                "scientific_name": row.get("Scientific Name")
                or (
                    "Rallus obsoletus"
                    if "rail" in spec["id"]
                    else "Reithrodontomys raviventris"
                    if "mouse" in spec["id"]
                    else "Charadrius nivosus"
                ),
                "federal": row.get("Federal") or ("E" if "mouse" in spec["id"] or "rail" in spec["id"] else "T"),
                "state": row.get("State") or ("E" if "mouse" in spec["id"] or "rail" in spec["id"] else ""),
                "occurrence": row.get("Occurrence") or "",
                "blurb": spec["blurb"],
                "taxon": "bird" if "Bird" in spec["sheet"] else "mammal",
            }
        )
    return {
        "species": species,
        "note": "Flagship refuge species drawn from inventory CSVs; blurbs are visitor-oriented.",
    }


def build_meta(synced_at: str) -> dict:
    return {
        "name": "desfb",
        "title": "Don Edwards SF Bay NWR — visitor companion",
        "refuge_url": "https://www.fws.gov/refuge/don-edwards-san-francisco-bay",
        "pages_url": "https://aksheyd.github.io/desfb/",
        "repo_url": "https://github.com/aksheyd/desfb",
        "tide_station": STATION,
        "forecast_point": {"lat": LAT, "lon": LON},
        "synced_at": synced_at,
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    synced_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    season = current_season()
    errors: list[str] = []

    tides: dict = {}
    forecast: dict = {}
    try:
        tides = fetch_tides()
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError, KeyError, ValueError) as e:
        errors.append(f"tides: {e}")
        tides = {
            "station_id": STATION,
            "station_name": "Alviso (CO-OPS 9414551)",
            "predictions": [],
            "error": str(e),
        }
    try:
        forecast = fetch_forecast()
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError, KeyError, ValueError) as e:
        errors.append(f"forecast: {e}")
        forecast = {"lat": LAT, "lon": LON, "periods": [], "error": str(e)}

    today = {
        "synced_at": synced_at,
        "timezone": "America/Los_Angeles",
        "season": season,
        "tides": tides,
        "forecast": forecast,
        "errors": errors,
    }
    write_json(PUBLIC / "today.json", today)
    write_json(PUBLIC / "season.json", build_season(season))
    write_json(PUBLIC / "featured.json", build_featured())
    write_json(PUBLIC / "meta.json", build_meta(synced_at))
    print(f"Wrote {PUBLIC} (season={season}, errors={errors or 'none'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
