import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agrodata.pipeline import collect, connection, encoded, now, query
from agrodata.region import contains, require_region, ring_location
from agrodata.tools import invoke


class RegionTests(unittest.TestCase):
    def test_kharkiv_oblast_points(self):
        for lat, lon in [(49.9935, 36.2304), (49.3716, 37.2708), (49.714, 37.615), (50.245, 36.927)]:
            self.assertTrue(contains(lat, lon), (lat, lon))

    def test_other_regions_rejected(self):
        for lat, lon in [(46.7491, 32.7091), (50.4501, 30.5234), (49.5883, 34.5514), (50.9077, 34.7981)]:
            with self.assertRaises(ValueError):
                require_region(lat, lon)

    def test_bounding_box_is_not_sufficient(self):
        # These coordinates are in the enclosing rectangle, outside the actual oblast.
        self.assertFalse(contains(48.6, 35.9))

    def test_ring_edges_and_hole_building_block(self):
        ring = [[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]
        self.assertEqual(ring_location(1, 1, ring), 1)
        self.assertEqual(ring_location(0, 1, ring), 2)
        self.assertEqual(ring_location(3, 1, ring), 0)

    def test_examples_all_belong_to_kharkiv(self):
        for path in (Path(__file__).parents[1] / "examples").glob("*.json"):
            p = json.loads(path.read_text())
            self.assertTrue(contains(p["latitude"], p["longitude"]), str(path))

    def test_reject_before_network(self):
        with tempfile.TemporaryDirectory() as directory, patch("agrodata.pipeline.request_json") as fetch:
            p = dict(latitude=46.7491, longitude=32.7091, start="2025-01-01", end="2025-01-02")
            with self.assertRaises(ValueError):
                collect(str(Path(directory) / "test.sqlite3"), p)
            with self.assertRaises(ValueError):
                invoke("agro_run", p, str(Path(directory) / "test.sqlite3"), directory)
            fetch.assert_not_called()

    def test_legacy_out_of_region_request_cannot_be_read(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "test.sqlite3")
            conn = connection(db)
            with conn:
                conn.execute("INSERT INTO requests VALUES(?,?,?,?,?,?)", ("legacy", "power",
                    encoded(dict(latitude=46.7491, longitude=32.7091)), now(), "https://example.test", "{}"))
            conn.close()
            with self.assertRaises(ValueError):
                query(db, {"request_id": "legacy"})
