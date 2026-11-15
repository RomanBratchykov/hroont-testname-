"""Bounded dashboard reads. Metadata discovery is deliberately distinct from raster analysis."""

import asyncio
import calendar
import json
import math
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree

import httpx

POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
VARIABLES = (
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "WS2M",
    "ALLSKY_SFC_SW_DWN",
)
LIMITATIONS = "Historical gridded regional estimates, not station measurements or a forecast. No field-level agronomic validation. Incomplete months are missing; precipitation is summed, other variables are daily means. UTC calendar."


def now():
    return datetime.now(UTC).isoformat()


def power_url(latitude, longitude):
    return (
        POWER
        + "?"
        + urlencode(
            dict(
                latitude=latitude,
                longitude=longitude,
                start="20160101",
                end="20251231",
                parameters=",".join(VARIABLES),
                community="AG",
                format="JSON",
                **{"time-standard": "UTC"},
            )
        )
    )


def cache_read(path, key):
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS dashboard_cache (key TEXT PRIMARY KEY, fetched REAL, raw TEXT, result TEXT)"
        )
        row = db.execute(
            "SELECT result FROM dashboard_cache WHERE key=? AND fetched > ?",
            (key, datetime.now().timestamp() - 21600),
        ).fetchone()
        return json.loads(row[0]) if row else None


def cache_write(path, key, raw, result):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT OR REPLACE INTO dashboard_cache VALUES (?, ?, ?, ?)",
            (
                key,
                datetime.now().timestamp(),
                json.dumps(raw),
                json.dumps(result, allow_nan=False),
            ),
        )
        db.execute(
            "DELETE FROM dashboard_cache WHERE key NOT IN (SELECT key FROM dashboard_cache ORDER BY fetched DESC LIMIT 64)"
        )


def summarize(raw):
    parameters = raw["properties"]["parameter"]
    if not isinstance(parameters, dict) or any(
        not isinstance(parameters.get(v), dict) for v in VARIABLES
    ):
        raise ValueError("Invalid daily series")
    units = {v: raw["parameters"][v]["units"] for v in VARIABLES}
    if any(not isinstance(unit, str) or not unit for unit in units.values()):
        raise ValueError("Missing units")
    # NASA Daily documents corrected precipitation as mm/day; never sum unknown units.
    if units["PRECTOTCORR"].lower().replace(" ", "") not in {
        "mm/day",
        "mm/d",
        "mmday-1",
    }:
        raise ValueError("Unsupported precipitation units")
    fill = raw.get("header", {}).get("fill_value", -999)
    months = []
    complete = True
    for year in range(2016, 2026):
        for month in range(1, 13):
            days = calendar.monthrange(year, month)[1]
            values, coverage = {}, {}
            for variable in VARIABLES:
                series = parameters[variable]
                valid = []
                for day in range(1, days + 1):
                    value = series.get(date(year, month, day).strftime("%Y%m%d"))
                    if (
                        isinstance(value, (float, int))
                        and not isinstance(value, bool)
                        and math.isfinite(value)
                        and value != fill
                        and value != -999
                    ):
                        if variable == "PRECTOTCORR" and value < 0:
                            continue
                        valid.append(value)
                coverage[variable] = len(valid)
                values[variable] = (
                    round(sum(valid) / (1 if variable == "PRECTOTCORR" else days), 3)
                    if len(valid) == days
                    else None
                )
                complete = complete and len(valid) == days
            months.append(
                {
                    "period": f"{year}-{month:02}",
                    "days": days,
                    "values": values,
                    "coverage": coverage,
                }
            )
    return months, {**units, "PRECTOTCORR": "mm/month"}, complete


async def climate(http, cache_path: Path, latitude, longitude):
    url = power_url(latitude, longitude)
    cached = await asyncio.to_thread(cache_read, cache_path, url)
    if cached:
        return {**cached, "cached": True}
    base = {
        "source": "NASA POWER Daily",
        "source_url": url,
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "period": "2016–2025",
        "resolution": "Native POWER grid; meteorology approximately 0.5° × 0.625°, solar approximately 1°",
        "method": "monthly-complete-daily-v1",
        "uncertainty_or_limitations": LIMITATIONS,
        "cached": False,
    }
    try:
        response = await get_with_retry(http, url, timeout=60)
        response.raise_for_status()
        if len(response.content) > 8 * 1024 * 1024:
            raise ValueError("Response too large")
        raw = response.json()
        months, units, complete = summarize(raw)
        result = {
            **base,
            "status": "available" if complete else "partial",
            "months": months,
            "units": units,
            "retrieved_at": now(),
        }
        await asyncio.to_thread(cache_write, cache_path, url, raw, result)
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {
            **base,
            "status": "unavailable",
            "months": [],
            "units": {},
            "retrieved_at": None,
            "reason": "NASA POWER data could not be retrieved or validated. Retry later; no example values have been substituted.",
        }


