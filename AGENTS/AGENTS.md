# AGENTS.md — Codex Engineering Rules

## Mission

Ship **correct, reliable, secure, maintainable code with the least necessary complexity**. Prefer working vertical slices over speculative architecture. Make future changes easy by keeping real boundaries clear—not by building frameworks for hypothetical scenarios.

**Decision order:** correctness and data integrity > security > simplicity > reliability > clarity > measured performance > future scalability. Never invent data, test outcomes, external API behavior, or completed functionality.

These rules are repository guidance, not permission to override the user's task. Inspect the actual repo before assuming a stack or layout. The AgroResilience-specific section applies to that project only.

## 1. Workflow for every task

1. **Inspect first.** Read relevant code, tests, config, lockfiles, README, and available specifications. Find existing patterns and the entry point of the requested behavior.
2. **Define success.** State the smallest observable outcome and a few acceptance checks. For nontrivial changes, give a brief approach; for small changes, implement directly.
3. **Change the minimum.** Extend existing code rather than writing parallel systems. Avoid unrelated refactors, dependency upgrades, bulk formatting, or architectural rewrites.
4. **Validate boundaries.** Check input, output, permissions, data units, error cases, and persistence. Prefer one working end-to-end flow before adding features.
5. **Verify.** Run relevant focused tests and available lint/type/build checks. Inspect your diff before completion.
6. **Report facts.** Say what changed, exact checks run, and what remains unverified. Never claim a test or deployment succeeded unless observed.

Make a reasonable, reversible assumption when a detail is missing. Ask only if proceeding could cause data loss, serious security/privacy harm, scientifically invalid claims, or incompatible product behavior. Do not stall ordinary implementation for hypothetical questions.

## 2. Code design: simple by default

- Prefer direct code, meaningful names, focused functions, explicit data flow, composition, and standard language features.
- Extract a helper for **real** duplication, distinct responsibility, or an independently testable boundary—not for imagined reuse. Some duplication is better than a misleading generic abstraction.
- Keep cohesive code together. Split modules by responsibility/change boundary, not arbitrary line limits. Avoid deep inheritance, reflection, magic configuration, and tiny pass-through wrappers.
- Apply types to important contracts (Python hints, TypeScript types) and **runtime validation** to external data. Avoid `any`, unchecked casts, and unexplained dynamic objects.
- Keep business and scientific functions independent from HTTP handlers, UI components, provider SDKs, and persistence details when that separation is genuinely useful.
- Preserve public contracts unless intentionally changing them; update callers, tests, and migrations together.
- Don't add fake implementations, dead code, unnecessary TODOs, or success responses that conceal incomplete work.

### Technology decision policy

| Need | Start with | Add complexity when |
|---|---|---|
| Backend architecture | One modular application | Independent scaling/deployment is demonstrated |
| Interfaces / adapters | Plain functions and a thin boundary | A second real implementation or difficult test seam requires it |
| Database | Existing PostgreSQL + straightforward SQL/ORM | Actual queries justify additional abstraction/indexes/extensions |
| Background work | Bounded request processing | Expensive work requires jobs; use persisted job state if crash recovery matters |
| Cache | None | Profiling shows repeated costly work; ownership and freshness are defined |
| Queue / Redis / Celery | None | Durable retries, workload isolation, or throughput requires them |
| RAG / vector DB | Parse and provide relevant document text | Repeated multi-document retrieval or context limits justify an index |
| Microservices / event bus | None | A measured operational constraint demands them |

**Avoid premature:** microservices, CQRS, factories, repository hierarchies, plugin engines, universal provider frameworks, speculative flags, and extra dependencies. Prefer the project's existing tools. Never use `--force` or `--legacy-peer-deps` to disguise dependency conflicts.

## 3. Reliability, performance, and security

