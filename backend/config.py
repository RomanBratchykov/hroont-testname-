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
    openai_base_url: str = ""
    rag_url: str = ""
    public_origin: str = ""
    phase: Literal["testing", "demo"] = "testing"
    input_rate: Decimal | None = Field(default=None, gt=0)
    output_rate: Decimal | None = Field(default=None, gt=0)
    max_model_calls: int = Field(default=6, ge=1, le=6)
    max_tool_calls: int = Field(default=10, ge=1, le=10)
    concurrency: int = Field(default=4, ge=1, le=4)
    max_context_bytes: int = Field(default=32000, ge=8000, le=128000)
    ollama_context_tokens: int = Field(default=16384, ge=1024, le=131072)
    max_output_tokens: int = Field(default=1024, ge=64, le=4096)
    max_reasoning_tokens: int = Field(default=4096, ge=64, le=32768)
    request_timeout: float = Field(default=120, gt=0, le=600)
    translation_url: str = ""
    translation_key: str = Field(default="", repr=False)

    @model_validator(mode="after")
    def local_model_server(self):
        from urllib.parse import urlsplit

        if self.public_origin:
            public = urlsplit(self.public_origin)
            if (
                public.scheme != "https"
                or not public.hostname
                or public.username
                or public.password
                or public.path
                or public.query
                or public.fragment
                or "*" in public.netloc
                or self.public_origin != f"https://{public.netloc}"
            ):
                raise ValueError(
                    "PUBLIC_ORIGIN must be an exact HTTPS origin without a path."
                )
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
        if self.rag_url and self.rag_url != "direct":
            rag = urlsplit(self.rag_url)
            if (
                rag.scheme not in {"http", "https"}
                or rag.hostname not in {"localhost", "127.0.0.1", "::1"}
                or rag.username
                or rag.password
                or rag.query
                or rag.fragment
            ):
                raise ValueError(
                    "RAG_URL must be 'direct' or a local HTTP(S) URL without credentials."
                )
        if self.openai_base_url:
            base = urlsplit(self.openai_base_url)
            if (
                base.scheme not in {"http", "https"}
                or not base.hostname
                or base.username
                or base.password
                or base.query
                or base.fragment
            ):
                raise ValueError(
                    "OPENAI_BASE_URL must be a valid HTTP(S) URL without credentials."
                )
        return self

    @property
    def paid_model(self) -> bool:
        from urllib.parse import urlsplit

        return self.provider == "deepseek" and (
            not self.openai_base_url
            or urlsplit(self.openai_base_url).hostname
            not in {"localhost", "127.0.0.1", "::1"}
        )

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
        provider = os.getenv("MODEL_PROVIDER", "ollama")
        openai_base_url = os.getenv("OPENAI_BASE_URL", "")
        model = os.getenv("MODEL_NAME", "")
        if not model and provider == "deepseek" and openai_base_url:
            model = os.getenv("DEEPSEEK_MODEL", "")
        values = {
            "provider": provider,
            "model": model,
            "database_path": os.getenv(
                "DATABASE_PATH", str(ROOT / "data/orchestrator.sqlite")
            ),
            "api_key": os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
            "ollama_url": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
            "openai_base_url": openai_base_url,
            "rag_url": os.getenv("RAG_URL", ""),
            "public_origin": os.getenv("PUBLIC_ORIGIN")
            or os.getenv("RENDER_EXTERNAL_URL", ""),
            "phase": os.getenv("BUDGET_PHASE", "testing"),
            "translation_url": os.getenv("TRANSLATION_URL", ""),
            "translation_key": os.getenv("TRANSLATION_API_KEY", ""),
        }
        for env, name in [
            ("DEEPSEEK_INPUT_USD_PER_MILLION", "input_rate"),
            ("DEEPSEEK_OUTPUT_USD_PER_MILLION", "output_rate"),
            ("MODEL_TIMEOUT_SECONDS", "request_timeout"),
            ("OLLAMA_CONTEXT_TOKENS", "ollama_context_tokens"),
            ("MODEL_MAX_OUTPUT_TOKENS", "max_output_tokens"),
            ("MODEL_MAX_REASONING_TOKENS", "max_reasoning_tokens"),
        ]:
            if os.getenv(env):
                values[name] = os.environ[env]
        return cls(**values)
