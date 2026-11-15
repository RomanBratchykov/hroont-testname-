"""Offline unit & integration tests for the RAG services and backend wiring."""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.api import create_app
from backend.config import Settings
from backend.store import Store
from backend.tools import build_tools
from RAG.app import db as rag_db
from RAG.app import llm_service, qdrant_service
from RAG.app import main as rag_main


class _FakeVector:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def tolist(self) -> list[float]:
        return self._values


class _FakeEmbedder:
    def encode(self, text: str, show_progress_bar: bool = False) -> _FakeVector:
        return _FakeVector([0.1, 0.2, 0.3])


class _FakeQdrantClient:
    def __init__(self, points: list[SimpleNamespace] | None = None, exists: bool = True) -> None:
        self._points = points or []
        self._exists = exists
        self.last_query_kwargs: dict | None = None

    def collection_exists(self, collection_name: str) -> bool:
        return self._exists and collection_name == "agronomy_knowledge"

    def get_collection(self, collection_name: str) -> SimpleNamespace:
        return SimpleNamespace(points_count=len(self._points))

    def query_points(self, **kwargs) -> SimpleNamespace:
        self.last_query_kwargs = kwargs
        limit = kwargs.get("limit", len(self._points))
        return SimpleNamespace(points=self._points[:limit])


def test_qdrant_retriever_returns_filtered_chunks_and_handles_offline():
    points = [
        SimpleNamespace(
            score=0.92,
            payload={"source_file": "Kherson/rotation.jsonl", "text": "Winter wheat after pea improves N."},
        ),
        SimpleNamespace(
            score=0.81,
            payload={"source_file": "Broadbalk/README.md", "text": "Broadbalk continuous wheat trial."},
        ),
    ]
    retriever = qdrant_service.QdrantRetriever(collection_name="agronomy_knowledge")
    retriever._client = _FakeQdrantClient(points=points)
    retriever._model = _FakeEmbedder()

    status = retriever.check_status()
    assert status["connected"] is True
    assert status["exists"] is True
    assert status["points_count"] == 2

    all_chunks = retriever.retrieve_chunks("winter wheat rotation", top_k=5)
    assert len(all_chunks) == 2
    assert all_chunks[0]["source_file"] == "Kherson/rotation.jsonl"
    assert all_chunks[0]["score"] == 0.92

    kherson_only = retriever.retrieve_chunks("wheat", top_k=5, source_filter="kherson")
    assert len(kherson_only) == 1
    assert kherson_only[0]["source_file"] == "Kherson/rotation.jsonl"

    missing_retriever = qdrant_service.QdrantRetriever(collection_name="agronomy_knowledge")
    missing_retriever._client = _FakeQdrantClient(exists=False)
    missing_retriever._model = _FakeEmbedder()
    assert missing_retriever.retrieve_chunks("wheat") == []


def test_postgres_helper_queries_relevant_tables_and_rejects_writes(tmp_path):
    db_file = tmp_path / "rag_sql_test.sqlite"
    engine = create_engine(f"sqlite:///{db_file}")
    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE broadbalk_wheat_yield (year INTEGER, treatment TEXT, grain_t_ha REAL)")
        )
        conn.execute(
            text("INSERT INTO broadbalk_wheat_yield VALUES (2015, 'N144', 7.8), (2016, 'Nil', 1.9)")
        )
        conn.execute(
            text("CREATE TABLE marchfeld_soilparameter (site TEXT, ph REAL, organic_c_pct REAL)")
        )
        conn.execute(
            text("INSERT INTO marchfeld_soilparameter VALUES ('Marchfeld', 7.4, 1.85)")
        )

    helper = rag_db.PostgresHelper(database_url=f"sqlite:///{db_file}")
    status = helper.check_status()
    assert status["connected"] is True
    assert status["table_count"] == 2

    wheat_results = helper.query_relevant_sql_data("What is Broadbalk wheat grain yield?", max_tables=1)
    assert len(wheat_results) == 1
    assert wheat_results[0]["table"] == "broadbalk_wheat_yield"
    assert wheat_results[0]["row_count"] == 2
    assert wheat_results[0]["sample_rows"][0]["grain_t_ha"] == 7.8

    rows = helper.execute_readonly_query("SELECT treatment, grain_t_ha FROM broadbalk_wheat_yield")
    assert len(rows) == 2

    for bad_sql in [
        "DELETE FROM broadbalk_wheat_yield",
        "DROP TABLE broadbalk_wheat_yield",
        "SELECT * FROM broadbalk_wheat_yield; DROP TABLE broadbalk_wheat_yield",
        "INSERT INTO broadbalk_wheat_yield VALUES (2020, 'X', 0)",
    ]:
        with pytest.raises(ValueError):
            helper.execute_readonly_query(bad_sql)


