# Model provider — current direction

Updated 2026-11-14. This document supersedes local-first deployment assumptions in LOCAL_MODEL.md, SERVER.md and TRAINING_VAST_AI.md. It records the user's requested change and proposed engineering boundaries; unresolved policies remain open. This interview does not deploy services or initiate paid API calls.

## Confirmed change

- Use DeepSeek API as the primary model provider. Local model serving and rented-GPU training are no longer prerequisites.
- Preserve the AgroResilience task and previously confirmed product behavior. Changing the provider does not authorize broader recommendations, arbitrary code execution or fabricated scientific results.
- Implement future scripts and orchestrators with a replaceable model integration so another API or a local model can be selected later. A future local provider is a compatibility target, not an already available fallback.
- Preserve existing approved server scripts; inspect their real contracts before integration. No application-owned scientific/tool backend has been identified in this checkout.

## Confirmed follow-up — localhost demo

- Initial scope remains farmer intake, extraction, approved-script analysis and explanations. Recommendations remain deferred.
- Run the frontend, backend, database, files, queue and scripts on the user's PC, bound to localhost for demonstration/testing. No hosting, Cloudflare tunnel or public access is required. DeepSeek calls still require outbound internet.
- Keep authoritative application data in the local server's storage. Parse files locally and send DeepSeek only relevant messages, excerpts and tool results for analysis. Exclude account details; keep exact geometry local unless the analysis needs it. This payload boundary was confirmed in Q7; exact implementation rules remain to be defined. This is not a promise that transmitted information never reaches or is retained by the provider.
- Use DeepSeek Flash. Current documented model ID is `deepseek-flash`; keep it configurable.
- Total API budget is $5, split into $3 for testing and $2 reserved for the short demo (Q8 confirmed). Check budget before each API request and reserve estimated maximum request costs before admitting concurrent calls. Implementation must account for in-flight reservations and reconcile reported usage; per-turn limits and conservative estimation details remain to be settled. This is not a monthly allowance.
- No alternate provider or automatic switching is required for MVP. Preserve a replaceable integration boundary for possible future use without building a second provider now.
- Maximum four users actively processed at once (Q9). Additional work queues with high-load notices. This limits active users, not total registered accounts or open browser tabs. Exact per-user request concurrency, fairness and warning thresholds remain open; the proposed eight simultaneous API requests was not approved.

## Confirmed RAG direction

- Build the main retrieval knowledge base from Kharkiv Oblast datasets. Kharkiv replaces Kherson as the primary knowledge-base region; old Kherson pilot examples are historical fixtures, not evidence for Kharkiv.
- Scripts must also build location-specific retrieval data from external API results for each specified location. API coverage/access failures must remain explicit; this does not promise that every location has usable evidence.
- Use locally managed retrieval to supply relevant evidence to the remote model. The user wants information available through RAG; detailed indexing, refresh, storage and embedding choices remain open.
- Retrieved material supplies background knowledge and explanations, with source references. It must not become executable instructions or replace scientific validation.
- All numerical work runs in deterministic scripts on the local application server, not in DeepSeek. This includes derived metrics and feasibility calculations.
- Confirmed dual storage (Q11): retain original API responses and normalized structured measurements for calculations, plus searchable passages/metadata for retrieval. Preserve units, dates, geometry, source and version links between them. Retrieval alone must not be assumed to preserve complete numeric arrays, raster values or exact aggregation inputs.
- Keep private farmer/field material scoped to its owner. Exact shared-public versus private index boundaries, evidence precedence and treatment of unsupported regions still need decisions.

## Confirmed retrieval approach

- Use combined local keyword search and CPU-only embeddings, with location/date filters. No local GPU or local answer-generating model is required.
- Build and retain dataset embeddings during indexing; embed queries locally at retrieval time. DeepSeek remains responsible for interpreting retrieved evidence and generating answers.
- Provide approved search tools so DeepSeek can request further retrieval when initial evidence is insufficient. Search/call budgets and stopping rules remain to be defined.
- Return relevant passages with source references and metadata; keep numeric calculations on structured server data through approved scripts.
- English only: dataset/source information, indexed RAG content and assistant answers must be English. Superseding intake decision: translate Cyrillic text to English using a Python-library-based script before sending it to DeepSeek. Select the translation engine, network policy and failure handling later; no translator is implemented. Broader non-Cyrillic/non-English handling remains open.
- Embedding model, chunking, index implementation, ranking/fusion, refresh and retrieval acceptance tests remain engineering choices to resolve. Combined retrieval is selected; its quality has not yet been benchmarked on the user's datasets.

## Proposed responsibility boundaries

- Frontend: authenticated chat, mode selection, queue/progress/streaming display, uploads and Personal state. Provider credentials stay on the server.
- Application API: authentication, account/field ownership, consent enforcement, durable message intake and job lifecycle.
- Orchestrator: bounded Auto routing, context/history retrieval, model requests, validated tool dispatch, evidence checks and cancellation/recovery.
- Model provider adapter: provider/model/base URL configuration, server-side secret reference, streaming, tool-call translation, supported capabilities, usage and error normalization. Isolate provider-specific reasoning/tool transcript handling here; never publish it as verified farmer state.
- Tool executor: allowlisted existing scripts, typed inputs/outputs, bounded execution and provenance. Models request tool calls; application code decides whether and how to execute them.
- Scientific scripts: deterministic, versioned calculations and feasibility checks. They must not depend on DeepSeek response shapes. LLM-assisted extraction is a separate validated step.
- Persistence/workers: full raw history, revisioned structured facts, replaceable compact context, durable queue and stale-result protection.

