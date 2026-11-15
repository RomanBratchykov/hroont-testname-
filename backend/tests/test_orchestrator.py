import asyncio
import json
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import Settings


def settings(tmp_path, **kwargs):
    return Settings(database_path=tmp_path / "test.sqlite", **kwargs)


def ollama_reply(content="Where is your field?", calls=None):
    return {
        "message": {
            "role": "assistant",
            "content": content,
            **({"tool_calls": calls} if calls else {}),
        },
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 100,
        "eval_count": 10,
    }


def events(response):
    assert response.status_code == 200, response.text
    return [json.loads(line) for line in response.text.splitlines() if line]


def test_chat_persists_history_and_reuses_completed_request(tmp_path):
    requests = []

    def upstream(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200, json=ollama_reply())

    app = create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    with TestClient(app) as client:
        payload = {
            "action": "send",
            "conversation_id": "field-a",
            "request_id": "turn-1",
            "message": "Hello",
        }
        first = events(client.post("/api/chat", json=payload))
        assert first[-1]["type"] == "answer"
        assert first[-1]["content"] == "Where is your field?"
        assert (
            events(client.post("/api/chat", json=payload))[-1]["content"]
            == first[-1]["content"]
        )
        assert len(requests) == 1
        events(
            client.post(
                "/api/chat",
                json={**payload, "request_id": "turn-2", "message": "Kharkiv"},
            )
        )
        assert [
            m["content"] for m in requests[-1]["messages"] if m["role"] != "system"
        ] == ["Hello", "Where is your field?", "Kharkiv"]
        history = client.post(
            "/api/chat", json={"action": "read", "conversation_id": "field-a"}
        ).json()
        assert [m["role"] for m in history["messages"]] == [
            "user",
            "assistant",
            "user",
            "assistant",
        ]
        assert (
            client.post(
                "/api/chat", json={**payload, "message": "different"}
            ).status_code
            == 409
        )
        saved_cookie = client.cookies.get("croptato_guest")
    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream)),
        cookies={"croptato_guest": saved_cookie},
    ) as client:
        assert (
            len(
                client.post("/api/chat", json={"action": "list"}).json()[
                    "conversations"
                ]
            )
            == 1
        )
        assert (
            client.post(
                "/api/chat", json={"action": "delete", "conversation_id": "field-a"}
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/chat", json={"action": "read", "conversation_id": "field-a"}
            ).status_code
            == 404
        )


def test_tools_are_bounded_and_unknown_tools_never_execute(tmp_path):
    count = 0

    def upstream(request):
        nonlocal count
        count += 1
        body = json.loads(request.content)
        if count == 1:
            assert {t["function"]["name"] for t in body["tools"]} == {
                "calculate_gross_margin",
                "calculate_crop_score",
                "validate_rotation",
                "calculate_rusle",
                "save_user_info",
                "clear_user_info",
                "read_user_info",
                "read_history",
                "get_capabilities",
                "get_climate_history",
                "check_data_sources",
            }
            return httpx.Response(
                200,
                json=ollama_reply(
                    "",
                    [
                        {
                            "function": {
                                "name": "run_shell",
                                "arguments": {"command": "touch /tmp/never"},
                            }
                        }
                    ],
                ),
            )
        assert json.loads(body["messages"][-1]["content"])["status"] == "unavailable"
        return httpx.Response(
            200,
            json=ollama_reply(
                "", [{"function": {"name": "get_capabilities", "arguments": {}}}]
            ),
        )

    app = create_app(
        settings(tmp_path, max_model_calls=2), transport=httpx.MockTransport(upstream)
    )
    with TestClient(app) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "action": "send",
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Calculate erosion",
                },
            )
        )
        assert result[-1]["type"] == "answer"
        assert result[-1]["status"] == "partial"
        assert (
            result[-1]["evidence"][-1]["result"]["scientific_analysis"] == "partial"
        )
        assert count == 2


