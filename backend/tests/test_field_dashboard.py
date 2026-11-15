"""Dashboard boundary tests: external failures must never produce demo climate."""

import calendar
from datetime import date, timedelta

import httpx
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import Settings


def dashboard_client(tmp_path, monkeypatch, handler):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "dashboard.sqlite"))
    return TestClient(
        create_app(Settings.from_env(), transport=httpx.MockTransport(handler))
    )


def power_response():
    values = {}
    for variable in [
        "T2M",
        "T2M_MAX",
        "T2M_MIN",
        "PRECTOTCORR",
        "RH2M",
        "WS2M",
        "ALLSKY_SFC_SW_DWN",
    ]:
        values[variable] = {}
        day = date(2016, 1, 1)
        while day <= date(2025, 12, 31):
            values[variable][day.strftime("%Y%m%d")] = (
                1 if variable == "PRECTOTCORR" else 15
            )
            day += timedelta(days=1)
    values["T2M"]["20160102"] = -999
    return {
        "properties": {"parameter": values},
        "parameters": {
            v: {"units": "mm/day" if v == "PRECTOTCORR" else "C"} for v in values
        },
        "header": {"fill_value": -999},
    }


def test_live_climate_keeps_missing_values_and_leap_days(tmp_path, monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=power_response())

    with dashboard_client(tmp_path, monkeypatch, handler) as client:
        response = client.get("/api/field-data?latitude=46.7491&longitude=32.7091")
        assert response.status_code == 200
        data = response.json()
        january = data["months"][0]
        assert (
            january["values"]["T2M"] is None
        )  # incomplete months are not silently averaged
        assert january["coverage"]["T2M"] == 30
        february = data["months"][1]
        assert february["values"]["PRECTOTCORR"] == calendar.monthrange(2016, 2)[1]
        assert data["status"] == "partial"
        assert data["months"][0]["period"] == "2016-01"
        assert data["source"] == "NASA POWER Daily"
        assert data["retrieved_at"]
        assert (
            client.get("/api/field-data?latitude=46.7491&longitude=32.7091").json()[
                "cached"
            ]
            is True
        )
        assert len(calls) == 1


def test_climate_failure_and_bad_coordinates(tmp_path, monkeypatch):
    with dashboard_client(
        tmp_path, monkeypatch, lambda r: httpx.Response(503)
    ) as client:
        result = client.get("/api/field-data?latitude=46&longitude=32").json()
        assert result["status"] == "unavailable"
        assert result["months"] == []
        assert client.get("/api/field-data?latitude=91&longitude=32").status_code == 422
        assert (
            client.get("/api/field-data?latitude=nan&longitude=32").status_code == 422
        )


def test_source_status_distinguishes_metadata_and_denied_access(tmp_path, monkeypatch):
    def handler(request):
        if "cmr.earthdata" in str(request.url):
            return httpx.Response(200, json={"feed": {"entry": [{"id": "granule"}]}})
        return httpx.Response(401)

    with dashboard_client(tmp_path, monkeypatch, handler) as client:
        response = client.get("/api/data-sources?latitude=46&longitude=32")
        assert response.status_code == 200
        sources = {row["id"]: row for row in response.json()["sources"]}
        assert set(sources) == {
            "power",
            "soilgrids",
            "nasadem",
            "hls",
            "gpm",
            "faostat",
        }
        assert sources["nasadem"]["status"] == "metadata_only"
        assert sources["hls"]["status"] == "metadata_only"
        assert sources["gpm"]["status"] == "partial"
        assert {check["status"] for check in sources["gpm"]["checks"]} == {"authentication_required", "metadata_only"}
        assert all(row["checked_at"] and row["source_url"] for row in sources.values())


def test_invalid_precipitation_units_and_malformed_series_are_unavailable(
    tmp_path, monkeypatch
):
    payload = power_response()
    payload["parameters"]["PRECTOTCORR"]["units"] = "unknown"
    with dashboard_client(
        tmp_path, monkeypatch, lambda r: httpx.Response(200, json=payload)
    ) as client:
        assert (
            client.get("/api/field-data?latitude=46&longitude=32").json()["status"]
            == "unavailable"
        )
        payload["parameters"]["PRECTOTCORR"]["units"] = "mm/day"
        payload["properties"]["parameter"]["T2M"] = []
        assert (
            client.get("/api/field-data?latitude=46&longitude=32").json()["status"]
            == "unavailable"
        )


