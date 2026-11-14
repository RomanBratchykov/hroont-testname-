# Server and orchestrator — design interview

Status: draft. Confirmed behavior below is separated from pending decisions. No backend implementation or deployment is authorized by this document alone.

## Related specifications

- `MODEL_PROVIDER.md`: current DeepSeek-first direction and replaceable-provider requirements.
- `LOCAL_MODEL.md`: historical interview decisions; local deployment assumptions are superseded.
- `AgroResilience_Farmer_Questionnaire.md`: adopted farmer context specification.
- `AgroResilience_External_API_Data.md`: external-data requirements to reconcile with available tools.
- `TRAINING_VAST_AI.md`: separate pre-production training; no production trainer.

## Confirmed boundaries

- MVP is showcased/tested only on the user's PC via localhost. Run application services and storage locally; no hosting, public exposure or Cloudflare setup is required. DeepSeek inference uses outbound API access.
- DeepSeek Flash (`deepseek-flash`) is the primary and only required MVP provider. Total API funds are $5: $3 for tests and $2 reserved for the demo. Budget checks precede each API request; reserve estimated maximum costs for concurrent in-flight requests. No GPU training, local inference service or provider failover is required.
- Application data remains authoritative in local server storage. Parse files locally; send DeepSeek relevant analysis excerpts/messages and tool results, excluding account details. Keep exact geometry local unless analysis requires it. Detailed payload/redaction implementation remains pending.
- LangChain orchestrates approved existing scripts and automatic authorized history retrieval. The model may not write or modify code. Initial scope remains intake, extraction, approved-script analysis and explanations; recommendations remain deferred.
- Maximum four users actively processed at once; the old two-run cap is superseded. Queue additional work and show high-load notices. This is not a four-account or four-browser-session limit. Per-user API concurrency, scientific-worker capacity, thresholds and fairness remain pending.
- Main local RAG knowledge base: Kharkiv Oblast datasets. Scripts also create location-specific retrieval data from API responses. Keep sources and geographic/temporal scope explicit; indexing does not validate regional scientific applicability. All numerical work runs in server scripts. Confirmed dual storage: raw API responses and normalized measurements for calculation, plus searchable passages/metadata for RAG, linked by provenance. Indexing and refresh details remain open.
- Confirmed retrieval: combine local keyword search with CPU-only embeddings and location/date filters. DeepSeek may request additional searches through approved tools; retrieval budgets and ranking details remain open. No GPU is required for the selected embedding direction.
- Save submitted messages to the server database before inference, including queued messages. Retain full conversations. Separate raw history, structured current state and compact inference context.
- New corrections supersede old values. Older jobs must not overwrite newer facts. Distinct fields are retained; clarify ambiguous changes.
- Background intake validates standard-format input and preserves conforming values; approved tools prepare other input. Publish profile updates only when ready.
- English RAG content and assistant answers. Translate incoming Cyrillic text to English with a Python-based script before DeepSeek; engine, validation and failure handling remain open. Markdown, TXT, JSON and Excel required; unsupported formats receive a clear rejection. Exact format variants/limits remain open.
- Localhost demo uses predefined database users; operators are administrators acting as farmers. Public registration is superseded for MVP. Personalization/isolation remains required. Consent handling for demo data and any future real farmer data needs reconciliation with the earlier registration-terms requirement; optional training consent is not implied.
- Auto mode defaults to fast for simple questions and thinking for harder ones; explicit Thinking selection warns of longer waits.
- First-writing targets: 1–1.5 seconds for small questions and 4–8 seconds for larger ones, subject to actual hardware/load validation. Largest tasks may take longer. Notify users of heavy load/possible slower output.
- Missing evidence triggers a specific explanation and reformulation/raw-data request, followed by filtering and a renewed sufficiency check.
- MVP internal failures produce an honest problem notice and direct users to support; the support destination is not supplied yet.
- No training or GPU rental is required for the DeepSeek deployment. The Vast.ai runbook is optional historical material for a future local provider. No live training flag/loop belongs in the serving orchestrator.

## Confirmed additional direction

- All backend, orchestration, scripts and data belong in this repository; actual tool/data inputs still need discovery or supply. Repository residence does not imply committing private data, secrets or indexes.
- Accept other locations and warn that location-data acquisition, organization and analysis can be lengthy.
- Idle users release slots; users can stop processing. Accepted work must be saved/restored after restart. Exact queue fairness, cancellation/recovery and the ambiguous slot statement remain open.
- If DeepSeek is unavailable, notify and wait; prolonged unavailability prompts trying later. Flash handles both modes.

## Current interview frontier — pending user decisions

39. Geographic validity: Kharkiv is the main RAG region; location-specific API retrieval is also required. Which analyses may run outside Kharkiv? Recommendation: accept locations broadly but gate scientific outputs on applicable data/methods; do not apply Kharkiv-specific assumptions elsewhere automatically.
40. Retention/deletion: keep full history until the farmer deletes it/account, or enforce automatic expiry? Recommendation: retain until deletion for MVP, with a defined active-data deletion and backup-expiry policy. No particular retention duration has been approved.
41. Host restart recovery: automatically resume accepted unanswered requests after a restart, or wait for users to retry? Recommendation: restore durable queued work; recover interrupted work from a safe checkpoint/known state, preventing duplicate writes and marking partial answers interrupted.
42. Queue fairness under configurable concurrency: how should work be shared among users? Recommendation: fair arrival-order scheduling, one active turn per conversation, and per-user limits under contention. Exact admission limits remain open.

## Engineering details still to specify

- DeepSeek Flash API/protocol selection, replaceable provider contracts, context/output/reasoning budgets, API spending controls and bounded Auto routing. Local runtime/artifact selection is deferred.
- Database/schema, authentication and session lifecycle, ownership checks, transaction/idempotency strategy.
- Message streaming, reconnect, cancellation, queue limits, restart recovery and failed-job states.
- Tool catalog/source paths, typed contracts, execution permissions, failure and execution limits.
- Upload parsers/size limits, profile/field revisions, compaction/retrieval rules, and consent records.
- Backup/restore, logs/metrics, support reference IDs, environment configuration and startup/shutdown.
- Measurable acceptance tests for correctness, data isolation, provider compatibility, API cost limits and concurrent-user latency.

Routine engineering choices may be proposed as defaults. Do not present unapproved product policies or untested performance as settled.
