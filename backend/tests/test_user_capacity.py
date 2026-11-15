import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.api import create_app
from backend.config import Settings


def test_default_deepseek_capacity_accepts_more_than_four_users(tmp_path):
    config = Settings(provider="deepseek", database_path=tmp_path / "capacity.sqlite")
    with TestClient(create_app(config)) as client:
        for _ in range(12):
            client.cookies.clear()
            assert client.post("/api/chat", json={"action": "list"}).status_code == 200
        health = client.get("/api/health").json()
        assert health["max_active_users"] == 50
        assert health["capacity"] == 4


def test_custom_capacity_is_enforced_and_existing_user_keeps_access(tmp_path):
    config = Settings(provider="deepseek", max_active_users=6, database_path=tmp_path / "limit.sqlite")
    with TestClient(create_app(config)) as client:
        for _ in range(6):
            client.cookies.clear()
            assert client.post("/api/chat", json={"action": "list"}).status_code == 200
        cookie = client.cookies.get("croptato_guest")
        client.cookies.clear()
        denied = client.post("/api/chat", json={"action": "list"})
        assert denied.status_code == 429
        assert "6-user capacity" in denied.json()["detail"]
        client.cookies.set("croptato_guest", cookie)
        assert client.post("/api/chat", json={"action": "list"}).status_code == 200


def test_capacity_and_model_parallelism_are_configurable(monkeypatch):
    monkeypatch.setenv("MAX_ACTIVE_USERS", "100")
    monkeypatch.setenv("MODEL_CONCURRENCY", "8")
    config = Settings.from_env()
    assert config.max_active_users == 100
    assert config.concurrency == 8


@pytest.mark.parametrize("kwargs", [{"max_active_users": 0}, {"concurrency": 0}, {"concurrency": 65}])
def test_capacity_settings_reject_invalid_limits(kwargs):
    with pytest.raises(ValidationError):
        Settings(**kwargs)
