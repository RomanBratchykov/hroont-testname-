import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api import create_app
from backend.calculations import (
    CropScoreArgs,
    GrossMarginArgs,
    RotationArgs,
    RusleArgs,
    crop_score,
    gross_margin,
    rusle,
    validate_rotation,
)
from backend.config import Settings
from backend.store import Store
from backend.tools import build_tools


def test_chickpea_margin_uses_explicit_configured_assumptions_and_current_area(
    tmp_path,
):
    store = Store(tmp_path / "math.sqlite")
    store.admit_guest("owner", None)
    store.begin("field", "turn", "Calculate chickpea return", "fast", [], owner="owner")
    result = build_tools(store)("field")["calculate_gross_margin"].invoke(
        {"crop": "chickpea", "use_configured_assumptions": True}
    )
    assert result["status"] == "computed"
    assert result["gross_margin_per_ha"] == {"value": 12800, "unit": "UAH/ha"}
    assert result["gross_margin_total"] == {"value": 384000, "unit": "UAH"}
    assert result["basis"] == "configured_assumptions"
    assert result["yield_forecast"] is None
    store.update_profile("owner", {"facts": {"field_area": "42 ha"}})
    changed = build_tools(store)("field")["calculate_gross_margin"].invoke(
        {"crop": "chickpea", "use_configured_assumptions": True}
    )
    assert changed["gross_margin_total"]["value"] == 537600
    store.update_profile(
        "owner",
        {
            "facts": {
                "chickpea_price_per_t": "20000",
                "price_year": "2025",
                "currency": "UAH",
            }
        },
    )
    corrected = build_tools(store)("field")["calculate_gross_margin"].invoke(
        {"crop": "chickpea", "use_configured_assumptions": True}
    )
    assert corrected["gross_margin_per_ha"]["value"] == 16000
    assert "saved profile" in corrected["input_sources"]["price_per_t"]
    store.clear_profile("owner")
    assert (
        build_tools(store)("field")["calculate_gross_margin"].invoke(
            {"crop": "chickpea"}
        )["status"]
        == "insufficient_data"
    )


def test_missing_inputs_are_not_zero_and_explicit_losses_are_allowed():
    missing = gross_margin(GrossMarginArgs(crop="chickpea"), {"facts": {}})
    assert missing["status"] == "insufficient_data"
    assert missing["gross_margin_per_ha"] is None
    result = gross_margin(
        GrossMarginArgs(
            crop="chickpea",
            yield_t_ha=1,
            price_per_t=100,
            variable_cost_per_ha=120,
            currency="USD",
            price_year=2025,
        ),
        {"facts": {}},
    )
    assert result["gross_margin_per_ha"]["value"] == -20
    assert result["gross_margin_total"] is None
    mismatch = gross_margin(
        GrossMarginArgs(
            crop="chickpea", use_configured_assumptions=True, price_year=2030
        ),
        {"facts": {}},
    )
    assert mismatch["gross_margin_per_ha"] is None


def test_crop_score_requires_all_components_and_passed_constraints():
    args = {
        "crop": "chickpea",
        "components": {
            key: {
                "value": value,
                "source": "regional review",
                "method": "documented test curve",
            }
            for key, value in [
                ("temperature", 80),
                ("water_climate", 60),
                ("soil", 70),
                ("rotation", 100),
            ]
        },
        "hard_constraints": {
            key: {"passed": True, "source": "validated fixture"}
            for key in ("climate", "soil", "irrigation", "calendar", "rotation")
        },
    }
    result = crop_score(CropScoreArgs.model_validate(args))
    assert result["score"]["value"] == 73
    assert result["interpretation"] == "comparative_screening_not_probability"
    args["hard_constraints"]["rotation"]["passed"] = False
    assert crop_score(CropScoreArgs.model_validate(args))["score"] is None
    del args["components"]["soil"]
    args["hard_constraints"]["rotation"]["passed"] = True
    assert (
        crop_score(CropScoreArgs.model_validate(args))["status"] == "insufficient_data"
    )


