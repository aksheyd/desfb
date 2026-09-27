#!/usr/bin/env python3
"""Render site/template.html with data/species.json into dist/, the whole site."""

import calendar
import html
import json
import math
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "species.json"
TEMPLATE = ROOT / "site" / "template.html"
DIST = ROOT / "dist"
SITE = "https://aksheyd.github.io/desfb/"
REFUGE = "Don Edwards San Francisco Bay National Wildlife Refuge"
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

SELDOM_BELOW = 30
MIGRANT_MIN = 200
SEEN_MIN = 5
PRESENT = 0.3
SEASON_SHARE = 0.3
OFF_SEASON_MAX = 0.08
PASSAGE_MAX = 0.12

GROUPS = [
    ("resident", "Here all year", "are seen in every month."),
    (
        "winter",
        "Winter visitors",
        "arrive in September and October and stay until spring.",
    ),
    ("summer", "Summer visitors", "come in spring and summer, many of them to nest."),
    (
        "passage",
        "Passing through",
        "stop here on their way north in spring or south in fall.",
    ),
    ("seldom", "Seldom seen", f"have fewer than {SELDOM_BELOW} sightings each."),
]
MIGRANTS = ("winter", "summer", "passage")


@dataclass(frozen=True)
class Species:
    name: str
    scientific: str
    formerly: str | None
    months: list[int]
    photo: str | None
    credit: str | None
    url: str | None
    profile: list[float]
    group: str

    @property
    def total(self) -> int:
        return sum(self.months)


@dataclass(frozen=True)
class Group:
    key: str
    title: str
    sentence: str
    ids: list[int]


@dataclass(frozen=True)
class Today:
    month: int
    fraction: float
    label: str
    arrivals: list[int]
    departures: list[int]


def classify(relative: list[float], total: int) -> str:
    if total < SELDOM_BELOW:
        return "seldom"
    share = sum(relative)
    winter = (relative[11] + relative[0] + relative[1]) / share
    summer = sum(relative[5:8]) / share
    if summer < OFF_SEASON_MAX and winter > SEASON_SHARE:
        return "winter"
    if winter < OFF_SEASON_MAX and summer > SEASON_SHARE:
        return "summer"
    if winter < PASSAGE_MAX and summer < PASSAGE_MAX:
        return "passage"
    return "resident"


def load_species(records: list[dict]) -> list[Species]:
    effort = [sum(r["months"][m] for r in records) for m in range(12)]
    species = []
    for r in records:
        relative = [n / e for n, e in zip(r["months"], effort)]
        top = max(relative) or 1
        species.append(
            Species(
                name=r["name"],
                scientific=r["scientific"],
                formerly=r.get("formerly"),
                months=r["months"],
                photo=r.get("photo"),
                credit=r.get("credit"),
                url=r.get("url"),
                profile=[x / top for x in relative],
                group=classify(relative, sum(r["months"])),
            )
        )
    return species


def most_seen_first(species: list[Species]) -> list[Species]:
    return sorted(species, key=lambda s: (-s.total, s.name))


def group_species(species: list[Species]) -> tuple[list[Species], list[Group]]:
    ordered: list[Species] = []
    groups: list[Group] = []
    for key, title, tail in GROUPS:
        members = most_seen_first([s for s in species if s.group == key])
        names = [s.name for s in members[:3]]
        sentence = f"{', '.join(names[:-1])} and {names[-1]} {tail}"
        ids = list(range(len(ordered), len(ordered) + len(members)))
        groups.append(Group(key, title, sentence, ids))
        ordered += members
    return ordered, groups


def month_summaries(ordered: list[Species]) -> list[dict]:
    migrants = [
        (i, s)
        for i, s in enumerate(ordered)
        if s.group in MIGRANTS and s.total >= MIGRANT_MIN
    ]
    migrants.sort(key=lambda pair: (-pair[1].total, pair[1].name))
    summaries = []
    for m in range(12):
        before, after = (m - 1) % 12, (m + 1) % 12
        summaries.append(
            {
                "seen": sum(1 for s in ordered if s.months[m] >= SEEN_MIN),
                "arr": [
                    i
                    for i, s in migrants
                    if s.profile[before] < PRESENT <= s.profile[m]
                ],
                "dep": [
                    i for i, s in migrants if s.profile[m] >= PRESENT > s.profile[after]
                ],
            }
        )
    return summaries


