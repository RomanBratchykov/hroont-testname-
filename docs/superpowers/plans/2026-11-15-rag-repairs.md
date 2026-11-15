# RAG Integration Repairs Implementation Plan

> For agentic workers: use superpowers:executing-plans; independent domains may use superpowers:dispatching-parallel-agents.

**Goal:** Make Croptato retrieval work with its main Ollama and cloud DeepSeek provider paths, with populated local stores, truthful availability, filters and reproducible tests.

**Architecture:** Keep one localhost retrieval service (/retrieve and /health), local PostgreSQL and Qdrant, CPU embeddings, and the main backend as the only model/budget/session authority. Retrieval is not scientific calculation. Keep supplied archives under RAG/rag/data unless an explicit data directory is configured.

**Tech Stack:** FastAPI, SQLAlchemy/PostgreSQL, Qdrant, sentence-transformers CPU, httpx, pytest.

**Spec:** AGENTS/AGENTS.md, AGENTS/AgroResilience_External_API_Data.md, current user instruction to fix all issues from the RAG audit.

## Constraints
- Never manufacture API keys, paid-call rates, scientific results or region applicability.
- Preserve data and unrelated changes; no database resets or automatic table replacement.
- Bind database and retrieval listeners to localhost; source credentials stay private.
- No paid inference for verification. Keep supported local/cloud provider wire tests offline.
- No commits or unrequested branch/worktree changes in this shared active workspace.

## Review focus
- Unreachable/empty stores must differ from a healthy query with no matching evidence.
- Region/date filters must not silently return another region's or year's rows.
- Ingestion must use actual archives, preserve source metadata, avoid duplicate vectors and resume partial ingestion.
- Custom model endpoints must not bypass paid-call budgets or silently change explicit thinking choices.
- Service failures/reboots must not silently advertise retrieval/scientific analysis readiness.

## Task 1: Retrieval contracts and filtering
- [x] Add failing tests for region/year filters and unavailable sources.
- [x] Modify RAG/app/db.py, qdrant_service.py and main.py: structured optional filters, bounded queries, metadata-aware retrieval, source status, truthful /health and /retrieve; main model endpoints must delegate or explicitly direct callers to the main backend rather than bypass provider controls.
- [x] Keep legacy read-only helpers compatible where safe; CPU embedding model and size must match ingestion.
- [x] Run focused RAG retrieval tests.

## Task 2: Main backend integration
- [x] Add failing tests proving both Ollama and cloud DeepSeek receive retrieval evidence and failure states.
- [x] Modify backend/tools.py, orchestrator.py, api.py, config.py, providers.py as needed: runtime health vs configured status, propagate filters and failures, no scientific-calculation claims for retrieval, budget enforcement for remote custom endpoints, preserve requested reasoning.
- [x] Run backend tests with no real model calls.

## Task 3: Ingestion and startup
- [x] Add failing tests for real data path, safe resumable/idempotent ingestion, startup failure and configured port checks.
- [x] Modify scripts/run.py, RAG/scripts/ingest_data.py, RAG/docker-compose.yml, dependency setup/config examples: actual archives, bounded safe extraction, per-source provenance, deterministic vector IDs, no silent partial import; CPU dependencies and local bindings.
- [x] Keep ordinary app startup available while lengthy indexing runs separately with visible status.
- [x] Run focused ingestion/launcher tests.

## Task 4: Local runtime and final verification
- [x] Install required dependencies and database/container runtime with tool approval where required.
- [x] Start local PostgreSQL/Qdrant, ingest supplied data, load CPU embedder, run real retrieval without model calls.
- [x] Run full application+RAG tests, lint, frontend checks; inspect diffs and perform a fresh review.
- [x] Restart Croptato with working retrieval and verify /health, source counts, actual filtered retrieval, and boot configuration.
- [x] Report any credential-dependent live DeepSeek verification as unverified; no invented success.

## Final verification

- 87 backend/RAG regression tests passed; frontend build, lint and tests passed; Ruff and pip dependency checks passed.
- Live retrieval is available: 151 SQL tables, 310 searchable chunks, verified CPU embeddings (384 dimensions).
- Real Kherson and United Kingdom region/year queries succeed; an unrepresented region returns no matches instead of unrelated data.
- Croptato, native PostgreSQL and native Qdrant user services are active and enabled at boot. The portable startup installer renders machine-specific paths instead of tracking this PC’s unit files.
- Unspecified launches default to hosted DeepSeek. The active site has an explicit Ollama override while the private DeepSeek key/rates remain unconfigured. No paid model calls were made; cloud provider integration was tested with mocked HTTP responses.
- New laptop setup uses root requirements, CPU embeddings, runtime/prerequisite checks and platform run scripts. Only Linux was physically verified; Windows/macOS branches require testing on those machines.
