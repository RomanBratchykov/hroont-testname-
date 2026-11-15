from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import Settings


def test_render_url_allows_browser_and_health_requests_but_rejects_other_hosts(
    tmp_path, monkeypatch
):
    origin = "https://croptato-test.onrender.com"
    monkeypatch.setenv("PUBLIC_ORIGIN", "")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", origin)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "render.sqlite"))
    with TestClient(create_app(Settings.from_env()), base_url=origin) as client:
        assert client.get("/api/health").status_code == 200
        assert (
            client.post(
                "/api/chat", headers={"Origin": origin}, json={"action": "list"}
            ).status_code
            == 200
        )
        assert (
            client.get("/api/health", headers={"Host": "other.example.com"}).status_code
            == 400
        )
        assert (
            client.post(
                "/api/chat",
                headers={"Origin": "https://other.example.com"},
                json={"action": "list"},
            ).status_code
            == 403
        )
