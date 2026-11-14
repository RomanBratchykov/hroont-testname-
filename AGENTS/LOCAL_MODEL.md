# Model design — historical local-model interview

> Superseded deployment direction (2026-11-14): use DeepSeek API first, with a replaceable provider boundary and a possible future local-model adapter. See [MODEL_PROVIDER.md](MODEL_PROVIDER.md) for the current direction. Local Qwen inference, mandatory GPU training and GPU-specific scheduling below are historical decisions, not current deployment requirements. Other confirmed product behavior remains applicable unless explicitly revised.

Status: serving design interview with a separate pre-production training runbook. Production-time training is excluded. Some integration facts and implementation details remain open. This file records the discussion, not instructions to connect a backend.

## Source

`AgroResilience_Farmer_Questionnaire.md` is the user-designated source for collected farmer context. `AgroResilience_Technical_Scientific_Specification_v1.1.docx.md`, especially sections 3, 11, 13–18, and 20, supplies scientific requirements. `SERVER.md` consolidates server requirements and pending decisions.

## Requirements stated by the AgroResilience document

- Interview farmers adaptively; accept unknown answers and ask follow-up questions for missing critical inputs.
- Extract structured field, crop-history, soil, irrigation, management, preference, and consent information.
- Restrict the LLM to interview, extraction, and explanation. Numerical analysis and crop feasibility belong to deterministic, versioned scientific code.
- Preserve provenance, units, uncertainty, and explicit assumptions. Missing/uncomputed metrics remain null, never invented or replaced with zero.
- Ask for exact crop years before enforcing exact return intervals.
- Seek three differentiated strategies: Economic, Balanced, and Climate/Soil Resilience. If fewer than three feasible alternatives exist, explain and return fewer.
- Economic potential is only a proxy without verified farm economics; example strategies/scores are illustrative fixtures.
- Keep historical climate exposure distinct from yield predictions. RUSLE covers sheet/rill water erosion, not wind or gully erosion.
- The document includes a Kherson-only scope annotation; confirm its authority and enforcement during the interview.

These are document requirements, not yet a confirmed scope for the user's local model.

## Established session constraints

- The application remains frontend-only until backend work is explicitly authorized.
- Personal state is currently a placeholder for future interview data.
- This task is an interview and documentation exercise; do not start model integration yet.

## Confirmed user decisions — round 1

- Host inference on the user's PC and make the application accessible through the web.
- Resource budget: 6 GB VRAM. Chosen model family/size: Qwen3.5-4B.
- First version accepts messages, analyzes them, supports fast/thinking modes, and returns answers.
- Use LangChain-related orchestration to define stopping, requests for clarification, inability responses, saved conversation state, and context compaction.
- Priorities: fast responses, consistency, and resource fit.
- Agricultural recommendations are deferred until better domain preparation/training. Include a domain-training plan in the design.
- Longer-term product has two capabilities: (1) script-driven data analysis with dashboards/visuals for farmer interpretation, (2) model-proposed possible actions and assistance choosing a course of action.
- Tool execution is now limited to existing approved scripts; whether the model may independently rank actions remains unresolved. Preserve the scientific document's deterministic calculation/feasibility requirement unless an explicit redesign is agreed.

## Verified technical facts and limits

- Qwen's official model card says Qwen3.5-4B supports thinking and non-thinking operation. It thinks by default; non-thinking uses serving/chat-template parameters such as `enable_thinking=false`. Qwen3 `/think` and `/nothink` prompt switches are not officially supported for Qwen3.5.
- Rough weight-only arithmetic: 4 billion parameters at 16 bits require approximately 8 GB before runtime state. A quantized deployment is therefore the starting candidate for the 6 GB budget, not a guarantee that a particular configuration fits. Context, concurrent requests, runtime buffers, other GPU consumers, and any vision components must be measured.
- LangGraph checkpointers support per-thread resumable state; stores support cross-thread durable information. LangChain documents summarization and model/tool call limits. These mechanisms need an application policy; framework selection alone does not define correctness.
- `ollama` and `nvidia-smi` executables are available in the workspace environment. NVIDIA driver access failed here, so actual GPU model, usable VRAM, and throughput have not been independently verified. No runtime is selected solely from executable availability.

Sources checked:
- https://huggingface.co/Qwen/Qwen3.5-4B
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://docs.langchain.com/oss/python/langchain/short-term-memory
- https://docs.langchain.com/oss/python/langchain/middleware/built-in

## Confirmed user decisions — round 2

