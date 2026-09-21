# Don Edwards San Francisco Bay Wildlife Refuge Climate Modeler

Michigan EcoData project by Akshey Deokule. Interactive toy tool that loads USFWS species lists for Don Edwards SF Bay NWR and assigns each species a **Danger Level** from a simple temperature-delta heuristic plus listing/occurrence rules. When Danger Level reaches 100, the model treats that species as “extinct” in-scenario.

**This is a toy heuristic, not a scientific climate or extinction model.** Thresholds are illustrative (EcoData-era experiments with linear/exponential curves). Species lists come from [USFWS Don Edwards San Francisco Bay](https://www.fws.gov/refuge/don-edwards-san-francisco-bay).

## Inputs / outputs

| Input | Description |
|-------|-------------|
| `BirdSheet.csv`, `MammalsSheet.csv`, `AmphibianReptilesSheet.csv`, `FishsSheet.csv` | Bundled sample species tables (repo root) |
| `--temp` / `-t` | Hypothetical temperature °F (baseline **60**) |
| `DATA_DIR` or `--data-dir` | Optional alternate CSV directory |

| Output | Description |
|--------|-------------|
| stdout summary | Per-group head rows + min/max/mean Danger Level |
| `output_*.csv` | Optional scored tables (`--keep-output`) |

## How to run

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# One command — baseline (60 °F)
python climate_modeler.py

# Warmer scenario
python climate_modeler.py --temp 75 --keep-output
```

Optional interactive C++ menu (shells out to the same Python scripts; no Boost):

```bash
make main.exe
./main.exe    # run from repo root
```

Sample captured run: [docs/SAMPLE_RUN.md](docs/SAMPLE_RUN.md).

## Layout notes

- Primary CLI: `climate_modeler.py`
- Legacy helpers used by the C++ menu: `sheet_analyzer.py`, `print_data.py`
- `pyqt_test.py` is an unfinished GUI sketch and is not part of the run path

## Known limitations (toy model)

- Danger Level rules and the temperature curve are hand-tuned EcoData experiments, not validated ecology.
- The original curve mainly increases scores when temperature **falls below** 60 °F; warming above baseline leaves `changeVal` near 0.
- Flora / plant list is not scored. `pyqt_test.py` is unused.
- Optional C++ binary is a menu only; all scoring is Python.