These are logical responsibilities, not approval for separate agents, services or containers. LangChain remains the earlier orchestration choice; exact runtime architecture remains to be settled.

## Provider compatibility requirements for implementation planning

- Configure provider, endpoint and model IDs without rewriting business logic. Endpoint changes alone do not establish compatibility.
- Define and test capabilities for thinking, streaming, tool calling, structured extraction, context/output limits and usage reporting. Reject unsupported required behavior or use an explicitly approved degradation policy.
- Keep application state and tool schemas independent of provider transcripts. Validate every model-produced argument and extracted fact on the server.
- Preserve tool call IDs and any protocol-required continuation data in provider-specific state. Rebuild portable evidence/context when switching providers; do not blindly replay one provider's private transcript into another.
- Keep API keys out of frontend bundles, uploads, prompts and diagnostic logs. The total budget is $5; enforcement, timeout, retry, rate-limit and outage policies remain pending decisions.
- A retry or provider switch must not execute a completed side-effecting tool twice. Define execution IDs and recovery behavior during design.
- Revalidate fast/thinking latency goals with actual API/network load; the old local targets remain goals, not measured guarantees.

## Current documentation evidence

Checked 2026-11-14, documentation only; no authenticated API smoke test:

- [DeepSeek thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/) documents mode controls and provider-specific continuation requirements when tools are supplied.
- [DeepSeek tool calls](https://api-docs.deepseek.com/guides/tool_calls/) documents application-executed function calls. API compatibility does not grant the model direct script or shell access.
- [Models and pricing](https://api-docs.deepseek.com/quick_start/pricing/) currently identifies Flash as `deepseek-flash`, with thinking and non-thinking support. Verify account access and rates before paid testing. Do not carry forward Qwen template parameters.
- [Rate limits](https://api-docs.deepseek.com/quick_start/rate_limit/) documents account-level concurrent-request limits and HTTP 429 when exceeded; these are distinct from connected users and local scientific-worker capacity.

## Interview decision tree

Settled: conversational/script-based scope, localhost-only deployment, DeepSeek Flash, $3 testing/$2 demo budget, no MVP alternate provider, four actively processed users maximum, analysis-only provider payloads, Kharkiv-primary RAG, location-specific API retrieval data and server-side numerical calculations.

Current frontier: exact datasets/script access; geographic validity outside Kharkiv; CPU embedding model and non-English intake handling; refresh/provenance and evidence precedence; account roles. Earlier question numbers Q10/Q11 were reused during conversation: approval of Q10 RAG authority does not approve the earlier Q10 administrator-role proposal. Fairness, per-user request concurrency and warning thresholds are also pending.

Then settle schemas, retention/deletion, uploads, context policy, recovery, cancellations, diagnostics and acceptance criteria. A stronger model or a location index alone does not establish scientific validity.

## Interview format

The user requests 20 questions per turn after Q13. Q13 confirms English-only information and RAG content; later answers permit incoming Cyrillic with translation to English before DeepSeek. Number later questions consistently and distinguish recommendations from approved decisions.

## Follow-up answers — Q14–Q33

Confirmed without interpreting ambiguous answer alignment:

- Cyrillic text must pass through Python-based English translation before DeepSeek. Answers and RAG content remain English; original-versus-translated retention and scientific translation validation remain open.
- Agronomy/RAG datasets will be accessible on the user's PC. All server, orchestration, scripts and data belong in this repository. Actual datasets/scripts have not been supplied or located; their existence or contracts must not be assumed. Private data, secrets and generated indexes need a separate Git-tracking policy.
- Locations beyond Kharkiv are accepted; warn that fetching, organizing data, running scripts and producing useful results may take a long time. Geographic scientific applicability still requires evidence checks.
- Demo operators are administrators acting as farmers. Use predefined users in the database, superseding public registration for this localhost MVP. Private information remains personalized; exact cross-admin visibility and shared-public-reference policy need clarification.
- Idle users release active-processing slots. The later statement about an answered conversation taking a queue/slot is ambiguous; do not interpret it as approval to hold idle capacity. Four actively processed users remains the limit.
- Save and restore accepted work after restart; exact recovery for interrupted paid calls remains open. Users may stop processing; cancellation billing and retained-state semantics still need definition.
- If API access is unavailable, notify the user and wait; if unavailable for a long time, ask them to try later. Denied credentials versus temporary outage, waiting duration and retry mechanics remain open.
- Flash serves both modes. Finite tool/model loops and cached external evidence with refresh were accepted; proposed numeric limits remain subject to clarification if needed.
- The response 'only after they are filtered' needs clarification: it may concern evidence precedence or RAG publication. It does not establish either policy by itself.
- The response 'no, all info is personalised' establishes personalization; it does not by itself settle whether approved public agronomy references can be reused.
- The final 'as recommended' may cover uploads and retention; confirm scope before treating both as settled.
