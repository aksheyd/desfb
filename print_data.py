#!/usr/bin/env python3
"""Legacy entry point: print danger-level summaries from output_*.csv."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from climate_modeler import SHEETS, print_summary, resolve_data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Print danger-level summaries")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory with output_*.csv (default: data/ or $DATA_DIR).",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Do not delete output_*.csv after printing.",
    )
    args = parser.parse_args()

    data_dir = resolve_data_dir(args.data_dir)
    frames = {}
    for key, (_infile, outfile, nrows) in SHEETS.items():
        path = data_dir / outfile
        if not path.is_file():
            raise SystemExit(
                f"Missing {path}. Run sheet_analyzer.py or climate_modeler.py first."
            )
        df = pd.read_csv(path)
        frames[key] = df[:nrows] if nrows is not None else df

    print_summary(frames)

    if not args.keep_output:
        for _key, (_infile, outfile, _nrows) in SHEETS.items():
            path = data_dir / outfile
            if path.is_file():
                path.unlink()


if __name__ == "__main__":
    main()
