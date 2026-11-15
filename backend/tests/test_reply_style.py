import json

import httpx
from fastapi.testclient import TestClient

from backend.api import create_app
from backend.config import Settings


def test_assistant_emphasis_is_removed_before_delivery_and_persistence(tmp_path):
    def upstream(request):
        body = json.loads(request.content)
        assert (
            "Use plain text and short, natural paragraphs"
            in body["messages"][0]["content"]
        )
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": "**Chickpea**: **12,800 UAH/ha**.",
                },
                "done": True,
            },
        )

    with TestClient(
        create_app(
            Settings(database_path=tmp_path / "style.sqlite"),
            transport=httpx.MockTransport(upstream),
        )
    ) as client:
        response = client.post(
            "/api/chat",
            json={
                "conversation_id": "plain",
                "request_id": "one",
                "message": "Keep my **input** unchanged.",
            },
        )
        answer = [json.loads(line) for line in response.text.splitlines()][-1]
        assert answer["content"] == "Chickpea: 12,800 UAH/ha."
        saved = client.post(
            "/api/chat", json={"action": "read", "conversation_id": "plain"}
        ).json()
        assert saved["messages"][-1]["content"] == answer["content"]
        assert saved["messages"][0]["content"] == "Keep my **input** unchanged."
