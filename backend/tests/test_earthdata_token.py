import httpx
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import Settings


def test_earthdata_token_only_reaches_allowlisted_nasa_hosts(tmp_path):
    seen = []

    def upstream(request):
        seen.append(request.url.host)
        if request.url.host in {"cmr.earthdata.nasa.gov", "gpm1.gesdisc.eosdis.nasa.gov"}:
            assert request.headers["authorization"] == "Bearer offline-token"
            return httpx.Response(302, headers={"location": "https://example.com/"})
        assert "authorization" not in request.headers
        return httpx.Response(401)

    config = Settings(database_path=tmp_path / "earthdata.sqlite", earthdata_token="offline-token")
    with TestClient(create_app(config, transport=httpx.MockTransport(upstream))) as client:
        response = client.get("/api/data-sources?latitude=46&longitude=32")
        assert response.status_code == 200
        assert "offline-token" not in response.text
    assert "cmr.earthdata.nasa.gov" in seen
    assert "gpm1.gesdisc.eosdis.nasa.gov" in seen
    assert "example.com" not in seen


def test_earthdata_token_is_loaded_without_exposing_it_in_config_repr(monkeypatch):
    monkeypatch.setenv("EARTHDATA_TOKEN", " offline-token ")
    config = Settings.from_env()
    assert config.earthdata_token == "offline-token"
    assert "offline-token" not in repr(config)
