"""Server-owned LangChain tools. Future scientific tools must be registered here."""

import json
import logging

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from backend.config import Settings
from backend.store import Store

log = logging.getLogger(__name__)


class HistoryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    limit: int = Field(default=10, ge=1, le=30)
    before: int | None = Field(default=None, ge=1)


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeSearchArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class SqlQueryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    max_tables: int = Field(default=3, ge=1, le=6)


def _bound_rag_payload(payload: dict, max_bytes: int = 13500) -> dict:
    """Trim retrieved chunks and SQL rows so tool results always stay within orchestrator bounds."""
    chunks = payload.get("chunks")
    if isinstance(chunks, list):
        trimmed_chunks = []
        for item in chunks:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", ""))
            if len(text) > 1000:
                text = text[:1000] + "..."
            trimmed_chunks.append(
                {
                    "source_file": str(item.get("source_file", "unknown")),
                    "score": round(float(item.get("score", 0.0)), 4),
                    "text": text,
                }
            )
        payload["chunks"] = trimmed_chunks

    sql_data = payload.get("sql_data")
    if isinstance(sql_data, list):
        trimmed_sql = []
        for entry in sql_data:
            if not isinstance(entry, dict):
                continue
            trimmed_sql.append(
                {
                    "table": str(entry.get("table", "unknown")),
                    "row_count": int(entry.get("row_count", 0)),
                    "columns": list(entry.get("columns", []))[:25],
                    "sample_rows": list(entry.get("sample_rows", []))[:5],
                }
            )
        payload["sql_data"] = trimmed_sql

    while len(json.dumps(payload, ensure_ascii=False).encode()) > max_bytes:
        if isinstance(payload.get("chunks"), list) and len(payload["chunks"]) > 1:
            payload["chunks"].pop()
        elif isinstance(payload.get("sql_data"), list) and len(payload["sql_data"]) > 1:
            payload["sql_data"].pop()
        elif isinstance(payload.get("sql_data"), list) and payload["sql_data"]:
            rows = payload["sql_data"][0].get("sample_rows", [])
            if len(rows) > 1:
                rows.pop()
            else:
                payload["sql_data"][0]["sample_rows"] = []
                break
        else:
            break
    return payload


def _call_rag_service(
    rag_url: str,
    query: str,
    top_k: int = 5,
    include_sql: bool = True,
) -> dict:
    """Query the RAG service via HTTP or direct in-process Python modules."""
    if rag_url != "direct":
        try:
            with httpx.Client(trust_env=False, timeout=8.0) as client:
                response = client.post(
                    f"{rag_url.rstrip('/')}/retrieve",
                    json={"query": query, "top_k": top_k, "include_sql": include_sql},
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    return _bound_rag_payload(data)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            log.warning("HTTP RAG call to %s failed, trying direct import: %s", rag_url, exc)

    try:
        from RAG.app.db import query_relevant_sql_data
        from RAG.app.qdrant_service import retrieve_chunks

        chunks = retrieve_chunks(query, top_k=top_k) if top_k > 0 else []
        sql_data = query_relevant_sql_data(query) if include_sql else []
        return _bound_rag_payload(
            {
                "status": "available",
                "query": query,
                "chunks": chunks,
                "sql_data": sql_data,
            }
        )
    except Exception as exc:  # noqa: BLE001 — keep chat available when RAG backends are offline.
        log.warning("Direct RAG retrieval failed: %s", exc)
        return {
            "status": "unavailable",
            "reason": "RAG retrieval service is unavailable.",
        }


def build_tools(store: Store, config: Settings | None = None):
    """Bind tools per chat; model arguments cannot select another chat's history."""
    rag_enabled = bool(config and config.rag_url)

    def for_chat(chat: str):
        def read_history(limit: int = 10, before: int | None = None) -> dict:
            records = store.history(chat, limit, before, for_model=True)
            messages = [
                {
                    "seq": row["seq"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                }
                for row in records
            ]
            # Bound output by text size, dropping oldest rows with explicit pagination.
            while len(json.dumps(messages).encode()) > 10000 and len(messages) > 1:
                messages.pop(0)
            if messages and len(messages[0]["content"]) > 8000:
                messages[0]["content"] = messages[0]["content"][:8000] + "\n[truncated]"
            return {
                "status": "available",
                "messages": messages,
                "next_before": messages[0]["seq"] if messages else None,
            }

        def get_capabilities() -> dict:
            if rag_enabled:
                return {
                    "status": "available",
                    "scientific_analysis": "available",
                    "datasets": ["agronomy_knowledge", "kherson_crop_db"],
                    "scientific_tools": [
                        "search_agronomy_knowledge",
                        "query_crop_soil_db",
                    ],
                    "reason": "Connected to Qdrant agronomy vector store and PostgreSQL crop/soil database.",
                    "available": [
                        "farmer interview",
                        "conversation history",
                        "agronomy knowledge vector retrieval",
                        "crop and soil SQL dataset retrieval",
                    ],
                    "recommendations": "rag_assisted",
                }
            return {
                "status": "available",
                "scientific_analysis": "unavailable",
                "datasets": [],
                "scientific_tools": [],
                "reason": "Scientific scripts and datasets will be added later. No NASA data has been fetched.",
                "available": [
                    "farmer interview",
                    "conversation history",
                    "saved demonstration dashboard",
                ],
                "demo_dashboard": "John’s synthetic Kherson profile and example rotations are in the supplied system context; no scientific results have been computed.",
                "recommendations": "deferred",
            }

        tool_list = [
            StructuredTool.from_function(
                read_history,
                name="read_history",
                args_schema=HistoryArgs,
                description="Read older messages in this chat. Use next_before to page backwards.",
            ),
            StructuredTool.from_function(
                get_capabilities,
                name="get_capabilities",
                args_schema=NoArgs,
                description="Check available datasets and scientific calculation capabilities.",
            ),
        ]

        if rag_enabled and config is not None:

            def search_agronomy_knowledge(query: str, top_k: int = 5) -> dict:
                res = _call_rag_service(
                    config.rag_url, query=query, top_k=top_k, include_sql=False
                )
                return {
                    "status": res.get("status", "available"),
                    "chunks": res.get("chunks", []),
                }

            def query_crop_soil_db(query: str, max_tables: int = 3) -> dict:
                res = _call_rag_service(
                    config.rag_url, query=query, top_k=0, include_sql=True
                )
                sql_data = res.get("sql_data", [])
                if isinstance(sql_data, list):
                    sql_data = sql_data[:max_tables]
                return _bound_rag_payload(
                    {
                        "status": res.get("status", "available"),
                        "sql_data": sql_data,
                    }
                )

            tool_list.extend(
                [
                    StructuredTool.from_function(
                        search_agronomy_knowledge,
                        name="search_agronomy_knowledge",
                        args_schema=KnowledgeSearchArgs,
                        description=(
                            "Search Qdrant agronomy_knowledge vector database for crop rotation "
                            "guidelines, farmer interviews, soil/climate rules, and scientific literature."
                        ),
                    ),
                    StructuredTool.from_function(
                        query_crop_soil_db,
                        name="query_crop_soil_db",
                        args_schema=SqlQueryArgs,
                        description=(
                            "Query ingested PostgreSQL historical crop yield, nutrient, management, "
                            "and soil parameter tables (Broadbalk, Marchfeld, Dryad, CIMMYT, Kherson)."
                        ),
                    ),
                ]
            )

        return {tool.name: tool for tool in tool_list}

    return for_chat
