# AgroResilience — interview handoff

Saved 2026-11-14 at the user's request to continue later. Resume the interview; do not assume pending recommendations are approved. No backend, translation, RAG or provider implementation has been performed during this session. No paid API calls, deployment, GPU rental or training were performed.

## Read first

1. This file for resume state.
2. MODEL_PROVIDER.md for current architecture direction and answer qualifications.
3. SERVER.md for server requirements.
4. LOCAL_MODEL.md for historical product decisions only. Local Qwen deployment assumptions are superseded; TRAINING_VAST_AI.md is an optional archived runbook.
5. Farmer questionnaire, external API specification and scientific specification for domain requirements. Historical Kherson pilot examples do not establish Kharkiv evidence.

## Confirmed direction

- Localhost demonstration/testing only on the user's PC, without hosting or Cloudflare. DeepSeek needs outbound internet.
- DeepSeek Flash, configurable provider boundary for future replacement, no second provider/failover required for MVP.
- Initial scope: intake, extraction, approved script execution and grounded explanations. Recommendations remain deferred. All numeric work runs in deterministic local server scripts.
- Total $5 budget: $3 testing and $2 reserved for demo. Check/reserve estimated request cost before dispatch, including concurrent work.
- Four users actively processed at once; additional work queues. Idle-slot wording needs clarification below.
- All backend, orchestrator, scripts and data should live in this repo. Datasets will be accessible on the PC, but actual dataset/script paths and contracts have not been supplied. Application-owned backend/tool scripts were not found in the reviewed checkout. Do not invent existing capabilities.
- Main RAG knowledge base: Kharkiv Oblast. Scripts also collect API data and build location-specific retrieval data. Other locations are accepted with a notice that preparation/analysis can take a long time; scientific applicability still needs gating.
- Both structured/raw API data for calculations and searchable passages/metadata for retrieval, linked by provenance.
- Combined local keyword retrieval and CPU embeddings with location/date filters. DeepSeek can request further searches through approved tools. No GPU needed for embedding direction; exact model and implementation remain open.
- English RAG content and answers. Superseding intake clarification: Python-based scripts translate incoming Cyrillic before DeepSeek. Engine, external-service permission, original retention and validation are unresolved.
- DeepSeek receives relevant English analysis information only; exclude account details and keep exact geometry local unless needed for analysis.
- Predefined users in the DB; operators are administrators acting as farmers. No public registration required for this demo. Personalization and private data isolation remain required.
- Save and restore accepted work after restart; users can stop processing. Detailed recovery/cancellation policy remains open.
- If API access is unavailable, notify and wait; prolonged unavailability should prompt trying later. Exact timeout and credential-error behavior are open.
- Flash for both thinking/non-thinking. Bounded loops and caching were accepted; exact numeric loop limits await explicit confirmation.
- Preserve earlier durable-history, latest-correction-wins, structured Personal state, approved-tools-only and no-arbitrary-code boundaries.

## Interview instructions and ambiguities

- The user requested 20 questions per turn after Q13. Continue with numbered questions and recommendations; user may approve a batch with exceptions.
- An earlier 'as you said' was explicitly corrected to approve Q7 only. Never treat it as acceptance of that entire earlier batch.
- Q10 was reused for RAG authority; its approval does not approve the older administrator-role proposal. Later answers separately establish administrators acting as farmers.
- The last answer batch was not fully numbered. 'Only after they are filtered', 'no, all info is personalised', and final 'as recommended' do not unambiguously settle evidence precedence, public-reference reuse, uploads and retention.
- Idle users release slots, but another sentence says an answered conversation still takes a queue/slot. Resolve Q34 instead of silently choosing.
- Q34–Q53 below have been asked but not answered. The user's next message was to save everything and return later. Do not ask the entire batch again automatically; identify it as the saved pending round and continue from their answers.

## Pending round — Q34–Q53

34. Slot release: release after an answer or retain until another event? Recommendation: release processing capacity after answering, retaining conversation/history.
35. Queue fairness: can one user submit several jobs while others wait? Recommendation: one active turn per user, arrival order among waiting users.
36. Load notice: show whenever waiting for capacity? Recommendation: yes, with status/cancel, without an unmeasured time estimate.
37. Interrupted paid calls: automatically rerun after restart? Recommendation: restore queued work automatically; ask before repeating paid calls with uncertain completion.
38. Outage wait duration? Recommendation: two minutes, then preserve the request and offer manual retry.
39. Invalid credentials/access denial? Recommendation: stop immediately with an administrator configuration error; wait only for temporary outages.
40. Translation may use an external service? Recommendation: prefer CPU-local translation; choose library/model after hardware/language review.
41. Retain original Cyrillic with English translation? Recommendation: yes locally, linked; send English only to DeepSeek.
42. Translate Cyrillic across messages/documents/spreadsheet cells/API text? Recommendation: yes, preserving numbers, units, dates, coordinates, identifiers and formulas.
43. Uncertain technical translation? Recommendation: flag and clarify before calculation.
44. Non-English text in other scripts? Recommendation: language detection, translate supported languages and clearly reject unsupported ones.
45. Meaning of filtering: validate/clean incoming evidence before calculation or RAG publication? Recommendation: yes, retain originals and transformation records.
46. Conflicting evidence after filtering? Recommendation: preserve both, prefer applicable validated field measurements, flag unresolved conflict.
47. Share approved public Kharkiv reference documents across personalized workspaces? Recommendation: yes; private farmer data stays isolated.
48. Cross-admin farmer-data visibility? Recommendation: isolate farmer workspaces; configuration access alone does not expose private data.
49. Shared RAG publication approval? Recommendation: administrator approval after filtering/provenance/indexing checks.
50. Git tracking? Recommendation: ignore private data, DB files, uploads, generated indexes and secrets inside repo; track code/schemas/small public fixtures.
51. Upload policy confirmation? Recommendation: .md/.txt/.json/.xlsx, 10 MB/file plus parsed-size limits; reject macros and legacy .xls.
52. Retention confirmation? Recommendation: until deletion/reset, including deletion of associated private retrieval entries.
53. Loop limits confirmation? Recommendation: six model calls and ten tool executions per turn, configurable, with supported partial findings and an explanation on exhaustion.

## Other work still required after this round

Inspect actual datasets/tools; settle translation and embedding implementations, retrieval tests/chunking/ranking, schemas and worker/resource facts, context/retrieval budgets, geographic validity, demo consent, diagnostic/support UX, startup/backup and acceptance criteria. Complete the design discussion and get shared-understanding confirmation before implementation. Preserve user authorization over skill defaults; do not deploy or incur paid calls merely to continue the interview.

## Workspace state

Documentation edits are saved but uncommitted: LOCAL_MODEL.md, SERVER.md, TRAINING_VAST_AI.md; new MODEL_PROVIDER.md and this handoff. No code changes made. `git diff --check` passed before the final handoff, and should be rerun after handoff edits. Do not commit unless requested.
