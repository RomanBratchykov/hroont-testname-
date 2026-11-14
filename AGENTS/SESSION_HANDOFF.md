# AgroResilience — session handoff

## Latest implementation state

User explicitly authorized the server/orchestrator foundation, with datasets and scientific
scripts supplied later, plus selectable DeepSeek/Ollama, two endpoints, unified launcher and
easy run instructions. Implemented in `backend/`, `scripts/run.py`, `run.sh` and the existing
frontend; see root `README.md` and `docs/orchestrator-plan.md`.

- `GET /api/health` and `POST /api/chat`; shared orchestration, explicit provider selection,
  no automatic fallback. Bounded model/tool loops, four active turns, one active turn per chat.
- SQLite for the standalone localhost test; one clearly labeled demo administrator workspace.
  Preview login is not authentication; PostgreSQL/domain accounts remain future work.
- Durable history, cancellation without automatic replay, last-chat-activity 30-day retention,
  consistent chat deletion, conservative persisted DeepSeek testing/demo spending reservations.
- Local bounded text/JSON/XLSX extraction, local language screening, optional configured
  LibreTranslate-compatible translation, top mascot status and hide-notice setting.
- History and capability tools implemented using LangChain structured tools. Scientific
  tools/datasets, embeddings/RAG, validated structured profile extraction and visual analytics
  are explicitly deferred; do not invent their results.
- Short ambiguous Latin text is treated as English; language detection is heuristic.
  Translation needs an explicitly configured service; sub-second latency is not benchmarked.
- Offline backend tests (17), including real localhost fake-model launcher/disconnect tests,
  pass. No paid/live model generation, scientific API calls, hosting or commits performed.
- Existing user changes in AGENTS/AGENTS.md were preserved. Code and documentation are
  uncommitted. The older interview snapshot below is historical and superseded by this state.

## Original interview snapshot

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

### Resume answers received

Q55 display clarified by user: translation status belongs at the top of the interface beside the mascot. Provide a setting to turn off that translation status notice. Translation itself remains enabled; this is a processing-status UI requirement, not model internal reasoning display. This supersedes the tentative display interpretation below; no Q55 clarification remains pending.

Latest numbered follow-up answers:

- Q37 clarification approved: closing/refreshing the browser cancels unfinished processing immediately, without automatic resumption. Do not claim an already dispatched provider request can be unbilled or forcibly stopped; implementation needs best-effort cancellation and stale-result protection.
- Q41–Q44 recommendations approved: retain original Cyrillic linked to English locally; translate messages/documents/spreadsheet cells/API text while preserving numeric/scientific structure; clarify uncertain translations affecting calculations; detect languages, translate supported languages and clearly explain unsupported cases.
- Q54: automatic 30-day retention runs from last activity in each chat, with associated information deleted consistently. Explicit deletion remains available.
- Q55: under-one-second translation target applies to short chat messages; larger files may take longer. User adds: "transfer it to the thinking process, make settings ability to turn it off". Working interpretation: show translation/preparation progress in the thinking/processing UI, with a setting to hide that display, while keeping required translation enabled. This display interpretation is not explicit approval to expose model internal reasoning or to bypass English translation; clarify if user intended a different toggle.

Q34–Q55 now have answers, except exact Q55 toggle semantics if the working interpretation is disputed. Continue the remaining design interview from Q56; do not repeat the original pending batch. Actual translation engine, input sizes/latency measurement, accepted file limits, schemas, dataset/tool access, and scientific applicability remain unresolved.

Further answers mapped to Q45–Q53:

- Q45: "filtering" means organizing all required fields with their parameters. This supersedes the earlier interpretation as evidence cleaning/publication approval; exact required fields and parameter schemas must follow the AgroResilience domain documents.
- Q46: prioritize user-provided data when sources conflict. If personal assertions conflict with technical evidence, notify the user that their data may be wrong and ask whether to base the answer on their supplied data or NASA API evidence. Preserve source attribution and scientific qualifications; choosing user inputs does not validate them scientifically.
- Q47: approved public references may be shared across personalized workspaces.
- Q48: for MVP, administrators may see all chats. This supersedes the proposed administrator chat-isolation restriction; it does not establish wider public access.
- Q49: administrator approves shared RAG publication.
- Q50: track code; keep data hidden/excluded from Git. Do not assume permission to commit public dataset fixtures.
- Q51: read uploaded/pasted files locally before DeepSeek; extract raw text or convert to Markdown to reduce API costs. Specific accepted formats, size limits, and handling of unreadable/oversized files remain unconfirmed. Preserve scientific structure, units and provenance when parsing.
- Q52: user can delete chat history and clear all information; deletions must be consistent across associated state. Automatically delete after 30 days; starting point (creation versus inactivity) and precise scope need clarification.
- Q53: approve six model calls and ten tool executions per turn, configurable, with supported partial findings and explanation when exhausted.

Scope reminder from user: MVP needs working scripts, good data visualizers, good reasoning and scientific accuracy based on AGENTS/AgroResilience documents; avoid unnecessary commercial/product infrastructure.

Q37 clarification and Q41–Q44 remain unanswered. Q45–Q53 answers above supersede the original recommendations below. Translation input-size target and 30-day retention clock also remain to clarify.

Q34–Q36 and Q39 recommendations are approved: release processing slots after answers, one active turn per user with arrival-order fairness, show queue status/cancel, and stop immediately for invalid credentials/access denial.

Q37: user rejects the proposed uncertain-call recovery flow: "keep those out, if user restarts when answer is not finished, or close it just turn over immediately". Clarify whether closing/reloading the browser cancels the unfinished turn immediately and whether queued work also cancels; do not assume automatic resumption or paid-call replay.

Q38: wait 30 seconds for temporary API unavailability, then tell the user to manually restart or try later (supersedes two-minute recommendation).

Q40: prefer CPU-local translation if it can finish in under one second; otherwise investigate free external translation services to meet that target. No engine selected, service contacted, or latency guarantee established. Define the input size covered by this target before implementation.

Q41–Q53 remain unanswered. The numbered list below preserves the original questions/recommendations; the answers above supersede its Q34–Q40 proposals.

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
