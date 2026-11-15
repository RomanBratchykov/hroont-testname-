import asyncio
import json

from backend.config import Settings
from backend.orchestrator import Orchestrator


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