def test_rusle_sums_cell_losses_instead_of_multiplying_factor_means():
    def cell(identifier, area, ls, cover):
        return {
            "cell_id": identifier,
            "area_ha": area,
            "R": {
                "value": 100,
                "unit": "MJ mm/(ha h yr)",
                "source": "processed rainfall",
                "method": "EI30",
            },
            "K": {
                "value": 0.02,
                "unit": "t ha h/(ha MJ mm)",
                "source": "soil estimate",
                "method": "validated conversion",
            },
            "LS": {
                "value": ls,
                "unit": "1",
                "source": "processed DEM",
                "method": "metric flow routing",
            },
            "C": {
                "value": cover,
                "unit": "1",
                "source": "cover model",
                "method": "erosivity-weighted annual cover",
            },
            "P": {
                "value": 1,
                "unit": "1",
                "source": "practice assessment",
                "method": "baseline",
            },
        }

    result = rusle(
        RusleArgs.model_validate(
            {
                "period": "2016-2025 long-term annual mean",
                "cells": [cell("one", 1, 1, 0.1), cell("two", 3, 2, 0.2)],
            }
        )
    )
    assert result["soil_loss_total"]["value"] == 2.6
    assert result["soil_loss_mean"]["value"] == 0.65
    assert rusle(RusleArgs())["soil_loss_mean"] is None
    bad = cell("bad", 1, 1, 0.1)
    bad["K"]["unit"] = "US customary"
    assert (
        rusle(RusleArgs.model_validate({"period": "2016-2025", "cells": [bad]}))[
            "status"
        ]
        == "insufficient_data"
    )
    zero = cell("zero", 1, 1, 0.1)
    zero["R"]["value"] = 0
    assert (
        rusle(RusleArgs.model_validate({"period": "2016-2025", "cells": [zero]}))[
            "soil_loss_mean"
        ]["value"]
        == 0
    )


def test_rotation_checks_exact_history_and_cyclic_boundary_before_scoring():
    constraints = {
        key: {"passed": True, "source": "regional review fixture"}
        for key in ("climate", "soil", "irrigation", "calendar")
    }
    args = {
        "start_year": 2026,
        "crops": ["sunflower", "wheat", "sunflower"],
        "history": [{"year": 2024, "crop": "wheat"}, {"year": 2025, "crop": "wheat"}],
        "return_rules": [
            {
                "crops": ["sunflower"],
                "minimum_years": 3,
                "source": "explicit scenario rule",
            },
            {
                "crops": ["wheat"],
                "minimum_years": 1,
                "source": "explicit scenario rule",
            },
        ],
        "other_constraints": constraints,
    }
    blocked = validate_rotation(RotationArgs.model_validate(args))
    assert blocked["feasible"] is False
    assert any(
        v["previous_year"] == 2028 and v["year"] == 2029 and v["gap_years"] == 1
        for v in blocked["violations"]
    )
    args["crops"] = ["sunflower", "wheat", "wheat"]
    assert validate_rotation(RotationArgs.model_validate(args))["feasible"] is True
    args["history"] = [{"year": 2025, "crop": "wheat"}]
    assert validate_rotation(RotationArgs.model_validate(args))["feasible"] is None
    args["history"] = [{"year": 2024, "crop": "sunflower"}]
    assert validate_rotation(RotationArgs.model_validate(args))["feasible"] is False
    args["history"] = []
    args["other_constraints"] = {}
    assert validate_rotation(RotationArgs.model_validate(args))["feasible"] is None


@pytest.mark.parametrize(
    "kwargs", [{"yield_t_ha": -1}, {"price_per_t": float("nan")}, {"area_ha": 0}]
)
def test_invalid_financial_inputs_are_rejected(kwargs):
    with pytest.raises(ValidationError):
        GrossMarginArgs(crop="chickpea", **kwargs)


@pytest.mark.parametrize("provider", ["ollama", "deepseek"])
def test_actual_chat_can_call_gross_margin_and_health_advertises_calculators(
    tmp_path, provider
):
    requests = []

    def upstream(request):
        body = json.loads(request.content)
        requests.append(body)
        assert any(
            tool["function"]["name"] == "calculate_gross_margin"
            for tool in body["tools"]
        )
        if len(requests) == 1:
            arguments = {"crop": "chickpea", "use_configured_assumptions": True}
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "margin-1",
                        "type": "function",
                        "function": {
                            "name": "calculate_gross_margin",
                            "arguments": json.dumps(arguments)
                            if provider == "deepseek"
                            else arguments,
                        },
                    }
                ],
            }
        else:
            result = json.loads(body["messages"][-1]["content"])
            assert result["gross_margin_per_ha"]["value"] == 12800
            message = {
                "role": "assistant",
                "content": "The assumed gross margin is 12,800 UAH/ha.",
            }
        payload = (
            {"choices": [{"message": message, "finish_reason": "stop"}]}
            if provider == "deepseek"
            else {"message": message, "done": True}
        )
        return httpx.Response(200, json=payload)

    config = Settings(
        database_path=tmp_path / "chat.sqlite",
        provider=provider,
        openai_base_url="http://localhost:8001" if provider == "deepseek" else "",
    )
    with TestClient(
        create_app(config, transport=httpx.MockTransport(upstream))
    ) as client:
        health = client.get("/api/health").json()
        assert "calculate_gross_margin" in health["scientific_tools"]
        response = client.post(
            "/api/chat",
            json={
                "conversation_id": "field",
                "request_id": "one",
                "message": "What would chickpea return using the configured inputs?",
                "mode": "fast",
            },
        )
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1]["type"] == "answer"
        assert events[-1]["evidence"][0]["result"]["status"] == "computed"