- The model may call existing approved scripts/tools only. It must not modify application code or generate/execute arbitrary replacement scripts. LangChain orchestrates the available tools.
- Scripts should clean, filter, and prepare data so the model receives understandable, relevant evidence rather than raw bulk data.
- Model work includes interpreting inputs, selecting available tools, understanding results, and asking concise, relevant follow-up questions.
- Small questions: target 1–1.5 seconds until writing starts; larger questions: 4–8 seconds until writing starts. These are first-writing latency targets, not full-completion deadlines. Largest tasks may take unrestricted time. Concurrency and warm/cold benchmark conditions remain unresolved.
- Users who explicitly request thinking should be told answers will take longer.
- Confirmed mode policy: Auto routing by default (simple → non-thinking; harder → thinking), with an explicit user Thinking override. Notify users who select Thinking that answers take longer.
- Durable memory must cover farmer capabilities/opportunities and the AgroResilience intake. Explicit additions requested: land amount, location, worker count, technology/machinery, and fertilizer resources.
- Ask the user about memory details not defined by the specification instead of silently inventing requirements.
- Recommendation functionality remains deferred.

## Memory coverage from the source specification

Persist these as structured facts with source, units/time period where relevant, and explicit unknown values; confirmation/correction rules remain pending:

- Field geometry/location, area, irrigation and reliable water availability.
- Crop history with calendar/harvest years and failed crops; included/excluded crops; planning horizon.
- Soil texture/type, test results, soil chemistry and physical constraints, slope/drainage context.
- Tillage, residue, erosion-control practices, observed erosion, fallow/cover crops, shelterbelts.
- Optional historic yields and farm economics (price/cost/currency/year/market access).
- Pests/diseases, farmer priorities, consent, and subsequent corrections/feedback.
- User-requested resource context: workers, available machinery/technology, fertilizer availability. Exact units, granularity, and farm-versus-field ownership are not specified yet.

Source conflict to resolve: AgroResilience section 1 excludes machinery and fertilizer purchasing capacity from MVP ranking. Collecting them as profile context is compatible; using them to rank strategies changes that scope. Do not infer that scope change from the request to remember them.

## Proposed implementation safeguards — not yet approved

- Evidence preparation reduces irrelevant context but does not guarantee absence of hallucinations. Validate extracted facts/tool arguments/results; retain unknowns; ask for missing inputs; keep scientific calculations in scripts.
- Distinguish an unsupported request, missing input, tool failure, and unavailable evidence. They need different responses rather than one generic refusal.
- Largest-task unlimited duration does not remove finite context/VRAM limits. Retry/call limits, cancellation, and stalled-loop handling need explicit policy.
- Do not persist generated reasoning as verified farmer facts. Keep structured state separate from a replaceable context summary.

## Confirmed user decisions — round 3

- Auto/default and explicit Thinking override are approved.
- Latency targets mean time until writing starts. Do not claim the entire answer completes within those budgets.
- Collect farmer context from `AgroResilience_Farmer_Questionnaire.md`. The user has adopted all questionnaire requirements/additions/refinements while preserving optional fields (round 4).
- When a question cannot be answered from available evidence, analyze the gap and state that the requested data/analysis is unavailable. Help reformulate the question or request additional raw information. Run approved filtering/preparation tools on new data, then reassess whether evidence covers the question before answering. Do not merely repeat a refusal or generate an unsupported conclusion.

## Evidence-gap workflow

1. Determine the requested outcome, needed evidence, and currently available evidence.
2. If evidence is insufficient or the task exceeds available capabilities, explain the specific limitation in concise language.
3. Offer a supported reformulation or ask for the raw information needed to proceed.
4. On receipt, use the existing approved filtering/cleaning tools and validate their outputs.
5. Recheck evidence sufficiency against the requested analysis. Answer only the supported scope; otherwise explain the remaining gap and ask a targeted follow-up.
6. Retain unknowns and source provenance. Retry/loop budgets remain undecided; new information does not automatically authorize indefinite tool retries.

## Adopted questionnaire and remaining schema details

- Q01–Q20 repeat the original intake and feedback fields.
- Q21–Q26 add machinery/services, per-hectare production budget, fertilizer practices, input-purchasing constraints, crop storage, and access/security/infrastructure constraints.
- Although additions/refinements remain labeled “Proposed” in the source, the user has adopted them for this design: soil knowledge optional, three crop-history years initially, eight-year comparison default, and consent before processing. Unknown remains valid; follow-ups depend on the information needed for the requested answer.
- The questionnaire explicitly separates consent from agronomic inputs and disallows inferring field security from satellite imagery.
- Worker count, requested earlier by the user, is absent from this questionnaire. Ask whether to retain it as an additional field rather than silently adding or dropping it.
- Any future use of Q21/Q22/Q24/Q26 for feasibility/ranking needs reconciliation with the older scientific MVP scope. Recommendation functionality remains deferred in this phase.

