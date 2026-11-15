"""Server-owned LangChain tools. Future scientific tools must be registered here."""

import asyncio
import json
import logging
import sqlite3
from typing import Literal

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from backend.config import Settings
from backend.field_data import check_sources, climate
from backend.store import Store
from backend.profile import ProfileUpdate

log = logging.getLogger(__name__)


class HistoryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    limit: int = Field(default=10, ge=1, le=30)
    before: int | None = Field(default=None, ge=1)


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceFilters(BaseModel):
    region: str | None = Field(default=None, min_length=1, max_length=100)
    start_year: int | None = Field(default=None, ge=1800, le=2100)
    end_year: int | None = Field(default=None, ge=1800, le=2100)


class KnowledgeSearchArgs(SourceFilters):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class SqlQueryArgs(SourceFilters):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=2000)
    max_tables: int = Field(default=3, ge=1, le=6)


def _bound_rag_payload(payload: dict, max_bytes: int = 13500) -> dict:
    """Trim retrieved chunks and SQL rows so tool results always stay within orchestrator bounds."""
    minimum = {"status": "unavailable", "truncated": True}
    if max_bytes < len(json.dumps(minimum).encode()):
        raise ValueError("Payload budget cannot represent an explicit failure.")

    def mark_truncated():
        payload["truncated"] = True
        if payload.get("status") == "available":
            payload["status"] = "partial"

    chunks = payload.get("chunks")
    if isinstance(chunks, list):
        trimmed_chunks = []
        for item in chunks:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", ""))
            if len(text) > 1000:
                text = text[:1000] + "..."
                mark_truncated()
            trimmed_chunks.append(
                {
                    "source_file": str(item.get("source_file", "unknown")),
                    "score": round(float(item.get("score", 0.0)), 4),
                    "text": text,
                    **{
                        key: item[key]
                        for key in ("region", "start_year", "end_year")
                        if key in item
                    },
                }
            )
        payload["chunks"] = trimmed_chunks

    sql_data = payload.get("sql_data")
    if isinstance(sql_data, list):
        trimmed_sql = []
        for entry in sql_data:
            if not isinstance(entry, dict):
                continue
            rows = list(entry.get("sample_rows", []))
            columns = list(entry.get("columns", []))
            if len(rows) > 5 or len(columns) > 25:
                mark_truncated()
            population = entry.get("population_row_count")
            if population is None and not entry.get("row_count_is_sample", False):
                population = entry.get("row_count")
            sample = rows[:5]
            trimmed_sql.append(
                {
                    **entry,
                    "table": str(entry.get("table", "unknown")),
                    "row_count": len(sample),
                    "row_count_is_sample": True,
                    "sample_row_count": len(sample),
                    "population_row_count": population,
                    "columns": columns[:25],
                    "sample_rows": sample,
                }
            )
        payload["sql_data"] = trimmed_sql

    while len(json.dumps(payload, ensure_ascii=False).encode()) > max_bytes:
        mark_truncated()
        if isinstance(payload.get("chunks"), list) and len(payload["chunks"]) > 1:
            payload["chunks"].pop()
        elif isinstance(payload.get("sql_data"), list) and len(payload["sql_data"]) > 1:
            payload["sql_data"].pop()
        elif (
            isinstance(payload.get("sql_data"), list)
            and payload["sql_data"]
            and payload["sql_data"][0]["sample_rows"]
        ):
            entry = payload["sql_data"][0]
            entry["sample_rows"].pop()
            entry["row_count"] = entry["sample_row_count"] = len(entry["sample_rows"])
        else:
            failure = _unavailable(
                "Evidence metadata exceeds the retrieval payload budget."
            )
            failure["truncated"] = True
            return (
                failure
                if len(json.dumps(failure, ensure_ascii=False).encode()) <= max_bytes
                else minimum
            )
    return payload


def _unavailable(reason: str) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "chunks": [],
        "sql_data": [],
        "sources": {
            "vector": {"status": "unavailable"},
            "sql": {"status": "unavailable"},
        },
    }


