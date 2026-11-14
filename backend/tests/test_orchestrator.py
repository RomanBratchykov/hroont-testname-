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
    with TestClient(
        create_app(settings(tmp_path), transport=httpx.MockTransport(upstream))
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
                "read_history",
                "get_capabilities",
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
            result[-1]["evidence"][-1]["result"]["scientific_analysis"] == "unavailable"
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
        assert result[-1]["code"] == "translation_unavailable"
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


def test_history_tool_never_sends_original_cyrillic_to_model(tmp_path):
    received = []

    def upstream(request):
        body = json.loads(request.content)
        if request.url.path == "/translate":
            return httpx.Response(
                200, json={"translatedText": "My field is 30 hectares"}
            )
        received.append(body)
        if len(received) == 1:
            return httpx.Response(
                200,
                json=ollama_reply(
                    "", [{"function": {"name": "read_history", "arguments": {}}}]
                ),
            )
        tool_result = json.loads(body["messages"][-1]["content"])
        assert not any(
            "\u0400" <= char <= "\u052f"
            for char in json.dumps(tool_result, ensure_ascii=False)
        )
        return httpx.Response(200, json=ollama_reply("Where is the field?"))

    config = settings(tmp_path, translation_url="http://127.0.0.1:5000/translate")
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
                    "message": "Моє поле 30 гектарів",
                },
            )
        )
        assert result[-1]["type"] == "answer"
        read = client.post(
            "/api/chat", json={"action": "read", "conversation_id": "a"}
        ).json()
        assert read["messages"][0]["content"] == "Моє поле 30 гектарів"
        client.post("/api/chat", json={"action": "clear"})
    from backend.store import Store

    with Store(config.database_path).connect() as db:
        assert db.execute("SELECT COUNT(*) FROM translations").fetchone()[0] == 0


def test_spreadsheet_and_text_are_parsed_locally_with_units_and_formulas(tmp_path):
    import base64
    import io

    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active.append(["Area (ha)", 30, "=B1*2"])
    binary = io.BytesIO()
    workbook.save(binary)

    def upstream(request):
        body = json.loads(request.content)
        text = body["messages"][-1]["content"]
        assert "Area (ha)\t30\t=B1*2" in text
        assert "Untrusted attachment: field.xlsx" in text
        assert "UEsDB" not in text
        return httpx.Response(200, json=ollama_reply())

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
                    "message": "Read my field",
                    "files": [
                        {
                            "name": "field.xlsx",
                            "data": base64.b64encode(binary.getvalue()).decode(),
                        }
                    ],
                },
            )
        )
        assert result[-1]["type"] == "answer"


def test_concurrency_cap_queue_fairness_and_cancelled_paid_reservation(tmp_path):
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

            tasks = [asyncio.create_task(turn(index)) for index in range(6)]
            for _ in range(100):
                await asyncio.sleep(0.005)
                if len(entered) == 4:
                    break
            assert entered == ["0", "1", "2", "3"]
            assert engine.active == 4
            tasks[0].cancel()
            with pytest.raises(asyncio.CancelledError):
                await tasks[0]
            for _ in range(100):
                await asyncio.sleep(0.005)
                if len(entered) == 5:
                    break
            assert entered[-1] == "4"
            assert store.budget("testing")["reserved_usd"] > 0
            release.set()
            await asyncio.gather(*tasks[1:])
            assert entered[-1] == "5"
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
        assert result[-1]["code"] == "translation_unavailable"


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
