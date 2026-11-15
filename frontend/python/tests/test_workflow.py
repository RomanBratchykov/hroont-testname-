import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from agrodata.analysis import analyze
from agrodata.pipeline import collect, query
from agrodata.report import export_csv
from agrodata.tools import invoke
from agrodata.workflow import inspect_run, run


def weather(start="2024-01-01", end="2025-12-31"):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    days = [(first+timedelta(days=i)).strftime("%Y%m%d") for i in range((last-first).days+1)]
    variables = {"PRECTOTCORR": 2, "T2M": 15, "T2M_MAX": 36, "T2M_MIN": -1}
    return dict(properties={"parameter": {v: {day: value for day in days} for v, value in variables.items()}},
                parameters={v: {"units": "mm/day" if v == "PRECTOTCORR" else "C"} for v in variables})


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = str(self.directory / "test.sqlite3")
        self.p = dict(latitude=49.9935, longitude=36.2304, start="2024-01-01", end="2025-12-31")

    def ingest(self, raw=None):
        with patch("agrodata.pipeline.request_json", return_value=raw or weather()):
            return collect(self.db, self.p)["power"]["request_id"]

    def test_run_creates_real_artifacts_and_compact_summary(self):
        with patch("agrodata.pipeline.request_json", return_value=weather()):
            result = run(self.db, self.p, self.directory / "reports")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["summary"]["precipitation_mm"], 1462)
        self.assertEqual(result["quality"]["complete_years"], 2)
        self.assertNotIn("records", result)
        self.assertNotIn("monthly", result)
        for value in result["artifacts"].values():
            self.assertTrue(Path(value).is_file())
        self.assertEqual(inspect_run(self.db, {"run_id": result["run_id"]}), result)
        document = Path(result["artifacts"]["dashboard"]).read_text()
        self.assertIn("Опади за місяцями", document)
        self.assertIn("Повнота даних", document)
        self.assertNotIn("https://cdn", document)
        with open(result["artifacts"]["csv"], encoding="utf-8-sig") as stream:
            self.assertEqual(len(list(csv.DictReader(stream))), 2924)

    def test_partial_run_preserves_climate_dashboard(self):
        with patch("agrodata.pipeline.request_json", side_effect=[weather(), OSError("source down")]):
            result = run(self.db, dict(self.p, sources=["power", "gpm"]), self.directory)
        self.assertEqual(result["status"], "partial")
        self.assertTrue(Path(result["artifacts"]["dashboard"]).exists())
        self.assertEqual(result["sources"]["gpm"]["status"], "error")

    def test_entire_missing_year_detected(self):
        key = self.ingest(weather("2024-01-01", "2024-12-31"))
        result = analyze(self.db, {"request_id": key})
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["excluded_years"][0]["year"], 2025)
        self.assertIsNone(result["period"]["precipitation_mm"])

    def test_winter_season_crosses_year_and_leap_day(self):
        key = self.ingest()
        result = analyze(self.db, dict(request_id=key, seasons=[dict(name="winter", start="10-01", end="06-30")]))
        windows = result["seasons"][0]["windows"]
        full = next(w for w in windows if w["harvest_year"] == 2025)
        self.assertTrue(full["complete"])
        self.assertEqual(full["start"], "2024-10-01")
        self.assertEqual(full["precipitation_mm"], 546)
        self.assertFalse(windows[0]["complete"])
        self.assertEqual(result["seasons"][0]["rainfall"]["n"], 1)

    def test_missing_day_never_counted_as_dry(self):
        raw = weather()
        raw["properties"]["parameter"]["PRECTOTCORR"]["20240201"] = -999
        key = self.ingest(raw)
        result = analyze(self.db, {"request_id": key})
        february = next(m for m in result["monthly"] if m["month"] == "2024-02")
        self.assertEqual(february["expected_days"], 29)
        self.assertIsNone(february["longest_dry_spell_days"])
        self.assertEqual(february["missing_by_variable"]["PRECTOTCORR"], 1)
        self.assertEqual(result["n"], 1)

    def test_failed_refresh_preserves_last_good_snapshot(self):
        key = self.ingest()
        with patch("agrodata.pipeline.request_json", side_effect=OSError("unavailable")):
            result = collect(self.db, dict(self.p, cache_hours=0))
        self.assertEqual(result["power"]["status"], "error")
        self.assertTrue(result["power"]["stale_available"])
        self.assertEqual(len(query(self.db, dict(request_id=key, limit=10000))), 2924)

    def test_cache_canonical_variable_order(self):
        self.ingest()
        with patch("agrodata.pipeline.request_json") as fetch:
            result = collect(self.db, dict(self.p, options={"power": {"variables": ["T2M_MIN", "PRECTOTCORR", "T2M_MAX", "T2M"]}}))
        self.assertEqual(result["power"]["status"], "cached")
        fetch.assert_not_called()

    def test_tool_rejects_paths_sql_and_unbounded_reads(self):
        for arguments in (dict(request_id="x", db="/tmp/other.sqlite"), dict(request_id="x", sql="DROP TABLE requests"), dict(request_id="x", limit=1001)):
            with self.assertRaises(ValueError):
                invoke("agro_read", arguments, self.db, self.directory)
        key = self.ingest()
        result = invoke("agro_analyze", {"request_id": key}, self.db, self.directory)
        self.assertNotIn("monthly", result)
        self.assertEqual(result["annual_rainfall"]["n"], 2)

    def test_csv_formula_escaping(self):
        key = self.ingest()
        from agrodata.pipeline import connection
        conn = connection(self.db)
        with conn:
            conn.execute("UPDATE records SET variable=? WHERE request_id=?", ("=DANGEROUS()", key))
        conn.close()
        output = self.directory / "export.csv"
        export_csv(self.db, {"request_id": key}, output)
        with output.open(encoding="utf-8-sig") as stream:
            first = next(csv.DictReader(stream))
        self.assertEqual(first["variable"], "'=DANGEROUS()")

    def test_invalid_shape_boolean_and_unknown_request(self):
        for p in ([], dict(self.p, latitude=True), dict(self.p, refresh="false"), dict(self.p, sources="power")):
            with self.assertRaises(ValueError):
                collect(self.db, p)
        with self.assertRaises(ValueError):
            query(self.db, {"request_id": "does-not-exist"})

    def test_model_schema_rejects_nested_options_before_fetch(self):
        for extra in (dict(latitude=True), dict(analysis={"heat_threshold": "35"}),
                      dict(dashboard={"cards": ["arbitrary_javascript"]}),
                      dict(options={"power": {"variables": ["password"]}})):
            with patch("agrodata.pipeline.request_json") as fetch:
                with self.assertRaises(ValueError):
                    invoke("agro_run", dict(self.p, **extra), self.db, self.directory)
                fetch.assert_not_called()

    def test_faostat_requires_token_without_sending_requests(self):
        with patch.dict("os.environ", {}, clear=True), patch("agrodata.pipeline.request_json") as fetch:
            result = collect(self.db, dict(self.p, sources=["faostat"],
                options={"faostat": {"items": [15], "elements": [5510]}}))
        self.assertEqual(result["faostat"]["status"], "error")
        self.assertIn("FAOSTAT_TOKEN", result["faostat"]["error"])
        fetch.assert_not_called()

    def test_faostat_current_normalizes_national_rows(self):
        response = {"data": [{"Year": 2024, "Item Code": 15, "Element Code": 5510, "Value": 100, "Unit": "t"}]}
        with patch.dict("os.environ", {"FAOSTAT_TOKEN": "test-not-a-real-token"}), patch("agrodata.pipeline.request_json", return_value=response) as fetch:
            result = collect(self.db, dict(self.p, sources=["faostat"],
                options={"faostat": {"items": [15], "elements": [5510]}}))
        self.assertEqual(result["faostat"]["status"], "collected")
        self.assertIn("faostatservices.fao.org", fetch.call_args.args[0])
        records = query(self.db, {"request_id": result["faostat"]["request_id"]})
        self.assertEqual(records[0]["value"], 100)
        self.assertEqual(records[0]["metadata"]["spatial_support"], "Ukraine national statistic")
