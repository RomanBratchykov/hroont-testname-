"""Qdrant vector retriever service for the `agronomy_knowledge` collection."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

RAG_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = RAG_ROOT.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(RAG_ROOT / ".env")

DEFAULT_COLLECTION = "agronomy_knowledge"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def get_qdrant_url() -> str:
    return (
        os.getenv("QDRANT_URL", "http://localhost:6333").strip()
        or "http://localhost:6333"
    )


def get_collection_name() -> str:
    return (
        os.getenv("QDRANT_COLLECTION_NAME")
        or os.getenv("QDRANT_COLLECTION")
        or DEFAULT_COLLECTION
    ).strip()


def get_embedding_model_name() -> str:
    return (
        os.getenv("EMBEDDING_MODEL_NAME", DEFAULT_EMBEDDING_MODEL).strip()
        or DEFAULT_EMBEDDING_MODEL
    )


class QdrantRetriever:
    """Lazy-initialized semantic retriever over the Qdrant `agronomy_knowledge` collection."""

    def __init__(
        self,
        qdrant_url: str | None = None,
        collection_name: str | None = None,
        embedding_model_name: str | None = None,
    ) -> None:
        self._qdrant_url = qdrant_url
        self._collection_name = collection_name
        self._embedding_model_name = embedding_model_name
        self._client: QdrantClient | None = None
        self._model: SentenceTransformer | None = None
        self._lock = threading.Lock()

    @property
    def qdrant_url(self) -> str:
        return self._qdrant_url or get_qdrant_url()

    @property
    def collection_name(self) -> str:
        return self._collection_name or get_collection_name()

    @property
    def embedding_model_name(self) -> str:
        return self._embedding_model_name or get_embedding_model_name()

    def get_client(self) -> QdrantClient:
        with self._lock:
            if self._client is None:
                self._client = QdrantClient(url=self.qdrant_url, timeout=10.0)
            return self._client

    def get_model(self) -> SentenceTransformer:
        with self._lock:
            if self._model is None:
                logger.info(
                    "Loading embedding model '%s'...", self.embedding_model_name
                )
                self._model = SentenceTransformer(
                    self.embedding_model_name, device="cpu"
                )
            return self._model

    def check_status(self) -> dict[str, Any]:
        collection = self.collection_name
        try:
            client = self.get_client()
            exists = bool(client.collection_exists(collection))
            points_count = 0
            if exists:
                info = client.get_collection(collection)
                points_count = int(getattr(info, "points_count", 0) or 0)
                if hasattr(client, "count"):
                    points_count = int(
                        client.count(
                            collection_name=collection,
                            count_filter=models.Filter(
                                must_not=[
                                    models.FieldCondition(
                                        key="ingestion_marker",
                                        match=models.MatchValue(value=True),
                                    )
                                ]
                            ),
                            exact=True,
                        ).count
                    )
            return {
                "connected": True,
                "state": "missing"
                if not exists
                else ("ready" if points_count else "empty"),
                "url": self.qdrant_url,
                "collection": collection,
                "exists": exists,
                "points_count": points_count,
            }
        except Exception as exc:  # noqa: BLE001 — degrade gracefully when Qdrant is offline.
            logger.warning("Qdrant health check failed (%s): %s", self.qdrant_url, exc)
            return {
                "connected": False,
                "state": "unavailable",
                "url": self.qdrant_url,
                "collection": collection,
                "exists": False,
                "points_count": 0,
                "error": str(exc),
            }

    def retrieve_chunks(
        self,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
        region: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[dict[str, Any]]:
        if region:
            region = region.strip().lower().removesuffix(" oblast").strip()
        if not query or not query.strip() or top_k <= 0:
            return []

        collection = self.collection_name
        try:
            client = self.get_client()
            if not client.collection_exists(collection):
                logger.warning("Qdrant collection '%s' does not exist yet.", collection)
                return []

            model = self.get_model()
            vector = model.encode(query.strip(), show_progress_bar=False)
            query_vector = (
                vector.tolist() if hasattr(vector, "tolist") else list(vector)
            )

            # Over-fetch when post-filtering by source_file substring.
            fetch_limit = min(max(top_k * 4, top_k), 50) if source_filter else top_k

            conditions = []
            if region:
                conditions.append(
                    models.FieldCondition(
                        key="region",
                        match=models.MatchValue(value=region.strip().lower()),
                    )
                )
            if start_year is not None:
                conditions.append(
                    models.FieldCondition(
                        key="end_year", range=models.Range(gte=start_year)
                    )
                )
            if end_year is not None:
                conditions.append(
                    models.FieldCondition(
                        key="start_year", range=models.Range(lte=end_year)
                    )
                )
            filters = (
                {"query_filter": models.Filter(must=conditions)} if conditions else {}
            )
            fetch_limit = min(fetch_limit, 50)
            if hasattr(client, "query_points"):
                response = client.query_points(
                    collection_name=collection,
                    query=query_vector,
                    limit=fetch_limit,
                    with_payload=True,
                    **filters,
                )
                hits = getattr(response, "points", response)
            else:
                hits = client.search(
                    collection_name=collection,
                    query_vector=query_vector,
                    limit=fetch_limit,
                    with_payload=True,
                    **filters,
                )

            results: list[dict[str, Any]] = []
            filter_lower = source_filter.lower().strip() if source_filter else ""
            for hit in hits:
                payload = getattr(hit, "payload", None) or {}
                if payload.get("ingestion_marker"):
                    continue
                text = str(payload.get("text", "")).strip()
                source_file = str(payload.get("source_file", "unknown"))
                if filter_lower and filter_lower not in source_file.lower():
                    continue
                if (
                    region
                    and str(payload.get("region", "")).strip().lower()
                    != region.strip().lower()
                ):
                    continue
                if start_year is not None and (
                    not isinstance(payload.get("end_year"), (int, float))
                    or payload["end_year"] < start_year
                ):
                    continue
                if end_year is not None and (
                    not isinstance(payload.get("start_year"), (int, float))
                    or payload["start_year"] > end_year
                ):
                    continue
                if not text:
                    continue
                results.append(
                    {
                        "text": text,
                        "source_file": source_file,
                        "region": payload.get("region"),
                        "start_year": payload.get("start_year"),
                        "end_year": payload.get("end_year"),
                        "score": float(getattr(hit, "score", 0.0) or 0.0),
                    }
                )
                if len(results) >= top_k:
                    break
            return results
        except Exception as exc:
            logger.warning("Qdrant retrieval failed (%s)", type(exc).__name__)
            raise RuntimeError("Vector retrieval unavailable") from exc


_default_retriever = QdrantRetriever()


def check_qdrant_status() -> dict[str, Any]:
    """Check Qdrant connectivity and `agronomy_knowledge` collection status."""
    return _default_retriever.check_status()


def retrieve_chunks(
    query: str,
    top_k: int = 5,
    source_filter: str | None = None,
    region: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> list[dict[str, Any]]:
    """Retrieve top-k semantic chunks from Qdrant for the given query."""
    return _default_retriever.retrieve_chunks(
        query,
        top_k=top_k,
        source_filter=source_filter,
        region=region,
        start_year=start_year,
        end_year=end_year,
    )
