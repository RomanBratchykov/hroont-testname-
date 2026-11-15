"""Use real orchestration, persistence and tools with the DeepSeek wire format."""

import json
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import ROOT, Settings


@pytest.mark.parametrize("mode", ["fast", "thinking"])
def test_deepseek_existing_showcase_history_tools_and_budget(tmp_path, mode):
    requests = []
    showcase = json.loads((ROOT / "input_data/john_showcase.json").read_text())

    def upstream(request):
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["authorization"] == "Bearer offline-test"
        body = json.loads(request.content)
        requests.append(body)
        assert body["thinking"]["type"] == (
            "enabled" if mode == "thinking" else "disabled"
        )
        assert "John" in body["messages"][0]["content"]
        assert "configured assumptions" in body["messages"][0]["content"]
        assert showcase["farmer"]["region"] in body["messages"][0]["content"]
        if len(requests) == 1:
            message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "history-1",
                        "type": "function",
                        "function": {
                            "name": "read_history",
                            "arguments": '{"limit": 10}',
                        },
                    },
                    {
                        "id": "capabilities-1",
                        "type": "function",
                        "function": {"name": "get_capabilities", "arguments": "{}"},
                    },
                ],
            }
            if mode == "thinking":
                message["reasoning_content"] = "Private provider reasoning"
        else:
            tool_messages = [m for m in body["messages"] if m["role"] == "tool"]
            assert [m["tool_call_id"] for m in tool_messages] == [
                "history-1",
                "capabilities-1",
            ]
            history, capabilities = [json.loads(m["content"]) for m in tool_messages]
            assert (
                history["messages"][0]["content"]
                == "Explain John’s saved example dashboard."
            )
            assert capabilities["scientific_analysis"] == "partial"
            assert "calculate_gross_margin" in capabilities["scientific_tools"]
            message = {
                "role": "assistant",
                "content": "John’s configured inputs can be used by the connected gross-margin calculator; other estimates need sourced inputs.",
            }
        return httpx.Response(
            200,
            json={
                "choices": [{"message": message, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 30},
            },
        )

    config = Settings(
        provider="deepseek",
        api_key="offline-test",
        input_rate=Decimal(".30"),
        output_rate=Decimal("1.20"),
        database_path=tmp_path / "isolated.sqlite",
    )
    with TestClient(
        create_app(config, transport=httpx.MockTransport(upstream))
    ) as client:
        payload = {
            "conversation_id": "deepseek",
            "request_id": "turn1",
            "mode": mode,
            "message": "Explain John’s saved example dashboard.",
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        events = [json.loads(line) for line in response.text.splitlines()]
        answer = events[-1]
        assert answer["type"] == "answer"
        assert answer["status"] == "completed"
        assert answer["provider"] == "deepseek"
        assert [e["tool"] for e in answer["evidence"]] == [
            "read_history",
            "get_capabilities",
        ]
        assert "Private provider reasoning" not in response.text
        repeated = client.post("/api/chat", json=payload)
        assert json.loads(repeated.text.splitlines()[-1]) == answer
        assert (
            len(requests) == 2
        )  # Replaying a completed turn never triggers another paid call.
        health = client.get("/api/health").json()
        assert health["budget"]["reserved_usd"] == 0
        assert health["budget"]["spent_usd"] > 0
