"""Explicit configuration for the localhost orchestrator test app."""

import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider: Literal["ollama", "deepseek"] = "ollama"
    model: str = ""
    database_path: Path = ROOT / "data" / "orchestrator.sqlite"
    api_key: str = Field(default="", repr=False)
    ollama_url: str = "http://127.0.0.1:11434"
    phase: Literal["testing", "demo"] = "testing"
    input_rate: Decimal | None = Field(default=None, gt=0)
    output_rate: Decimal | None = Field(default=None, gt=0)
    max_model_calls: int = Field(default=6, ge=1, le=6)
    max_tool_calls: int = Field(default=10, ge=1, le=10)
    concurrency: int = Field(default=4, ge=1, le=4)
    max_context_bytes: int = Field(default=32000, ge=8000, le=128000)
    max_output_tokens: int = Field(default=1024, ge=64, le=4096)
    max_reasoning_tokens: int = Field(default=4096, ge=64, le=32768)
    request_timeout: float = Field(default=120, gt=0, le=600)
    translation_url: str = ""
    translation_key: str = Field(default="", repr=False)

    @model_validator(mode="after")
    def local_model_server(self):
        from urllib.parse import urlsplit

        url = urlsplit(self.ollama_url)
        if url.scheme != "http" or url.hostname not in {
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError(
                "Ollama URL must be local HTTP; remote fallback is disabled."
            )
        if url.username or url.password or url.query or url.fragment:
            raise ValueError(
                "Ollama URL must not contain credentials, query or fragment."
            )
        return self

    @property
    def model_name(self):
        return self.model or (
            "deepseek-flash" if self.provider == "deepseek" else "qwen3.5:4b"
        )

    def output_tokens(self, thinking: bool) -> int:
        return (
            max(self.max_output_tokens, self.max_reasoning_tokens)
            if thinking
            else self.max_output_tokens
        )

    @property
    def phase_budget(self):
        return Decimal(2) if self.phase == "demo" else Decimal(3)

    @classmethod
    def from_env(cls):
        values = {
            "provider": os.getenv("MODEL_PROVIDER", "ollama"),
            "model": os.getenv("MODEL_NAME", ""),
            "database_path": os.getenv(
                "DATABASE_PATH", str(ROOT / "data/orchestrator.sqlite")
            ),
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "ollama_url": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            "phase": os.getenv("BUDGET_PHASE", "testing"),
            "translation_url": os.getenv("TRANSLATION_URL", ""),
            "translation_key": os.getenv("TRANSLATION_API_KEY", ""),
        }
        for env, name in [
            ("DEEPSEEK_INPUT_USD_PER_MILLION", "input_rate"),
            ("DEEPSEEK_OUTPUT_USD_PER_MILLION", "output_rate"),
            ("MODEL_TIMEOUT_SECONDS", "request_timeout"),
            ("MODEL_MAX_OUTPUT_TOKENS", "max_output_tokens"),
            ("MODEL_MAX_REASONING_TOKENS", "max_reasoning_tokens"),
        ]:
            if os.getenv(env):
                values[name] = os.environ[env]
        return cls(**values)
