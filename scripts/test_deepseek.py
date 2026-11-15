#!/usr/bin/env python3
"""Opt-in paid smoke test of the real orchestrator using the saved synthetic profile."""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend/python"))

import httpx
from agrodata.ollama_report import render

from backend.config import Settings
from backend.orchestrator import Orchestrator
from backend.providers import Provider
from backend.store import Store
from backend.tools import build_tools
from scripts.run import environment, select_provider


class SmokeSettings(Settings):
    @property
    def phase_budget(self):
        return Decimal("0.10")


async def check(config, output):
    store = Store(config.database_path)
    events = []
    started = time.monotonic()

    def record(stage, data):
        event = {
            "stage": stage,
            "data": data,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        events.append(event)
        with (output / "trace.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        render(events, output)

    class TracedProvider(Provider):
        async def complete(self, messages, tools, thinking):
            # Never include HTTP headers or provider-private reasoning in the report.
            record(
                "request",
                {
                    "model": config.model_name,
                    "messages": list(messages),
                    "tools": tools,
                },
            )
            response = await super().complete(messages, tools, thinking)
            record(
                "response",
                {
                    k: v
                    for k, v in response.message.items()
                    if k not in ("reasoning_content", "thinking")
                },
            )
            return response

    cases = [
        (
            "saved-profile",
            "fast",
            "Explain John’s saved example dashboard. Clearly distinguish synthetic examples from computed scientific results.",
        ),
        (
            "tools-and-history",
            "fast",
            "Call read_history to recover my previous question, then call get_capabilities. Report what can actually be calculated and whether you can create or modify my dashboard.",
        ),
        (
            "thinking",
            "thinking",
            "Based on the saved example, explain which inputs and scientific tools are missing before a validated crop rotation can be recommended. Do not invent measurements.",
        ),
    ]
    results = []
    async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as http:
        engine = Orchestrator(
            config, store, TracedProvider(config, http), build_tools(store, config)
        )
        for name, mode, prompt in cases:
            store.begin("smoke", name, prompt, mode, [])
            turn = [
                event async for event in engine.run("smoke", name, prompt, mode, [])
            ]
            final = turn[-1]
            for evidence in final.get("evidence", []):
                record(
                    "tool_result",
                    {"name": evidence["tool"], "result": evidence["result"]},
                )
            success = (
                final.get("type") == "answer" and final.get("status") == "completed"
            )
            if name == "tools-and-history":
                used = {item["tool"] for item in final.get("evidence", [])}
                success = success and {"read_history", "get_capabilities"} <= used
            results.append({"case": name, "passed": success, "event": final})
            if not success:
                record("error", {"case": name, "event": final})
                break
    passed = len(results) == len(cases) and all(item["passed"] for item in results)
    record("finished", {"status": "completed" if passed else "failed"})
    report = {
        "passed": passed,
        "cases": results,
        "budget": store.budget(config.phase),
        "dashboard": str(output / "run-dashboard.html"),
        "limitations": [
            "Model behavior needs human review.",
            "Scientific calculations and dashboard editing are not connected to the main orchestrator.",
            "Retrieval is tested only when --with-rag is explicitly selected.",
        ],
    }
    (output / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Authorize paid API calls, with a $0.10 local reservation cap",
    )
    parser.add_argument(
        "--with-rag",
        action="store_true",
        help="Use configured local RAG service and its existing indexed data",
    )
    args = parser.parse_args()
    if not args.live:
        print(
            "No paid requests made. Use --live to test saved-profile, tools/history, and thinking; optionally --with-rag."
        )
        return 0
    env = environment()
    select_provider(env, "deepseek", None)
    if not env.get("DEEPSEEK_API_KEY"):
        print(
            "DEEPSEEK_API_KEY is missing. Add it to .env; do not paste it in chat.",
            file=sys.stderr,
        )
        return 1
    if env.get("OPENAI_BASE_URL"):
        print("Clear OPENAI_BASE_URL to test the hosted DeepSeek API.", file=sys.stderr)
        return 1
    for key, value in env.items():
        os.environ[key] = value
    base = Settings.from_env()
    if base.input_rate is None or base.output_rate is None:
        print(
            "Set both DEEPSEEK_*_USD_PER_MILLION rates in .env first.", file=sys.stderr
        )
        return 1
    output = (
        ROOT / "data/deepseek-smoke" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    )
    output.mkdir(parents=True)
    config = SmokeSettings(
        **(
            base.model_dump()
            | {
                "database_path": output / "test.sqlite",
                "model": env["MODEL_NAME"],
                "rag_url": base.rag_url if args.with_rag else "",
                "max_model_calls": 3,
                "max_output_tokens": 512,
                "max_reasoning_tokens": 2048,
                "request_timeout": 120,
            }
        )
    )
    return asyncio.run(check(config, output))


if __name__ == "__main__":
    sys.exit(main())