def test_model_can_fetch_climate_outside_ukraine_with_provenance(tmp_path, monkeypatch):
    calls = []

    def handler(request):
        if request.url.host == "power.larc.nasa.gov":
            calls.append(request)
            return httpx.Response(200, json=power_response())
        body = __import__("json").loads(request.content)
        if not any(m["role"] == "tool" for m in body["messages"]):
            reply = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_climate_history",
                            "arguments": {
                                "latitude": -23.55,
                                "longitude": -46.63,
                                "year": 2020,
                                "variable": "PRECTOTCORR",
                            },
                        }
                    }
                ],
            }
        else:
            reply = {
                "role": "assistant",
                "content": "NASA POWER historical rainfall is available for this point in Brazil.",
            }
        return httpx.Response(200, json={"message": reply, "done": True})

    with dashboard_client(tmp_path, monkeypatch, handler) as client:
        response = client.post(
            "/api/chat",
            json={
                "conversation_id": "brazil",
                "request_id": "outside-region",
                "message": "Retrieve rainfall at -23.55, -46.63 in 2020.",
            },
        )
        events = [__import__("json").loads(line) for line in response.text.splitlines()]
        assert events[-1]["type"] == "answer"
        evidence = events[-1]["evidence"][-1]
        assert evidence["tool"] == "get_climate_history"
        result = evidence["result"]
        assert (
            result["status"] == "partial"
        )  # upstream fixture includes a missing 2016 day
        assert len(result["months"]) == 12
        assert result["months"][1]["value"] == 29
        assert result["geometry"]["coordinates"] == [-46.63, -23.55]
        assert result["source_url"].startswith("https://power.larc.nasa.gov/")
        assert calls[0].url.params["latitude"] == "-23.55"


def test_model_capabilities_expose_global_retrieval_without_claiming_agronomic_analysis(
    tmp_path, monkeypatch
):
    import asyncio

    from backend.config import Settings
    from backend.store import Store
    from backend.tools import build_tools

    async def check():
        config = Settings(database_path=tmp_path / "model.sqlite")
        async with httpx.AsyncClient() as http:
            tools = build_tools(
                Store(config.database_path),
                config,
                data_http=http,
                data_slots=asyncio.Semaphore(2),
            )("chat")
            result = tools["get_capabilities"].invoke({})
            assert (
                result["climate_retrieval"]["region"] == "Global coordinates, 85°S–85°N"
            )
            assert result["scientific_analysis"] == "unavailable"
            assert "check_data_sources" in tools

    asyncio.run(check())


def test_dashboard_for_another_region_does_not_force_kherson_rag_filters(
    tmp_path, monkeypatch
):
    from backend.config import Settings

    requests = []

    def retrieve(url, **kwargs):
        requests.append(kwargs)
        return {
            "status": "unavailable",
            "reason": "No local regional evidence",
            "chunks": [],
            "sql_data": [],
            "sources": {},
        }

    monkeypatch.setattr("backend.tools._call_rag_service", retrieve)
    config = Settings(
        database_path=tmp_path / "regions.sqlite", rag_url="http://localhost:8000"
    )

    def handler(request):
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": "Local evidence is unavailable.",
                },
                "done": True,
            },
        )

    with TestClient(
        create_app(config, transport=httpx.MockTransport(handler))
    ) as client:
        response = client.post(
            "/api/chat",
            json={
                "conversation_id": "region",
                "request_id": "region-1",
                "message": "Explore my dashboard in Brazil at -23.55, -46.63.",
            },
        )
        assert response.status_code == 200
    assert len(requests) == 2
    assert all(request.get("region") is None for request in requests)


def test_model_answers_combined_data_request_with_history_at_default_context_budget(
    tmp_path, monkeypatch
):
    import json

    def handler(request):
        if request.url.host == "power.larc.nasa.gov":
            return httpx.Response(200, json=power_response())
        if request.url.host not in {"localhost", "127.0.0.1"}:
            return httpx.Response(401)
        body = json.loads(request.content)
        current = [m["content"] for m in body["messages"] if m["role"] == "user"][-1]
        if current.startswith("Background"):
            reply = {"role": "assistant", "content": "Background noted."}
        elif not any(m["role"] == "tool" for m in body["messages"]):
            reply = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_climate_history",
                            "arguments": {"latitude": -23.55, "longitude": -46.63},
                        }
                    },
                    {
                        "function": {
                            "name": "check_data_sources",
                            "arguments": {"latitude": -23.55, "longitude": -46.63},
                        }
                    },
                ],
            }
        else:
            assert (
                len(
                    json.dumps(
                        {"messages": body["messages"], "tools": body["tools"]},
                        ensure_ascii=False,
                    ).encode()
                )
                <= 32000
            )
            assert len([m for m in body["messages"] if m["role"] == "tool"]) == 2
            reply = {
                "role": "assistant",
                "content": "Climate retrieved; source checks report restricted access.",
            }
        return httpx.Response(200, json={"message": reply, "done": True})

    with dashboard_client(tmp_path, monkeypatch, handler) as client:
        client.post(
            "/api/chat",
            json={
                "conversation_id": "combined",
                "request_id": "background",
                "message": "Background: " + "farm " * 650,
            },
        )
        response = client.post(
            "/api/chat",
            json={
                "conversation_id": "combined",
                "request_id": "both",
                "message": "Get climate and check sources for latitude -23.55, longitude -46.63.",
            },
        )
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1]["type"] == "answer", events[-1]
        assert len(events[-1]["evidence"]) == 2