## Confirmed user decisions — round 4

- Adopt all questionnaire requirements/additions/refinements, preserving optional fields.
- If answers to required questions do not contain enough information for the requested final answer, ask additional targeted questions. Filling every form field does not establish evidence sufficiency.
- Farmer input should trigger background analysis/preparation. Save resulting information to Personal state when ready, in a clear, script-compatible representation.
- If input is already understandable and follows the scripts' standard format, validate it and preserve it as supplied rather than rewriting it through the model.
- Support several simultaneous sessions, accepting a reduction in token throughput.
- When output performance falls below a configurable threshold, notify the user of high load, retain the input, and pass it to the model when resources become available.
- Round 5 settles a two-active-run limit, immediate database persistence, overload notices, and correction precedence. Numeric throughput thresholds and precise scheduling/recovery rules remain open.
- Worker information remains requested from round 2; its exact field definition is still absent from the questionnaire.

## Background intake policy

The user has authorized this as a future capability, not a background job to start during this design interview.

- Capture incoming messages, validate standard-format input, and prepare nonstandard input with approved tools.
- Publish usable results to Personal state after checks complete; do not treat unfinished processing as verified profile data.
- Already conforming values remain unchanged after validation; provenance and job metadata may be stored alongside them.
- All submitted messages must be saved to the server database upon receipt, before model processing. Explicit newer corrections supersede older facts. Recovery, idempotency, and ambiguous-conflict details still need design.
- GPU-based extraction/compaction must be counted against the same finite inference resources as foreground answers; a background label does not imply free GPU capacity.

## Confirmed user decisions — round 5

- Maximum two simultaneous active model sessions/runs. The model must work on both; a third waits until one releases resources. Do not implement a third concurrent model run.
- Preserve acceptable response performance, with high-load/possible-slow-output notifications. The cap is a scheduling requirement, not a proven hardware-performance guarantee.
- Save every farmer message to the server database as soon as it is received, even if queued or not yet analyzed.
- Save clear farmer information to current Personal state; when the farmer corrects it, update that state. The final response must reflect the corrections/current submitted data.
- Older messages or older background-job results must never overwrite newer information.

## Proposed persistence and correction semantics

These implementation details express the confirmed behavior but still need final design review:

- Keep original messages as history; “resave” means update the current structured value, not silently rewrite the historical message.
- Assign server-side message sequence IDs and profile revisions. Validate writes against source order rather than background-job completion time.
- A correction such as “not 30” without a replacement invalidates the old value and triggers clarification; never invent a replacement number.
- A correction such as “35, not 30” makes 35 the current value after validation. Mark affected old analysis as stale and regenerate from the newer state before presenting it as current.
- Database acknowledgement precedes a “saved/queued” UI acknowledgement. If persistence fails, show a failure and permit safe retry rather than claim the message was saved.
- Raw queued messages and normalized profile values are distinct records; unprocessed input is not yet trusted structured state.
- Background GPU extraction/compaction shares the same two active-run capacity; non-GPU validation/persistence need not wait for inference capacity.
- Numeric high-load thresholds, queued-message cancellation, retry deduplication, queue fairness, and recovery after restart remain open.

## Confirmed user decisions — round 6

- Release the active model slot when a turn ends or the assistant waits for farmer input. Idle conversations do not retain inference capacity.
- Briefly acknowledge profile changes rather than repeat the whole profile in each response.
- If a farmer reports multiple fields, save that fact and retain distinct field contexts. Clarify the field/value to change when a requested update is ambiguous; never guess the target.
- English is the only initial language.
- English text chat and file input are required. Round 7 confirms Markdown, TXT, JSON and Excel; exact Excel variants, other formats, and size limits remain open. Unsupported types must be rejected clearly.

## Repository observations

A search for application-owned Python scripts, Python project/dependency manifests, and example CSV/GeoJSON/KML files found none in this checkout (excluding dependencies and the vendored assistant-ui source). The approved tool catalog and canonical script input/output schemas have not been located. Ask for their location or confirm that a separate tool-library implementation is needed; do not fabricate compatibility with a nonexistent schema.

## Confirmed user decisions — round 7

