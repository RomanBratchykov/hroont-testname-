import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agrodata.assets import sample_soil
from agrodata.pipeline import collect, connection, now, query
from agrodata.rasters import process_hls, process_dem


@unittest.skipUnless(importlib.util.find_spec("rasterio"), "Optional rasterio is not installed")
class RasterTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        import rasterio
        from rasterio.transform import from_origin
        self.np, self.rasterio = np, rasterio
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = str(self.directory / "db.sqlite3")
        self.p = dict(latitude=49.9935, longitude=36.2304, start="2025-01-01", end="2025-01-02")
        self.transform = from_origin(36.2289, 49.9950, .001, .001)

    def raster(self, filename, value, dtype="int16"):
        path = self.directory / filename
        with self.rasterio.open(path, "w", driver="GTiff", width=3, height=3, count=1,
                dtype=dtype, crs="EPSG:4326", transform=self.transform) as dataset:
            dataset.write(self.np.full((3, 3), value, dtype=dtype), 1)
        return path

    def register(self, request_id, files):
        conn = connection(self.db)
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS files(request_id TEXT,url TEXT,path TEXT,sha256 TEXT,bytes INTEGER,downloaded_at TEXT)")
            for url, path in files:
                conn.execute("INSERT INTO files VALUES(?,?,?,?,?,?)", (request_id, url, str(path),
                    hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size, now()))
        conn.close()

    def test_soil_units_and_depth(self):
        result = collect(self.db, dict(self.p, sources=["soilgrids"], options={"soilgrids": {"properties": ["clay"], "depths": ["0-5cm"]}}))
        key = result["soilgrids"]["request_id"]
        asset = query(self.db, {"request_id": key})[0]
        self.register(key, [(asset["metadata"]["links"][0]["href"], self.raster("soil.tif", 399))])
        self.assertEqual(sample_soil(self.db, {"request_id": key})["sampled"], 1)
        record = query(self.db, dict(request_id=key, kind="observation"))[0]
        self.assertEqual(record["value"], 39.9)
        self.assertEqual(record["unit"], "%")

    def hls(self, qa):
        urls = {b: "https://data.nasa.gov/HLS." + b + ".tif" for b in ("B04", "B8A", "Fmask")}
        raw = {"feed": {"entry": [dict(id="G1", time_start="2025-01-01T00:00:00Z", links=[{"href": url} for url in urls.values()])]}}
        with patch("agrodata.pipeline.request_json", return_value=raw):
            key = collect(self.db, dict(self.p, sources=["hls_s30"]))["hls_s30"]["request_id"]
        self.register(key, [(urls[band], self.raster(band+".tif", value, dtype)) for band, value, dtype in
                           [("B04", 2000, "int16"), ("B8A", 6000, "int16"), ("Fmask", qa, "uint8")]])
        return key

    def test_hls_ndvi_uses_correct_bands(self):
        key = self.hls(0)
        result = process_hls(self.db, {"request_id": key})
        self.assertAlmostEqual(result["processed"][0]["ndvi"], .5)
        self.assertEqual(query(self.db, dict(request_id=key, variable="NDVI"))[0]["unit"], "1")

    def test_hls_cloud_and_aerosol_masked(self):
        key = self.hls(2)
        result = process_hls(self.db, {"request_id": key})
        self.assertIsNone(result["processed"][0]["ndvi"])
        self.assertIn("qa_rejected", result["processed"][0]["quality_flags"])

    def test_hls_high_aerosol_masked(self):
        key = self.hls(192)
        self.assertIsNone(process_hls(self.db, {"request_id": key})["processed"][0]["ndvi"])

    def test_dem_projected_plane_has_45_degree_slope(self):
        from rasterio.warp import transform
        from rasterio.transform import from_origin
        xs, ys = transform("EPSG:4326", "EPSG:32637", [self.p["longitude"]], [self.p["latitude"]])
        path = self.directory / "dem.tif"
        with self.rasterio.open(path, "w", driver="GTiff", width=3, height=3, count=1,
                dtype="float32", crs="EPSG:32637", transform=from_origin(xs[0]-45, ys[0]+45, 30, 30)) as raster:
            raster.write(self.np.array([[0, 30, 60]]*3, dtype="float32"), 1)
        url = "https://data.nasa.gov/dem.tif"
        raw = {"feed": {"entry": [dict(id="GDEM", links=[{"href": url}])]}}
        with patch("agrodata.pipeline.request_json", return_value=raw):
            key = collect(self.db, dict(self.p, sources=["nasadem"]))["nasadem"]["request_id"]
        self.register(key, [(url, path)])
        result = process_dem(self.db, {"request_id": key})
        self.assertAlmostEqual(result["processed"][0]["slope_degrees"], 45)
        self.assertAlmostEqual(result["processed"][0]["elevation_m"], 30)