def today_at(day: date, months: list[dict]) -> Today:
    m = day.month - 1
    part = "Early" if day.day <= 10 else "Mid" if day.day <= 20 else "Late"
    days = calendar.monthrange(day.year, day.month)[1]
    arrivals = months[m]["arr"]
    arriving_next = [i for i in months[(m + 1) % 12]["arr"] if i not in arrivals]
    return Today(
        month=m,
        fraction=(m + (day.day - 0.5) / days) / 12,
        label=f"{part} {MONTHS[m]}",
        arrivals=arrivals + arriving_next,
        departures=months[m]["dep"],
    )


def gradient(counts: list[int], max_count: int) -> str:
    shade = [math.log1p(n) / math.log1p(max_count) for n in counts]
    wrap = (shade[0] + shade[11]) / 2
    stops = (
        [(wrap, 0)]
        + [(a, (i + 0.5) / 12 * 100) for i, a in enumerate(shade)]
        + [(wrap, 100)]
    )
    return (
        "linear-gradient(to right, "
        + ", ".join(f"rgb(15 76 70 / {a:.3f}) {at:.2f}%" for a, at in stops)
        + ")"
    )


def name_buttons(ids: list[int], species: list[Species], shown: int = 3) -> str:
    visible = ids[:shown]
    parts = []
    for j, i in enumerate(visible):
        if j:
            parts.append(
                " and " if j == len(visible) - 1 and len(ids) <= shown else ", "
            )
        parts.append(
            f'<button type="button" class="link">{html.escape(species[i].name)}</button>'
        )
    if len(ids) > shown:
        parts.append(f" and {len(ids) - shown} more")
    return "".join(parts)


def context_html(
    today: Today, months: list[dict], species: list[Species], year: int
) -> str:
    seen = months[today.month]["seen"]
    most = (
        ", more than in any other month"
        if seen == max(m["seen"] for m in months)
        else ""
    )
    moves = "".join(
        f"<dt>{label}</dt><dd>{name_buttons(ids, species)}</dd>"
        for label, ids in (("Arriving", today.arrivals), ("Leaving", today.departures))
        if ids
    )
    return (
        f'<h2><span class="yr">{year}</span> <span class="now">{today.label}</span></h2>'
        f"<p>{seen} species are seen here in {MONTHS[today.month]}{most}.</p>"
        f'<dl class="moves">{moves}</dl>'
    )


def months_html() -> str:
    return "".join(
        f'<button type="button" title="Who is here in {m}" aria-pressed="false">{m[:3]}</button>'
        for m in MONTHS
    )


def figure_html(groups: list[Group], species: list[Species], today: Today) -> str:
    max_count = max(max(s.months) for s in species)
    out = []
    for k, g in enumerate(groups):
        row = 2 + 2 * k
        n = len(g.ids)
        lines = "".join(
            f'<div class="ln" data-i="{i}" aria-hidden="true" '
            f'style="background-image:{gradient(species[i].months, max_count)}"></div>'
            f'<span class="nm" data-i="{i}" role="listitem">{html.escape(species[i].name)}</span>'
            for i in g.ids
        )
        out.append(
            f'<aside class="note" data-group="{g.key}" style="--r:{row}"><h3>{g.title}<span>{n}</span></h3>'
            f'<p>{html.escape(g.sentence)}</p><button type="button" class="link" aria-expanded="false">'
            f"Show all {n} names</button></aside>\n"
            f'<div class="band" data-group="{g.key}" style="--r:{row}" role="list" '
            f'aria-label="{g.title}: {n} species">{lines}</div>\n'
        )
    left = f"calc((100% - var(--gap)) * {2 / 3 * today.fraction:.6f})"
    out.append(
        f'<div class="mcol" hidden></div><div class="today" style="left:{left}"></div>'
        f'<span class="today-label" style="left:{left}">Today</span>'
    )
    return "".join(out)


def footer_html(generated: date) -> str:
    as_of = f"{MONTHS[generated.month - 1]} {generated.day}, {generated.year}"
    return (
        "<div><p>Sightings are observations people have shared on "
        '<a href="https://www.gbif.org/">GBIF</a>, which gathers eBird, iNaturalist and other sources. '
        "We counted them by month within an outline of the refuge's shoreline. The species are the refuge's "
        "2008 U.S. Fish and Wildlife Service checklist. Photos come from iNaturalist, with credit on each card. "
        f"Counts as of {as_of}.</p>"
        "<p>An unofficial guide, not affiliated with the U.S. Fish and Wildlife Service.</p></div>"
        '<div><ul><li><a href="https://www.fws.gov/refuge/don-edwards-san-francisco-bay">Official refuge site</a></li>'
        '<li><a href="https://github.com/aksheyd/desfb">Source on GitHub</a></li></ul>'
        "<p>The arrow keys or W, A, S and D step through species, and Esc closes a card.</p></div>"
    )


