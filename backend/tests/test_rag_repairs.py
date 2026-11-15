import json
from decimal import Decimal

import httpx
import pytest

from backend.config import Settings
from backend.providers import Provider, ProviderError
from backend.store import Store
from backend.tools import build_tools


def test_remote_rag_rejected():
    with pytest.raises(ValueError, match="local"):
        Settings(rag_url="https://external.example")


def test_filters_and_unavailable_propagate(tmp_path, monkeypatch):
    requests = []

    def upstream(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "unavailable",
                "reason": "stores offline",
                "chunks": [],
                "sql_data": [],
                "sources": {
                    "vector": {"status": "unavailable"},
                    "sql": {"status": "unavailable"},
                },
            },
        )

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(transport=httpx.MockTransport(upstream), **kw),
    )
    store = Store(tmp_path / "test.sqlite")
    tools = build_tools(store, Settings(rag_url="http://localhost:8000"))("chat")
    result = tools["search_agronomy_knowledge"].invoke(
        {"query": "wheat", "region": "Kherson", "start_year": 2016, "end_year": 2025}
    )
    assert requests[0]["region"] == "Kherson"
    assert result["status"] == "unavailable"
    assert result["reason"] == "stores offline"
    assert result["sources"]["vector"]["status"] == "unavailable"


@pytest.mark.parametrize("provider", ["ollama", "deepseek"])
@pytest.mark.parametrize("available", [True, False])
def test_prefetch_reaches_both_provider_wires(
    tmp_path, monkeypatch, provider, available
):
    retrieval_requests = []

    def retrieval(request):
        retrieval_requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "available" if available else "unavailable",
                "chunks": [
                    {
                        "source_file": "regional.csv",
                        "text": "verified retrieval marker",
                        "score": 1,
                    }
                ]
                if available
                else [],
                "sql_data": [],
                "reason": "stores offline" if not available else "",
                "sources": {},
            },
        )

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(transport=httpx.MockTransport(retrieval), **kw),
    )
    bodies = []

    def upstream(request):
        bodies.append(json.loads(request.content))
        if provider == "ollama":
            return httpx.Response(
                200,
                json={
                    "message": {"role": "assistant", "content": "Answer"},
                    "done": True,
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "Answer"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10},
            },
        )

    config = Settings(
        database_path=tmp_path / "test.sqlite",
        provider=provider,
        rag_url="http://localhost:8000",
        api_key="test",
        input_rate=Decimal(1),
        output_rate=Decimal(1),
    )

    async def run():
        from backend.orchestrator import Orchestrator

        store = Store(config.database_path)
        store.begin("a", "one", "What about John's wheat?", "auto", [])
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            engine = Orchestrator(
                config, store, Provider(config, client), build_tools(store, config)
            )
            return [
                event
                async for event in engine.run(
                    "a", "one", "What about John's wheat?", "auto", []
                )
            ]

    import asyncio

    result = asyncio.run(run())[-1]
    assert result["type"] == "answer", result
    assert retrieval_requests[0]["region"] == "Kherson Oblast"
    assert retrieval_requests[0]["start_year"] == 2016
    assert retrieval_requests[0]["end_year"] == 2025
    prompt = bodies[0]["messages"][0]["content"]
    assert ("verified retrieval marker" if available else "unavailable") in prompt
    assert result["evidence"][0]["result"]["status"] == (
        "available" if available else "unavailable"
    )


def test_provider_does_not_drop_explicit_tools_or_thinking():
    seen = []

    def upstream(request):
        seen.append(json.loads(request.content))
        return httpx.Response(422)

    config = Settings(provider="ollama", rag_url="direct")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            with pytest.raises(ProviderError):
                await Provider(config, client).complete(
                    [{"role": "user", "content": "hi"}], [{"type": "function"}], True
                )

    import asyncio

    asyncio.run(run())
    assert len(seen) == 1


def test_remote_custom_endpoint_cannot_bypass_budget(tmp_path):
    from backend.orchestrator import Orchestrator

    calls = []

    def upstream(request):
        calls.append(request)
        return httpx.Response(500)

    async def run():
        config = Settings(
            provider="deepseek", openai_base_url="https://remote.example/v1"
        )
        store = Store(tmp_path / "budget.sqlite")
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            engine = Orchestrator(
                config, store, Provider(config, client), build_tools(store, config)
            )
            with pytest.raises(ProviderError, match="rates"):
                await engine.model_call([{"role": "user", "content": "hi"}], [], False)

    import asyncio

    asyncio.run(run())
    assert not calls


def test_http_rag_failure_never_falls_back(monkeypatch):
    from backend import tools as module

    original = httpx.Client

    def upstream(request):
        return httpx.Response(503)

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(transport=httpx.MockTransport(upstream), **kw),
    )
    result = module._call_rag_service("http://localhost:8000", "wheat")
    assert result["status"] == "unavailable"
    assert result["chunks"] == []


def test_health_and_capabilities_do_not_claim_scientific_readiness(
    tmp_path, monkeypatch
):
    original = httpx.Client

    def upstream(request):
        assert request.url.path == "/health"
        return httpx.Response(
            200,
            json={
                "status": "partial",
                "sources": {
                    "vector": {"status": "unavailable"},
                    "sql": {"status": "available"},
                },
            },
        )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(transport=httpx.MockTransport(upstream), **kw),
    )
    result = build_tools(
        Store(tmp_path / "health.sqlite"), Settings(rag_url="http://localhost:8000")
    )("a")["get_capabilities"].invoke({})
    assert result["scientific_analysis"] == "unavailable"
    assert result["retrieval"]["status"] == "partial"