def test_llm_service_combines_rag_context_and_strips_think_tags(monkeypatch):
    captured: dict = {}

    class _FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="<think>internal reasoning</think>Winter wheat after legumes yields better [Kherson/rotation.jsonl] and Broadbalk N144 shows 7.8 t/ha [broadbalk_wheat_yield]."
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))

    monkeypatch.setattr(
        llm_service,
        "retrieve_chunks",
        lambda q, top_k=5, source_filter=None: [
            {"source_file": "Kherson/rotation.jsonl", "score": 0.91, "text": "Legumes precede winter wheat."}
        ],
    )
    monkeypatch.setattr(
        llm_service,
        "query_relevant_sql_data",
        lambda q: [
            {
                "table": "broadbalk_wheat_yield",
                "columns": ["year", "treatment", "grain_t_ha"],
                "row_count": 2,
                "sample_rows": [{"year": 2015, "treatment": "N144", "grain_t_ha": 7.8}],
            }
        ],
    )

    result = llm_service.generate_rag_answer(
        "Recommend a rotation for winter wheat yield",
        history=[{"role": "user", "content": "My farm is in Kherson."}],
        client=fake_client,
    )
    assert result["status"] == "completed"
    assert "internal reasoning" not in result["answer"]
    assert "Winter wheat after legumes" in result["answer"]
    assert len(result["sources"]) == 1
    assert len(result["sql_data"]) == 1
    assert any(e["type"] == "vector" for e in result["evidence"])
    assert any(e["type"] == "sql" for e in result["evidence"])

    user_msg = captured["messages"][-1]["content"]
    assert "[Vector Knowledge Base]" in user_msg
    assert "Kherson/rotation.jsonl" in user_msg
    assert "[PostgreSQL Historical Crop & Soil Data]" in user_msg
    assert "broadbalk_wheat_yield" in user_msg


def test_llm_service_handles_unreachable_deepseek_gracefully(monkeypatch):
    class _BrokenCompletions:
        def create(self, **kwargs):
            raise ConnectionError("Ollama not running")

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=_BrokenCompletions()))
    monkeypatch.setattr(
        llm_service,
        "retrieve_chunks",
        lambda q, top_k=5, source_filter=None: [
            {"source_file": "Kherson/README.md", "score": 0.88, "text": "Kherson rotation guide."}
        ],
    )
    monkeypatch.setattr(llm_service, "query_relevant_sql_data", lambda q: [])

    result = llm_service.generate_rag_answer("Kherson rotation?", client=fake_client)
    assert result["status"] == "partial"
    assert "unavailable" in result["answer"].lower()
    assert len(result["sources"]) == 1


