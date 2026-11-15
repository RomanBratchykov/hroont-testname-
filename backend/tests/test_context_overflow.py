import asyncio
import json

import pytest

from backend.config import Settings
from backend.orchestrator import Orchestrator


def test_deepseek_has_room_for_tools_without_changing_ollama_budget(monkeypatch):
    assert Settings(provider="deepseek").max_context_bytes == 128000
    assert Settings(provider="ollama").max_context_bytes == 32000
    assert (
        Settings(provider="deepseek", max_context_bytes=8000).max_context_bytes == 8000
    )
    monkeypatch.setenv("MODEL_MAX_CONTEXT_BYTES", "64000")
    assert Settings.from_env().max_context_bytes == 64000


@pytest.mark.parametrize("summary_unavailable", [False, True])
def test_overgrown_reasoning_recovers_a_real_calculation_without_technical_reply(
    tmp_path,
    summary_unavailable,
):
    import httpx
    from fastapi.testclient import TestClient

    from backend.api import create_app

    bodies = []

    def upstream(request):
        body = json.loads(request.content)
        bodies.append(body)
        if len(bodies) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "reasoning_content": "private thought " * 5000,
                "tool_calls": [
                    {
                        "id": "margin",
                        "type": "function",
                        "function": {
                            "name": "calculate_gross_margin",
                            "arguments": '{"crop":"chickpea","use_configured_assumptions":true}',
                        },
                    }
                ],
            }
        else:
            assert "tools" not in body
            assert "12800" in body["messages"][-1]["content"]
            assert "private thought" not in json.dumps(body)
            if summary_unavailable:
                return httpx.Response(503, json={"error": "Unavailable"})
            message = {
                "role": "assistant",
                "content": "Using your configured inputs, chickpea's gross margin is 12,800 UAH/ha.",
            }
        return httpx.Response(
            200, json={"choices": [{"message": message, "finish_reason": "stop"}]}
        )

    config = Settings(
        provider="deepseek",
        openai_base_url="http://localhost:8001",
        database_path=tmp_path / "recovery.sqlite",
        max_context_bytes=32000,
    )
    with TestClient(
        create_app(config, transport=httpx.MockTransport(upstream))
    ) as client:
        response = client.post(
            "/api/chat",
            json={
                "conversation_id": "field",
                "request_id": "math",
                "message": "Calculate chickpea return with the configured inputs.",
                "mode": "thinking",
            },
        )
        event = [json.loads(line) for line in response.text.splitlines()][-1]
        assert event["type"] == "answer"
        assert ("12800.0 UAH/ha" if summary_unavailable else "12,800 UAH/ha") in event[
            "content"
        ]
        assert event["status"] == ("partial" if summary_unavailable else "completed")
        assert "context limit" not in event["content"]
        assert "No final scientific conclusion" not in event["content"]
        assert event["evidence"][0]["result"]["gross_margin_per_ha"]["value"] == 12800
        assert len(bodies) == 2


def test_large_tool_results_fit_without_breaking_deepseek_call_sequence():
    config = Settings(
        provider="deepseek",
        openai_base_url="http://localhost:8001",
        max_context_bytes=8000,
    )
    messages = [
        {"role": "system", "content": "policy"},
        {
            "role": "user",
            "content": '{"type":"Polygon","coordinates":[[[32.691944,46.733694],[32.686611,46.764778],[32.732806,46.766306],[32.730944,46.731722],[32.691944,46.733694]]]}',
        },
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "Check sources.",
            "tool_calls": [
                {
                    "id": "one",
                    "type": "function",
                    "function": {"name": "source", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "one",
            "content": '{"data":"' + "x" * 12000 + '"}',
        },
    ]

    class Provider:
        async def complete(self, sent, schemas, thinking):
            assert Orchestrator.payload_bytes(sent, schemas) <= 8000
            assert sent[2]["reasoning_content"] == "Check sources."
            assert sent[3]["tool_call_id"] == "one"
            assert "omitted" in sent[3]["content"]
            return "completed"

    engine = Orchestrator(config, None, Provider(), None)
    assert asyncio.run(engine.model_call(messages, [], False)) == "completed"


def test_context_compaction_retains_source_statuses_and_call_ids():
    result = {
        "geometry": {"type": "Point", "coordinates": [32, 46]},
        "sources": [
            {
                "id": name,
                "name": name,
                "status": status,
                "checked_at": "2026-11-15T00:00:00Z",
                "limitation": "detailed provenance " * 300,
                "checks": [{"url": "https://example.com/", "status": status}],
            }
            for name, status in [
                ("power", "reachable"),
                ("soilgrids", "metadata_only"),
                ("nasadem", "no_coverage"),
                ("hls", "partial"),
                ("gpm", "authentication_required"),
                ("faostat", "unavailable"),
            ]
        ],
    }
    config = Settings(
        provider="deepseek",
        openai_base_url="http://localhost:8001",
        max_context_bytes=8000,
    )
    messages = [
        {"role": "system", "content": "policy " * 400},
        {"role": "user", "content": "Check sources for my small field."},
        {
            "role": "assistant",
            "content": "",
            "reasoning_content": "Inspect access.",
            "tool_calls": [
                {
                    "id": "sources",
                    "type": "function",
                    "function": {"name": "check_data_sources", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "sources", "content": json.dumps(result)},
    ]

    class Provider:
        async def complete(self, sent, schemas, thinking):
            assert Orchestrator.payload_bytes(sent, schemas) <= 8000
            assert sent[-1]["tool_call_id"] == "sources"
            compact = json.loads(sent[-1]["content"])
            assert [(s["id"], s["status"]) for s in compact["sources"]] == [
                (s["id"], s["status"]) for s in result["sources"]
            ]
            assert compact["details_omitted"] is True
            assert "context_omitted" not in compact
            return "completed"

    engine = Orchestrator(config, None, Provider(), None)
    assert asyncio.run(engine.model_call(messages, [], True)) == "completed"
