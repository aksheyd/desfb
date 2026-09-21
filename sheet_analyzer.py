#!/usr/bin/env python3
"""Legacy entry point: score species CSVs and write output_*.csv.

Prefer: python climate_modeler.py --temp N
Kept so the optional C++ menu can still shell out to this script.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from climate_modeler import (
    AVG_TEMP_F,
    load_and_score,
    temperature_change_value,
    write_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyzer for data")
    parser.add_argument(
        "-p",
        "--print_string",
        help="Temperature in °F for the toy danger heuristic.",
        nargs="*",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Directory with species CSVs (default: repo root or $DATA_DIR).",
    )
    args = parser.parse_args()

    if not args.print_string:
        raise SystemExit("Error: pass a temperature, e.g. -p 60")
    new_temp = int(args.print_string[0])

    if args.data_dir is not None:
        data_dir = args.data_dir.resolve()
    elif os.environ.get("DATA_DIR"):
        data_dir = Path(os.environ["DATA_DIR"]).resolve()
    else:
        data_dir = Path(__file__).resolve().parent

    change_val = temperature_change_value(new_temp, AVG_TEMP_F)
    frames = load_and_score(data_dir, change_val)
    write_outputs(frames, data_dir)


if __name__ == "__main__":
    main()
