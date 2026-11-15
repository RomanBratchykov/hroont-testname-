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
        get_collection=lambda _: _ready_collection(),
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


def _ready_collection(size=2):
    return SimpleNamespace(
        points_count=3,
        config=SimpleNamespace(
            params=SimpleNamespace(vectors=SimpleNamespace(size=size))
        ),
    )


def test_embedding_readiness_and_dimension_mismatch(monkeypatch):
    from RAG.app import qdrant_service

    retriever = QdrantRetriever()
    retriever._client = SimpleNamespace(
        collection_exists=lambda _: True,
        get_collection=lambda _: _ready_collection(384),
    )
    assert retriever.check_status()["state"] == "warming"

    def fail(*a, **kw):
        raise OSError("model absent")

    monkeypatch.setattr(qdrant_service, "SentenceTransformer", fail)
    retriever.warm_embeddings()
    assert retriever.check_status()["state"] == "unavailable"
    assert retriever.check_status()["embedding_state"] == "unavailable"
    good = QdrantRetriever()
    good._client = retriever._client
    good._model = SimpleNamespace(encode=lambda *a, **kw: [0.1, 0.2])
    good.warm_embeddings()
    assert good.check_status()["state"] == "unavailable"
    assert good.check_status()["reason"] == "embedding_dimension_mismatch"


def test_lifecycle_warms_embeddings_once(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "warm_embeddings", lambda: calls.append("warm"))
    monkeypatch.setattr(
        main, "check_qdrant_status", lambda: {"connected": True, "state": "ready"}
    )
    monkeypatch.setattr(
        main, "check_postgres_status", lambda: {"connected": True, "state": "ready"}
    )
    with TestClient(main.app) as client:
        assert client.get("/health").json()["status"] == "available"
        assert client.get("/health").json()["status"] == "available"
    assert calls == ["warm"]


def test_direct_retrieval_warms_without_lifespan(monkeypatch):
    from RAG.app import qdrant_service

    retriever = QdrantRetriever()
    loads = []

    def model(*a, **kw):
        loads.append(kw)
        return SimpleNamespace(encode=lambda *a, **kw: [0.1, 0.2])

    monkeypatch.setattr(qdrant_service, "SentenceTransformer", model)
    retriever._client = SimpleNamespace(
        collection_exists=lambda _: True,
        get_collection=lambda _: _ready_collection(),
        query_points=lambda **kw: SimpleNamespace(points=[]),
    )
    monkeypatch.setattr(main, "check_qdrant_status", retriever.check_status)
    monkeypatch.setattr(main, "retrieve_chunks", retriever.retrieve_chunks)
    monkeypatch.setattr(
        main, "check_postgres_status", lambda: {"state": "empty", "connected": True}
    )
    client = TestClient(main.app)
    assert client.get("/health").json()["sources"]["vector"]["state"] == "warming"
    result = client.post(
        "/retrieve", json={"query": "crop", "include_sql": False}
    ).json()
    assert result["status"] == "available"
    assert client.get("/health").json()["sources"]["vector"]["state"] == "ready"
    assert loads == [{"device": "cpu"}]


def test_text_year_metadata_does_not_match_unknown_or_invalid_years():
    helper = PostgresHelper()
    helper._engine = create_engine("sqlite://")
    with helper._engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE crop_years (_rag_region TEXT, _rag_start_year TEXT, _rag_end_year TEXT)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO crop_years VALUES ('kherson','',''),('kherson','unknown','unknown'),('kherson','2020','2020'),('kherson','2020.0','2020.0')"
            )
        )
    results = helper.query_relevant_sql_data("crop", region="Kherson", end_year=2025)
    rows = [row for table in results for row in table["sample_rows"]]
    assert [row["_rag_start_year"] for row in rows] == ["2020", "2020.0"]
