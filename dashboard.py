#!/usr/bin/env python3
"""Scrollable explore dashboard for the Don Edwards toy climate modeler.

  python dashboard.py
  # → http://127.0.0.1:5050
"""

from __future__ import annotations

import traceback
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from climate_modeler import (
    AVG_TEMP_F,
    SHEETS,
    TAXON_LABELS,
    load_and_score,
    resolve_data_dir,
    summarize,
    temperature_change_value,
)
from refresh_data import refresh as refresh_species_data

REPO_ROOT = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(REPO_ROOT / "templates"),
    static_folder=str(REPO_ROOT / "static"),
)


def _temp_from_request() -> int:
    raw = request.args.get("temp", request.json.get("temp") if request.is_json else None)
    try:
        temp = int(raw if raw is not None else AVG_TEMP_F)
    except (TypeError, ValueError):
        temp = AVG_TEMP_F
    return max(0, min(99, temp))


def _meta_payload() -> dict:
    meta_path = resolve_data_dir() / "refresh_meta.json"
    if meta_path.is_file():
        import json

        try:
            return json.loads(meta_path.read_text())
        except Exception:
            return {"ok": False, "message": "Could not parse refresh_meta.json"}
    return {
        "ok": True,
        "mode": "unknown",
        "message": "No refresh yet — using whatever CSVs are in data/ (or bundled).",
    }


@app.get("/")
def index():
    return render_template("dashboard.html", baseline=AVG_TEMP_F)


@app.get("/api/summary")
def api_summary():
    temp = _temp_from_request()
    change = temperature_change_value(temp)
    frames = load_and_score(resolve_data_dir(), change)
    payload = summarize(frames, temp, change)
    payload["refresh_meta"] = _meta_payload()
    return jsonify(payload)


@app.get("/api/taxa/<key>")
def api_taxa(key: str):
    if key not in SHEETS:
        return jsonify({"error": f"Unknown taxa key: {key}"}), 404
    temp = _temp_from_request()
    q = (request.args.get("q") or "").strip().casefold()
    change = temperature_change_value(temp)
    frames = load_and_score(resolve_data_dir(), change)
    df = frames[key]
    if q:
        mask = (
            df["Common Name"].astype(str).str.casefold().str.contains(q, na=False)
            | df["Scientific Name"].astype(str).str.casefold().str.contains(q, na=False)
        )
        df = df[mask]
    # Sort by danger desc then name
    df = df.sort_values(["Danger Level", "Common Name"], ascending=[False, True])
    cols = [
        c
        for c in (
            "Common Name",
            "Scientific Name",
            "Danger Level",
            "Occurrence",
            "Classification",
            "Federal",
            "State",
            "Source",
            "Obs Count",
        )
        if c in df.columns
    ]
    records = df[cols].fillna("").to_dict(orient="records")
    # histogram bins
    dangers = df["Danger Level"].tolist()
    return jsonify(
        {
            "key": key,
            "label": TAXON_LABELS[key],
            "temp_f": temp,
            "change_val": change,
            "count": len(records),
            "rows": records,
            "danger_values": dangers,
        }
    )


@app.post("/api/refresh")
def api_refresh():
    body = request.get_json(silent=True) or {}
    bundled_only = bool(body.get("bundled_only", False))
    use_inat = bool(body.get("use_inat", False))
    try:
        meta = refresh_species_data(
            prefer_live=not bundled_only,
            use_inat=use_inat,
            bundled_only=bundled_only,
        )
        return jsonify(meta)
    except Exception as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": str(exc),
                    "trace": traceback.format_exc(limit=5),
                }
            ),
            500,
        )


@app.get("/api/health")
def api_health():
    data_dir = resolve_data_dir()
    files = {}
    for _key, (infile, _out, _n) in SHEETS.items():
        files[infile] = (data_dir / infile).is_file()
    return jsonify(
        {
            "ok": True,
            "data_dir": str(data_dir),
            "files": files,
            "refresh_meta": _meta_payload(),
        }
    )


def main() -> None:
    # Ensure data/ has CSVs before first paint
    data_dir = resolve_data_dir()
    missing = [
        infile
        for _k, (infile, _o, _n) in SHEETS.items()
        if not (data_dir / infile).is_file()
    ]
    if missing:
        print(f"Missing {missing}; restoring bundled …")
        refresh_species_data(prefer_live=False)

    print("Don Edwards explore dashboard → http://127.0.0.1:5050")
    print("Toy heuristic — not a scientific model.")
    app.run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
