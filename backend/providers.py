"""Native wire protocols behind a small shared chat boundary. No provider fallback."""

import json
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.config import Settings


class ProviderError(Exception):
    def __init__(self, code: str, message: str, definitely_unbilled=False):
        self.code, self.message = code, message
        self.definitely_unbilled = definitely_unbilled
        super().__init__(message)


class FunctionCall(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    arguments: str | dict


class ToolCall(BaseModel):
    id: str = ""
    function: FunctionCall


class AssistantMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    role: str = "assistant"
    content: str | None = ""
    reasoning_content: str | None = None
    thinking: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list, max_length=20)


@dataclass
class Completion:
    message: dict
    calls: list[ToolCall]
    prompt_tokens: int | None
    completion_tokens: int | None
    truncated: bool = False


class Provider:
    def __init__(self, settings: Settings, http: httpx.AsyncClient):
        self.settings, self.http = settings, http

    async def complete(
        self, messages: list[dict], tools: list[dict], thinking: bool
    ) -> Completion:
        config = self.settings
        if config.provider == "deepseek":
            if not config.api_key:
                raise ProviderError(
                    "configuration", "Set DEEPSEEK_API_KEY on the server.", True
                )
            url = "https://api.deepseek.com/chat/completions"
            body = {
                "model": config.model_name,
                "messages": messages,
                "stream": False,
                "max_tokens": config.output_tokens(thinking),
                "thinking": {"type": "enabled" if thinking else "disabled"},
            }
            headers = {"Authorization": f"Bearer {config.api_key}"}
        else:
            url = config.ollama_url.rstrip("/") + "/api/chat"
            body = {
                "model": config.model_name,
                "messages": messages,
                "stream": False,
                "think": thinking,
                "options": {"num_predict": config.output_tokens(thinking)},
            }
            headers = {}
        if tools:
            body["tools"] = tools
        try:
            async with self.http.stream(
                "POST",
                url,
                json=body,
                headers=headers,
                timeout=httpx.Timeout(config.request_timeout, connect=5),
            ) as response:
                if response.status_code in {401, 403}:
                    raise ProviderError(
                        "configuration",
                        "Model access denied. Check the server credentials.",
                        True,
                    )
                if response.status_code in {400, 404, 422}:
                    raise ProviderError(
                        "configuration",
                        "Model or request capability is unavailable. Check model name and tool/thinking support.",
                        True,
                    )
                if response.status_code >= 400:
                    raise ProviderError(
                        "unavailable",
                        "Model unavailable. Restart manually or try later.",
                    )
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 2_000_000:
                        raise ProviderError(
                            "invalid_response",
                            "Model response exceeded the safety limit.",
                        )
            data = json.loads(raw)
            if config.provider == "deepseek":
                choice = data["choices"][0]
                raw_message = choice["message"]
                usage = data.get("usage") or {}
                prompt, completion = (
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                )
                truncated = choice.get("finish_reason") == "length"
            else:
                if data.get("done") is not True or data.get("error"):
                    raise ValueError("Incomplete Ollama response")
                raw_message = data["message"]
                prompt, completion = (
                    data.get("prompt_eval_count"),
                    data.get("eval_count"),
                )
                truncated = data.get("done_reason") == "length"
            parsed = AssistantMessage.model_validate(raw_message)
            if (
                thinking
                and truncated
                and parsed.role == "assistant"
                and not parsed.content
                and not parsed.tool_calls
                and (parsed.thinking or parsed.reasoning_content)
            ):
                raise ProviderError(
                    "reasoning_limit",
                    "I reached the reasoning limit before I could finish an answer. "
                    "Please try a narrower question or switch to Fast mode.",
                )
            if parsed.role != "assistant" or (
                not parsed.content and not parsed.tool_calls
            ):
                raise ValueError("Missing assistant answer")
            for value in (prompt, completion):
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError("Invalid usage")
            message = parsed.model_dump(exclude_none=True)
            # Preserve provider-private reasoning only in this turn's protocol continuation.
            if config.provider == "ollama":
                message.pop("reasoning_content", None)
                message["tool_calls"] = [
                    {
                        "function": {
                            "name": call.function.name,
                            "arguments": json.loads(call.function.arguments)
                            if isinstance(call.function.arguments, str)
                            else call.function.arguments,
                        }
                    }
                    for call in parsed.tool_calls
                ]
            else:
                message.pop("thinking", None)
                message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments
                            if isinstance(call.function.arguments, str)
                            else json.dumps(call.function.arguments),
                        },
                    }
                    for call in parsed.tool_calls
                ]
                if any(not call.id for call in parsed.tool_calls):
                    raise ValueError("Missing tool call ID")
            if not parsed.tool_calls:
                message.pop("tool_calls", None)
            return Completion(message, parsed.tool_calls, prompt, completion, truncated)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                "timeout", "Model timed out. Restart manually or try later."
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                "unavailable",
                "Cannot reach the selected model. Restart manually or try later.",
            ) from exc
        except (ValueError, KeyError, IndexError, TypeError, ValidationError) as exc:
            raise ProviderError(
                "invalid_response", "Model returned an invalid or incomplete response."
            ) from exc