def test_provider_errors_are_honest_and_do_not_leak_response(tmp_path):
    def upstream(request):
        return httpx.Response(401, text="secret API token details")

    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "action": "send",
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Hello",
                },
            )
        )
        assert result[-1]["type"] == "error"
        assert result[-1]["code"] == "configuration"
        assert "secret" not in json.dumps(result)


def test_deepseek_protocol_preserves_thinking_tool_continuation_and_budget(tmp_path):
    calls = []

    def upstream(request):
        assert request.url == "https://api.deepseek.com/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        calls.append(body)
        if len(calls) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "reasoning_content": "private thought",
                "tool_calls": [
                    {
                        "id": "call-a",
                        "type": "function",
                        "function": {"name": "get_capabilities", "arguments": "{}"},
                    }
                ],
            }
        else:
            assert body["messages"][-2]["reasoning_content"] == "private thought"
            assert body["messages"][-1]["tool_call_id"] == "call-a"
            message = {
                "role": "assistant",
                "content": "Scientific scripts are not connected.",
            }
        return httpx.Response(
            200,
            json={
                "choices": [{"message": message, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20},
            },
        )

    config = settings(
        tmp_path,
        provider="deepseek",
        api_key="test-key",
        input_rate=Decimal(1),
        output_rate=Decimal(2),
    )
    with TestClient(
        create_app(config, transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "action": "send",
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Hello",
                    "mode": "thinking",
                },
            )
        )
        assert calls[0]["thinking"] == {"type": "enabled"}
        assert result[-1]["type"] == "answer"
        assert "private thought" not in json.dumps(result)
        assert Decimal(
            str(client.get("/api/health").json()["budget"]["spent_usd"])
        ) == Decimal("0.00028")


def test_budget_blocks_dispatch_and_is_durable(tmp_path):
    def upstream(request):
        pytest.fail("Budget-exhausted call must not reach provider")

    config = settings(
        tmp_path,
        provider="deepseek",
        api_key="key",
        input_rate=Decimal(1000),
        output_rate=Decimal(1000),
    )
    with TestClient(
        create_app(config, transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "action": "send",
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Hello",
                },
            )
        )
        assert result[-1]["code"] == "budget_exhausted"


def test_no_fallback_and_cyrillic_not_sent_untranslated(tmp_path):
    def upstream(request):
        pytest.fail("Untranslated input must not reach model")

    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "action": "send",
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Привіт",
                },
            )
        )
        assert result[-1]["code"] == "unsupported_language"
        assert client.get("/api/health").json()["provider"] == "ollama"


def test_invalid_actions_origin_and_upload_rejected(tmp_path):
    with TestClient(create_app(settings(tmp_path))) as client:
        assert client.post("/api/chat", json={"action": "arbitrary"}).status_code == 422
        assert (
            client.post(
                "/api/chat",
                headers={"Origin": "https://evil.example"},
                json={"action": "clear"},
            ).status_code
            == 403
        )
        result = client.post(
            "/api/chat",
            json={
                "action": "send",
                "conversation_id": "a",
                "request_id": "r",
                "message": "Read",
                "files": [{"name": "../bad.exe", "data": "AA=="}],
            },
        )
        assert result.status_code == 422


def test_retention_deletes_chat_and_associated_runs_but_not_budget(tmp_path):
    from backend.store import Store

    store = Store(tmp_path / "store.sqlite")
    store.begin("old", "r", "Hello", "fast", [])
    store.reserve("charge", Decimal("0.25"), "testing", Decimal(3))
    with store.connect() as db:
        db.execute("UPDATE conversations SET updated_at = 1")
    store.expire()
    assert store.list_chats() == []
    assert store.budget("testing")["reserved_usd"] == 0.25
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 0


