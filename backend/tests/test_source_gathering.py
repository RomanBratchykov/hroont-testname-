import asyncio
import json

import httpx

from backend.field_data import check_sources


def test_transient_source_failure_is_retried_and_checks_are_concurrent():
    calls = {}
    active = peak = 0

    async def upstream(request):
        nonlocal active, peak
        key = str(request.url)
        calls[key] = calls.get(key, 0) + 1
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.001)
        active -= 1
        if request.url.host == "cmr.earthdata.nasa.gov" and calls[key] == 1:
            return httpx.Response(503)
        if request.url.host == "cmr.earthdata.nasa.gov":
            return httpx.Response(200, json={"feed": {"entry": [{"id": "match"}]}})
        return httpx.Response(401)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            result = await check_sources(http, 46, 32)
        sources = {row["id"]: row for row in result["sources"]}
        assert sources["nasadem"]["status"] == "metadata_only"
        assert sources["hls"]["status"] == "metadata_only"
        assert sources["soilgrids"]["status"] == "authentication_required"
        assert sources["soilgrids"]["checks"][0]["http_status"] == 401
        assert peak <= 4
        assert all(count <= 2 for count in calls.values())

    asyncio.run(check())


def test_source_checks_explain_timeout_and_invalid_payloads_without_claiming_data():
    async def upstream(request):
        if request.url.host == "maps.isric.org":
            raise httpx.ReadTimeout("private transport details")
        return httpx.Response(200, text="Unexpected login page")

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            result = await check_sources(http, 46, 32)
        sources = {row["id"]: row for row in result["sources"]}
        assert sources["soilgrids"]["checks"][0]["reason"] == "timeout"
        assert sources["power"]["checks"][0]["reason"] == "invalid_response"
        assert all(source["status"] == "unavailable" for source in result["sources"])
        assert "private transport details" not in json.dumps(result)

    asyncio.run(check())


def test_source_details_over_16kb_are_kept_as_evidence_but_not_sent_to_model(tmp_path):
    from langchain_core.tools import StructuredTool

    from backend.config import Settings
    from backend.orchestrator import Orchestrator
    from backend.providers import Completion, FunctionCall, ToolCall
    from backend.store import Store
    from backend.tools import FieldPointArgs

    result = {
        "geometry": {"type": "Point", "coordinates": [32, 46]},
        "sources": [
            {
                "id": name,
                "status": "metadata_only",
                "checked_at": "2026-11-15T00:00:00Z",
                "limitation": "Detailed source provenance. " * 200,
                "checks": [],
            }
            for name in ("power", "soilgrids", "nasadem", "hls", "gpm", "faostat")
        ],
    }
    assert len(json.dumps(result).encode()) > 16000
    invocations = []

    def check_data_sources(latitude, longitude):
        invocations.append((latitude, longitude))
        return result

    tool = StructuredTool.from_function(
        check_data_sources,
        args_schema=FieldPointArgs,
        description="Inspect source access.",
    )

    class Provider:
        calls = 0

        async def complete(self, messages, schemas, thinking):
            self.calls += 1
            if self.calls <= 2:
                call = ToolCall(
                    id=str(self.calls),
                    function=FunctionCall(
                        name="check_data_sources",
                        arguments={"latitude": 46, "longitude": 32},
                    ),
                )
                return Completion(
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [call.model_dump()],
                    },
                    [call],
                    None,
                    None,
                )
            compact = json.loads(messages[-1]["content"])
            assert len(compact["sources"]) == 6
            assert compact["details_omitted"] is True
            return Completion(
                {"role": "assistant", "content": "Metadata checked."}, [], None, None
            )

    store = Store(tmp_path / "evidence.sqlite")
    store.begin("field", "request", "Check source access at 46, 32.", "fast", [])
    engine = Orchestrator(
        Settings(database_path=store.path),
        store,
        Provider(),
        lambda _: {"check_data_sources": tool},
    )

    async def check():
        events = [
            event
            async for event in engine.run(
                "field", "request", "Check source access at 46, 32.", "fast", []
            )
        ]
        assert events[-1]["type"] == "answer"
        assert events[-1]["evidence"][0]["result"] == result
        assert invocations == [(46, 32)]

    asyncio.run(check())