def rag_health(rag_url: str) -> dict:
    if not rag_url:
        return _unavailable("RAG is not configured.")
    try:
        if rag_url == "direct":
            from RAG.app.main import health_check

            data = asyncio.run(health_check())
        else:
            with httpx.Client(trust_env=False, timeout=2.0) as client:
                response = client.get(f"{rag_url.rstrip('/')}/health")
                response.raise_for_status()
                data = response.json()
        if not isinstance(data, dict) or data.get("status") not in {
            "available",
            "partial",
            "unavailable",
        }:
            return _unavailable("RAG health response is invalid.")
        return data
    except Exception as exc:  # noqa: BLE001 — optional retrieval must keep chat available.
        log.warning("RAG health unavailable: %s", type(exc).__name__)
        return _unavailable("RAG retrieval service is unavailable.")


def _call_rag_service(
    rag_url: str,
    query: str,
    top_k: int = 5,
    include_sql: bool = True,
    region: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict:
    request = {
        "query": query,
        "top_k": top_k,
        "include_sql": include_sql,
        **{
            k: v
            for k, v in {
                "region": region,
                "start_year": start_year,
                "end_year": end_year,
            }.items()
            if v is not None
        },
    }
    try:
        if rag_url == "direct":
            from RAG.app.main import RetrieveRequest, retrieve_evidence

            data = asyncio.run(retrieve_evidence(RetrieveRequest(**request)))
        else:
            with httpx.Client(trust_env=False, timeout=8.0) as client:
                response = client.post(f"{rag_url.rstrip('/')}/retrieve", json=request)
                response.raise_for_status()
                data = response.json()
        if (
            not isinstance(data, dict)
            or data.get("status") not in {"available", "partial", "unavailable"}
            or not isinstance(data.get("sources"), dict)
        ):
            return _unavailable("RAG retrieval response is invalid.")
        return _bound_rag_payload(data)
    except Exception as exc:  # noqa: BLE001 — optional retrieval must keep chat available.
        log.warning("RAG retrieval unavailable: %s", type(exc).__name__)
        return _unavailable("RAG retrieval service is unavailable.")


class FieldPointArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    latitude: float = Field(
        ge=-85,
        le=85,
        description="User-confirmed latitude; never guess precise coordinates.",
    )
    longitude: float = Field(ge=-180, le=180, description="User-confirmed longitude.")


class ClimateHistoryArgs(FieldPointArgs):
    year: int = Field(default=2025, ge=2016, le=2025)
    variable: Literal[
        "T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"
    ] = "T2M"


def build_tools(
    store: Store, config: Settings | None = None, *, data_http=None, data_slots=None
):
    """Bind tools per chat; model arguments cannot select another chat's history."""
    rag_enabled = bool(config and config.rag_url)

    def for_chat(chat: str):
        def read_user_info() -> dict:
            owner = store.chat_owner(chat)
            if owner is None:
                return {"status": "unavailable", "reason": "No account session is associated with this chat."}
            try:
                return {"status": "available", "profile": store.profile(owner)}
            except sqlite3.Error:
                return {"status": "unavailable", "reason": "Saved profile storage is unavailable. Retry later."}

        def save_user_info(facts: dict[str, str] | None = None, boundary: list[list[float]] | None = None) -> dict:
            owner = store.chat_owner(chat)
            if owner is None:
                return {"status": "unavailable", "reason": "No account session is associated with this chat."}
            try:
                profile = store.update_profile(owner, {"facts": facts or {}, "boundary": boundary})
            except ValueError:
                return {"status": "invalid", "reason": "Profile validation failed; no changes were saved."}
            except sqlite3.Error:
                return {"status": "unavailable", "reason": "Profile storage failed; saving was not confirmed. Retry later."}
            return {"status": "saved", "profile": profile}

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
            state = rag_health(config.rag_url if config else "")
            return {
                "status": "available",
                "scientific_analysis": "unavailable",
                "retrieval": state,
                "datasets": ["NASA POWER Daily 2016–2025"]
                if data_http is not None
                else [],
                "climate_retrieval": {
                    "status": "available" if data_http is not None else "unavailable",
                    "region": "Global coordinates, 85°S–85°N",
                    "place_name_geocoding": "unavailable; ask for a map pin or coordinates",
                    "source_status": "Check each requested location; global access is not regional agronomic validation.",
                },
                "scientific_tools": [],
                "reason": "Reference and historical climate retrieval do not establish agronomic feasibility; scientific calculations are not connected.",
                "available": ["farmer interview", "conversation history", "save_user_info", "read_user_info"],
                "recommendations": "deferred",
            }

        tool_list = [
            StructuredTool.from_function(
                save_user_info, name="save_user_info", args_schema=ProfileUpdate,
                description="Persist user-provided farmer profile facts and/or field boundary to the current private account session. Facts are short named string values; boundary is four [longitude, latitude] corners in boundary order (a repeated closing fifth point is accepted). Save only supplied facts; never guess. A saved boundary is farmer-reported, not verified. Only report success when status is saved.",
            ),
            StructuredTool.from_function(
                read_user_info, name="read_user_info", args_schema=NoArgs,
                description="Read the current account's saved farmer profile and field boundary across chats.",
            ),
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

        if data_http is not None and config is not None and data_slots is not None:

            async def get_climate_history(
                latitude: float,
                longitude: float,
                year: int = 2025,
                variable: str = "T2M",
            ) -> dict:
                async with data_slots:
                    result = await climate(
                        data_http,
                        config.database_path.parent / "dashboard-cache.sqlite",
                        latitude,
                        longitude,
                    )
                months = result.pop("months")
                result["requested_year"] = year
                result["variable"] = variable
                result["unit"] = result["units"].get(variable)
                result["months"] = [
                    {
                        "period": row["period"],
                        "value": row["values"][variable],
                        "valid_days": row["coverage"][variable],
                        "required_days": row["days"],
                    }
                    for row in months
                    if row["period"].startswith(str(year))
                ]
                return result

            async def check_data_sources(latitude: float, longitude: float) -> dict:
                async with data_slots:
                    result = await check_sources(data_http, latitude, longitude)
                # Keep provider provenance and limitations without duplicating all probe URLs.
                # The dashboard retains full per-property request details.
                return {
                    "geometry": result["geometry"],
                    "sources": [
                        {
                            key: source[key]
                            for key in (
                                "id",
                                "name",
                                "status",
                                "source_url",
                                "checked_at",
                                "limitation",
                            )
                        }
                        | {
                            "check_statuses": [
                                check["status"] for check in source["checks"]
                            ]
                        }
                        for source in result["sources"]
                    ],
                }

            tool_list.extend(
                [
                    StructuredTool.from_function(
                        coroutine=get_climate_history,
                        name="get_climate_history",
                        args_schema=ClimateHistoryArgs,
                        description="Retrieve one year and variable of historical NASA POWER monthly climate at user-confirmed coordinates worldwide, including outside Kharkiv/Ukraine. Years 2016–2025. Return source, units, coverage and missing values; not forecasts or crop suitability. Ask for a pin if coordinates are unknown.",
                    ),
                    StructuredTool.from_function(
                        coroutine=check_data_sources,
                        name="check_data_sources",
                        args_schema=FieldPointArgs,
                        description="Check the six specified NASA, ISRIC and FAOSTAT APIs for a location worldwide. Metadata/catalog access does not mean raster extraction or analysis. FAOSTAT is only the documented Ukraine benchmark probe.",
                    ),
                ]
            )

        if rag_enabled and config is not None:

            def search_agronomy_knowledge(
                query: str,
                top_k: int = 5,
                region: str | None = None,
                start_year: int | None = None,
                end_year: int | None = None,
            ) -> dict:
                res = _call_rag_service(
                    config.rag_url,
                    query=query,
                    top_k=top_k,
                    include_sql=False,
                    region=region,
                    start_year=start_year,
                    end_year=end_year,
                )
                return res

            def query_crop_soil_db(
                query: str,
                max_tables: int = 3,
                region: str | None = None,
                start_year: int | None = None,
                end_year: int | None = None,
            ) -> dict:
                res = _call_rag_service(
                    config.rag_url,
                    query=query,
                    top_k=0,
                    include_sql=True,
                    region=region,
                    start_year=start_year,
                    end_year=end_year,
                )
                sql_data = res.get("sql_data", [])
                if isinstance(sql_data, list):
                    sql_data = sql_data[:max_tables]
                res["sql_data"] = sql_data
                return _bound_rag_payload(res)

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
