import json

import httpx
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import Settings
from backend.store import Store
from backend.tools import build_tools

CORNERS = [[32.691944, 46.733694], [32.686611, 46.764778], [32.732806, 46.766306], [32.730944, 46.731722]]


def test_profile_tool_persists_across_chats_and_restart_without_crossing_owners(tmp_path):
    path = tmp_path / "profile.sqlite"
    store = Store(path)
    for owner in ("alice", "bob"):
        store.admit_guest(owner, None)
        store.begin(owner, owner, "Save my field", "fast", [], owner=owner)
    tools = build_tools(store)("alice")
    saved = tools["save_user_info"].invoke({"facts": {"name": "Alice"}, "boundary": CORNERS})
    assert saved["status"] == "saved"
    assert saved["profile"]["boundary"]["coordinates"][0] == CORNERS + [CORNERS[0]]
    restarted = Store(path)
    assert restarted.profile("alice")["facts"]["name"] == "Alice"
    assert build_tools(restarted)("bob")["read_user_info"].invoke({})["profile"]["facts"]["name"] == "John"
    restarted.update_profile("alice", {"facts": {"irrigation": "Rainfed"}})
    assert restarted.profile("alice")["facts"]["name"] == "Alice"
    assert restarted.profile("alice")["facts"]["irrigation"] == "Rainfed"


def test_profile_api_is_private_and_invalid_boundary_does_not_overwrite(tmp_path):
    config = Settings(database_path=tmp_path / "api.sqlite")
    app = create_app(config)
    with TestClient(app) as alice, TestClient(app) as bob:
        saved = alice.post("/api/chat", json={"action": "save_profile", "profile": {"facts": {"name": "Alice"}, "boundary": CORNERS}})
        assert saved.status_code == 200
        assert bob.post("/api/chat", json={"action": "profile"}).json()["facts"]["name"] == "John"
        invalid = alice.post("/api/chat", json={"action": "save_profile", "profile": {"boundary": [CORNERS[0], CORNERS[2], CORNERS[1], CORNERS[3]]}})
        assert invalid.status_code == 422
        assert alice.post("/api/chat", json={"action": "profile"}).json()["facts"]["name"] == "Alice"


def test_starting_profile_can_be_changed_and_cleared_without_reseeding(tmp_path):
    path = tmp_path / "defaults.sqlite"
    store = Store(path)
    store.admit_guest("alice", None)
    profile = store.profile("alice")
    assert profile["facts"]["name"] == "John"
    assert profile["facts"]["field_area"] == "30 ha"
    assert profile["boundary"] is not None
    store.update_profile("alice", {"facts": {"field_area": "42 ha"}})
    assert Store(path).profile("alice")["facts"]["field_area"] == "42 ha"
    cleared = store.clear_profile("alice")
    assert cleared["facts"] == {}
    assert cleared["boundary"] is None
    assert Store(path).profile("alice")["facts"] == {}


def test_clear_profile_api_only_clears_the_current_user(tmp_path):
    config = Settings(database_path=tmp_path / "clear.sqlite")
    with TestClient(create_app(config)) as client:
        assert client.post("/api/chat", json={"action": "profile"}).json()["facts"]["name"] == "John"
        cleared = client.post("/api/chat", json={"action": "clear_profile"})
        assert cleared.status_code == 200
        assert cleared.json()["facts"] == {}
        assert cleared.json()["boundary"] is None
        assert client.post("/api/chat", json={"action": "profile"}).json()["facts"] == {}
        client.cookies.clear()
        assert client.post("/api/chat", json={"action": "profile"}).json()["facts"]["name"] == "John"


def test_chat_can_save_profile_and_new_chat_receives_it(tmp_path):
    requests = []

    def upstream(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            message = {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "save_user_info", "arguments": {"facts": {"name": "Alice"}, "boundary": CORNERS}}}]}
        else:
            message = {"role": "assistant", "content": "Your information is saved."}
        return httpx.Response(200, json={"message": message, "done": True})

    config = Settings(database_path=tmp_path / "chat.sqlite")
    with TestClient(create_app(config, transport=httpx.MockTransport(upstream))) as client:
        response = client.post("/api/chat", json={"conversation_id": "one", "request_id": "save", "message": "Save my name Alice and field boundary", "mode": "fast"})
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1]["evidence"][0]["result"]["status"] == "saved"
        client.post("/api/chat", json={"conversation_id": "two", "request_id": "read", "message": "What is my name?", "mode": "fast"})
        assert "Alice" in requests[-1]["messages"][0]["content"]
