import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agrodata.assets import download, trusted
from agrodata.pipeline import collect


class Response(io.BytesIO):
    headers = {"Content-Type": "image/tiff"}


class AssetTests(unittest.TestCase):
    def test_trusted_hosts(self):
        self.assertTrue(trusted("https://maps.isric.org/mapserv?a=1"))
        self.assertTrue(trusted("https://data.lpdaac.earthdatacloud.nasa.gov/file.tif"))
        self.assertFalse(trusted("http://maps.isric.org/mapserv"))
        self.assertFalse(trusted("https://maps.isric.org.evil.test/file.tif"))
        self.assertFalse(trusted("https://user:password@maps.isric.org/file.tif"))

    def test_download_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "test.sqlite3")
            result = collect(db, dict(latitude=49.9935, longitude=36.2304, start="2025-01-01",
                end="2025-01-02", sources=["soilgrids"],
                options={"soilgrids": {"properties": ["clay"], "depths": ["0-5cm"]}}))
            params = {"request_id": result["soilgrids"]["request_id"]}
            with patch("agrodata.assets.build_opener") as opener:
                opener.return_value.open.return_value = Response(b"test-raster-bytes")
                files = download(db, params, Path(directory) / "assets")
                self.assertEqual(files[0]["status"], "downloaded")
                self.assertEqual(files[0]["bytes"], 17)
                self.assertEqual(download(db, params, Path(directory) / "assets")[0]["status"], "cached")
                self.assertEqual(opener.return_value.open.call_count, 1)

    def test_oversize_download_is_not_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "test.sqlite3")
            result = collect(db, dict(latitude=49.9935, longitude=36.2304, start="2025-01-01",
                end="2025-01-02", sources=["soilgrids"]))
            params = dict(request_id=result["soilgrids"]["request_id"], max_bytes=1)
            with patch("agrodata.assets.build_opener") as opener:
                opener.return_value.open.return_value = Response(b"too large")
                with self.assertRaises(ValueError):
                    download(db, params, Path(directory) / "assets")
            self.assertEqual(list((Path(directory) / "assets").iterdir()), [])
