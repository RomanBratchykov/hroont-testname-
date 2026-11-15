"""Local DeepSeek LLM orchestration service combining Qdrant RAG chunks and PostgreSQL data."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from .db import query_relevant_sql_data
from .qdrant_service import retrieve_chunks

logger = logging.getLogger(__name__)

RAG_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = RAG_ROOT.parent
load_dotenv(REPO_ROOT / ".env")
load_dotenv(RAG_ROOT / ".env")

SYSTEM_PROMPT = """You are Soily, the AgroResilience agronomic assistant helping farmers analyze fields, soil conditions, and sustainable crop rotations.

Grounding and scientific integrity rules:
1. Base all agronomic facts, historical yields, soil parameters, and rotation candidates on the retrieved [Vector Knowledge Base] passages and [PostgreSQL Historical Crop & Soil Data] tables supplied in the prompt.
2. Always cite your evidence inline using [source_file] for vector passages and [table_name] for SQL data.
3. Preserve exact units, dates, crop years, and regional provenance. Never apply Kherson, Broadbalk (UK), Marchfeld (Austria), Hoytville/Wooster (Ohio), or Texcoco (Mexico) pilot assumptions outside their geographic scope without noting the regional limitation.
4. Never fabricate numbers, yields, profits, erosion metrics, or chemical measurements. If a needed measurement or tool output is missing, state clearly that it is unavailable / not_computed — never substitute zero for missing values.
5. When proposing crop rotation options (and evidence supports them), distinguish up to three strategies: Economic Potential, Balanced, and Climate & Soil Resilience. Explain any missing inputs needed to validate field-level feasibility.
6. Keep answers clear, warm, concise, and practical for farmers."""

_THINK_BLOCK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK_RE = re.compile(r"<think>.*$", re.DOTALL | re.IGNORECASE)


def get_openai_base_url() -> str:
    explicit = os.getenv("OPENAI_BASE_URL", "").strip()
    if explicit:
        return explicit
    ollama = (
        os.getenv("OLLAMA_URL", "http://localhost:11434").strip()
        or "http://localhost:11434"
    )
    return ollama.rstrip("/") + "/v1"


def get_openai_api_key() -> str:
    return (
        os.getenv("OPENAI_API_KEY", "").strip()
        or os.getenv("DEEPSEEK_API_KEY", "").strip()
        or "sk-local-deepseek-dummy-key"
    )


def get_deepseek_model() -> str:
    return (
        os.getenv("DEEPSEEK_MODEL", "").strip()
        or os.getenv("MODEL_NAME", "").strip()
        or "deepseek-r1:8b"
    )


def strip_think_tags(text: str) -> tuple[str, str | None]:
    """Separate DeepSeek <think>...</think> reasoning blocks from the final visible answer."""
    if not text:
        return "", None
    thoughts = [
        match.group(1).strip()
        for match in _THINK_BLOCK_RE.finditer(text)
        if match.group(1).strip()
    ]
    cleaned = _THINK_BLOCK_RE.sub("", text)
    if "<think>" in cleaned.lower():
        unclosed = _UNCLOSED_THINK_RE.search(cleaned)
        if unclosed:
            trailing = unclosed.group(0)[7:].strip()
            if trailing:
                thoughts.append(trailing)
            cleaned = _UNCLOSED_THINK_RE.sub("", cleaned)
    reasoning = "\n\n".join(thoughts) if thoughts else None
    return cleaned.strip(), reasoning


def format_rag_context(
    chunks: list[dict[str, Any]], sql_data: list[dict[str, Any]]
) -> str:
    """Format retrieved vector chunks and PostgreSQL table samples into a bounded prompt section."""
    sections: list[str] = []

    if chunks:
        chunk_lines = ["[Vector Knowledge Base]"]
        for idx, chunk in enumerate(chunks, start=1):
            source = chunk.get("source_file", "unknown")
            score = chunk.get("score", 0.0)
            text = str(chunk.get("text", "")).strip()
            chunk_lines.append(
                f"({idx}) [source: {source} | score: {score:.3f}]\n{text}"
            )
        sections.append("\n\n".join(chunk_lines))
    else:
        sections.append(
            "[Vector Knowledge Base]\nNo matching passages retrieved from Qdrant."
        )

    if sql_data:
        sql_lines = ["[PostgreSQL Historical Crop & Soil Data]"]
        for table_entry in sql_data:
            table_name = table_entry.get("table", "unknown")
            row_count = table_entry.get("row_count", 0)
            columns = table_entry.get("columns", [])
            sample_rows = table_entry.get("sample_rows", [])
            rows_json = json.dumps(sample_rows, ensure_ascii=False)
            if len(rows_json) > 2500:
                rows_json = rows_json[:2500] + "... [truncated]"
            sql_lines.append(
                f"Table [{table_name}] (total_rows={row_count}, columns={columns}):\n{rows_json}"
            )
        sections.append("\n\n".join(sql_lines))
    else:
        sections.append(
            "[PostgreSQL Historical Crop & Soil Data]\nNo relevant SQL tables retrieved."
        )

    return "\n\n---\n\n".join(sections)


def _build_evidence(
    chunks: list[dict[str, Any]], sql_data: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for chunk in chunks:
        evidence.append(
            {
                "type": "vector",
                "source_file": chunk.get("source_file", "unknown"),
                "score": round(float(chunk.get("score", 0.0)), 4),
                "excerpt": str(chunk.get("text", ""))[:300],
            }
        )
    for table in sql_data:
        evidence.append(
            {
                "type": "sql",
                "table": table.get("table", "unknown"),
                "row_count": table.get("row_count", 0),
                "columns": table.get("columns", []),
                "sample_rows": table.get("sample_rows", [])[:3],
            }
        )
    return evidence


def generate_rag_answer(
    query: str,
    history: list[dict[str, str]] | None = None,
    top_k: int = 5,
    include_sql: bool = True,
    source_filter: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    client: OpenAI | None = None,
) -> dict[str, Any]:
    """Retrieve Qdrant + PostgreSQL evidence and generate a grounded answer via local DeepSeek."""
    clean_query = (query or "").strip()
    if not clean_query:
        return {
            "answer": "Please provide an agronomic question or field description.",
            "status": "invalid",
            "model": get_deepseek_model(),
            "sources": [],
            "sql_data": [],
            "evidence": [],
        }

    chunks = retrieve_chunks(clean_query, top_k=top_k, source_filter=source_filter)
    sql_data = query_relevant_sql_data(clean_query) if include_sql else []
    context_block = format_rag_context(chunks, sql_data)
    evidence = _build_evidence(chunks, sql_data)

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for item in history[-10:]:
            role = item.get("role", "")
            content = item.get("content", "")
            if (
                role in {"user", "assistant"}
                and isinstance(content, str)
                and content.strip()
            ):
                messages.append({"role": role, "content": content.strip()})

    user_prompt = (
        f"Retrieved Agronomic Evidence:\n\n{context_block}\n\n"
        f"Farmer Question / Request:\n{clean_query}"
    )
    messages.append({"role": "user", "content": user_prompt})

    model_name = get_deepseek_model()
    base_url = get_openai_base_url()
    timeout_s = float(os.getenv("MODEL_TIMEOUT_SECONDS", "120"))

    try:
        openai_client = client or OpenAI(
            base_url=base_url,
            api_key=get_openai_api_key(),
            timeout=timeout_s,
        )
        completion = openai_client.chat.completions.create(
            model=model_name,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        raw_content = ""
        if completion.choices and completion.choices[0].message:
            raw_content = completion.choices[0].message.content or ""
        answer, _reasoning = strip_think_tags(raw_content)
        if not answer and raw_content.strip():
            # Fallback if model put everything inside <think> and hit max_tokens
            answer = (
                "The local model exhausted its thinking budget before writing a final summary. "
                "Retrieved evidence is attached; please retry or narrow your question."
            )
            status = "partial"
        elif not answer:
            answer = "The model returned an empty response. Please try again."
            status = "partial"
        else:
            status = "completed"

        return {
            "answer": answer,
            "status": status,
            "model": model_name,
            "sources": chunks,
            "sql_data": sql_data,
            "evidence": evidence,
        }
    except Exception as exc:  # noqa: BLE001 — degrade gracefully when local DeepSeek server is unreachable.
        logger.warning(
            "Local DeepSeek call failed (%s, model=%s): %s", base_url, model_name, exc
        )
        fallback_lines = [
            f"Local DeepSeek inference at `{base_url}` (`{model_name}`) is currently unavailable ({type(exc).__name__}).",
        ]
        if chunks or sql_data:
            fallback_lines.append(
                f"However, I retrieved {len(chunks)} vector passage(s) from Qdrant and {len(sql_data)} PostgreSQL table(s) for your query. See the attached evidence below."
            )
        else:
            fallback_lines.append(
                "Please verify that Ollama / your local DeepSeek server is running."
            )
        return {
            "answer": "\n\n".join(fallback_lines),
            "status": "partial",
            "model": model_name,
            "sources": chunks,
            "sql_data": sql_data,
            "evidence": evidence,
            "error": str(exc),
        }
