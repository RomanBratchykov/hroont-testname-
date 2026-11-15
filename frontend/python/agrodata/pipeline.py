"""Python 3.10+, standard library only. Public functions accept JSON-compatible dicts."""

import hashlib
import json
import math
import os
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .contracts import dates, integer, number, object_params, request_ref, strings
from .region import require_region

VERSION = "0.2.0"
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
PRODUCTS = {"hls_s30": ("HLSS30", "2.0"), "hls_l30": ("HLSL30", "2.0"),
            "gpm": ("GPM_3IMERGHH", "07"), "nasadem": ("NASADEM_HGT", "001"),
            "srtm": ("SRTMGL1", "003"), "smap": ("SPL3SMP", "009")}
POWER_VARS = {"T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"}


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def now():
    return datetime.now(timezone.utc).isoformat()


def request_json(url, headers=None):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": "AgroResilience/" + VERSION, **(headers or {})}), timeout=60) as response:
                data = json.load(response)
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object from data service")
                return data
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** attempt)


def connection(db):
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
      CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY, source TEXT NOT NULL, parameters TEXT NOT NULL,
        fetched_at TEXT NOT NULL, source_url TEXT NOT NULL, raw_json TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS records (
        request_id TEXT NOT NULL REFERENCES requests(id), record_key TEXT NOT NULL,
        source TEXT NOT NULL, observed_at TEXT NOT NULL, variable TEXT NOT NULL,
        value REAL, unit TEXT, kind TEXT NOT NULL, metadata TEXT NOT NULL,
        PRIMARY KEY(request_id, record_key)
      );
      CREATE INDEX IF NOT EXISTS records_filter ON records(source, variable, observed_at);
      CREATE TABLE IF NOT EXISTS failures (
        id INTEGER PRIMARY KEY, source TEXT NOT NULL, request_id TEXT NOT NULL,
        failed_at TEXT NOT NULL, error TEXT NOT NULL
      );
    """)
    return conn


def validate(p):
    object_params(p)
    lat = number(p.get("latitude"), "latitude", -90, 90)
    lon = number(p.get("longitude"), "longitude", -180, 180)
    require_region(lat, lon)
    start, end = dates(p)
    return lat, lon, start, end


def row(source, observed, variable, value, unit, kind, metadata):
    if value is not None and (isinstance(value, bool) or not math.isfinite(float(value))):
        raise ValueError("Invalid numeric observation")
    return dict(source=source, observed_at=observed, variable=variable, value=value,
                unit=unit, kind=kind, metadata=metadata)


def fetch_power(p):
    lat, lon, start, end = validate(p)
    variables = strings(p.get("variables", ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]), "variables", POWER_VARS)
    url = POWER + "?" + urlencode(dict(latitude=lat, longitude=lon, start=start.strftime("%Y%m%d"),
        end=end.strftime("%Y%m%d"), parameters=",".join(variables), community="AG", format="JSON", **{"time-standard": "UTC"}))
    data = request_json(url)
    result = []
    for variable in variables:
        unit = data["parameters"][variable]["units"]
        for day, value in data["properties"]["parameter"][variable].items():
            observed = datetime.strptime(day, "%Y%m%d").date().isoformat()
            if not start <= date.fromisoformat(observed) <= end:
                continue
            missing = value is None or value == data.get("header", {}).get("fill_value", -999)
            result.append(row("power", observed, variable, None if missing else value, unit, "observation",
                dict(product="NASA POWER Daily", product_version=data.get("header", {}).get("api", {}).get("version"),
                     latitude=lat, longitude=lon, crs="EPSG:4326", spatial_support="coarse grid point",
                     source_coordinates=data.get("geometry", {}).get("coordinates"),
                     calendar="UTC", quality_flags=["missing"] if missing else [],
                     license="See NASA POWER source metadata")))
    return url, data, result


def fetch_catalog(source, p):
    lat, lon, start, end = validate(p)
    product, version = PRODUCTS[source]
    limit = integer(p.get("max_pages", 1), "max_pages", 1, 100)
    pages, rows, seen = [], [], set()
    base = dict(short_name=product, version=version, point=f"{lon},{lat}", page_size=100,
                sort_key=["start_date", "producer_granule_id"])
    if p.get("collection_id"):
        base.pop("short_name")
        base.pop("version")
        base["collection_concept_id"] = p["collection_id"]
    if source not in ("nasadem", "srtm"):
        base["temporal"] = f"{start}T00:00:00Z,{end}T23:59:59Z"
    for page in range(1, limit + 1):
        url = CMR + "?" + urlencode(dict(base, page_num=page), doseq=True)
        data = request_json(url)
        pages.append(data)
        entries = data["feed"]["entry"]
        for item in entries:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            rows.append(row(source, item.get("time_start", ""), "granule", None, None, "asset",
                dict(product=product, product_version=version, granule_id=item["id"],
                     title=item.get("title"), links=item.get("links", []),
                     latitude=lat, longitude=lon, crs="EPSG:4326", spatial_support="intersecting granule",
                     quality_flags=["metadata_only", "raster_processing_required"],
                     license="See granule links and collection metadata")))
        if len(entries) < 100:
            break
    return CMR + "?" + urlencode(base, doseq=True), {"pages": pages, "possibly_truncated": len(entries) == 100}, rows


def fetch_faostat(p):
    _, _, start, end = validate(p)
    if not p.get("items") or not p.get("elements"):
        raise ValueError("FAOSTAT requires items and elements codes")
    for name in ("items", "elements"):
        if not isinstance(p[name], list) or len(p[name]) > 100:
            raise ValueError(f"FAOSTAT {name} must be a list of at most 100 integer codes")
        for code in p[name]:
            integer(code, name, 1, 1000000)
    base = dict(area=230, item=",".join(map(str, p["items"])),
                element=",".join(map(str, p["elements"])),
                year=",".join(map(str, range(start.year, end.year + 1))), page_size=100)
    pages, result = [], []
    limit = integer(p.get("max_pages", 1), "max_pages", 1, 100)
    service = p.get("service", "current")
    if service not in ("current", "legacy"):
        raise ValueError("FAOSTAT service must be current or legacy")
    headers = {}
    if service == "current":
        token = os.environ.get("FAOSTAT_TOKEN")
        if not token:
            raise ValueError("Current FAOSTAT API requires FAOSTAT_TOKEN; the legacy endpoint was unavailable in live checks")
        endpoint = "https://faostatservices.fao.org/api/v1/en/data/QCL"
        headers = {"Authorization": "Bearer " + token}
        # Current official API has no documented pagination: this is a bounded country/item/year query.
        base.pop("page_size")
        base["output_type"] = "objects"
        limit = 1
    else:
        endpoint = "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL"
    for page in range(1, limit + 1):
        url = endpoint + "?" + urlencode(dict(base, page_number=page) if service == "legacy" else base)
        data = request_json(url, headers=headers)
        pages.append(data)
        entries = data["data"]
        for item in entries:
            result.append(row("faostat", f'{int(item["Year"])}-01-01',
                f'{item["Item Code"]}:{item["Element Code"]}', item.get("Value"), item.get("Unit"),
                "observation", dict(product="FAOSTAT QCL", product_version=None,
                spatial_support="Ukraine national statistic", crs=None, item=item,
                quality_flags=["not_field_level", "annual_statistic"], license="FAOSTAT source terms")))
        if len(entries) < 100:
            break
    return endpoint + "?" + urlencode(base), {"pages": pages, "possibly_truncated": service == "legacy" and len(entries) == 100}, result


def fetch_soilgrids(p):
    lat, lon, _, _ = validate(p)
    properties = p.get("properties", ["clay", "sand", "silt", "soc", "phh2o", "bdod"])
    depths = p.get("depths", ["0-5cm"])
    if not properties or not set(properties) <= {"clay", "sand", "silt", "soc", "phh2o", "bdod"}:
        raise ValueError("Unsupported SoilGrids property")
    if not depths or not set(depths) <= {"0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"}:
        raise ValueError("Unsupported SoilGrids depth")
    # WCS coverage links are persisted as assets, never mistaken for soil measurements.
    result = []
    for prop in properties:
        for depth in depths:
            coverage = f"{prop}_{depth}_mean"
            url = "https://maps.isric.org/mapserv?" + urlencode({"map": f"/map/{prop}.map",
                "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCoverage",
                "COVERAGEID": coverage, "FORMAT": "image/tiff",
                "SUBSETTINGCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
                "SUBSET": [f"Long({lon - .002},{lon + .002})", f"Lat({lat - .002},{lat + .002})"]}, doseq=True)
            result.append(row("soilgrids", "", prop, None, None, "asset", dict(
                product="SoilGrids 250m", product_version="2.0", depth=depth,
                latitude=lat, longitude=lon, crs="EPSG:4326", spatial_support="point envelope at 250m",
                links=[{"href": url}], quality_flags=["planned_asset", "not_downloaded", "raster_processing_required"],
                license="CC BY 4.0")))
    return "https://maps.isric.org", {"status": "planned_wcs_requests"}, result


def collect(db, parameters):
    """Collect selected sources only; commits each source atomically, preserves failures."""
    validate(parameters)
    sources = strings(parameters.get("sources", ["power"]), "sources", {"power", "faostat", "soilgrids", *PRODUCTS})
    ttl = number(parameters.get("cache_hours", 24 * 30), "cache_hours", 0, 24 * 3650)
    if not isinstance(parameters.get("refresh", False), bool):
        raise ValueError("refresh must be a boolean")
    options_map = object_params(parameters.get("options", {}))
    if set(options_map) - {"power", "faostat", "soilgrids", *PRODUCTS}:
        raise ValueError("Unknown source in options")
    for source, opts in options_map.items():
        object_params(opts)
        allowed = {"variables"} if source == "power" else {"properties", "depths"} if source == "soilgrids" else {"items", "elements", "max_pages", "service"} if source == "faostat" else {"max_pages", "collection_id"}
        if set(opts) - allowed:
            raise ValueError(f"Unknown options for {source}: {sorted(set(opts)-allowed)}")
    report = {}
    conn = connection(db)
    try:
        for source in dict.fromkeys(sources):
            p = {k: parameters[k] for k in ("latitude", "longitude", "start", "end")}
            options = object_params(options_map.get(source, {}))
            if set(options) & {"latitude", "longitude", "start", "end"}:
                raise ValueError("Source options cannot override field location or dates")
            p.update(options)
            if source == "power":
                p["variables"] = sorted(strings(p.get("variables", ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]), "variables", POWER_VARS))
            key = hashlib.sha256(encoded([VERSION, source, p]).encode()).hexdigest()
            cached = conn.execute("SELECT fetched_at,raw_json FROM requests WHERE id=?", (key,)).fetchone()
            fresh = cached and (datetime.now(timezone.utc) - datetime.fromisoformat(cached[0])).total_seconds() < ttl * 3600
            if fresh and not parameters.get("refresh", False):
                count = conn.execute("SELECT COUNT(*) FROM records WHERE request_id=?", (key,)).fetchone()[0]
                report[source] = dict(status="cached", request_id=key, fetched_at=cached[0], count=count,
                    possibly_truncated=json.loads(cached[1]).get("possibly_truncated", False))
                continue
            try:
                if source in PRODUCTS:
                    url, raw, records = fetch_catalog(source, p)
                else:
                    url, raw, records = {"power": fetch_power, "faostat": fetch_faostat,
                                         "soilgrids": fetch_soilgrids}[source](p)
                fetched = now()
                with conn:
                    conn.execute("""INSERT INTO requests VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                        fetched_at=excluded.fetched_at, source_url=excluded.source_url, raw_json=excluded.raw_json""",
                                 (key, source, encoded(p), fetched, url, encoded(raw)))
                    conn.execute("DELETE FROM records WHERE request_id=?", (key,))
                    for record in records:
                        metadata = dict(record["metadata"], retrieved_at=fetched, source_url=url, processing_version=VERSION)
                        identity = [record["observed_at"], record["variable"], metadata.get("granule_id"), metadata.get("depth")]
                        record_key = hashlib.sha256(encoded(identity).encode()).hexdigest()
                        conn.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?)", (key, record_key, source,
                            record["observed_at"], record["variable"], record["value"], record["unit"], record["kind"], encoded(metadata)))
                report[source] = dict(status="planned" if source == "soilgrids" else "collected", request_id=key,
                    count=len(records), possibly_truncated=raw.get("possibly_truncated", False))
            except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as exc:
                message = f"{type(exc).__name__}: {exc}"
                with conn:
                    conn.execute("INSERT INTO failures(source,request_id,failed_at,error) VALUES(?,?,?,?)", (source, key, now(), message))
                report[source] = dict(status="error", request_id=key, error=message,
                    stale_available=bool(cached), stale_fetched_at=cached[0] if cached else None)
    finally:
        conn.close()
    return report


def query(db, parameters):
    """Read one ingestion request, preventing accidental combination of different points."""
    request_id = request_ref(parameters)
    limit = integer(parameters.get("limit", 1000), "limit", 1, 100000)
    offset = integer(parameters.get("offset", 0), "offset", 0, 10000000)
    clauses, args = ["request_id=?"], [request_id]
    for name, column in (("variable", "variable"), ("kind", "kind")):
        if name in parameters:
            clauses.append(column + "=?")
            args.append(parameters[name])
    for name, operator in (("start", ">="), ("end", "<=")):
        if name in parameters:
            clauses.append("substr(observed_at,1,10)" + operator + "?")
            args.append(date.fromisoformat(parameters[name]).isoformat())
    conn = connection(db)
    try:
        stored = conn.execute("SELECT parameters FROM requests WHERE id=?", (request_id,)).fetchone()
        if not stored:
            raise ValueError("Unknown request_id")
        location = json.loads(stored["parameters"])
        require_region(location["latitude"], location["longitude"])
        records = conn.execute("SELECT * FROM records WHERE " + " AND ".join(clauses) +
            " ORDER BY observed_at, variable, record_key LIMIT ? OFFSET ?", [*args, limit, offset]).fetchall()
        return [dict(dict(record), metadata=json.loads(record["metadata"])) for record in records]
    finally:
        conn.close()


def dashboard(db, parameters, output):
    """Render a single variable or a multi-card climate report."""
    from .report import dashboard as render
    return render(db, parameters, output)