def test_cancelled_turn_releases_slot_and_is_not_replayed(tmp_path):
    from backend.orchestrator import Orchestrator
    from backend.providers import Provider
    from backend.store import Store
    from backend.tools import build_tools

    async def check():
        entered = asyncio.Event()

        async def upstream(request):
            entered.set()
            await asyncio.sleep(60)

        config = settings(tmp_path)
        store = Store(config.database_path)
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            engine = Orchestrator(
                config, store, Provider(config, http), build_tools(store)
            )
            store.begin("a", "r", "Hello", "fast", [])

            async def consume():
                return [
                    event async for event in engine.run("a", "r", "Hello", "fast", [])
                ]

            task = asyncio.create_task(consume())
            await entered.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert store.run_record("r")["status"] == "cancelled"
            assert engine.active == 0
            assert store.begin("a", "r", "Hello", "fast", [])["status"] == "cancelled"

    asyncio.run(check())


def test_non_english_is_rejected_even_when_translation_is_configured(tmp_path):
    def upstream(request):
        pytest.fail("Unsupported input must not reach translation or model services")

    config = settings(tmp_path, translation_url="http://127.0.0.1:5000/translate")
    with TestClient(
        create_app(config, transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Моє поле 30 гектарів",
                },
            )
        )
        assert result[-1]["code"] == "unsupported_language"
        assert (
            result[-1]["message"]
            == "I currently support English only. Please send your message in English."
        )
        assert not any(event.get("stage") == "translating" for event in result)


@pytest.mark.parametrize("name,text", [
    ("field.json", '{"type":"Polygon","coordinates":[[[32,46],[33,46],[33,47],[32,47],[32,46]]]}'),
    ("field.txt", "Area (ha): 30"),
    ("field.md", "# Field\nArea (ha): 30"),
    ("field.csv", "area_ha\n30"),
])
def test_text_attachments_are_parsed_locally(tmp_path, name, text):
    import base64

    def upstream(request):
        body = json.loads(request.content)
        content = body["messages"][-1]["content"]
        assert text in content
        assert f"Untrusted attachment: {name}" in content
        return httpx.Response(200, json=ollama_reply())

    with TestClient(create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))) as client:
        result = events(client.post("/api/chat", json={
            "conversation_id": "a", "request_id": "r", "message": "Read my field",
            "files": [{"name": name, "data": base64.b64encode(text.encode()).decode()}],
        }))
        assert result[-1]["type"] == "answer"


@pytest.mark.parametrize("name", ["image.png", "report.pdf", "field.xlsx"])
def test_binary_formats_explain_how_to_supply_text(tmp_path, name):
    from backend.documents import Attachment
    with pytest.raises(ValueError, match="paste it into the message"):
        Attachment(name=name, data="AA==")

@pytest.mark.parametrize("parallelism", [4, 8])
def test_concurrency_cap_queue_fairness_and_cancelled_paid_reservation(tmp_path, parallelism):
    from backend.orchestrator import Orchestrator
    from backend.providers import Provider
    from backend.store import Store
    from backend.tools import build_tools

    async def check():
        entered = []
        release = asyncio.Event()

        async def upstream(request):
            text = json.loads(request.content)["messages"][-1]["content"]
            entered.append(text)
            await release.wait()
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": "Hello"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

        config = settings(
            tmp_path,
            provider="deepseek",
            concurrency=parallelism,
            api_key="key",
            input_rate=Decimal(1),
            output_rate=Decimal(2),
        )
        store = Store(config.database_path)
        async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as http:
            engine = Orchestrator(
                config, store, Provider(config, http), build_tools(store)
            )

            async def turn(index):
                key = str(index)
                store.begin(key, key, key, "fast", [])
                return [event async for event in engine.run(key, key, key, "fast", [])]

            tasks = [asyncio.create_task(turn(index)) for index in range(parallelism + 2)]
            for _ in range(100):
                await asyncio.sleep(0.005)
                if len(entered) == parallelism:
                    break
            assert entered == [str(index) for index in range(parallelism)]
            assert engine.active == parallelism
            tasks[0].cancel()
            with pytest.raises(asyncio.CancelledError):
                await tasks[0]
            for _ in range(100):
                await asyncio.sleep(0.005)
                if len(entered) == parallelism + 1:
                    break
            assert entered[-1] == str(parallelism)
            assert store.budget("testing")["reserved_usd"] > 0
            release.set()
            await asyncio.gather(*tasks[1:])
            assert entered[-1] == str(parallelism + 1)
            assert engine.active == 0
            remaining = store.budget("testing")["reserved_usd"]
            assert remaining > 0
            store.recover()
            assert store.budget("testing")["reserved_usd"] == remaining

    asyncio.run(check())


