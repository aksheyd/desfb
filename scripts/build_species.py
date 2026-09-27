#!/usr/bin/env python3
"""Bake the refuge checklist, current names, monthly GBIF sightings and iNaturalist photos into data/species.json."""

from __future__ import annotations

import csv
import json
import string
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "source"
OUT = ROOT / "data" / "species.json"
UA = "desfb (https://github.com/aksheyd/desfb)"

# Counterclockwise lon/lat ring: GBIF reads a clockwise ring as everything outside it.
AREA = (
    "POLYGON((-122.240 37.548, -122.245 37.520, -122.235 37.502, -122.200 37.495, "
    "-122.175 37.487, -122.150 37.487, -122.135 37.475, -122.120 37.462, "
    "-122.100 37.445, -122.080 37.435, -122.055 37.432, -122.025 37.425, "
    "-121.980 37.420, -121.955 37.420, -121.940 37.440, -121.935 37.465, "
    "-121.960 37.488, -122.010 37.505, -122.040 37.525, -122.050 37.543, "
    "-122.070 37.548, -122.085 37.565, -122.100 37.575, -122.140 37.590, "
    "-122.240 37.548))"
)

SHEETS = {"BirdSheet.csv": "Aves", "MammalsSheet.csv": "Mammalia"}
GBIF_CLASSES = (212, 359)
INAT_CALIFORNIA = 14

# The sheet's scientific name is blank, wrong, or has since passed to a species that lives elsewhere.
LOOKUP_AS = {
    "Barn Owl": "Tyto furcata",
    "Black Rail": "Laterallus jamaicensis",
    "Black Scoter": "Melanitta americana",
    "Clapper Rail": "Rallus obsoletus",
    "Common Moorhen": "Gallinula galeata",
    "Least Tern": "Sternula antillarum",
    "Mew Gull": "Larus brachyrhynchus",
    "Northern Harrier": "Circus hudsonius",
    "Solitary Vireo": "Vireo cassinii",
    "Thayer's Gull": "Larus glaucoides",
    "Western red bats": "Lasiurus blossevillii",
    "White-crowned Sparrow": "Zonotrichia leucophrys",
    "White-tailed Kite": "Elanus leucurus",
    "White-throated Sparrow": "Zonotrichia albicollis",
    "White-winged Scoter": "Melanitta deglandi",
}


def get(url: str, params: dict, pause: float = 0) -> dict:
    query = urllib.parse.urlencode(params, doseq=True, quote_via=urllib.parse.quote)
    req = urllib.request.Request(
        f"{url}?{query}", headers={"User-Agent": UA, "Accept": "application/json"}
    )
    for wait in (5, 10, 20, None):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
            time.sleep(pause)
            return data
        except OSError as e:
            if wait is None:
                raise OSError(f"{url} failed: {e}") from e
            time.sleep(wait)


def checklist() -> list[tuple[str, str, str]]:
    rows = []
    for sheet, taxon_class in SHEETS.items():
        with (SOURCE / sheet).open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                common = " ".join(row["Common Name"].split())
                sci = " ".join(row["Scientific Name"].split()).capitalize()
                rows.append((common, LOOKUP_AS.get(common, sci), taxon_class))
    return rows


def monthly_sightings() -> dict[int, list[int]]:
    counts: dict[int, list[int]] = {}
    for month in range(1, 13):
        offset = 0
        while True:
            res = get(
                "https://api.gbif.org/v1/occurrence/search",
                {
                    "geometry": AREA,
                    "month": month,
                    "taxonKey": GBIF_CLASSES,
                    "basisOfRecord": "HUMAN_OBSERVATION",
                    "occurrenceStatus": "PRESENT",
                    "hasGeospatialIssue": "false",
                    "limit": 0,
                    "facet": "speciesKey",
                    "facetLimit": 1000,
                    "facetOffset": offset,
                },
            )
            buckets = res["facets"][0]["counts"] if res["facets"] else []
            for bucket in buckets:
                species_key = int(bucket["name"])
                counts.setdefault(species_key, [0] * 12)[month - 1] = bucket["count"]
            if len(buckets) < 1000:
                break
            offset += 1000
    return counts


