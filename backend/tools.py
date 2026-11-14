"""Server-owned LangChain tools. Future scientific tools must be registered here."""

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field

from backend.store import Store


class HistoryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    limit: int = Field(default=10, ge=1, le=30)
    before: int | None = Field(default=None, ge=1)


class NoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


def build_tools(store: Store):
    """Bind tools per chat; model arguments cannot select another chat's history."""

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
            import json

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
            return {
                "status": "available",
                "scientific_analysis": "unavailable",
                "datasets": [],
                "scientific_tools": [],
                "reason": "Scientific scripts and datasets will be added later. No NASA data has been fetched.",
                "available": ["farmer interview", "conversation history"],
                "recommendations": "deferred",
            }

        return {
            tool.name: tool
            for tool in [
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
        }

    return for_chat