@pytest.mark.parametrize(
    "message",
    [
        "我的农田面积是30公顷",
        "مساحة حقلي 30 هكتار",
        "Mi campo tiene treinta hectareas y quiero conocer su clima historico.",
    ],
)
def test_unsupported_scripts_are_not_dispatched_untranslated(tmp_path, message):
    def upstream(request):
        pytest.fail("Non-English input must not bypass translation")

    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={"conversation_id": "a", "request_id": "r", "message": message},
            )
        )
        assert result[-1]["code"] == "unsupported_language"


def test_request_ids_cannot_collide_with_assistant_message_ids(tmp_path):
    def upstream(request):
        return httpx.Response(200, json=ollama_reply())

    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    ) as client:
        for request_id in ["r", "r-answer"]:
            result = events(
                client.post(
                    "/api/chat",
                    json={
                        "conversation_id": "a",
                        "request_id": request_id,
                        "message": "Hello",
                    },
                )
            )
            assert result[-1]["type"] == "answer"


def test_model_receives_unlabelled_topics_and_conversational_guidance(tmp_path):
    import re

    from backend.orchestrator import Orchestrator
    from backend.store import Store

    store = Store(tmp_path / "context.sqlite")
    store.begin("field-a", "friendly-turn", "My field is near Kharkiv.", "fast", [])
    engine = Orchestrator(settings(tmp_path), store, None, None)
    messages = engine.context("field-a", "My field is near Kharkiv.", [])
    policy = messages[0]["content"]
    assert not re.search(r"\bQ\d{2}\b", policy)
    assert "farmer-interview assistant" not in policy
    assert "Internal field-information reference" in policy
    assert "Do not copy" in policy
    assert "one short, relevant question" in policy
    # Retain the information needs without exposing the numbered questionnaire.
    assert "GeoJSON" in policy
    assert "irrigated" in policy
    assert "Unknown is valid" in policy
    assert messages[-1]["content"] == "My field is near Kharkiv."


@pytest.mark.parametrize("mode,expected", [("fast", 1024), ("thinking", 4096)])
def test_reasoning_has_separate_output_budget(tmp_path, mode, expected):
    def upstream(request):
        body = json.loads(request.content)
        assert body["options"]["num_predict"] == expected
        assert body["think"] is (mode == "thinking")
        return httpx.Response(200, json=ollama_reply())

    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Hello",
                    "mode": mode,
                },
            )
        )
        assert result[-1]["type"] == "answer"


def test_reasoning_exhaustion_is_reported_without_exposing_private_thoughts(tmp_path):
    def upstream(request):
        reply = ollama_reply("")
        reply["message"]["thinking"] = "private reasoning"
        reply["done_reason"] = "length"
        return httpx.Response(200, json=reply)

    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "conversation_id": "a",
                    "request_id": "r",
                    "message": "Hello",
                    "mode": "thinking",
                },
            )
        )
        assert result[-1]["code"] == "reasoning_limit"
        assert "private reasoning" not in json.dumps(result)
        assert "Fast" in result[-1]["message"]


