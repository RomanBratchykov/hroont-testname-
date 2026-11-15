"""FastAPI entrypoint for the AgroResilience RAG + Local DeepSeek service."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from .db import check_postgres_status, query_relevant_sql_data
from .llm_service import (
    generate_rag_answer,
    get_deepseek_model,
    get_openai_base_url,
)
from .qdrant_service import check_qdrant_status, retrieve_chunks

RAG_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = RAG_ROOT.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(RAG_ROOT / ".env")

app = FastAPI(
    title="Kherson Crop Rotation Dashboard API",
    description=(
        "Backend API for the NASA Space Apps Challenge agricultural crop rotation "
        "dashboard powered by local DeepSeek & hybrid Qdrant/PostgreSQL RAG."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory conversation store when RAG service is used directly by a chat UI.
_CONVERSATIONS: dict[str, dict[str, Any]] = {}


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=16000)
    top_k: int = Field(default=5, ge=0, le=20)
    include_sql: bool = True
    source_filter: str | None = None


class RagChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: Literal["send", "list", "read", "rename", "delete", "clear"] = "send"
    conversation_id: str = Field(default="", max_length=100)
    request_id: str = Field(default="", max_length=100)
    query: str = Field(default="", max_length=16000)
    message: str = Field(default="", max_length=16000)
    history: list[HistoryTurn] = Field(default_factory=list)
    mode: Literal["auto", "fast", "thinking"] = "auto"
    title: str = Field(default="", max_length=100)
    files: list[dict[str, Any]] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)
    include_sql: bool = True
    source_filter: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1500, ge=64, le=8192)


def _extract_prompt(payload: RagChatRequest) -> str:
    return (payload.query or payload.message or "").strip()


def _handle_conversation_command(payload: RagChatRequest) -> dict[str, Any] | None:
    if payload.action == "list":
        ordered = sorted(
            _CONVERSATIONS.values(),
            key=lambda c: c["updated_at"],
            reverse=True,
        )
        return {
            "conversations": [
                {
                    "id": c["id"],
                    "title": c["title"],
                    "updated_at": c["updated_at"],
                }
                for c in ordered
            ]
        }
    if payload.action == "read":
        conv = _CONVERSATIONS.get(payload.conversation_id)
        if conv is None:
            raise HTTPException(status_code=404, detail="Chat not found.")
        return conv
    if payload.action == "delete":
        _CONVERSATIONS.pop(payload.conversation_id, None)
        return {"status": "deleted"}
    if payload.action == "clear":
        _CONVERSATIONS.clear()
        return {"status": "deleted"}
    if payload.action == "rename":
        conv = _CONVERSATIONS.get(payload.conversation_id)
        if conv is None or not payload.title.strip():
            raise HTTPException(status_code=404, detail="Chat not found.")
        conv["title"] = payload.title.strip()
        conv["updated_at"] = time.time()
        return {"status": "renamed"}
    return None


@app.get("/health", tags=["System"])
@app.get("/api/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    """Verify that the FastAPI, Qdrant, and PostgreSQL services are reachable."""
    qdrant_status, postgres_status = await asyncio.gather(
        asyncio.to_thread(check_qdrant_status),
        asyncio.to_thread(check_postgres_status),
    )
    return {
        "status": "ok",
        "service": "kherson-crop-rotation-api",
        "environment": os.getenv("APP_ENV", "development"),
        "provider": "deepseek",
        "model": get_deepseek_model(),
        "openai_base_url": get_openai_base_url(),
        "configured": True,
        "scientific_tools": ["search_agronomy_knowledge", "query_crop_soil_db"],
        "qdrant": qdrant_status,
        "postgres": postgres_status,
    }


@app.post("/retrieve", tags=["RAG"])
async def retrieve_evidence(payload: RetrieveRequest) -> dict[str, Any]:
    """Retrieve matching Qdrant chunks and PostgreSQL table samples without calling an LLM."""
    chunks_task = (
        asyncio.to_thread(
            retrieve_chunks,
            payload.query,
            payload.top_k,
            payload.source_filter,
        )
        if payload.top_k > 0
        else asyncio.sleep(0, result=[])
    )
    if payload.include_sql:
        sql_task = asyncio.to_thread(query_relevant_sql_data, payload.query)
        chunks, sql_data = await asyncio.gather(chunks_task, sql_task)
    else:
        chunks = await chunks_task
        sql_data = []

    return {
        "status": "available",
        "query": payload.query,
        "chunks": chunks,
        "sql_data": sql_data,
    }


@app.post("/chat", tags=["Chat"])
@app.post("/recommend", tags=["Chat"])
async def chat_or_recommend(payload: RagChatRequest) -> dict[str, Any]:
    """Run hybrid Qdrant + PostgreSQL RAG with local DeepSeek and return a structured JSON answer."""
    command_result = _handle_conversation_command(payload)
    if command_result is not None:
        return command_result

    prompt = _extract_prompt(payload)
    if not prompt:
        raise HTTPException(status_code=422, detail="Either 'query' or 'message' must be non-empty.")

    history_dicts = [turn.model_dump() for turn in payload.history]
    if not history_dicts and payload.conversation_id in _CONVERSATIONS:
        history_dicts = [
            {"role": m["role"], "content": m["content"]}
            for m in _CONVERSATIONS[payload.conversation_id]["messages"]
        ]

    result = await asyncio.to_thread(
        generate_rag_answer,
        prompt,
        history=history_dicts,
        top_k=payload.top_k,
        include_sql=payload.include_sql,
        source_filter=payload.source_filter,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )

    conv_id = payload.conversation_id or uuid.uuid4().hex
    now = time.time()
    conv = _CONVERSATIONS.setdefault(
        conv_id,
        {
            "id": conv_id,
            "title": prompt[:60] or "Agronomy chat",
            "updated_at": now,
            "messages": [],
        },
    )
    req_id = payload.request_id or uuid.uuid4().hex
    conv["messages"].append(
        {"id": req_id, "role": "user", "content": prompt, "created_at": now}
    )
    conv["messages"].append(
        {
            "id": f"{req_id}:answer",
            "role": "assistant",
            "content": result["answer"],
            "created_at": time.time(),
        }
    )
    conv["updated_at"] = time.time()

    return {
        **result,
        "content": result["answer"],
        "conversation_id": conv_id,
        "request_id": req_id,
    }


@app.post("/api/chat", tags=["Chat"])
async def frontend_chat_endpoint(payload: RagChatRequest) -> Any:
    """Frontend-compatible NDJSON streaming chat endpoint matching `backend/api.py`."""
    command_result = _handle_conversation_command(payload)
    if command_result is not None:
        return command_result

    prompt = _extract_prompt(payload)
    if not prompt:
        raise HTTPException(status_code=422, detail="Sending requires a non-empty message or query.")

    conv_id = payload.conversation_id or uuid.uuid4().hex
    req_id = payload.request_id or uuid.uuid4().hex
    history_dicts = [turn.model_dump() for turn in payload.history]
    if not history_dicts and conv_id in _CONVERSATIONS:
        history_dicts = [
            {"role": m["role"], "content": m["content"]}
            for m in _CONVERSATIONS[conv_id]["messages"]
        ]

    async def stream():
        yield (
            json.dumps(
                {
                    "type": "status",
                    "stage": "retrieving",
                    "message": "Searching agronomy knowledge & SQL datasets…",
                }
            )
            + "\n"
        )
        yield (
            json.dumps(
                {
                    "type": "status",
                    "stage": "thinking" if payload.mode == "thinking" else "processing",
                    "message": "Thinking with local DeepSeek…"
                    if payload.mode == "thinking"
                    else "Preparing grounded answer…",
                }
            )
            + "\n"
        )
        try:
            result = await asyncio.to_thread(
                generate_rag_answer,
                prompt,
                history=history_dicts,
                top_k=payload.top_k,
                include_sql=payload.include_sql,
                source_filter=payload.source_filter,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
            )
            now = time.time()
            conv = _CONVERSATIONS.setdefault(
                conv_id,
                {
                    "id": conv_id,
                    "title": prompt[:60] or "Agronomy chat",
                    "updated_at": now,
                    "messages": [],
                },
            )
            conv["messages"].append(
                {"id": req_id, "role": "user", "content": prompt, "created_at": now}
            )
            conv["messages"].append(
                {
                    "id": f"{req_id}:answer",
                    "role": "assistant",
                    "content": result["answer"],
                    "created_at": time.time(),
                }
            )
            conv["updated_at"] = time.time()

            yield (
                json.dumps(
                    {
                        "type": "answer",
                        "content": result["answer"],
                        "status": "partial" if result.get("status") == "partial" else "completed",
                        "conversation_id": conv_id,
                        "request_id": req_id,
                        "evidence": result.get("evidence", []),
                        "provider": "deepseek",
                        "model": result.get("model", get_deepseek_model()),
                    }
                )
                + "\n"
            )
        except Exception as exc:  # noqa: BLE001 — emit client-safe error event inside NDJSON stream.
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "code": "failed",
                        "message": f"RAG processing failed ({type(exc).__name__}).",
                    }
                )
                + "\n"
            )

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )
