"""Bounded pixel processing of downloaded HLS bands. No entire tile in RAM."""

import hashlib
import math
import zipfile
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlparse

from .pipeline import VERSION, connection, encoded, now, query


def process_hls(db, parameters):
    try:
        import numpy as np
        import rasterio
        from rasterio.warp import transform
        from rasterio.windows import Window
    except ImportError as exc:
        raise ValueError("HLS processing requires requirements-raster.txt") from exc
    records = query(db, dict(request_id=parameters["request_id"], kind="asset", limit=100000))
    if not records or any(r["source"] not in ("hls_s30", "hls_l30") for r in records):
        raise ValueError("Expected HLS S30 or L30 request")
    conn = connection(db)
    processed, skipped = [], []
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='files'").fetchone():
            raise ValueError("Download B04, B8A (S30) or B05 (L30), and Fmask first")
        with conn:
            for record in records:
                meta = record["metadata"]
                granule = meta["granule_id"]
                if parameters.get("granule_id") and granule != parameters["granule_id"]:
                    continue
                required = ("B04", "B8A" if record["source"] == "hls_s30" else "B05", "Fmask")
                files = {}
                for link in meta.get("links", []):
                    url = link.get("href", "")
                    for band in required:
                        if urlparse(url).path.endswith("." + band + ".tif"):
                            stored = conn.execute("SELECT * FROM files WHERE request_id=? AND url=?", (record["request_id"], url)).fetchone()
                            if stored and Path(stored["path"]).is_file():
                                files[band] = dict(stored)
                if set(required) - set(files):
                    skipped.append(dict(granule_id=granule, reason="missing downloaded bands", missing=sorted(set(required)-set(files))))
                    continue
                with ExitStack() as stack:
                    rasters = [stack.enter_context(rasterio.open(files[band]["path"])) for band in required]
                    reference = rasters[0]
                    if reference.crs is None:
                        raise ValueError("HLS CRS is unknown")
                    if any((r.crs, r.transform, r.width, r.height) != (reference.crs, reference.transform, reference.width, reference.height) for r in rasters[1:]):
                        raise ValueError("HLS bands do not share a grid")
                    xs, ys = transform("EPSG:4326", reference.crs, [meta["longitude"]], [meta["latitude"]])
                    y, x = reference.index(xs[0], ys[0])
                    flags, value, qa = [], None, None
                    if not 0 <= y < reference.height or not 0 <= x < reference.width:
                        flags = ["outside_granule"]
                    else:
                        pixels = [r.read(1, window=Window(x, y, 1, 1), masked=True)[0, 0] for r in rasters]
                        if any(np.ma.is_masked(p) or not np.isfinite(p) for p in pixels) or pixels[0] == -9999 or pixels[1] == -9999:
                            flags = ["missing"]
                        else:
                            red, nir, qa = float(pixels[0])*.0001, float(pixels[1])*.0001, int(pixels[2])
                            # HLS v2: bits 1..5 cloud, adjacency, shadow, snow, water; bits 6..7 aerosol.
                            if qa == 255 or qa & 0b00111110 or (qa >> 6) & 3 == 3:
                                flags = ["qa_rejected"]
                            elif nir + red <= 0:
                                flags = ["invalid_reflectance"]
                            else:
                                candidate = (nir-red)/(nir+red)
                                if not -1 <= candidate <= 1:
                                    flags = ["invalid_ndvi"]
                                else:
                                    value = candidate
                    derived = dict(meta, spatial_support="single 30m modeled reflectance pixel at requested point",
                        processing_version=VERSION, processed_at=now(), quality_flags=flags,
                        fmask=qa, formula="(NIR - RED) / (NIR + RED)", bands=list(required),
                        raster_sha256={band: files[band]["sha256"] for band in required},
                        caveat="NDVI is not crop identity, residue coverage or measured yield")
                    key = "ndvi:" + hashlib.sha256(granule.encode()).hexdigest()
                    conn.execute("INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?,?,?)", (record["request_id"], key,
                        record["source"], record["observed_at"], "NDVI", value, "1", "observation", encoded(derived)))
                    processed.append(dict(granule_id=granule, ndvi=value, quality_flags=flags))
    finally:
        conn.close()
    return dict(processed=processed, skipped=skipped)


