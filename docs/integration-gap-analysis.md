# Analysis of reported scientific, retrieval and source-check gaps

Follow-up implementation: source-status summaries now preserve actual statuses while full
evidence stays outside model context; identical gathering calls are reused within a turn.
Source checks now have four-request concurrency, bounded retries, safe failure reasons and
separate GPM metadata/download checks. `NASA_TOKEN` supports a NASA Open APIs access check;
Earthdata authentication remains separate. Qdrant API-key support was added to runtime and
ingestion, and embedding imports are deferred so SQL/client checks can run independently.
Reference-store provisioning/indexing and the scientific calculation stages remain required.

## Scope

Code inspection of the reported assistant response. The deployed backend's configuration,
failing request, tool findings and logs were not available, so the exact production size-limit
trigger is not established. Text reveal timing was changed to twice its previous speed;
the backend integrations below have not been changed by this analysis.

## 1. Source checks lose useful data when context is full

`backend/orchestrator.py` rejects any individual tool result above 16,000 JSON bytes.
Separately, `Settings.max_context_bytes` defaults to 32,000 bytes for messages plus tool
schemas. This includes policy, saved profile, questionnaire, chat history, DeepSeek reasoning
continuations, tool arguments and every tool response. It is an application byte budget,
not the provider's advertised token window.

`check_data_sources` in `backend/tools.py` already omits raw probe URLs but still includes
descriptions, limitations, provenance URLs and per-probe status arrays for six providers.
When the combined request is too large, the orchestrator first removes older turns, then
replaces entire tool responses with `context_omitted` notices. Full accepted tool results
remain in Tool findings, but the model cannot explain source statuses it no longer receives.
An individual result rejected before evidence is recorded does not retain that full result.

Recommended repair:

1. Reproduce a failing source-check continuation with mocked provider responses and a real
   default-size system prompt; distinguish individual-result rejection from total overflow.
2. Keep a compact deterministic summary containing coordinates, source IDs, actual statuses,
   check time and essential limitations. Keep full provenance in evidence/dashboard storage.
3. Compact source-check responses by schema before dropping them entirely. Preserve actual
   statuses and unknowns; do not ask a language model to invent a summary of omitted data.
4. Offer a single-provider detail request and reuse identical completed checks within a turn.
5. Reserve room for tool continuations when selecting history and pre-retrieved text. Preserve
   DeepSeek call IDs and required reasoning; simply raising limits is not a complete repair.

Acceptance: all six source statuses reach the final model request for a small polygon, even
with prior chat history. Oversized details cannot erase available status evidence. Remaining
overflow is explicit and partial; no failed endpoint becomes available or a numeric zero.

## 2. Reference retrieval needs an actual indexed evidence store

`rag_health` in `backend/tools.py` returns unavailable when `RAG_URL` is empty. Enabling the
URL alone does not populate sources. Retrieval uses PostgreSQL and Qdrant, with document
ingestion in `RAG/scripts/ingest_data.py`; local literature must carry appropriate region,
period and source metadata. Healthy stores can still return no matching Kherson evidence.

Deployment choices supported or constrained by current code:

- `RAG_URL=direct`: load the retrieval application in the backend process. Install the RAG
  dependencies and embedding model, configure `DATABASE_URL`, `QDRANT_URL` and the collection,
  and ingest the selected documents/datasets. Provisioning storage and indexing remain required.
- A separate retrieval service: the current `Settings` validator only permits localhost RAG
  HTTP URLs. A remote service needs an explicit validated-host/authentication change; setting a
  hosted URL today will fail validation.
- Qdrant Cloud/authenticated Qdrant: both the runtime client and ingestion client construct
  `QdrantClient` without an API key. Add matching backend-only API-key support to both paths
  before using an authenticated deployment. Do not expose databases publicly without access control.

Acceptance: backend health reports retrieval readiness, and a targeted Kherson query returns
inspectable source citations. A no-match or unindexed store must remain distinct from an API
failure. An Earthdata token does not configure literature retrieval.

## 3. Scientific outputs require implementation, not a prompt change

`get_capabilities` explicitly reports `scientific_analysis=unavailable`, an empty scientific
tool list and deferred recommendations. The chat registry exposes profile operations, history,
climate/source retrieval and optional RAG; it does not expose the requested rotation/scoring,
erosion, gross-margin or yield-forecast calculations.

There is reusable work in `frontend/python/agrodata`: daily climate collection, exposure
statistics and bounded download/processing tools. It is separate from chat and its region
validation explicitly restricts it to Kharkiv Oblast. It cannot simply be enabled for a Kherson
profile, and climate exposure statistics are not calibrated crop scores or yield forecasts.

Recommended implementation sequence:

1. Normalize the editable profile into typed analysis inputs with units, exact crop years,
   provenance and missing-data states. Bind persisted analysis results to the input revision.
2. Connect approved historical climate features with coverage/units/crop-window checks for
   the supported region; retain explicit unavailable values where evidence is insufficient.
3. Implement deterministic rotation constraints, including return intervals, sow/harvest
   windows, irrigation limits and last-year-to-first-year cycle closure, before ranking options.
4. Add documented comparative scoring only after feasibility and regional evidence checks.
   Calculate gross margins only from supported yields, prices, costs and currency-year inputs.
5. Connect validated raster acquisition and compatible R/K/LS/C/P methods before RUSLE.
   A token, endpoint response, NDVI or annual rainfall alone is not an erosion estimate.
6. Treat yield forecasting as a separate calibrated model requiring suitable observations
   and validation; do not label generic LLM estimates as forecasts.

## Practical order

Repair preservation of source statuses first, then provision and verify reference retrieval.
Deliver historical climate features and rotation feasibility as the first calculation slice.
Keep unsupported erosion, financial and forecast outputs explicitly not computed until their
own data and method requirements are met. None of these integrations is enabled by the
text-speed change.
