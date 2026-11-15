"""Explicit, bounded raster downloads. Credentials are never stored in SQLite."""

import hashlib
import math
import os
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

from .pipeline import connection, encoded, now, query
from .contracts import integer


def trusted(url):
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return parsed.scheme == "https" and (host.endswith(".nasa.gov") or host.endswith(".isric.org")) and not parsed.username and not parsed.password


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not trusted(newurl):
            raise ValueError("Redirect outside trusted NASA/ISRIC HTTPS hosts")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected:
            redirected.remove_header("Authorization")
        return redirected


def download(db, parameters, directory):
    """Select stored asset links by request and optional filename substring."""
    max_files = integer(parameters.get("max_files", 1), "max_files", 1, 100)
    max_bytes = integer(parameters.get("max_bytes", 100_000_000), "max_bytes", 1, 1_000_000_000)
    records = query(db, dict(request_id=parameters["request_id"], kind="asset", limit=100000))
    bands = parameters.get("bands")
    if bands is not None and (not isinstance(bands, list) or not bands or not set(bands) <= {"B04", "B05", "B8A", "Fmask"}):
        raise ValueError("bands must contain HLS B04, B05, B8A or Fmask")
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    opener = build_opener(SafeRedirect())
    result, seen = [], set()
    conn = connection(db)
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS files (
          request_id TEXT NOT NULL, url TEXT NOT NULL, path TEXT NOT NULL,
          sha256 TEXT NOT NULL, bytes INTEGER NOT NULL, downloaded_at TEXT NOT NULL,
          PRIMARY KEY(request_id, url))""")
        for record in records:
            if parameters.get("granule_id") and record["metadata"].get("granule_id") != parameters["granule_id"]:
                continue
            for link in record["metadata"].get("links", []):
                url = link.get("href", "")
                if url in seen or not trusted(url) or link.get("inherited"):
                    continue
                parsed = urlparse(url)
                if bands is not None and not any(parsed.path.endswith("." + band + ".tif") for band in bands):
                    continue
                is_wcs = record["source"] == "soilgrids"
                if not is_wcs and not parsed.path.lower().endswith((".tif", ".tiff", ".nc", ".nc4", ".h5", ".hdf", ".zip")):
                    continue
                if parameters.get("contains", "") not in url:
                    continue
                seen.add(url)
                if len(result) >= max_files:
                    return result
                cached = conn.execute("SELECT * FROM files WHERE request_id=? AND url=?", (parameters["request_id"], url)).fetchone()
                if cached and Path(cached["path"]).is_file():
                    cached_path = Path(cached["path"])
                    digest = hashlib.sha256()
                    with cached_path.open("rb") as stream:
                        while chunk := stream.read(1024 * 1024):
                            digest.update(chunk)
                    if cached_path.stat().st_size == cached["bytes"] and digest.hexdigest() == cached["sha256"]:
                        result.append(dict(cached, status="cached"))
                        continue
                suffix = ".tif" if is_wcs else Path(parsed.path).suffix
                target = destination / (hashlib.sha256(url.encode()).hexdigest() + suffix)
                headers = {"User-Agent": "AgroResilience/0.1.0"}
                token = os.environ.get("EARTHDATA_TOKEN")
                if token and (parsed.hostname or "").endswith(".nasa.gov"):
                    headers["Authorization"] = "Bearer " + token
                temporary = None
                try:
                    with opener.open(Request(url, headers=headers), timeout=60) as response:
                        content_type = response.headers.get("Content-Type", "").lower()
                        if "html" in content_type or "xml" in content_type or "json" in content_type:
                            raise ValueError("Expected raster/archive, received a login or service error document")
                        if int(response.headers.get("Content-Length", 0)) > max_bytes:
                            raise ValueError("File exceeds max_bytes")
                        digest, size = hashlib.sha256(), 0
                        with tempfile.NamedTemporaryFile(dir=destination, delete=False) as stream:
                            temporary = Path(stream.name)
                            while chunk := response.read(1024 * 1024):
                                size += len(chunk)
                                if size > max_bytes:
                                    raise ValueError("File exceeds max_bytes")
                                stream.write(chunk)
                                digest.update(chunk)
                    if not size:
                        raise ValueError("Empty download")
                    temporary.replace(target)
                    info = dict(request_id=parameters["request_id"], url=url, path=str(target.resolve()),
                                sha256=digest.hexdigest(), bytes=size, downloaded_at=now())
                    with conn:
                        conn.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?)", tuple(info.values()))
                    result.append(dict(info, status="downloaded"))
                finally:
                    if temporary and temporary.exists():
                        temporary.unlink()
        return result
    finally:
        conn.close()


def sample_soil(db, parameters):
    """Optional rasterio: normalize a downloaded WCS mean at the requested point."""
    try:
        import rasterio
        from rasterio.warp import transform
    except ImportError as exc:
        raise ValueError("Soil sampling requires rasterio: pip install -r requirements-raster.txt") from exc
    records = query(db, dict(request_id=parameters["request_id"], kind="asset", limit=100000))
    if not records or any(r["source"] != "soilgrids" for r in records):
        raise ValueError("Expected a SoilGrids request")
    factors = {"sand": (10, "%"), "silt": (10, "%"), "clay": (10, "%"),
               "soc": (10, "g/kg"), "phh2o": (10, "pH"), "bdod": (100, "kg/dm3")}
    conn = connection(db)
    count = 0
    try:
        with conn:
            for record in records:
                meta = record["metadata"]
                url = meta["links"][0]["href"]
                try:
                    stored = conn.execute("SELECT path, sha256 FROM files WHERE request_id=? AND url=?", (parameters["request_id"], url)).fetchone()
                except sqlite3.OperationalError as exc:
                    if "no such table" in str(exc):
                        raise ValueError("Download the SoilGrids assets first") from exc
                    raise
                if not stored:
                    continue
                with rasterio.open(stored["path"]) as raster:
                    if raster.crs is None:
                        raise ValueError("Raster CRS is unknown")
                    xs, ys = transform("EPSG:4326", raster.crs, [meta["longitude"]], [meta["latitude"]])
                    pixel = next(raster.sample([(xs[0], ys[0])], masked=True))[0]
                    value = None if getattr(pixel, "mask", False) else float(pixel)
                    if value is not None and (not math.isfinite(value) or value < 0):
                        value = None
                factor, unit = factors[record["variable"]]
                meta = dict(meta, spatial_support="250m modeled pixel at requested point", raster_sha256=stored["sha256"],
                            quality_flags=["modeled_soil", "missing"] if value is None else ["modeled_soil"],
                            conversion_divisor=factor, processed_at=now())
                key = "sample:" + record["record_key"]
                conn.execute("INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?,?,?)", (
                    parameters["request_id"], key, "soilgrids", "", record["variable"] + ":" + meta["depth"],
                    None if value is None else value/factor, unit, "observation", encoded(meta)))
                count += 1
    finally:
        conn.close()
    return dict(sampled=count, request_id=parameters["request_id"])
