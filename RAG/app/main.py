"""Local evidence retrieval; model generation belongs to the main Croptato backend."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator

from .db import check_postgres_status, query_relevant_sql_data
from .qdrant_service import check_qdrant_status, retrieve_chunks

app = FastAPI(title="Croptato evidence retrieval", version="0.3.0")


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=16000)
    top_k: int = Field(default=5, ge=0, le=20)
    include_sql: bool = True
    source_filter: str | None = Field(default=None, max_length=500)
    region: str | None = Field(default=None, min_length=1, max_length=100)
    start_year: int | None = Field(default=None, ge=1, le=9999)
    end_year: int | None = Field(default=None, ge=1, le=9999)

    @model_validator(mode="after")
    def validate_period(self):
        if not self.query.strip() or (
            self.region is not None and not self.region.strip()
        ):
            raise ValueError("Query and region must not be blank")
        if (
            self.start_year is not None
            and self.end_year is not None
            and self.start_year > self.end_year
        ):
            raise ValueError("start_year must not exceed end_year")
        return self


def _state(source: dict[str, Any], vector: bool) -> dict[str, Any]:
    source = dict(source)
    if "state" not in source:
        source["state"] = (
            "unavailable"
            if not source.get("connected")
            else "missing"
            if vector and not source.get("exists")
            else "ready"
            if source.get("points_count" if vector else "table_count", 0)
            else "empty"
        )
    source.pop("error", None)
    source.pop("url", None)
    return source


def _overall(sources: dict[str, dict[str, Any]]) -> str:
    enabled = [s for s in sources.values() if s["state"] != "disabled"]
    usable = sum(s["state"] in {"ready", "no_match"} for s in enabled)
    return (
        "available"
        if enabled and usable == len(enabled)
        else "partial"
        if usable
        else "unavailable"
    )


async def _source_health() -> dict[str, dict[str, Any]]:
    async def check(fn, vector):
        try:
            return _state(await asyncio.to_thread(fn), vector)
        except Exception:  # noqa: BLE001 — external source failures are availability states.
            return {"connected": False, "state": "unavailable"}

    vector, sql = await asyncio.gather(
        check(check_qdrant_status, True), check(check_postgres_status, False)
    )
    return {"vector": vector, "sql": sql}


@app.get("/health")
@app.get("/api/health")
async def health_check() -> dict[str, Any]:
    sources = await _source_health()
    return {
        "status": _overall(sources),
        "service": "croptato-retrieval",
        "sources": sources,
        "qdrant": sources["vector"],
        "postgres": sources["sql"],
        "retrieval_tools": ["search_agronomy_knowledge", "query_crop_soil_db"],
        "scientific_tools": [],
    }


@app.post("/retrieve")
async def retrieve_evidence(payload: RetrieveRequest) -> dict[str, Any]:
    sources = await _source_health()
    filters = {
        "region": payload.region,
        "start_year": payload.start_year,
        "end_year": payload.end_year,
    }

    async def fetch(name, enabled, fn, **kwargs):
        source = sources[name]
        if not enabled:
            source["state"] = "disabled"
            return []
        if source["state"] != "ready":
            return []
        try:
            rows = await asyncio.to_thread(fn, payload.query, **kwargs, **filters)
            source["state"] = "ready" if rows else "no_match"
            source["matches"] = len(rows)
            return rows
        except Exception:  # noqa: BLE001 — external source failures are availability states.
            source.update(state="unavailable", connected=False)
            return []

    chunks, sql_data = await asyncio.gather(
        fetch(
            "vector",
            payload.top_k > 0,
            retrieve_chunks,
            top_k=payload.top_k,
            source_filter=payload.source_filter,
        ),
        fetch("sql", payload.include_sql, query_relevant_sql_data),
    )
    return {
        "status": _overall(sources),
        "query": payload.query,
        "chunks": chunks,
        "sql_data": sql_data,
        "sources": sources,
    }


@app.post("/chat")
@app.post("/recommend")
@app.post("/api/chat")
async def chat_or_recommend() -> None:
    raise HTTPException(
        status_code=410,
        detail={
            "code": "use_main_backend",
            "message": "Send chat requests to the main Croptato backend /api/chat; it owns provider selection, budgets and sessions.",
        },
    )
