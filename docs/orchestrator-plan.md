# Local orchestrator implementation

User authorized implementation on 2026-11-14, with datasets/scientific scripts supplied later.
Reference: all files in AGENTS; current conversation overrides historical deployment requirements.

## Design

One FastAPI application, native HTTP adapters for DeepSeek and Ollama, Pydantic contracts,
LangChain structured tools, SQLite persistence for a standalone localhost test.
Two endpoints: GET /api/health and POST /api/chat (send/list/read/rename/delete/clear actions).
The send response streams NDJSON lifecycle events and the final answer. A single explicit
local demo administrator owns the test workspace; the preview login is not authentication.
Provider is selected at startup, never by model output, and never falls back remotely.
Scientific calculations, dataset RAG and validated profile extraction are deferred.

Alternative: separate provider endpoints duplicate orchestration and tie the UI to vendors.
PostgreSQL is the future domain-storage default; SQLite avoids a separate service for this test.
No cloud deployment, model downloads, paid calls, or commits during implementation.

## Tasks and acceptance checks

- [x] Write offline boundary tests first: provider protocol, durable history/deletion,
  bounded tools, missing scientific evidence, budget reservations and cancellation.
- [x] Implement configuration, adapters, persistence, safe tools, bounded orchestrator,
  and two HTTP endpoints. No shell execution or arbitrary tool registration by clients.
- [x] Wire existing chat to the shared API with cancellation, statuses and assistant replies;
  preserve preview-only frontend mode. Add local document extraction with strict limits.
- [x] Add unified launcher and simple README for frontend-only, backend-only, Ollama,
  and DeepSeek testing/demo phases.
- [x] Run backend tests, frontend tests/build/lint, launcher checks and inspect changes.

## Review focus

Cross-chat contamination; malformed/unknown tools; cancelled paid requests and uncertain
usage; context/file limits; failed models must never produce fabricated scientific results.
Tests fake only external HTTP/model responses, not internal orchestration or persistence.

## Progress

Inspection complete. No scientific tools/data found. Existing chat stores user-only messages
in localStorage. Provider protocols checked against official DeepSeek and Ollama docs.
Ruling: build directly as requested; no additional design approval round. Work in the shared
checkout to preserve existing uncommitted AGENTS edits; do not commit or change branches.

Implementation and independent review completed. Review fixes: history snapshot merges and
answer deduplication, cancellation guards, local language screening before provider/history dispatch,
and collision-free assistant message IDs. SQLite stores originals and linked English translations;
chat deletion cascades through messages/runs/translations while retaining non-content spending records.

Verification: 17 offline backend tests passed, including real localhost launcher/fake-Ollama
and disconnect cancellation. Frontend regression tests/build/lint and Python ruff checks pass.
No authenticated DeepSeek or live Ollama generation was attempted; credentials, installed model
capabilities and actual inference/translation latency require testing on the user's setup.
The user's pre-existing AGENTS/AGENTS.md edit has three Markdown trailing-space warnings;
implementation diff checking excludes that file and does not alter the user's instructions.