- Validate untrusted requests, files, remote responses, model output, and tool arguments at their boundaries. Use consistent, client-safe error categories; log private technical details without secrets.
- Set explicit network timeouts; retry only transient, safe/idempotent operations with a bounded count and backoff. Respect rate limits and cancellations. Distinguish `not_found`, `invalid`, `unavailable`, and `failed` rather than swallowing exceptions.
- Use DB transactions for atomic updates, parameterized queries, paginated results, and indexes based on actual access patterns. Keep durable state out of global process memory. Preserve migrations and stored data.
- Bound file sizes, AI context/output, concurrency, memory use, and external calls. Prefer efficient queries, fewer round trips, streamed/batched large data, and simple algorithms before profiling-driven optimization.
- Do not block an async server with synchronous network calls or heavy CPU/raster tasks. Use appropriate workers when needed, with explicit status and recovery semantics. In-process background tasks are **not durable**.
- Authenticate and authorize on the **server**, including object ownership. Never trust client-supplied user IDs for authorization. Test cross-user access when applicable.
- Protect uploads and HTTP integrations from path traversal, resource exhaustion, injection, and SSRF. Do not execute arbitrary shell, Python, SQL, or URLs suggested by a model.
- Put secrets in environment/secret storage, not source. Do not commit `.env`, API keys, credentials, tokens, or personal data. Keep CORS restricted; use secure cookies and CSRF protection where applicable.
- Keep internal model servers, databases, admin tools, and dev servers off the public internet. Minimize collection and retention of precise location and personal data.
- Use lightweight actionable logs (stage, request/job ID, timing, failure category), without exposing field data or chat text unnecessarily.

## 4. AI integration: deterministic tools, probabilistic language

**The LLM handles conversation, extraction, tool selection, and explanation. Trusted application code handles validation, authorization, calculations, writes, and scientific conclusions.**

Preferred flow:

`request -> validate -> conversation state -> optional document retrieval -> allowed tool -> validate arguments -> deterministic execution -> validate result -> sourced explanation`

- Keep prompts small, versioned, and separate from domain rules. Use schema-validated structured outputs for decisions/actions. Handle invalid JSON or incomplete responses with a **bounded** correction policy.
- Expose only an allowlisted set of tools with argument/result schemas, permissions, timeouts, maximum iterations, and safe failure handling. Treat retrieved documents and API content as **untrusted data**, never executable instructions.
- **File parsing is not RAG.** Parse documents first; use direct context for small files. Add chunking/search/embeddings only when justified by evidence and volume. Preserve file/page/source references.
- Persist needed interview facts and session state deliberately; send bounded relevant context rather than replaying full chat histories/documents.
- Use a **small adapter only for providers actually supported**. Ollama and DeepSeek may be switched by explicit configuration, but never silently transmit private farmer data to a remote provider when local inference fails.
- Enforce LLM timeouts, request/concurrency caps, context and output budgets, and paid-API spending limits when configured. Support honest partial/error states. Streaming text does not imply that tools or analysis succeeded.
- A failed NASA/API/tool request must **not** be replaced by plausible model-generated data. Synthetic demo results must be clearly labeled and isolated from real outputs.

## 5. AgroResilience project rules

If available in the repo, consult `AgroResilience_Technical_Scientific_Specification_v1.1.docx.md` for detailed scientific requirements. The file may not be in the local workspace: do not pretend to have read it. Distinguish its normative requirements from illustrative examples, and flag material contradictions instead of inventing a reconciliation.

### Scope and implementation sequence

**P0:** guided farmer interview, verified/clearly synthetic field geometry, real NASA POWER historical climate, coverage/QA, explainable climate features.  
**P1:** validated crop history with exact years, agronomic constraints, feasible cyclic rotations, three distinct objectives: Economic Potential, Balanced, Climate & Soil Resilience. Return fewer candidates **with explanation** if three genuinely distinct feasible options do not exist.  
**P2:** RUSLE water-erosion analysis only after factor units, source quality, assumptions, and spatial methods pass QA.  
**P3+:** regional scientific review, calibration, optional advanced water/wind/economic models.

Do not let complex RAG, RUSLE, model fine-tuning, or UI polish block the correct P0/P1 workflow.

### Scientific invariants (not optional)