def test_evidence_is_bounded_with_large_profile(tmp_path):
    from backend.orchestrator import Orchestrator

    config = Settings(rag_url="direct")
    store = Store(tmp_path / "context.sqlite")
    engine = Orchestrator(config, store, None, None)
    messages = engine.context("a", "hello", [], rag_context="x" * 10000)
    assert engine.payload_bytes(messages, []) <= config.max_context_bytes


def test_escaped_evidence_fits_budget(tmp_path):
    from backend.orchestrator import Orchestrator

    config = Settings(rag_url="direct")
    engine = Orchestrator(config, Store(tmp_path / "escaped.sqlite"), None, None)
    messages = engine.context("a", "hello", [], rag_context='"\\' * 10000)
    assert engine.payload_bytes(messages, []) <= config.max_context_bytes


def test_bounded_evidence_preserves_spatial_temporal_scope():
    from backend.tools import _bound_rag_payload

    result = _bound_rag_payload(
        {
            "chunks": [
                {
                    "text": "evidence",
                    "score": 1,
                    "source_file": "field.csv",
                    "region": "Kherson",
                    "start_year": 2016,
                    "end_year": 2025,
                }
            ]
        }
    )
    assert result["chunks"][0]["region"] == "Kherson"
    assert result["chunks"][0]["start_year"] == 2016
    assert result["chunks"][0]["end_year"] == 2025


def test_sql_sample_counts_and_provenance_survive_bounds():
    from backend.tools import _bound_rag_payload

    payload = {
        "status": "available",
        "sql_data": [
            {
                "table": "weather",
                "row_count": 8,
                "row_count_is_sample": True,
                "source_file": "weather.csv",
                "region": "Kherson",
                "sample_rows": [{"year": year} for year in range(2016, 2024)],
                "columns": ["year"],
            }
        ],
    }
    result = _bound_rag_payload(payload)
    entry = result["sql_data"][0]
    assert entry["row_count_is_sample"] is True
    assert (
        entry["row_count"]
        == entry["sample_row_count"]
        == len(entry["sample_rows"])
        == 5
    )
    assert entry["population_row_count"] is None
    assert entry["source_file"] == "weather.csv"
    assert entry["region"] == "Kherson"


def test_sql_counts_update_when_byte_budget_drops_rows():
    from backend.tools import _bound_rag_payload

    result = _bound_rag_payload(
        {
            "status": "available",
            "sql_data": [
                {
                    "table": "weather",
                    "row_count": 50,
                    "sample_rows": [{"value": "x" * 150} for _ in range(5)],
                }
            ],
        },
        max_bytes=650,
    )
    entry = result["sql_data"][0]
    assert len(entry["sample_rows"]) < 5
    assert entry["row_count"] == entry["sample_row_count"] == len(entry["sample_rows"])
    assert entry["population_row_count"] == 50
    assert result["truncated"] is True
    assert result["status"] == "partial"
    assert len(json.dumps(result, ensure_ascii=False).encode()) <= 650


@pytest.mark.parametrize(
    "payload",
    [
        {
            "status": "available",
            "chunks": [{"source_file": "x" * 2000, "text": "evidence", "score": 1}],
        },
        {
            "status": "available",
            "sql_data": [
                {
                    "table": "x" * 2000,
                    "row_count": 1,
                    "sample_rows": [{"value": "x" * 2000}],
                }
            ],
        },
        {"status": "available", "sources": {"vector": {"metadata": "x" * 2000}}},
    ],
)
def test_oversized_required_metadata_has_bounded_explicit_failure(payload):
    from backend.tools import _bound_rag_payload

    result = _bound_rag_payload(payload, max_bytes=400)
    assert len(json.dumps(result, ensure_ascii=False).encode()) <= 400
    assert result["status"] == "unavailable"
    assert result["truncated"] is True


def test_ollama_context_window_is_explicit_and_cloud_wire_unchanged(monkeypatch):
    import asyncio

    monkeypatch.setenv("OLLAMA_CONTEXT_TOKENS", "24576")
    config = Settings.from_env()
    assert config.ollama_context_tokens == 24576
    assert Settings().ollama_context_tokens == 16384
    for value in (0, -1, 262145):
        with pytest.raises(ValueError):
            Settings(ollama_context_tokens=value)

    async def run(provider):
        bodies = []

        def upstream(request):
            bodies.append(json.loads(request.content))
            response = (
                {"message": {"role": "assistant", "content": "ok"}, "done": True}
                if provider == "ollama"
                else {
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": "ok"},
                            "finish_reason": "stop",
                        }
                    ]
                }
            )
            return httpx.Response(200, json=response)

        settings = Settings(
            provider=provider, api_key="offline-test", ollama_context_tokens=24576
        )
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as client:
            await Provider(settings, client).complete(
                [{"role": "user", "content": "hello"}], [], False
            )
        return bodies[0]

    assert asyncio.run(run("ollama"))["options"]["num_ctx"] == 24576
    assert "options" not in asyncio.run(run("deepseek"))