def test_rag_fastapi_endpoints_and_cors(monkeypatch):
    rag_main._CONVERSATIONS.clear()
    monkeypatch.setattr(
        rag_main,
        "check_qdrant_status",
        lambda: {"connected": True, "collection": "agronomy_knowledge", "exists": True, "points_count": 10},
    )
    monkeypatch.setattr(
        rag_main,
        "check_postgres_status",
        lambda: {"connected": True, "table_count": 3, "tables": ["yield_data"]},
    )
    monkeypatch.setattr(
        rag_main,
        "retrieve_chunks",
        lambda q, top_k=5, source_filter=None: [
            {"source_file": "Kherson/rotation.jsonl", "score": 0.9, "text": "Sunflower-wheat rotation."}
        ],
    )
    monkeypatch.setattr(
        rag_main,
        "query_relevant_sql_data",
        lambda q: [{"table": "yield_data", "columns": ["crop"], "row_count": 1, "sample_rows": [{"crop": "wheat"}]}],
    )
    monkeypatch.setattr(
        rag_main,
        "generate_rag_answer",
        lambda prompt, **kwargs: {
            "answer": f"Grounded reply for: {prompt}",
            "status": "completed",
            "model": "deepseek-r1:8b",
            "sources": [{"source_file": "Kherson/rotation.jsonl", "score": 0.9, "text": "Sunflower-wheat rotation."}],
            "sql_data": [{"table": "yield_data", "columns": ["crop"], "row_count": 1, "sample_rows": [{"crop": "wheat"}]}],
            "evidence": [{"type": "vector", "source_file": "Kherson/rotation.jsonl"}],
        },
    )

    with TestClient(rag_main.app) as client:
        health = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert health.status_code == 200
        assert health.headers.get("access-control-allow-origin") == "*"
        assert health.json()["qdrant"]["points_count"] == 10
        assert health.json()["postgres"]["table_count"] == 3

        retrieved = client.post("/retrieve", json={"query": "wheat", "top_k": 3})
        assert retrieved.status_code == 200
        assert len(retrieved.json()["chunks"]) == 1
        assert len(retrieved.json()["sql_data"]) == 1

        rec = client.post("/recommend", json={"query": "Best rotation for Kherson?"})
        assert rec.status_code == 200
        assert "Grounded reply" in rec.json()["answer"]

        stream_resp = client.post(
            "/api/chat",
            json={
                "action": "send",
                "conversation_id": "conv-1",
                "request_id": "req-1",
                "message": "Analyze Kherson soil",
                "mode": "fast",
            },
        )
        assert stream_resp.status_code == 200
        events = [json.loads(line) for line in stream_resp.text.splitlines() if line]
        assert events[-1]["type"] == "answer"
        assert "Grounded reply" in events[-1]["content"]
        assert len(events[-1]["evidence"]) == 1

        listed = client.post("/api/chat", json={"action": "list"})
        assert len(listed.json()["conversations"]) == 1


def test_backend_wiring_with_rag_and_local_deepseek(tmp_path, monkeypatch):
    monkeypatch.setattr(
        qdrant_service,
        "retrieve_chunks",
        lambda q, top_k=5, source_filter=None: [
            {"source_file": "Kherson/rotation.jsonl", "score": 0.95, "text": "Sainfoin improves soil structure."}
        ],
    )
    monkeypatch.setattr(
        rag_db,
        "query_relevant_sql_data",
        lambda q, max_tables=4, rows_per_table=8: [
            {"table": "yield_data", "columns": ["crop", "yield"], "row_count": 5, "sample_rows": [{"crop": "wheat", "yield": 4.2}]}
        ],
    )

    config = Settings(
        database_path=tmp_path / "wired.sqlite",
        provider="deepseek",
        model="deepseek-r1:8b",
        openai_base_url="http://127.0.0.1:11434/v1",
        rag_url="direct",
    )
    store = Store(config.database_path)
    tools = build_tools(store, config)("chat-1")
    assert {"read_history", "get_capabilities", "search_agronomy_knowledge", "query_crop_soil_db"} == set(tools)
    assert tools["get_capabilities"].invoke({})["scientific_analysis"] == "available"

    captured_requests: list[dict] = []

    def fake_local_deepseek(request: httpx.Request):
        assert str(request.url) == "http://127.0.0.1:11434/v1/chat/completions"
        body = json.loads(request.content)
        captured_requests.append(body)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "<think>checking soil tables</think>Sainfoin and winter wheat fit well based on [Kherson/rotation.jsonl] and [yield_data].",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 50, "completion_tokens": 25},
            },
        )

    app = create_app(config, transport=httpx.MockTransport(fake_local_deepseek))
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        assert health["configured"] is True
        assert health["rag_configured"] is True
        assert "search_agronomy_knowledge" in health["scientific_tools"]

        resp = client.post(
            "/api/chat",
            json={
                "action": "send",
                "conversation_id": "chat-1",
                "request_id": "turn-1",
                "message": "What crop rotation fits Kherson wheat?",
                "mode": "fast",
            },
        )
        events = [json.loads(line) for line in resp.text.splitlines() if line]
        assert any(e.get("stage") == "retrieving" for e in events)
        answer = events[-1]
        assert answer["type"] == "answer"
        assert "checking soil tables" not in answer["content"]
        assert "Sainfoin and winter wheat" in answer["content"]
        assert len(answer["evidence"]) == 2
        assert "Sainfoin improves soil structure." in captured_requests[0]["messages"][0]["content"]
