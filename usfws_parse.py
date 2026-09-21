#!/usr/bin/env python3
"""Parse USFWS Don Edwards official species materials into climate_modeler CSVs.

Birds: ServCat 2008 checklist PDF via `pdftotext -bbox` word geometry.
Scientific Name / Federal / State / Classification merged from bundled
EcoData sheets by common-name match when available.

Mammals / herps / fish: data/bundled/*.csv (EcoData-era USFWS-derived).

Plants (optional, unscored): Plant_List.pdf → PlantSheet.csv.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from html import unescape
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"
BUNDLED_DIR = DATA_DIR / "bundled"
OFFICIAL_DIR = DATA_DIR / "official"

ABUNDANCE_RANK = {"a": 5, "c": 4, "u": 3, "o": 2, "r": 1}
ABUNDANCE_LABEL = {
    "a": "abundant",
    "c": "common",
    "u": "uncommon",
    "o": "occasional",
    "r": "rare",
}

LEGACY_COLUMNS = [
    "Common Name",
    "Scientific Name",
    "Occurrence",
    "Classification",
    "Federal",
    "State",
]

CAT_PREFIXES = (
    "Waterfowl",
    "Gallinaceous",
    "Loons",
    "Grebes",
    "Pelicans",
    "Cormorants",
    "Bitterns",
    "Ibises",
    "New World",
    "Osprey,",
    "Sandpipers",
    "Falcons",
    "Rails",
    "Cranes",
    "Plovers",
    "Stilts",
    "Skuas",
    "Auks",
    "Pigeons",
    "Barn Owls",
    "Typical Owls",
    "Swifts",
    "Hummingbirds",
    "Kingfishers",
    "Woodpeckers",
    "Tyrant",
    "Shrikes",
    "Vireos",
    "Crows",
    "Larks",
    "Swallows",
    "Titmice",
    "Bushtits",
    "Wrens",
    "Kinglets",
    "Old World",
    "Thrushes",
    "Mimic",
    "Starlings",
    "Wagtails",
    "Waxwings",
    "Wood Warblers",
    "Tanagers",
    "Sparrows",
    "Cardinals",
    "Blackbirds",
    "Finches",
    "Common Name",
    "Notes",
    "Accidental",
    "Species",
)


def norm_name(name: str) -> str:
    s = str(name or "")
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u2013", "-")
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return s


def clean(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none") else s


def occurrence_from_codes(
    codes: list[str], *, nest: bool = False, accidental: bool = False
) -> str:
    if accidental:
        return "accidental"
    if nest:
        return "nests locally"
    if not codes:
        return ""
    best = max(codes, key=lambda c: ABUNDANCE_RANK.get(c, 0))
    return ABUNDANCE_LABEL.get(best, best)


def load_lookup_by_common(*csv_paths: Path) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for path in csv_paths:
        if not path or not Path(path).is_file():
            continue
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        df.columns = [str(c).lstrip("\ufeff").strip() for c in df.columns]
        for _, row in df.iterrows():
            key = norm_name(row.get("Common Name", ""))
            if not key or key in lookup:
                continue
            lookup[key] = {
                "Scientific Name": clean(row.get("Scientific Name")),
                "Classification": clean(row.get("Classification")),
                "Federal": clean(row.get("Federal")),
                "State": clean(row.get("State")),
                "Occurrence": clean(row.get("Occurrence")),
            }
    return lookup


def pdftotext_bbox(pdf_path: Path) -> str:
    if shutil.which("pdftotext") is None:
        raise RuntimeError(
            "pdftotext not found (poppler-utils). Required to parse the bird PDF."
        )
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        subprocess.run(
            ["pdftotext", "-bbox", str(pdf_path), str(out)],
            check=True,
            capture_output=True,
        )
        return out.read_text(encoding="utf-8", errors="replace")
    finally:
        out.unlink(missing_ok=True)


def _parse_bbox_words(page_html: str) -> list[dict]:
    words = []
    for m in re.finditer(
        r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">'
        r"(.*?)</word>",
        page_html,
    ):
        x0, y0, x1, y1, t = m.groups()
        t = unescape(t).replace("\u2019", "'").replace("\u2018", "'").strip()
        t = t.replace("\t", "")
        if not t:
            continue
        words.append(
            {
                "x0": float(x0),
                "y0": float(y0),
                "x1": float(x1),
                "y1": float(y1),
                "t": t,
            }
        )
    return words


def _page_width(page_html: str) -> float:
    m = re.match(r'width="([\d.]+)"', page_html)
    return float(m.group(1)) if m else 330.0


def _group_lines(words: list[dict], y_tol: float = 4.0) -> list[list[dict]]:
    words = sorted(words, key=lambda w: (w["y0"], w["x0"]))
    lines: list[list[dict]] = []
    cur: list[dict] = []
    cy: float | None = None
    for w in words:
        if cy is None or abs(w["y0"] - cy) <= y_tol:
            cur.append(w)
            cy = w["y0"] if cy is None else cy
        else:
            lines.append(sorted(cur, key=lambda x: x["x0"]))
            cur, cy = [w], w["y0"]
    if cur:
        lines.append(sorted(cur, key=lambda x: x["x0"]))
    return lines


def _is_category(text: str) -> bool:
    return any(text.startswith(p) for p in CAT_PREFIXES)


def _parse_half(words_half: list[dict]) -> dict | None:
    if not words_half:
        return None
    tokens = [w["t"] for w in words_half]
    codes: list[str] = []
    i = len(tokens) - 1
    while i >= 0 and tokens[i] in "acuor":
        codes.append(tokens[i])
        i -= 1
    codes.reverse()
    name_tokens = tokens[: i + 1]
    if not name_tokens:
        return None
    refuge = None
    if (
        len(name_tokens) >= 2
        and name_tokens[-2] == "S"
        and name_tokens[-1] == "Refuge"
    ):
        refuge = "S Refuge"
        name_tokens = name_tokens[:-2]
    elif name_tokens and name_tokens[-1] == "NRefuge":
        refuge = "NRefuge"
        name_tokens = name_tokens[:-1]
    text = " ".join(name_tokens).strip()
    if not text or _is_category(text) or not codes:
        return None
    nest = text.startswith("*")
    name = text.lstrip("*").strip()
    if not re.match(r"^[A-Z][A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+){0,6}$", name):
        return None
    return {"nest": nest, "name": name, "refuge": refuge, "codes": codes}


def _parse_accidental_names(words: list[dict]) -> list[str]:
    right = [w for w in words if w["x0"] > 120]
    lines = _group_lines(right, y_tol=5.0)
    skip = {
        "accidental",
        "species",
        "notes",
        "red-tailed hawk",
    }
    names: list[str] = []
    for ln in lines:
        text = " ".join(w["t"] for w in sorted(ln, key=lambda z: z["x0"]))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        low = text.casefold()
        if low in skip or "©" in text or "/" in text:
            continue
        if re.match(r"^[A-Z][A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+){0,5}$", text):
            names.append(text)
    return names


def parse_bird_checklist_pdf(pdf_path: Path) -> list[dict]:
    xhtml = pdftotext_bbox(pdf_path)
    pages = re.split(r"<page\s+", xhtml)[1:]
    entries: list[dict] = []
    seen: set[str] = set()

    for page_html in pages:
        width = _page_width(page_html)
        words = _parse_bbox_words(page_html)
        texts = {w["t"] for w in words}

        if "Accidental" in texts and (
            "Booby" in texts or "Frigatebird" in texts or "Booby" in " ".join(texts)
        ):
            for name in _parse_accidental_names(words):
                key = norm_name(name)
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    {
                        "name": name,
                        "nest": False,
                        "codes": [],
                        "refuge": None,
                        "accidental": True,
                    }
                )
            continue

        if width < 400:
            continue

        mid = width / 2.0
        for line in _group_lines(words):
            left = [w for w in line if w["x0"] < mid]
            right = [w for w in line if w["x0"] >= mid]
            for half in (left, right):
                parsed = _parse_half(half)
                if not parsed:
                    continue
                key = norm_name(parsed["name"])
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    {
                        "name": parsed["name"],
                        "nest": parsed["nest"],
                        "codes": parsed["codes"],
                        "refuge": parsed["refuge"],
                        "accidental": False,
                    }
                )
    return entries


def birds_to_dataframe(
    entries: list[dict],
    lookup: dict[str, dict] | None = None,
    source_label: str = "USFWS ServCat bird checklist 2008",
) -> pd.DataFrame:
    lookup = lookup or {}
    rows = []
    for e in entries:
        prior = lookup.get(norm_name(e["name"]), {})
        occ = occurrence_from_codes(
            e.get("codes") or [],
            nest=bool(e.get("nest")),
            accidental=bool(e.get("accidental")),
        )
        if not occ:
            occ = prior.get("Occurrence", "")
        rows.append(
            {
                "Common Name": e["name"],
                "Scientific Name": prior.get("Scientific Name", ""),
                "Occurrence": occ,
                "Classification": prior.get("Classification", ""),
                "Federal": prior.get("Federal", ""),
                "State": prior.get("State", ""),
                "Source": source_label,
                "Abundance Codes": " ".join(e.get("codes") or []),
                "Nests Locally": "yes" if e.get("nest") else "",
            }
        )
    df = pd.DataFrame(rows)
    extras = [c for c in df.columns if c not in LEGACY_COLUMNS]
    return df[LEGACY_COLUMNS + extras]


def copy_bundled_sheet(name: str, dest_dir: Path) -> Path:
    src = BUNDLED_DIR / name
    if not src.is_file():
        raise FileNotFoundError(f"Missing bundled sheet: {src}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    df = pd.read_csv(src)
    df.columns = [str(c).lstrip("\ufeff").strip() for c in df.columns]
    if "Source" not in df.columns:
        df["Source"] = "bundled EcoData / USFWS-derived"
    for col in LEGACY_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    extras = [c for c in df.columns if c not in LEGACY_COLUMNS]
    df = df[LEGACY_COLUMNS + extras]
    df.to_csv(dest, index=False)
    return dest


def parse_plant_list_pdf(pdf_path: Path) -> pd.DataFrame | None:
    if not pdf_path.is_file() or shutil.which("pdftotext") is None:
        return None
    text = subprocess.check_output(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        text=True,
        errors="replace",
    )
    rows = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or ("Family" in line and "Scientific" in line):
            continue
        if "Plant List" in line or re.match(r"^\s*[A-Z]?-?\d+\s*$", line):
            continue
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) < 4:
            continue
        family, sci, common, status = parts[0], parts[1], parts[2], parts[-1]
        if status.casefold() not in ("native", "non-native"):
            continue
        if not re.match(r"^[A-Z]", family):
            continue
        classification = "native" if status.casefold() == "native" else "non-native"
        rows.append(
            {
                "Common Name": common.strip(),
                "Scientific Name": sci.strip(),
                "Occurrence": "",
                "Classification": classification,
                "Federal": "",
                "State": "",
                "Source": "USFWS / EcoData Plant_List.pdf",
                "Family": family.strip(),
            }
        )
    if not rows:
        return None
    return pd.DataFrame(rows)


def build_bird_sheet(
    pdf_path: Path,
    lookup_paths: list[Path] | None = None,
) -> pd.DataFrame:
    lookup_paths = lookup_paths or [
        BUNDLED_DIR / "BirdSheet.csv",
        REPO_ROOT / "BirdSheet.csv",
        DATA_DIR / "BirdSheet.csv",
    ]
    lookup = load_lookup_by_common(*lookup_paths)
    entries = parse_bird_checklist_pdf(pdf_path)
    if len(entries) < 100:
        raise RuntimeError(
            f"Bird PDF parse produced only {len(entries)} rows; expected ~227+."
        )
    return birds_to_dataframe(entries, lookup=lookup)


if __name__ == "__main__":
    pdf = OFFICIAL_DIR / "SFB_2008_BirdList.pdf"
    if not pdf.is_file():
        raise SystemExit(f"Missing {pdf}; run refresh_data.py first.")
    df = build_bird_sheet(pdf)
    print(f"Parsed {len(df)} birds")
    print(df.head())
    print("Occurrence counts:\n", df["Occurrence"].value_counts())
