"""Durable one-command workflows; return summaries rather than raw arrays to a model."""

import json
import uuid
from pathlib import Path

from .analysis import analyze
from .contracts import object_params
from .pipeline import collect, connection, encoded, now, validate
from .report import dashboard, export_csv

DEFAULT_SEASONS = [
    {"name": "Озимі зернові: орієнтовне вікно", "start": "10-01", "end": "06-30"},
    {"name": "Ярі культури: орієнтовне вікно", "start": "04-01", "end": "09-30"},
]


def run(db, parameters, directory="data/reports"):
    """Collect selected sources, persist analysis and exports; preserve source failures."""
    object_params(parameters)
    unknown = set(parameters) - {"latitude", "longitude", "start", "end", "sources", "options", "refresh", "cache_hours", "analysis", "dashboard", "field_name"}
    if unknown:
        raise ValueError(f"Unknown workflow parameters: {sorted(unknown)}")
    collection = {k: v for k, v in parameters.items() if k not in {"analysis", "dashboard", "field_name"}}
    validate(collection)
    analysis_options = object_params(parameters.get("analysis", {}))
    chart_options = object_params(parameters.get("dashboard", {}))
    if set(analysis_options) - {"heat_threshold", "frost_threshold", "dry_threshold", "seasons"}:
        raise ValueError("Unknown analysis options")
    if set(chart_options) - {"cards", "title"}:
        raise ValueError("Unknown dashboard options")
    name = parameters.get("field_name", "Пілотне поле")
    if not isinstance(name, str) or not 1 <= len(name) <= 150:
        raise ValueError("field_name must be 1..150 characters")
    identifier = uuid.uuid4().hex
    output = Path(directory) / identifier
    output.mkdir(parents=True, exist_ok=True)
    started = now()
    conn = connection(db)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS runs (
          id TEXT PRIMARY KEY, status TEXT NOT NULL, started_at TEXT NOT NULL,
          finished_at TEXT, parameters TEXT NOT NULL, result TEXT)""")
        with conn:
            conn.execute("INSERT INTO runs VALUES(?,?,?,?,?,?)", (identifier, "running", started, None, encoded(parameters), None))
        result = dict(run_id=identifier, status="running", started_at=started, sources={}, artifacts={})
        try:
            collected = collect(db, collection)
            result["sources"] = collected
            errors = [source for source, info in collected.items() if info["status"] == "error"]
            result["status"] = "partial" if errors else "completed"
            result["warnings"] = []
            for source, info in collected.items():
                if info.get("possibly_truncated"):
                    result["warnings"].append(f"{source}: catalog page limit may have truncated results")
                if source not in ("power", "faostat") and info["status"] != "error":
                    result["warnings"].append(f"{source}: catalog/planned assets only; download and raster processing are separate")
            weather = collected.get("power", {})
            if weather.get("status") in ("collected", "cached"):
                ref = weather["request_id"]
                analysis_parameters = dict(analysis_options, request_id=ref)
                analysis_parameters.setdefault("seasons", DEFAULT_SEASONS)
                metrics = analyze(db, analysis_parameters)
                (output / "analysis.json").write_text(encoded(metrics), encoding="utf-8")
                report = dashboard(db, dict(analysis_parameters, **chart_options,
                    **({} if "title" in chart_options else {"title": name + " · кліматичний огляд"})), output / "dashboard.html")
                export_csv(db, {"request_id": ref, "kind": "observation"}, output / "weather.csv")
                result["summary"] = report["summary"]
                result["artifacts"] = {name: str((output / filename).resolve()) for name, filename in
                    (("dashboard", "dashboard.html"), ("analysis", "analysis.json"), ("csv", "weather.csv"))}
                result["quality"] = dict(complete_years=metrics["n"], excluded_years=metrics["excluded_years"],
                    missing_by_variable=metrics["period"]["missing_by_variable"])
                if not metrics["period"]["complete"]:
                    result["warnings"].append("Climate metrics have incomplete coverage; nulls are not zero")
            if errors and len(errors) == len(collected):
                result["status"] = "failed"
            result["finished_at"] = now()
        except Exception as exc:
            result.update(status="failed", finished_at=now(), error=f"{type(exc).__name__}: {exc}")
        with conn:
            conn.execute("UPDATE runs SET status=?,finished_at=?,result=? WHERE id=?",
                         (result["status"], result["finished_at"], encoded(result), identifier))
        (output / "manifest.json").write_text(encoded(result), encoding="utf-8")
        return result
    finally:
        conn.close()


def inspect_run(db, parameters):
    object_params(parameters)
    identifier = parameters.get("run_id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("run_id is required")
    conn = connection(db)
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runs'").fetchone():
            raise ValueError("No workflow runs found")
        item = conn.execute("SELECT * FROM runs WHERE id=?", (identifier,)).fetchone()
        if not item:
            raise ValueError("Unknown run_id")
        validate(json.loads(item["parameters"]))
        return json.loads(item["result"]) if item["result"] else dict(run_id=identifier, status=item["status"])
    finally:
        conn.close()
