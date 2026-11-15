import asyncio
import json

import httpx

from backend.config import Settings
from backend.field_data import check_sources


def test_nasa_token_is_private_and_only_sent_to_nasa_open_apis(monkeypatch):
    monkeypatch.setenv("NASA_TOKEN", " private-nasa-key ")
    config = Settings.from_env()
    assert config.nasa_token == "private-nasa-key"
    assert "private-nasa-key" not in repr(config)
    seen = []

    def upstream(request):
        seen.append(request.url.host)
        assert "private-nasa-key" not in str(request.url)
        if request.url.host == "api.nasa.gov":
            assert request.headers["X-Api-Key"] == "private-nasa-key"
            assert "authorization" not in request.headers
            return httpx.Response(200, json={"near_earth_objects": []})
        assert "X-Api-Key" not in request.headers
        return httpx.Response(401)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            result = await check_sources(http, 46, 32, nasa_token=config.nasa_token)
        assert result["nasa_open_api"]["status"] == "reachable"
        assert "private-nasa-key" not in json.dumps(result)
        assert len(result["sources"]) == 6

    asyncio.run(check())
    assert "api.nasa.gov" in seen


def test_missing_nasa_token_is_explicit_and_does_not_use_demo_key():
    def upstream(request):
        assert request.url.host != "api.nasa.gov"
        return httpx.Response(401)

    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            result = await check_sources(http, 46, 32)
        assert result["nasa_open_api"]["status"] == "not_configured"

    asyncio.run(check())