def process_dem(db, parameters):
    """Elevation and a local central-difference slope; never infer LS or erosion."""
    try:
        import numpy as np
        import rasterio
        from rasterio.warp import transform
        from rasterio.windows import Window
    except ImportError as exc:
        raise ValueError("DEM processing requires requirements-raster.txt") from exc
    records = query(db, dict(request_id=parameters["request_id"], kind="asset", limit=100000))
    if not records or any(r["source"] not in ("nasadem", "srtm") for r in records):
        raise ValueError("Expected NASADEM or SRTM request")
    conn = connection(db)
    processed, skipped = [], []
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='files'").fetchone():
            raise ValueError("Download the DEM assets first")
        with conn:
            for record in records:
                meta = record["metadata"]
                granule = meta["granule_id"]
                if parameters.get("granule_id") and granule != parameters["granule_id"]:
                    continue
                files = []
                for link in meta.get("links", []):
                    item = conn.execute("SELECT * FROM files WHERE request_id=? AND url=?", (record["request_id"], link.get("href", ""))).fetchone()
                    if item and Path(item["path"]).is_file():
                        files.append(dict(item))
                if not files:
                    skipped.append(dict(granule_id=granule, reason="missing downloaded DEM"))
                    continue
                if len(files) != 1:
                    raise ValueError("Select exactly one DEM download per granule")
                item = files[0]
                path = item["path"]
                if path.lower().endswith(".zip"):
                    with zipfile.ZipFile(path) as archive:
                        entries = archive.infolist()
                        if len(entries) > 1000:
                            raise ValueError("DEM archive has too many entries")
                        candidates = [e for e in entries if e.filename.lower().endswith((".hgt", ".tif", ".tiff"))]
                        if len(candidates) != 1 or candidates[0].file_size > 1_000_000_000:
                            raise ValueError("Expected exactly one bounded elevation raster in DEM archive")
                        name = candidates[0].filename
                        if ".." in Path(name).parts or name.startswith("/"):
                            raise ValueError("Unsafe DEM archive member")
                    path = "zip://" + path + "!" + name
                elevation, slope, flags = None, None, []
                with rasterio.open(path) as raster:
                    if raster.crs is None or raster.transform.b != 0 or raster.transform.d != 0:
                        raise ValueError("Expected a georeferenced unrotated DEM grid")
                    xs, ys = transform("EPSG:4326", raster.crs, [meta["longitude"]], [meta["latitude"]])
                    y, x = raster.index(xs[0], ys[0])
                    if not 0 <= y < raster.height or not 0 <= x < raster.width:
                        flags = ["outside_granule"]
                    else:
                        pixel = raster.read(1, window=Window(x, y, 1, 1), masked=True)[0, 0]
                        if np.ma.is_masked(pixel) or not np.isfinite(pixel) or pixel == -32768:
                            flags = ["missing"]
                        else:
                            elevation = float(pixel) * raster.scales[0] + raster.offsets[0]
                            if 1 <= y < raster.height-1 and 1 <= x < raster.width-1:
                                window = raster.read(1, window=Window(x-1, y-1, 3, 3), masked=True)
                                if not np.any(np.ma.getmaskarray(window)) and np.all(np.isfinite(window)) and not np.any(window == -32768):
                                    if raster.crs.is_geographic:
                                        dx = abs(raster.transform.a) * 111320 * math.cos(math.radians(meta["latitude"]))
                                        dy = abs(raster.transform.e) * 111320
                                        flags.append("approximate_geographic_pixel_distances")
                                    else:
                                        _, factor = raster.crs.linear_units_factor
                                        dx, dy = abs(raster.transform.a)*factor, abs(raster.transform.e)*factor
                                    if dx <= 0 or dy <= 0:
                                        raise ValueError("Invalid DEM cell size")
                                    dzdx = float(window[1, 2]-window[1, 0]) * raster.scales[0] / (2*dx)
                                    dzdy = float(window[2, 1]-window[0, 1]) * raster.scales[0] / (2*dy)
                                    slope = math.degrees(math.atan(math.hypot(dzdx, dzdy)))
                            if slope is None:
                                flags.append("slope_missing_neighborhood")
                    derived = dict(meta, processing_version=VERSION, processed_at=now(),
                        spatial_support="single DEM cell and 3x3 neighborhood; not a field mean",
                        raster_crs=str(raster.crs), raster_sha256=item["sha256"], quality_flags=flags,
                        slope_method="central difference; geographic distances approximated if needed",
                        caveat="Terrain model artifacts require GIS verification; no flow accumulation or LS computed")
                for variable, value, unit in (("ELEVATION", elevation, "m"), ("SLOPE", slope, "degree")):
                    conn.execute("INSERT OR REPLACE INTO records VALUES(?,?,?,?,?,?,?,?,?)", (
                        record["request_id"], "dem:" + granule + ":" + variable, record["source"],
                        "", variable, value, unit, "observation", encoded(derived)))
                processed.append(dict(granule_id=granule, elevation_m=elevation, slope_degrees=slope, quality_flags=flags))
    finally:
        conn.close()
    return dict(processed=processed, skipped=skipped)
