#!/usr/bin/env python3
"""Don Edwards SF Bay NWR climate modeler — toy danger-level heuristic CLI.

Reads species CSVs (default: data/), applies a simple temperature-delta heuristic
to a per-species Danger Level score, and prints a summary. Not a scientific model.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = REPO_ROOT / "data"
AVG_TEMP_F = 60  # baseline used by the original EcoData heuristic

# filename, output name, optional max rows (None = all)
SHEETS = {
    "birds": ("BirdSheet.csv", "output_birds.csv", None),
    "mammals": ("MammalsSheet.csv", "output_mammals.csv", None),
    "amphibian_reptiles": (
        "AmphibianReptilesSheet.csv",
        "output_amphibianreptiles.csv",
        None,
    ),
    "fish": ("FishsSheet.csv", "output_fishs.csv", None),
}

TAXON_LABELS = {
    "birds": "Birds",
    "mammals": "Mammals",
    "amphibian_reptiles": "Amphibians/Reptiles",
    "fish": "Fish",
}


def temperature_change_value(new_temp: int, avg_temp: int = AVG_TEMP_F) -> int:
    """Toy mapping from temperature delta (°F) to a base danger increment."""
    if new_temp == avg_temp:
        return 0
    diff = avg_temp - new_temp
    if diff <= 11:
        return math.ceil(pow(1.2, diff) - 1)
    return math.ceil(0.0032 * pow(diff - 35, 3) + 50)


def danger_level(row: pd.Series, change_val: int) -> int:
    """Heuristic score from occurrence / classification / listing status."""
    return_val = change_val

    occurrence = str(row.get("Occurrence", "nan"))
    classification = str(row.get("Classification", "nan"))
    federal = str(row.get("Federal", "nan"))
    state = str(row.get("State", "nan"))

    if occurrence == "nests locally":
        return_val += 1
    elif occurrence == "nan":
        return_val += 5
    elif occurrence == "accidental":
        return_val += 10

    if occurrence in ("upland", "marsh", "tidal sloughs"):
        return_val += 10
    elif occurrence == "all habitats":
        return_val += 5

    if occurrence == "present in tidal waters":
        return_val += 10
    elif occurrence == "present in tidal waters and ponds":
        return_val += 5
    elif occurrence == "rare in tidal waters":
        return_val += 20

    if classification == "native":
        return_val += 1
    elif classification == "non-native":
        return_val += 5

    if federal == "E":
        return_val += 50
    elif federal == "T":
        return_val += 25

    if state == "E":
        return_val += 0
    elif state == "T":
        return_val += 25
    elif state in ("SSC", "SC"):
        return_val += 50
    elif state in ("SP", "FP"):
        return 0

    return return_val


def resolve_data_dir(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env = os.environ.get("DATA_DIR")
    if env:
        return Path(env).resolve()
    if DEFAULT_DATA_DIR.is_dir():
        return DEFAULT_DATA_DIR
    return REPO_ROOT


def load_and_score(data_dir: Path, change_val: int) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for key, (infile, _outfile, nrows) in SHEETS.items():
        path = data_dir / infile
        if not path.is_file():
            # Fall back to repo-root historical copies
            alt = REPO_ROOT / infile
            if alt.is_file():
                path = alt
            else:
                raise FileNotFoundError(f"Missing input CSV: {path}")
        df = pd.read_csv(path)
        if nrows is not None:
            df = df[:nrows].copy()
        else:
            df = df.copy()
        for col in ("Occurrence", "Classification", "Federal", "State"):
            if col in df.columns:
                df[col] = df[col].astype(str)
        df["Danger Level"] = df.apply(
            lambda row: danger_level(row, change_val), axis=1
        )
        frames[key] = df
    return frames


def write_outputs(frames: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for key, (_infile, outfile, _nrows) in SHEETS.items():
        frames[key].to_csv(out_dir / outfile, index=False)


def print_summary(frames: dict[str, pd.DataFrame]) -> None:
    for key, label in TAXON_LABELS.items():
        df = frames[key]
        print(f"{label}: ")
        print("=" * max(len(label) + 1, 6))
        cols = [
            c
            for c in ("Common Name", "Scientific Name", "Danger Level")
            if c in df.columns
        ]
        print(df[cols].head())
        print(f"Max Danger Level for {label} = ", df["Danger Level"].max())
        print(f"Min Danger Level for {label} = ", df["Danger Level"].min())
        print(
            f"Average Danger Level for {label} = ",
            "{:.2f}".format(df["Danger Level"].mean()),
        )
        print(f"Amount of {label} = ", len(df))
        print()


def summarize(frames: dict[str, pd.DataFrame], temp: int, change_val: int) -> dict:
    """JSON-friendly summary for the dashboard."""
    groups = []
    extinct = 0
    for key, label in TAXON_LABELS.items():
        df = frames[key]
        n_ext = int((df["Danger Level"] >= 100).sum())
        extinct += n_ext
        groups.append(
            {
                "key": key,
                "label": label,
                "count": int(len(df)),
                "avg_danger": round(float(df["Danger Level"].mean()), 2)
                if len(df)
                else 0.0,
                "max_danger": int(df["Danger Level"].max()) if len(df) else 0,
                "min_danger": int(df["Danger Level"].min()) if len(df) else 0,
                "extinctish": n_ext,
            }
        )
    return {
        "temp_f": temp,
        "baseline_f": AVG_TEMP_F,
        "change_val": change_val,
        "extinctish_total": extinct,
        "groups": groups,
        "note": (
            "Danger Level is a toy EcoData heuristic, not a scientific "
            "extinction model."
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Toy climate danger-level heuristic for Don Edwards SF Bay NWR "
            "species lists. Not a scientific extinction model."
        )
    )
    parser.add_argument(
        "-t",
        "--temp",
        type=int,
        default=AVG_TEMP_F,
        help=f"Hypothetical temperature in °F (default: {AVG_TEMP_F}, the baseline).",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory containing the species CSVs (default: data/, or $DATA_DIR).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory for output_*.csv files (default: same as data-dir).",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Keep output_*.csv files after printing (default: delete them).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.temp < 0 or args.temp > 99:
        print("Error: temperature must be between 0 and 99 °F.", file=sys.stderr)
        return 2

    data_dir = resolve_data_dir(args.data_dir)
    out_dir = args.out_dir.resolve() if args.out_dir else data_dir
    change_val = temperature_change_value(args.temp)

    print(
        f"Don Edwards SF Bay NWR Climate Modeler (toy heuristic)\n"
        f"Temperature: {args.temp} °F (baseline {AVG_TEMP_F} °F) → "
        f"base changeVal={change_val}\n"
        f"Data dir: {data_dir}\n"
    )

    frames = load_and_score(data_dir, change_val)
    write_outputs(frames, out_dir)
    print_summary(frames)

    if not args.keep_output:
        for _key, (_infile, outfile, _nrows) in SHEETS.items():
            path = out_dir / outfile
            if path.is_file():
                path.unlink()

    extinctish = sum(
        int((df["Danger Level"] >= 100).sum()) for df in frames.values()
    )
    print(
        f"Species with Danger Level ≥ 100 (treated as 'extinct' in this toy model): "
        f"{extinctish}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
