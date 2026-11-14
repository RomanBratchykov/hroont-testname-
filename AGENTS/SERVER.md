# Server and orchestrator — design interview

Status: draft. Confirmed behavior below is separated from pending decisions. No backend implementation or deployment is authorized by this document alone.

## Related specifications

- `LOCAL_MODEL.md`: model/interview decisions and their history.
- `AgroResilience_Farmer_Questionnaire.md`: adopted farmer context specification.
- `AgroResilience_External_API_Data.md`: external-data requirements to reconcile with available tools.
- `TRAINING_VAST_AI.md`: separate pre-production training; no production trainer.

## Confirmed boundaries

- The user manages Cloudflare configuration. Later deployment must unify the frontend, API, persistence, queue, orchestration, tools, and model serving through configurable service boundaries. Do not change Cloudflare or expose services during this interview.
- The user's PC hosts inference; GPU is an NVIDIA RTX 3050 with 6 GB. Serving runtime, host OS and RAM still require discovery/confirmation.
- LangChain orchestrates approved existing scripts and automatic authorized history retrieval. The model may not write or modify code.
- At most two active model runs; additional requests queue. Idle conversations release their slot. GPU background extraction/compaction shares this capacity.
- Save submitted messages to the server database before inference, including queued messages. Retain full conversations. Separate raw history, structured current state and compact inference context.
- New corrections supersede old values. Older jobs must not overwrite newer facts. Distinct fields are retained; clarify ambiguous changes.
- Background intake validates standard-format input and preserves conforming values; approved tools prepare other input. Publish profile updates only when ready.
- English initially. Markdown, TXT, JSON and Excel required; unsupported formats receive a clear rejection. Exact format variants/limits remain open.
- Registered accounts required. Required terms acceptance at registration precedes farmer-data intake. Training permission is separate and optional.
- Auto mode defaults to fast for simple questions and thinking for harder ones; explicit Thinking selection warns of longer waits.
- First-writing targets: 1–1.5 seconds for small questions and 4–8 seconds for larger ones, subject to actual hardware/load validation. Largest tasks may take longer. Notify users of heavy load/possible slower output.
- Missing evidence triggers a specific explanation and reformulation/raw-data request, followed by filtering and a renewed sufficiency check.
- MVP internal failures produce an honest problem notice and direct users to support; the support destination is not supplied yet.
- Training occurs separately on a rented RTX 4090 before production. No live training flag/loop in the serving orchestrator.

## Current interview frontier — pending user decisions

39. Geographic scope: Kherson-only intake, or broader intake with analysis explicitly limited to supported regions? Recommendation: accept profiles broadly, but apply geographic gates to scientific tools/results; do not imply regional validity outside reviewed coverage.
40. Retention/deletion: keep full history until the farmer deletes it/account, or enforce automatic expiry? Recommendation: retain until deletion for MVP, with a defined active-data deletion and backup-expiry policy. No particular retention duration has been approved.
41. Host restart recovery: automatically resume accepted unanswered requests after a restart, or wait for users to retry? Recommendation: restore durable queued work; recover interrupted work from a safe checkpoint/known state, preventing duplicate writes and marking partial answers interrupted.
42. Queue fairness: strict arrival order with one active run per user while other users wait, or allow one user to occupy both slots? Recommendation: fair arrival-order scheduling, per-user exclusivity under contention; use a second slot for that user only if no other users wait.

## Engineering details still to specify

- Runtime/artifact selection, context/output/reasoning budgets and bounded Auto routing.
- Database/schema, authentication and session lifecycle, ownership checks, transaction/idempotency strategy.
- Message streaming, reconnect, cancellation, queue limits, restart recovery and failed-job states.
- Tool catalog/source paths, typed contracts, execution permissions, failure and execution limits.
- Upload parsers/size limits, profile/field revisions, compaction/retrieval rules, and consent records.
- Backup/restore, logs/metrics, support reference IDs, environment configuration and startup/shutdown.
- Measurable acceptance tests for correctness, data isolation, resource fit and two-run latency.

Routine engineering choices may be proposed as defaults. Do not present unapproved product policies or untested performance as settled.
