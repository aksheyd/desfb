#!/usr/bin/env python3
"""Legacy entry point: print danger-level summaries from output_*.csv.

Prefer: python climate_modeler.py --temp N
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from climate_modeler import SHEETS, print_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Print danger-level summaries")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory with output_*.csv (default: repo root or $DATA_DIR).",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Do not delete output_*.csv after printing.",
    )
    args = parser.parse_args()

    if args.data_dir is not None:
        data_dir = args.data_dir.resolve()
    elif os.environ.get("DATA_DIR"):
        data_dir = Path(os.environ["DATA_DIR"]).resolve()
    else:
        data_dir = Path(__file__).resolve().parent

    frames = {}
    for key, (_infile, outfile, nrows) in SHEETS.items():
        path = data_dir / outfile
        if not path.is_file():
            raise SystemExit(
                f"Missing {path}. Run sheet_analyzer.py or climate_modeler.py first."
            )
        df = pd.read_csv(path)
        frames[key] = df[:nrows]

    print_summary(frames)

    if not args.keep_output:
        for _key, (_infile, outfile, _nrows) in SHEETS.items():
            path = data_dir / outfile
            if path.is_file():
                path.unlink()


if __name__ == "__main__":
    main()