def test_configured_public_origin_accepts_tunnel_and_rejects_other_sites(tmp_path):
    config = settings(tmp_path, public_origin="https://gravitydefiers.dpdns.org")
    with TestClient(create_app(config), base_url=config.public_origin) as client:
        assert client.get("/api/health").status_code == 200
        assert (
            client.post(
                "/api/chat",
                headers={"Origin": config.public_origin},
                json={"action": "list"},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/chat",
                headers={"Origin": "https://other.example"},
                json={"action": "list"},
            ).status_code
            == 403
        )
        assert (
            client.get("/api/health", headers={"Host": "other.example"}).status_code
            == 400
        )


def test_guest_workspaces_are_private_and_clear_only_own_history(tmp_path):
    app = create_app(
        settings(tmp_path),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=ollama_reply())
        ),
    )
    with TestClient(app) as first, TestClient(app) as second:
        payload = {"conversation_id": "private", "request_id": "r", "message": "Hello"}
        assert events(first.post("/api/chat", json=payload))[-1]["type"] == "answer"
        assert first.cookies.get("croptato_guest")
        assert (
            second.post("/api/chat", json={"action": "list"}).json()["conversations"]
            == []
        )
        for action in ["read", "delete", "rename"]:
            assert (
                second.post(
                    "/api/chat",
                    json={
                        "action": action,
                        "conversation_id": "private",
                        "title": "Stolen",
                    },
                ).status_code
                == 404
            )
        assert (
            second.post(
                "/api/chat", json={**payload, "request_id": "another"}
            ).status_code
            == 404
        )
        assert second.post("/api/chat", json={"action": "clear"}).status_code == 200
        assert (
            first.post(
                "/api/chat", json={"action": "read", "conversation_id": "private"}
            ).status_code
            == 200
        )
        assert second.post("/api/chat", json=payload).status_code == 404


@pytest.mark.parametrize("provider,expected", [("deepseek", 429), ("ollama", 200)])
def test_guest_capacity_is_provider_specific(tmp_path, provider, expected):
    app = create_app(settings(tmp_path, provider=provider, max_active_users=4))
    with TestClient(app) as client:
        for _ in range(4):
            client.cookies.clear()
            assert client.post("/api/chat", json={"action": "list"}).status_code == 200
        client.cookies.clear()
        assert client.post("/api/chat", json={"action": "list"}).status_code == expected


def test_guest_session_survives_reload_and_inactive_slot_can_be_reused(tmp_path):
    config = settings(tmp_path, provider="deepseek", max_active_users=4)
    app = create_app(config)
    with TestClient(app) as client:
        assert client.post("/api/chat", json={"action": "list"}).status_code == 200
        cookie = client.cookies.get("croptato_guest")
        assert cookie
        assert client.post("/api/chat", json={"action": "list"}).status_code == 200
        assert client.cookies.get("croptato_guest") == cookie
        for _ in range(3):
            client.cookies.clear()
            assert client.post("/api/chat", json={"action": "list"}).status_code == 200
        import sqlite3

        with sqlite3.connect(config.database_path) as db:
            db.execute("UPDATE guest_sessions SET last_seen=0")
        client.cookies.clear()
        assert client.post("/api/chat", json={"action": "list"}).status_code == 200


def test_soily_receives_johns_demo_profile_and_saved_dashboard(tmp_path):
    received = []

    def upstream(request):
        body = json.loads(request.content)
        received.append(body)
        return httpx.Response(
            200, json=ollama_reply("John’s field is a demonstration example.")
        )

    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
    ) as client:
        result = events(
            client.post(
                "/api/chat",
                json={
                    "conversation_id": "demo",
                    "request_id": "demo-question",
                    "message": "Tell me about the test account.",
                    "mode": "fast",
                },
            )
        )
        assert result[-1]["type"] == "answer"
        context = "\n".join(
            message["content"]
            for message in received[0]["messages"]
            if message["role"] == "system"
        )
        assert "John" in context
        assert "Kherson" in context
        assert "configured assumptions" in context
        assert "current" in context
        assert "calculate_gross_margin" in context
        assert "Do not claim to save" in context