def jsonld(count: int, generated: str) -> str:
    graph = [
        {
            "@type": "WebSite",
            "@id": f"{SITE}#site",
            "url": SITE,
            "name": "Don Edwards SF Bay Refuge, an unofficial guide",
            "inLanguage": "en",
        },
        {
            "@type": "WebPage",
            "@id": f"{SITE}#page",
            "url": SITE,
            "name": "Who's at the refuge, and when",
            "description": f"When to see each of the {count} birds and mammals at {REFUGE}, month by month.",
            "isPartOf": {"@id": f"{SITE}#site"},
            "about": {"@id": f"{SITE}#refuge"},
            "inLanguage": "en",
            "dateModified": generated,
            "primaryImageOfPage": f"{SITE}og.png",
        },
        {
            "@type": ["TouristAttraction", "Park"],
            "@id": f"{SITE}#refuge",
            "name": REFUGE,
            "description": "A national wildlife refuge protecting marshes and former salt ponds "
            "at the south end of San Francisco Bay.",
            "sameAs": ["https://www.fws.gov/refuge/don-edwards-san-francisco-bay"],
        },
        {
            "@type": "Dataset",
            "@id": f"{SITE}#data",
            "name": f"Monthly sightings of {count} birds and mammals at {REFUGE}",
            "description": "For each species on the refuge's 2008 checklist, the number of human observations "
            "shared on GBIF in each month of the year, counted within an outline of the refuge's shoreline.",
            "url": SITE,
            "isAccessibleForFree": True,
            "keywords": [
                "birds",
                "mammals",
                "wildlife",
                "bird migration",
                "San Francisco Bay",
                "national wildlife refuge",
                "eBird",
                "iNaturalist",
                "GBIF",
            ],
            "isBasedOn": "https://www.gbif.org/",
            "spatialCoverage": {"@id": f"{SITE}#refuge"},
            "variableMeasured": "Reported sightings per month",
            "dateModified": generated,
            "distribution": {
                "@type": "DataDownload",
                "encodingFormat": "application/json",
                "contentUrl": f"{SITE}data/species.json",
            },
        },
    ]
    return json.dumps(
        {"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False
    ).replace("</", "<\\/")


def sitemap(generated: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url>\n    <loc>{SITE}</loc>\n    <lastmod>{generated}</lastmod>\n  </url>\n"
        "</urlset>\n"
    )


def payload(
    species: list[Species], groups: list[Group], months: list[dict], year: int
) -> str:
    data = {
        "nowYear": year,
        "maxSeen": max(m["seen"] for m in months),
        "present": PRESENT,
        "seldom": SELDOM_BELOW,
        "months": months,
        "groups": [{"key": g.key, "title": g.title, "ids": g.ids} for g in groups],
        "species": [
            {
                "n": s.name,
                "s": s.scientific,
                "f": s.formerly,
                "m": s.months,
                "p": [round(x, 3) for x in s.profile],
                "ph": s.photo,
                "cr": s.credit,
                "u": s.url,
                "key": " ".join(
                    filter(None, [s.name, s.scientific, s.formerly])
                ).lower(),
            }
            for s in species
        ],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def main() -> None:
    source = json.loads(DATA.read_text(encoding="utf-8"))
    generated = date.fromisoformat(source["generated"])
    species, groups = group_species(load_species(source["species"]))
    months = month_summaries(species)
    today = today_at(datetime.now(ZoneInfo("America/Los_Angeles")).date(), months)
    data = payload(species, groups, months, generated.year)
    page = TEMPLATE.read_text(encoding="utf-8")
    for marker, content in (
        ("/*JSONLD*/", jsonld(len(species), source["generated"])),
        ("<!--CONTEXT-->", context_html(today, months, species, generated.year)),
        ("<!--MONTHS-->", months_html()),
        ("<!--FIG-->", figure_html(groups, species, today)),
        ("<!--FOOTER-->", footer_html(generated)),
        ("<!--COUNT-->", str(len(species))),
        ("/*DATA*/", data),
    ):
        if marker not in page:
            raise SystemExit(f"{TEMPLATE.name} is missing {marker}")
        page = page.replace(marker, content)
    shutil.rmtree(DIST, ignore_errors=True)
    (DIST / "data").mkdir(parents=True)
    (DIST / "index.html").write_text(page, encoding="utf-8")
    (DIST / "sitemap.xml").write_text(sitemap(source["generated"]), encoding="utf-8")
    shutil.copy(ROOT / "site" / "og.png", DIST / "og.png")
    shutil.copy(DATA, DIST / "data" / "species.json")
    print(
        f"dist/index.html: {len(species)} species, {len(page) // 1024} KB, today is {today.label}"
    )


if __name__ == "__main__":
    main()
