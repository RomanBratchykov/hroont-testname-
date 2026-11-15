import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_inputs():
    return json.loads((ROOT / "input_data/john_showcase.json").read_text())


def test_showcase_covers_every_question_with_explicit_synthetic_provenance():
    data = load_inputs()
    questions = set(
        re.findall(
            r"\*\*(Q\d+)\*\*",
            (ROOT / "AGENTS/AgroResilience_Farmer_Questionnaire.md").read_text(),
        )
    )
    assert set(data["questionnaire_mapping"]) == questions
    assert data["provenance"]["status"] == "synthetic"
    for path in data["questionnaire_mapping"].values():
        value = data
        for key in path.split("."):
            value = value[key]
        assert value is not None
    assert data["consent"]["real_person_consent"] is None


def test_showcase_geometry_history_and_soil_are_internally_consistent():
    data = load_inputs()
    feature = json.loads((ROOT / "input_data/john_field.geojson").read_text())
    assert feature["geometry"] == data["field"]["geometry"]
    ring = feature["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]
    assert len(ring) == 5
    west, east = min(p[0] for p in ring), max(p[0] for p in ring)
    south, north = min(p[1] for p in ring), max(p[1] for p in ring)
    lon, lat = data["field"]["center"]["longitude"], data["field"]["center"]["latitude"]
    assert west < lon < east and south < lat < north
    area = (
        6371008.8**2
        * math.radians(east - west)
        * (math.sin(math.radians(north)) - math.sin(math.radians(south)))
        / 10000
    )
    assert abs(area - data["field"]["declared_area"]["value"]) < 0.05
    assert data["field"]["verified_boundary"] is False
    history = data["crop_history"]["records"]
    assert [row["harvest_year"] for row in history] == list(range(2016, 2026))
    assert [row["crop"] for row in history[-3:]] == [
        "sunflower",
        "sunflower",
        "winter_wheat",
    ]
    for layer in data["soil"]["layers"]:
        assert sum(layer[name]["value"] for name in ["sand", "silt", "clay"]) == 1000


def test_showcase_economics_are_assumptions_and_api_results_are_not_fabricated():
    data = load_inputs()
    assert data["analysis_request"]["historical_period"] == {
        "start": "2016-01-01",
        "end": "2025-12-31",
    }
    assumptions = data["economics"]["crop_assumptions"]
    for crop in data["crop_preferences"]["include"]:
        assert crop in assumptions
        assert assumptions[crop]["yield"]["unit"] == "t/ha"
        assert assumptions[crop]["price"]["unit"] == "UAH/t"
        assert assumptions[crop]["variable_cost"]["unit"] == "UAH/ha"
    assert data["economics"]["status"] == "synthetic"
    for source in data["external_data"].values():
        assert source["status"] == "not_retrieved"
        assert source["values"] is None
    assert all(value is None for value in data["computed_outputs"].values())