- Climate from NASA POWER is **historical gridded data**, not a field-station observation or a future weather forecast. The initial pilot analysis uses **2016–2025**.
- SoilGrids estimates are **not NASA** and not a farmer's measured soil test. State soil depth, spatial resolution, source, and uncertainty.
- HLS/NDVI is **not directly** residue coverage or RUSLE `C`. Do not invent conversions.
- RUSLE estimates long-term **sheet/rill water erosion**; it does not measure wind erosion, gully erosion, or actual field soil loss. Compute only with justified compatible `R`, `K`, `LS`, `C`, `P` inputs; otherwise return `null`/`not_computed` plus reason, **never zero for unknown**.
- Validate crop sow/harvest windows, predecessor and disease-return constraints, **last-year -> first-year rotation continuity**, precipitation units, missing values, leap days, polygon/CRS, pixel areas, and nodata.
- Numeric outputs require **value, units, period, source/provenance, method or version, assumptions, and uncertainty/limitations**. Distinguish observed, satellite-derived, model-estimated, farmer-reported, assumed, and demo data.
- Suitability scores are **comparative screening indicators**, not crop-damage probabilities. Hard agronomic gates must pass **before** ranking. Use consistent candidate pools and baselines for strategy comparisons.
- Missing real yield, cost, or price data means **Economic Potential/proxy**, not predicted profit. Do not invent water savings, carbon gains, soil-loss numbers, yields, confidence percentages, or agronomic certainty.
- The Kherson ~30-ha pilot geometry and illustrative strategy/dashboard values are **synthetic/demo examples**, not verified field observations. Keep demo fixtures visibly separate from live computations.
- Do not make field-level validated agronomic claims without appropriate regional validation. Express decisions as support with assumptions and limitations.

### Repo-specific defaults (verify first)

- **Frontend:** React + TypeScript + Vite; reuse installed Tailwind/shadcn/assistant-ui. Handle loading, partial, unavailable, and retry states. Keep the frontend independent of provider-specific message formats.
- **Backend:** FastAPI + Pydantic; use `uv`, `pytest`, and `ruff` if configured. Keep numeric/scientific logic as pure, reproducible Python functions where possible.
- **Persistence:** PostgreSQL for users, fields, interview state, analyses, and reports. PostGIS when actual spatial queries require it; pgvector only for implemented retrieval.
- **LLM:** local Ollama on **6 GB GPU** or hosted DeepSeek by explicit choice; cap parallel generations, input context, and tool steps.
- **Hosting:** Linux Mint PC behind Cloudflare Tunnel; serve a **production frontend build**, not a publicly accessible Vite dev server. Keep Ollama, Postgres, and internal API protected/private.
- **Jobs:** use queued/running/completed/failed/insufficient-data states if long analyses become asynchronous; don't overbuild a queue before it is needed.

## 6. Testing and finishing

Tests should prove **behavior**, not implementation details. Prefer pure-function unit tests, a few boundary/integration tests, and one representative end-to-end workflow. Fake **external services**, not the internal business logic. Keep tests deterministic and offline by default; don't call paid models or NASA services in routine CI.

Prioritize these regressions:

- Missing data does not turn into `0` or a fabricated recommendation.
- Authentication and field ownership cannot cross user boundaries.
- Climate units and dates (including crop-year crossing) are correct.
- Rotation constraints apply across all years **and** the cyclic boundary.
- RUSLE unit/spatial QA and basic invariants (`R = 0` implies modeled `A = 0`; cover-management direction consistent when other factors are fixed).
- API/tool failures surface as unavailable/partial, not hidden demo data.

Use commands actually configured in the repo, such as:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
npm run build
npm run lint
```

Don't install or alter toolchains solely to make illustrative commands run. Report exactly what ran and what didn't.

**Completion response (concise):**

1. **Changed:** concrete behavior and files.
2. **Verified:** tests/build/lint and actual results.
3. **Caveats:** unresolved risks, assumptions, necessary configuration or migration.

**Bottom line:** implement the smallest trustworthy solution, expose real failure states, keep scientific claims reproducible, and add infrastructure only when a measured need appears.
