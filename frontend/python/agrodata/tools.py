"""Model-facing tools with fixed storage paths and bounded responses."""

from pathlib import Path
from uuid import uuid4

from .analysis import analyze
from .contracts import integer, object_params, schema_check
from .pipeline import PRODUCTS, POWER_VARS, query
from .report import CARDS, dashboard
from .workflow import inspect_run, run
from .assets import download, sample_soil
from .rasters import process_dem, process_hls
from .region import bounds

WEST, SOUTH, EAST, NORTH = bounds()

SOURCES = ["power", "faostat", "soilgrids", *PRODUCTS]
SEASON_SCHEMA = {"type": "object", "additionalProperties": False,
    "properties": {"name": {"type": "string", "maxLength": 100},
        "start": {"type": "string", "pattern": r"^\d{2}-\d{2}$"},
        "end": {"type": "string", "pattern": r"^\d{2}-\d{2}$"}}, "required": ["name", "start", "end"]}
ANALYSIS_PROPERTIES = {
    "heat_threshold": {"type": "number", "minimum": -80, "maximum": 80},
    "frost_threshold": {"type": "number", "minimum": -80, "maximum": 80},
    "dry_threshold": {"type": "number", "minimum": 0, "maximum": 1000},
    "seasons": {"type": "array", "maxItems": 20, "items": SEASON_SCHEMA},
}
REF = {"request_id": {"type": "string", "maxLength": 128}}
RUN_PROPERTIES = {
    "latitude": {"type": "number", "minimum": SOUTH, "maximum": NORTH},
    "longitude": {"type": "number", "minimum": WEST, "maximum": EAST},
    "start": {"type": "string", "format": "date"}, "end": {"type": "string", "format": "date"},
    "field_name": {"type": "string", "maxLength": 150},
    "sources": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": SOURCES}},
    "cache_hours": {"type": "number", "minimum": 0, "maximum": 87600},
    "refresh": {"type": "boolean"},
    "options": {"type": "object", "additionalProperties": False, "properties": {
        "power": {"type": "object", "additionalProperties": False, "properties": {
            "variables": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": sorted(POWER_VARS)}}}},
        "soilgrids": {"type": "object", "additionalProperties": False, "properties": {
            "properties": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": ["sand", "silt", "clay", "soc", "phh2o", "bdod"]}},
            "depths": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]}}}},
        "faostat": {"type": "object", "additionalProperties": False, "properties": {
            "items": {"type": "array", "minItems": 1, "maxItems": 100, "items": {"type": "integer", "minimum": 1, "maximum": 1000000}},
            "elements": {"type": "array", "minItems": 1, "maxItems": 100, "items": {"type": "integer", "minimum": 1, "maximum": 1000000}},
            "service": {"type": "string", "enum": ["current", "legacy"]}}},
        **{source: {"type": "object", "additionalProperties": False, "properties": {
            "max_pages": {"type": "integer", "minimum": 1, "maximum": 100},
            "collection_id": {"type": "string", "pattern": r"C\d+-[A-Za-z0-9_]+"}}} for source in PRODUCTS},
    }},
    "analysis": {"type": "object", "additionalProperties": False, "properties": ANALYSIS_PROPERTIES},
    "dashboard": {"type": "object", "additionalProperties": False, "properties": {
        "title": {"type": "string", "maxLength": 200},
        "cards": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": sorted(CARDS)}}}},
}


def definition(name, description, properties, required):
    return {"name": name, "description": description,
            "parameters": {"type": "object", "additionalProperties": False, "properties": properties, "required": required}}


def definitions():
    return [
        definition("agro_run", "Collect daily climate, save SQLite data, calculate exposure and generate offline dashboard/CSV. Returns compact summary and artifact paths; no raw arrays. Only Kharkiv Oblast (UA-63); the administrative polygon is checked at runtime.", RUN_PROPERTIES, ["latitude", "longitude", "start", "end"]),
        definition("agro_analyze", "Analyze a stored POWER request. Thresholds are heuristics, never calibrated crop damage probabilities.", REF | ANALYSIS_PROPERTIES | {
            "start": {"type": "string", "format": "date"}, "end": {"type": "string", "format": "date"}}, ["request_id"]),
        definition("agro_read", "Read at most 1000 stored records per call; prefer agro_analyze or agro_run for model context.", REF | {
            "variable": {"type": "string"}, "kind": {"type": "string", "enum": ["observation", "asset"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
            "offset": {"type": "integer", "minimum": 0, "maximum": 10000000}}, ["request_id"]),
        definition("agro_dashboard", "Generate a climate dashboard from an existing request without collecting again.", REF | ANALYSIS_PROPERTIES | {
            "variable": {"type": "string", "maxLength": 100},
            "title": {"type": "string", "maxLength": 200},
            "cards": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": sorted(CARDS)}}}, ["request_id"]),
        definition("agro_inspect_run", "Read persisted workflow status and summary.", {"run_id": {"type": "string"}}, ["run_id"]),
        definition("agro_download", "Download bounded selected catalog assets. NASA files may require EARTHDATA_TOKEN configured by the host. Files stay on disk.", REF | {
            "max_files": {"type": "integer", "minimum": 1, "maximum": 12},
            "max_bytes": {"type": "integer", "minimum": 1, "maximum": 200000000},
            "granule_id": {"type": "string", "maxLength": 150},
            "contains": {"type": "string", "maxLength": 100},
            "bands": {"type": "array", "minItems": 1, "items": {"type": "string", "enum": ["B04", "B05", "B8A", "Fmask"]}}}, ["request_id"]),
        definition("agro_process", "Process already downloaded soil, HLS or DEM assets. Uses Python; returns a bounded summary. No field-wide or calibrated agronomic claims.", REF | {
            "processor": {"type": "string", "enum": ["soil", "hls", "dem"]},
            "granule_id": {"type": "string", "maxLength": 150}}, ["request_id", "processor"]),
    ]


def invoke(name, arguments, db="data/agro.sqlite3", directory="data/reports"):
    """Storage paths come from the host application, never from model arguments."""
    object_params(arguments)
    specs = {tool["name"]: tool["parameters"] for tool in definitions()}
    if name not in specs:
        raise ValueError("Unknown model tool")
    spec = specs[name]
    schema_check(arguments, spec)
    if name == "agro_run":
        return run(db, arguments, directory)
    if name == "agro_read":
        args = dict(arguments)
        args["limit"] = integer(args.get("limit", 100), "limit", 1, 1000)
        return query(db, args)
    if name == "agro_inspect_run":
        return inspect_run(db, arguments)
    if name == "agro_download":
        files = download(db, arguments, Path(directory).parent / "assets")
        return dict(count=len(files), files=[{k: f[k] for k in ("path", "bytes", "sha256", "status")} for f in files])
    if name == "agro_process":
        result = {"soil": sample_soil, "hls": process_hls, "dem": process_dem}[arguments["processor"]](db, arguments)
        if "processed" in result:
            return dict(processed_count=len(result["processed"]), skipped_count=len(result["skipped"]),
                processed_sample=result["processed"][:5], skipped_sample=result["skipped"][:5])
        return result
    if name == "agro_dashboard":
        return dashboard(db, arguments, Path(directory) / (uuid4().hex + ".html"))
    result = analyze(db, arguments)
    # No daily observations or hundreds of monthly values in a model context.
    return {k: result[k] for k in ("request_id", "period", "annual_rainfall", "thresholds", "provenance", "caveats")} | {
        "seasons": [dict(name=s["name"], rainfall=s["rainfall"]) for s in result["seasons"]],
        "excluded_years": result["excluded_years"]}