- Required upload formats include Markdown (`.md`), plain text (`.txt`), JSON, and Excel. The phrase “and all” is not an implementation promise of universal file support; additional formats need explicit parser support. Exact legacy/current Excel coverage and upload size limits remain implementation decisions to settle.
- If a format is unsupported, tell the user that this file type cannot be attached/processed. Do not accept it and pretend its contents were analyzed.
- Access is for registered users, with a server-side account database. Registration eligibility, identity mechanism, and ownership enforcement still need design.
- MVP internal/tool failures should produce a clear problem notice and direct the user to support. Do not manufacture an analysis result. A real support destination/contact and internal diagnostic policy are not yet supplied.
- The user subsequently confirmed the existing scripts are on the server. Their source path, catalog, and schemas have not been supplied or inspected; treat discovery of those contracts as a prerequisite for integration, not as a reason to invent new tools.

## Confirmed user decisions — round 8

- Approved existing scripts are on the server. No tool source or schema has been inspected from that server yet.
- The user's PC is the host, with Cloudflare providing web access. Exact Cloudflare setup and host OS/RAM/GPU model/runtime remain unverified. Do not infer that a public inference endpoint or any specific tunnel configuration is authorized.
- Save all conversations in the server database, in addition to the already-confirmed immediate persistence of submitted farmer messages. Do not discard full history during compaction.
- Message persistence is a backend responsibility independent of the model/GPU queue; asking the model to remember a message is not a substitute for a database commit.
- Retention of all conversations does not settle how much history belongs in each inference context. The user has not yet confirmed the proposed compaction policy.
- Consent timing is settled in round 9: explicit agreement to terms and conditions is required during registration before farmer-data intake/background processing.

## Confirmed user decisions — round 9

- Terms and conditions declare the consent for the application.
- Every user must explicitly state agreement during registration, before entering the farmer interview and background agricultural-data processing.
- This is a product requirement, not a legal assessment of the terms' adequacy.

## Proposed consent implementation details

- Require an affirmative, initially unchecked acceptance control linked to the terms; reject registration without acceptance on the server as well as in the UI.
- Store the accepted terms version and server-side acceptance timestamp with the account, rather than rely solely on a browser checkbox.
- Terms content, retention/deletion rules, and behavior after terms changes remain to be written/settled. Do not invent legal text or assume registration consent automatically permits using farmer conversations for model training.

## Confirmed user decisions — round 10

- Use relevant information in Qwen's normal inference context rather than automatically load every saved conversation on every turn.
- When asked, Qwen may access the full saved conversation history. The full records remain in the database; context compaction does not delete them.
- Training use requires separate optional permission, as recommended; refusing training permission does not block application access.

## Proposed history-access implementation

- Use an approved read-only history tool to retrieve original messages beyond the current compact context.
- Enforce account/session/field ownership server-side; access to full history means the requesting farmer's authorized history, never another farmer's messages.
- Page/chunk large histories to stay within the finite context budget, preserving message IDs, dates, and corrections. “Can access the whole history” does not mean all history must fit in a single model call.
- The user has approved automatic history lookup, orchestrated by LangChain (round 11). Account ownership and unambiguous field/conversation scope must still be enforced.

## Proposed training-permission implementation

- Separate optional, initially unchecked training opt-in from required registration terms acceptance.
- Record permission scope, version, and timestamp. Do not copy conversations into training datasets without this permission and the reviewed-data process.
- Permission withdrawal/deletion behavior, anonymization requirements, and the handling of existing datasets/adapters remain open product decisions; do not promise reversal of an already trained model's behavior without an explicit mechanism.

## Confirmed user decisions — round 11

- Automatic history lookup is approved and should be orchestrated by LangChain.
- Domain-training material will be supplied as datasets and generated by other agents.
- Earlier discussion proposed `training=1`; the user has now superseded it with separate rented-GPU training before production. Do not implement a production training flag/loop.
- Superseding decision: train on a rented Vast.ai RTX 4090 (24 GB). Serve on the user's NVIDIA RTX 3050 (6 GB). The user requested instructions; no rental, paid job, or external data upload has been executed.
- Provide training-time examples by dataset size, with assumptions and hardware uncertainty explicit.

## Training feasibility evidence — checked 2026-11-14

Source: https://unsloth.ai/docs/models/qwen3.5/fine-tune

- Unsloth's Qwen3.5-specific guide lists about 10 GB VRAM for 4B bf16 LoRA, and about 5 GB for 2B bf16 LoRA. These are documented recipe figures, not universal bounds or a benchmark of the user's GPU.
- The same guide advises against Qwen3.5 4-bit QLoRA because of quantization differences. Do not assume a generic low-VRAM QLoRA recipe solves this model's 6 GB training constraint without validation.
- Thus the documented 4B bf16 LoRA recipe exceeds the budget. Whether another constrained/offloaded configuration is workable remains an experiment, not an implementation promise.
- An inference artifact that fits in 6 GB does not establish that training fits. Training-plus-two-live-inference runs on this GPU is not a validated requirement we can promise to meet.

