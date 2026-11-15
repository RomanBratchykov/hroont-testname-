import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agrodata.pipeline import collect, query, dashboard
from agrodata.analysis import analyze


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / "test.sqlite3")
        self.p = dict(latitude=49.9935, longitude=36.2304, start="2025-01-01", end="2025-01-02", sources=["power"])
        self.raw = dict(header={"fill_value": -999}, parameters={"T2M": {"units": "C"}},
                        properties={"parameter": {"T2M": {"20250101": 5, "20250102": -999}}})
        self.p["options"] = {"power": {"variables": ["T2M"]}}

    def ingest(self):
        with patch("agrodata.pipeline.request_json", return_value=self.raw):
            return collect(self.db, self.p)["power"]["request_id"]

    def test_cache_refresh_and_missing(self):
        key = self.ingest()
        with patch("agrodata.pipeline.request_json") as fetch:
            self.assertEqual(collect(self.db, self.p)["power"]["status"], "cached")
            fetch.assert_not_called()
        records = query(self.db, {"request_id": key})
        self.assertEqual([r["value"] for r in records], [5, None])
        self.assertEqual(records[1]["metadata"]["quality_flags"], ["missing"])
        self.raw["properties"]["parameter"]["T2M"]["20250101"] = 7
        with patch("agrodata.pipeline.request_json", return_value=self.raw):
            collect(self.db, dict(self.p, refresh=True))
        self.assertEqual(len(query(self.db, {"request_id": key})), 2)
        self.assertEqual(query(self.db, {"request_id": key})[0]["value"], 7)

    def test_dashboard_escape_filter_and_summary(self):
        key = self.ingest()
        output = Path(self.temp.name) / "dashboard.html"
        result = dashboard(self.db, dict(request_id=key, variable="T2M", title="<script>alert(1)</script>"), output)
        self.assertEqual(result["summary"]["mean"], 5)
        self.assertEqual(result["summary"]["missing"], 1)
        self.assertNotIn("<script>", output.read_text())
        self.assertEqual(len(query(self.db, dict(request_id=key, start="2025-01-02"))), 1)

    def test_different_points_isolated(self):
        first = self.ingest()
        with patch("agrodata.pipeline.request_json", return_value=self.raw):
            other = collect(self.db, dict(self.p, latitude=50.0))["power"]["request_id"]
        self.assertNotEqual(first, other)
        self.assertEqual(len(query(self.db, {"request_id": first})), 2)

    def test_partial_failures_keep_success(self):
        p = dict(self.p, sources=["power", "hls_s30"])
        with patch("agrodata.pipeline.request_json", side_effect=[self.raw, ValueError("invalid response")]):
            result = collect(self.db, p)
        self.assertEqual(result["power"]["status"], "collected")
        self.assertEqual(result["hls_s30"]["status"], "error")

    def test_catalog_pagination(self):
        entry = dict(id="G1", time_start="2025-01-01T00:00:00Z")
        with patch("agrodata.pipeline.request_json", side_effect=[{"feed": {"entry": [entry] * 100}},
                {"feed": {"entry": [dict(entry, id="G2")]}}]) as fetch:
            result = collect(self.db, dict(self.p, sources=["hls_s30"], options={"hls_s30": {"max_pages": 2}}))
        self.assertEqual(fetch.call_count, 2)
        self.assertFalse(result["hls_s30"]["possibly_truncated"])
        self.assertEqual(result["hls_s30"]["count"], 2)

    def test_incomplete_year_excluded(self):
        key = self.ingest()
        result = analyze(self.db, {"request_id": key})
        self.assertEqual(result["n"], 0)
        self.assertEqual(len(result["excluded_years"]), 1)

    def test_complete_leap_year_and_dry_spells(self):
        from datetime import date, timedelta
        days = [(date(2024, 1, 1) + timedelta(days=i)).strftime("%Y%m%d") for i in range(366)]
        parameters = {"PRECTOTCORR": {day: 0 if i < 3 else 2 for i, day in enumerate(days)},
                      "T2M_MAX": {day: 36 for day in days}, "T2M_MIN": {day: -1 for day in days}}
        raw = dict(properties={"parameter": parameters}, parameters={k: {"units": "mm/day" if k == "PRECTOTCORR" else "C"} for k in parameters})
        p = dict(self.p, start="2024-01-01", end="2024-12-31", options={"power": {"variables": list(parameters)}})
        with patch("agrodata.pipeline.request_json", return_value=raw):
            key = collect(self.db, p)["power"]["request_id"]
        result = analyze(self.db, {"request_id": key})
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["years"][0]["longest_dry_spell_days"], 3)
        self.assertEqual(result["years"][0]["precipitation_mm"], 726)
        self.assertEqual(result["years"][0]["heat_days"], 366)

    def test_validation(self):
        with self.assertRaises(ValueError):
            collect(self.db, dict(self.p, latitude=46.7491))
        with self.assertRaises(ValueError):
            collect(self.db, dict(self.p, sources=["unknown"]))


if __name__ == "__main__":
    unittest.main()