def source_definitions(latitude, longitude):
    point = f"{longitude},{latitude}"

    def cmr(name, version, temporal=True):
        params = {
            "short_name": name,
            "version": version,
            "point": point,
            "page_size": 1,
        }
        if temporal:
            params["temporal"] = "2025-04-01T00:00:00Z,2025-09-30T23:59:59Z"
        return CMR + "?" + urlencode(params)

    return [
        {
            "id": "power",
            "name": "NASA POWER Daily",
            "urls": [
                power_url(latitude, longitude)
                .replace("start=20160101", "start=20250101")
                .replace("end=20251231", "end=20250101")
            ],
            "kind": "power",
            "variables": ", ".join(VARIABLES),
            "resolution": "Regional meteorology / solar grids",
            "limitation": LIMITATIONS,
        },
        {
            "id": "soilgrids",
            "name": "ISRIC SoilGrids WCS",
            "urls": [
                f"https://maps.isric.org/mapserv?map=/map/{p}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities"
                for p in ["sand", "silt", "clay", "soc", "phh2o", "bdod"]
            ],
            "kind": "wcs",
            "variables": "sand, silt, clay, soc, phh2o, bdod · depth and quantile required",
            "resolution": "250 m · modeled soil",
            "limitation": "ISRIC, not NASA or a measured soil test. Capabilities only; depth, quantile, CRS and scale factors must be validated before raster extraction.",
        },
        {
            "id": "nasadem",
            "name": "NASADEM",
            "urls": [cmr("NASADEM_HGT", "001", False)],
            "kind": "cmr",
            "variables": "Elevation raster → slope, flow accumulation, LS",
            "resolution": "1 arc-second terrain grid",
            "limitation": "Granule metadata only. Raster download and local terrain analysis are not connected; slope and LS are not computed.",
        },
        {
            "id": "hls",
            "name": "NASA HLS S30 / L30",
            "urls": [cmr("HLSS30", "2.0"), cmr("HLSL30", "2.0")],
            "kind": "cmr",
            "variables": "S30 B04/B8A; L30 B04/B05; Fmask",
            "resolution": "30 m satellite imagery",
            "limitation": "2025 Apr–Sep metadata search only. Authenticated band access and cloud masking still required. NDVI is not crop residue or RUSLE C.",
        },
        {
            "id": "gpm",
            "name": "GPM IMERG Final V07",
            "urls": [
                "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGHH.07/",
                cmr("GPM_3IMERGHH", "07"),
            ],
            "kind": "catalog",
            "variables": "Half-hourly precipitation (mm/h)",
            "resolution": "Approximately 0.1°",
            "limitation": "Catalog access only. Earthdata authentication, granule extraction and justified erosivity calculation required. R is not computed.",
        },
        {
            "id": "faostat",
            "name": "FAOSTAT · optional benchmark",
            "urls": [
                "https://fenixservices.fao.org/faostat/api/v1/en/data/QCL?area=230&item=15&element=5510&year=2023"
            ],
            "kind": "fao",
            "variables": "Country/year production, area, yield",
            "resolution": "Country aggregate · Ukraine example, 2023",
            "limitation": "FAO, not NASA. Endpoint/filter check only, not selected-field data, prices, costs or profit.",
        },
    ]


async def get_with_retry(http, url, *, timeout, headers=None, slots=None):
    """At most one retry for transient GET failures; credentials never follow redirects."""
    for attempt in range(2):
        try:
            if slots is None:
                response = await http.get(
                    url, timeout=timeout, headers=headers or {}, follow_redirects=False
                )
            else:
                async with slots:
                    response = await http.get(
                        url,
                        timeout=timeout,
                        headers=headers or {},
                        follow_redirects=False,
                    )
        except httpx.TransportError:
            if attempt:
                raise
            await asyncio.sleep(0.2)
            continue
        if attempt or response.status_code not in {429, 502, 503, 504}:
            return response
        try:
            delay = float(response.headers.get("retry-after", ".2"))
        except ValueError:
            return (
                response  # An HTTP-date or unknown delay requires a later manual retry.
            )
        if not 0 <= delay <= 2:
            return response
        await asyncio.sleep(delay)
    raise RuntimeError("GET retry loop did not return")