## Training workflow — pre-production only

Follow [TRAINING_VAST_AI.md](TRAINING_VAST_AI.md) for dataset preparation, renting/configuring a 24 GB RTX 4090, bf16 LoRA, pilot benchmarking, evaluation, quantized export, download, and local RTX 3050 tests.

- Remove production-time continuous training and `training=1` from the intended serving orchestrator. Production only loads approved, versioned inference artifacts.
- Train separately on reviewed dataset snapshots, evaluate candidates, then deliberately promote a release. Future updates repeat this offline process.
- Do not share the RTX 3050 between a production trainer and the two live model runs. No live-training scheduling feature is required.
- Generated datasets still need review and consent checks where applicable; separate optional training permission remains required for real farmer conversations.
- Store adapters, model/template revisions, dataset hashes, configuration and evaluation results; retain rollback artifacts.
- The runbook is documentation, not an executed GPU benchmark. No training data or rented instance is available in the workspace.

## Training-time calculation examples

Estimate training-loop time as:

`examples × average processed tokens/example × epochs ÷ measured training tokens/second`

Use processed input-plus-target tokens, not inference generation speed. Padding/packing, sequence length, checkpointing, offloading and hardware affect the measured rate. Add preprocessing, kernel compilation/warm-up, evaluation, checkpoint/export and deployment time separately.

Illustrative arithmetic only: 512 processed tokens/example, 3 epochs, assumed 25–100 training tokens/second. Neither that throughput range nor the 6 GB fit has been benchmarked:

| Examples | Processed token presentations | Illustrative training-loop time |
| --- | --- | --- |
| 100 | 153,600 | 26 minutes–1.7 hours |
| 1,000 | 1,536,000 | 4.3–17.1 hours |
| 10,000 | 15,360,000 | 42.7–170.7 hours |

Three epochs is a calculation assumption, not a chosen schedule. Obtain a real estimate from a feasible 50–100-step representative pilot after warm-up; do not turn these arithmetic examples into promised delivery times.

## Confirmed training deployment decision

- Q35–Q37's production-training scheduling and 6 GB training trade-offs are superseded: rented 4090 training occurs before production.
- Q38 is partially answered: local GPU is an NVIDIA RTX 3050 with 6 GB VRAM. System RAM, OS and installed inference runtime are still unverified.
- The user authorized creation of a Vast.ai training guide, not an agent purchase/rental or training run.

## Integration facts still needed later

- Server tool directory/catalog and input/output schemas; read-only access for inspection when integration work is authorized.
- Host system RAM, OS, model artifact/quantization, serving runtime, and usable RTX 3050 VRAM with the desktop running.
- Cloudflare access configuration, application authentication/session strategy, support destination, and persistence/backup settings.

## Proposed domain-training roadmap — not approved

1. Build a held-out evaluation set before tuning: agricultural scope, missing/contradictory inputs, exact years/units, schema validity, abstention, tool selection, state corrections, memory after compaction, and both response modes.
2. Establish the quantized base-model baseline with a concise policy, typed outputs/tools, and bounded context. Benchmark the actual deployment hardware.
3. Assemble a versioned, licensed, agronomist-reviewed knowledge collection. Retrieval is for updatable evidence; model weights are not the source of current field data or scientific calculations.
4. Collect reviewed interview/extraction/explanation examples. Farmer conversations require the separately approved training opt-in; application terms alone are insufficient for this product requirement. Split evaluation by farmer/field/scenario to reduce leakage; synthetic examples require review and do not become scientific evidence.
5. Use the separate Vast.ai RTX 4090 pre-production runbook for adapter tuning; validate a small pilot before the full run. The RTX 3050 is the inference target, not the training target.
6. Compare tuned and base models on the same held-out tasks and hardware after deployment quantization. Gate any recommendation capability on scientific validation in addition to language-model evaluation.

## Remaining branches

Settle actual hardware benchmarks, throughput thresholds, queue fairness and recovery, precise resource/profile schema, approved tool location/contracts and execution limits, upload formats/limits, domain boundaries, identity/privacy and web access policy, runtime/quantization/context budget, failure/retry/time limits, cancellation/streaming, data sources, and the actual training dataset. No production-time trainer is planned. Decide recommendation boundaries separately from the conversational MVP. No backend or model integration has begun.

## Server/orchestrator continuation

The user owns Cloudflare connection work; later integration will unify the deployment through configurable service boundaries. See [SERVER.md](SERVER.md) for the consolidated confirmed server requirements and the next interview frontier (Q39–Q42). This remains design/documentation work, with no backend connection yet.
