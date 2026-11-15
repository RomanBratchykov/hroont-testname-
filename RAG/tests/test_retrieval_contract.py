"""Offline regressions for honest, geographically constrained retrieval."""

from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from RAG.app import main
from RAG.app.db import PostgresHelper
from RAG.app.qdrant_service import QdrantRetriever


def test_sql_filters_rows_and_excludes_unlocated_tables():
    helper = PostgresHelper()
    helper._engine = create_engine("sqlite://")
    with helper._engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE crop_yield (region TEXT, year INTEGER, yield REAL)")
        )
        conn.execute(
            text(
                "INSERT INTO crop_yield VALUES ('Kherson',2020,2),('Other',2020,3),('Kherson',2010,4)"
            )
        )
        conn.execute(text("CREATE TABLE crop_unknown (year INTEGER)"))
        conn.execute(text("INSERT INTO crop_unknown VALUES (2020)"))
    result = helper.query_relevant_sql_data(
        "crop yield", region="Kherson Oblast", start_year=2019, end_year=2021
    )
    assert len(result) == 1
    assert result[0]["sample_rows"] == [
        {"region": "Kherson", "year": 2020, "yield": 2.0}
    ]
    assert result[0]["row_count"] == 1


def test_vector_metadata_filter_is_sent_and_enforced():
    retriever = QdrantRetriever()
    calls = []
    retriever._client = SimpleNamespace(
        collection_exists=lambda _: True,
        query_points=lambda **kw: (
            calls.append(kw)
            or SimpleNamespace(
                points=[
                    SimpleNamespace(
                        score=0.8,
                        payload={
                            "text": "correct",
                            "region": "Kherson",
                            "start_year": 2019,
                            "end_year": 2021,
                        },
                    ),
                    SimpleNamespace(
                        score=0.9,
                        payload={
                            "text": "wrong",
                            "region": "Other",
                            "start_year": 2019,
                            "end_year": 2021,
                        },
                    ),
                    SimpleNamespace(
                        score=0.7, payload={"text": "unknown", "region": "Kherson"}
                    ),
                ]
            )
        ),
    )
    retriever._model = SimpleNamespace(encode=lambda *a, **kw: [0.1, 0.2])
    results = retriever.retrieve_chunks(
        "crop", region="Kherson", start_year=2020, end_year=2020
    )
    assert [row["text"] for row in results] == ["correct"]
    assert calls[0]["query_filter"] is not None


def test_offline_is_unavailable_but_no_match_is_available(monkeypatch):
    monkeypatch.setattr(
        main,
        "check_qdrant_status",
        lambda: {"connected": False, "state": "unavailable"},
    )
    monkeypatch.setattr(
        main,
        "check_postgres_status",
        lambda: {"connected": False, "state": "unavailable"},
    )
    client = TestClient(main.app)
    response = client.post("/retrieve", json={"query": "crop"}).json()
    assert response["status"] == "unavailable"
    monkeypatch.setattr(
        main,
        "check_qdrant_status",
        lambda: {
            "connected": True,
            "exists": True,
            "points_count": 5,
            "state": "ready",
        },
    )
    monkeypatch.setattr(main, "retrieve_chunks", lambda *a, **kw: [])
    response = client.post(
        "/retrieve", json={"query": "crop", "include_sql": False}
    ).json()
    assert response["status"] == "available"
    assert response["sources"]["vector"]["state"] == "no_match"
    assert client.post("/api/chat", json={"message": "crop"}).status_code == 410


def test_empty_sql_tables_are_not_ready():
    helper = PostgresHelper()
    helper._engine = create_engine("sqlite://")
    with helper._engine.begin() as conn:
        conn.execute(text("CREATE TABLE crop_yield (year INTEGER)"))
    assert helper.check_status()["state"] == "empty"


def test_sql_ingestion_metadata_and_actual_row_year():
    helper = PostgresHelper()
    helper._engine = create_engine("sqlite://")
    with helper._engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE crop_yield (year INTEGER, _rag_region TEXT, _rag_start_year INTEGER, _rag_end_year INTEGER)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO crop_yield VALUES (2020,'kherson',1968,2021),(2010,'kherson',1968,2021)"
            )
        )
    result = helper.query_relevant_sql_data(
        "crop", region="Kherson Oblast", start_year=2019, end_year=2021
    )
    assert [row["year"] for row in result[0]["sample_rows"]] == [2020]


def test_failed_query_is_not_reported_as_no_match(monkeypatch):
    monkeypatch.setattr(
        main, "check_qdrant_status", lambda: {"state": "ready", "connected": True}
    )
    monkeypatch.setattr(
        main, "check_postgres_status", lambda: {"state": "ready", "connected": True}
    )

    def fail(*args, **kwargs):
        raise RuntimeError("private database connection details")

    monkeypatch.setattr(main, "retrieve_chunks", fail)
    monkeypatch.setattr(main, "query_relevant_sql_data", lambda *a, **kw: [])
    response = TestClient(main.app).post("/retrieve", json={"query": "crop"}).json()
    assert response["status"] == "partial"
    assert response["sources"]["vector"]["state"] == "unavailable"
    assert response["sources"]["sql"]["state"] == "no_match"
    assert "private" not in str(response)