async def check_sources(
    http, latitude, longitude, *, earthdata_token="", nasa_token=""
):
    slots = asyncio.Semaphore(4)

    async def probe(source, url):
        item = {"url": url, "status": "unavailable"}
        try:
            parsed = urlsplit(url)
            authenticated = (
                earthdata_token
                and parsed.scheme == "https"
                and parsed.hostname
                in {
                    "cmr.earthdata.nasa.gov",
                    "gpm1.gesdisc.eosdis.nasa.gov",
                }
            )
            headers = (
                {"Authorization": f"Bearer {earthdata_token}"} if authenticated else {}
            )
            if (
                source["kind"] == "nasa_key"
                and parsed.scheme == "https"
                and parsed.hostname == "api.nasa.gov"
            ):
                headers = {"X-Api-Key": nasa_token}
            response = await get_with_retry(
                http, url, timeout=12, headers=headers, slots=slots
            )
            item["http_status"] = response.status_code
            location = urlsplit(response.headers.get("location", ""))
            if response.status_code in (401, 403) or (
                response.is_redirect and location.hostname == "urs.earthdata.nasa.gov"
            ):
                return {
                    **item,
                    "status": "authentication_required",
                    "reason": "credentials_missing_or_rejected",
                }
            if response.status_code == 429:
                return {**item, "reason": "rate_limited"}
            response.raise_for_status()
            if len(response.content) > 1024 * 1024:
                raise ValueError("Oversized source response")
            if source["kind"] == "cmr" or parsed.hostname == "cmr.earthdata.nasa.gov":
                entries = response.json()["feed"]["entry"]
                if not isinstance(entries, list):
                    raise ValueError("Invalid CMR entries")
                status = "metadata_only" if entries else "no_coverage"
            elif source["kind"] == "wcs":
                root = ElementTree.fromstring(response.content)
                if root.tag.split("}")[-1] != "Capabilities":
                    raise ValueError("Not WCS capabilities")
                status = "metadata_only"
            elif source["kind"] == "power":
                data = response.json()
                if not all(v in data["properties"]["parameter"] for v in VARIABLES):
                    raise ValueError("Missing variables")
                status = "reachable"
            elif source["kind"] == "fao":
                rows = response.json()["data"]
                if not isinstance(rows, list):
                    raise ValueError("Invalid FAOSTAT rows")
                status = "reachable" if rows else "no_coverage"
            elif source["kind"] == "nasa_key":
                if not isinstance(response.json().get("near_earth_objects"), list):
                    raise ValueError("Invalid NASA Open APIs response")
                status = "reachable"
            else:
                if "GPM_3IMERGHH" not in response.text:
                    raise ValueError("Unexpected catalog")
                status = "catalog_only"
            return {**item, "status": status}
        except httpx.TimeoutException:
            return {**item, "reason": "timeout"}
        except httpx.HTTPStatusError:
            return {
                **item,
                "reason": "redirect_not_followed"
                if 300 <= item["http_status"] < 400
                else "http_error",
            }
        except httpx.TransportError:
            return {**item, "reason": "connection_failed"}
        except (
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            ElementTree.ParseError,
        ):
            return {**item, "reason": "invalid_response"}

    async def check(source):
        checks = await asyncio.gather(*(probe(source, url) for url in source["urls"]))
        statuses = {item["status"] for item in checks}
        status = next(iter(statuses)) if len(statuses) == 1 else "partial"
        return {k: v for k, v in source.items() if k not in {"urls", "kind"}} | {
            "status": status,
            "source_url": source["urls"][0],
            "checked_at": now(),
            "checks": checks,
        }

    async def nasa_access():
        url = "https://api.nasa.gov/neo/rest/v1/neo/browse?page=0&size=1"
        base = {
            "name": "NASA Open APIs",
            "source_url": url,
            "checked_at": now(),
            "limitation": "Credential/service check using NeoWs metadata only. Not field climate, Earthdata access or agronomic analysis.",
        }
        if not nasa_token:
            return {
                **base,
                "status": "not_configured",
                "reason": "Set NASA_TOKEN in the backend environment.",
            }
        return {**base, **await probe({"kind": "nasa_key"}, url)}

    sources, nasa = await asyncio.gather(
        asyncio.gather(*(check(s) for s in source_definitions(latitude, longitude))),
        nasa_access(),
    )
    return {
        "sources": sources,
        "nasa_open_api": nasa,
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
    }