def gbif_species(name: str, taxon_class: str) -> dict | None:
    match = get(
        "https://api.gbif.org/v1/species/match", {"name": name, "class": taxon_class}
    )
    return match if match.get("speciesKey") else None


def inat_taxon(*names: str | None) -> dict | None:
    for name in dict.fromkeys(filter(None, names)):
        res = get(
            "https://api.inaturalist.org/v1/taxa",
            {
                "q": name,
                "rank": "species",
                "is_active": "true",
                "locale": "en",
                "preferred_place_id": INAT_CALIFORNIA,
                "per_page": 10,
            },
            pause=1,
        )
        for taxon in res["results"]:
            if name.lower() in (
                taxon["name"].lower(),
                (taxon.get("matched_term") or "").lower(),
            ):
                return taxon
    return None


def same_name(a: str, b: str) -> bool:
    def words(s: str) -> list[str]:
        return s.lower().replace("\u2019", "'").replace("-", " ").split()

    return words(a) == words(b)


def build() -> tuple[list[dict], dict[str, list[str]]]:
    sightings = monthly_sightings()
    rows = checklist()
    species, seen = [], {}
    report: dict[str, list[str]] = {
        "not matched on GBIF": [],
        "duplicates skipped": [],
        "common names changed": [],
        "without a licensed iNaturalist photo": [],
        "with no sightings in the area": [],
    }

    for i, (common, lookup, taxon_class) in enumerate(rows, 1):
        print(f"\r{i}/{len(rows)} {common:<40}", end="", flush=True)
        match = gbif_species(lookup, taxon_class) if lookup else None
        key = match["speciesKey"] if match else None
        if key in seen:
            report["duplicates skipped"].append(
                f"{common} (same GBIF species as {seen[key]})"
            )
            continue
        if key:
            seen[key] = common
        else:
            report["not matched on GBIF"].append(common)

        taxon = inat_taxon(" ".join(lookup.split()[:2]), match and match.get("species"))
        name = (taxon or {}).get("preferred_common_name")
        if len(lookup.split()) > 2 or not name:
            name = string.capwords(common)

        scientific = taxon["name"] if taxon else (match or {}).get("species", lookup)
        record = {"name": name, "scientific": scientific}
        if not same_name(common, name):
            record["formerly"] = common
            report["common names changed"].append(f"{common} → {name}")
        record["months"] = sightings.get(key, [0] * 12)
        if not any(record["months"]):
            report["with no sightings in the area"].append(name)
        if key:
            record["gbif"] = key

        photo = (taxon or {}).get("default_photo") or {}
        # Photos without a license code are all rights reserved.
        if photo.get("license_code") and photo.get("medium_url"):
            record["photo"] = photo["medium_url"].replace("/medium.", "/small.")
            record["credit"] = photo["attribution"]
        else:
            report["without a licensed iNaturalist photo"].append(name)
        if taxon:
            record["url"] = f"https://www.inaturalist.org/taxa/{taxon['id']}"
        species.append(record)

    print()
    return species, report


def write(species: list[dict]) -> None:
    rows = ",\n".join(json.dumps(s, ensure_ascii=False) for s in species)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        f'{{"generated": "{date.today().isoformat()}", "area": {json.dumps(AREA)}, "species": [\n{rows}\n]}}\n',
        encoding="utf-8",
    )


def main() -> int:
    try:
        species, report = build()
    except OSError as e:
        print(f"\nStopped, nothing written. {e}")
        return 1
    write(species)
    print(f"{len(species)} species written to {OUT.relative_to(ROOT)}")
    for label, names in report.items():
        print(f"\n{len(names)} {label}" + "".join(f"\n  {n}" for n in names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
