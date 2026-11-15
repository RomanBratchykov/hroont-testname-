# Croptato scientific pipeline inventory

Status: requirements audit for the design interview; no scientific implementation is authorized or claimed by this document.

## Sources and precedence

Current user direction requires both a published analysis of predefined farmer inputs and new analyses requested through Soily. Both must use the same retrieval and calculation pipeline.

Latest confirmed product decisions (15 November 2026):

- The deadline is midnight tonight in Kyiv: 00:00 on 16 November 2026. A useful working result is wanted sooner.
- There is one shared John showcase account. Accepted profile changes affect Personal info and the startup introduction for all subsequent visitors; earlier proposals for private visitor profiles do not describe the requested showcase.
- Existing displayed results belong to the input revision that produced them. The proposed engineering behavior is to mark affected results outdated after a correction and replace them only after a successful recalculation for the current revision.

Read alongside `AGENTS/AGENTS.md`, the technical/scientific specification v1.1, the external API data specification, the farmer questionnaire, and the server design notes. Current user instructions supersede historical server notes about localhost-only operation, providers, registration and language support.

The scientific specification's numerical examples and dashboard fixtures do not constitute measured or calculated pilot results. Its named pilot files still require existence, provenance and suitability checks before reuse.

## Required responsibilities

These are callable analysis stages, not a requirement for a separate executable or service for every row. Python modules can share one reproducible command-line entry point and the same allowlisted orchestration tools.

| Stage | Required inputs and behavior | Output and safeguards | Authority |
|---|---|---|---|
| Farmer profile | Extract structured field, management, crop history with exact years, restrictions, priorities and consent; validate and preserve unknowns | Versioned profile, provenance, missing inputs; ambiguity triggers a relevant follow-up | Questionnaire; technical §§3, 14, 16 |
| Field geometry | Normalize supplied polygon, validate CRS and topology, measure area, distinguish approximate point from confirmed field | Geometry/area record; synthetic pilot explicitly identified; spatial dataset mismatches flagged | Technical §§3–5, 10, 14 |
| POWER retrieval and QA | Retrieve required daily temperature and precipitation variables for 2016–2025; optional wind, humidity and radiation; cache original responses | Normalized daily values, units, calendar, missing codes, coverage, spatial support; incomplete years excluded from annual summaries | External API §1; technical §§4, 6 |
| Historical climate features | Apply crop windows including previous-year winter establishment | Seasonal rain, heat/frost days, longest dry spell, anomalies and distribution summaries; explicit thresholds and sample size, no forecast claims | Technical §6 |
| SoilGrids retrieval | Discover WCS coverage identifiers, subset properties and depth/quantile layers, validate units/scale/CRS | Modeled soil properties and uncertainty; unknown SoilFit stays uncertain | External API §1; technical §§4, 8, 10 |
| Crop requirements and feasibility | Version crop calendars and agronomic rules; check previous history, sow/harvest overlap, return/disease intervals, irrigation and cycle closure | Feasible candidates or explicit failed/unknown constraints; no precise sunflower interval inferred from undated history | Technical §7 |
| Suitability and optimization | Evaluate eligible sequences under consistent historical scenarios; use one candidate pool, transparent components and versioned objective weights | Economic Potential, Balanced, Climate & Soil Resilience; meaningful differences or justified fewer; unavailable factors excluded explicitly | Technical §§8, 11–12, 20.7 |
| IMERG rainfall erosivity | Retrieve half-hourly precipitation, convert rate to depth, apply documented erosive-event segmentation and energy/intensity method | Annual/monthly R, coverage, uncertainty and method version; annual rainfall is not a substitute | Technical §10 |
| Terrain processing | Retrieve buffered NASADEM/SRTM terrain, reproject to a suitable metric CRS, condition hydrology, route flow and calculate slope/LS | Pixel-level terrain/LS and area summaries; independent-method verification; EPSG:32636 applies to the specified pilot | Technical §§4–5, 10, 16 |
| Soil erodibility | Derive K using justified soil depths, validated pedotransfer and documented conversion | K values/ranges in units compatible with R; no invented structure/permeability | Technical §10 |
| Cover and support practices | Retrieve HLS reflectance/Fmask and derive cloud-masked vegetation history; combine validated management/calendar/residue evidence and practice tables | Modeled seasonal C and documented P; NDVI is not residue or a direct C factor; no-till is not an arbitrary P discount | Technical §10 |
| Spatial RUSLE | Combine compatible validated R/K/LS/C/P, erosivity-weight temporal cover, evaluate historical scenarios/cycle phases, aggregate per-pixel by area | Sheet/rill erosion estimates with uncertainty, or null/not_computed with reasons; no wind/gully tonnage | Technical §§10, 12, 16 |
| Economic assessment | Use credible farmer/local yield, price, currency-year and cost inputs; calculate gross margin and justified scenario/discount calculations | Actual gross-margin assessment only with supported inputs; otherwise unavailable or a named non-monetary proxy | Technical §§11, 20.7; later economic-method discussion |
| Results and publication | Save inputs/revisions, source manifest, processing versions, checks, outputs and limitations | Reproducible dashboard snapshot; JSON/PDF preserve disclosures; publishing a showcase does not make illustrative values scientific results | Technical §§14, 16, 20.9–20.10 |
| Live jobs and corrections | Bind allowlisted stages to validated requests, preserve accepted jobs and revision dependencies, bound time/resource use | Queued/running/completed/failed/insufficient-data states; old jobs cannot overwrite newer inputs; stop/retry behavior avoids duplicate charges or writes | Server notes; technical §14; repository rules |
| Operations and verification | Startup/shutdown, backups/restores, cached-data handling, diagnostics, boundary/units/scientific tests | Repeatable execution and recovery; no synthetic fallback for failed API calls | Technical §16; repository rules |

## Implementation order already prescribed

1. P0: intake, field validation, real NASA POWER, normalized data QA and climate-window metrics.
2. P1: crop catalog, hard sequence constraints, suitability and differentiated objective selection.
3. P2: erosion retrieval and all factor calculations, with spatial validation and uncertainty gates.
4. P3: regional agronomy review, calibration and comparisons to independent observations.
5. P4: optional water balance, wind modeling and calibrated economics.

Persistence, provenance, saved showcase publication, orchestration and failure presentation accompany each working stage. They are not a final polish phase.

## Optional or conditional, not initial blockers

- FAOSTAT is a broad benchmark, not field-level yield, local market price or farm profit.
- FAO-56 is a methodology implemented locally, not a calculation API. The water-balance module is an explicitly uncertain research/sensitivity module until its required parameters are supported.
- SMAP and wind exposure/model extensions are optional. No satellite product independently measures this field's root-zone water or wind erosion tonnage.
- Existing RAG ingestion does not provide scientific calculations or validate data. Retrieval/indexing must not block the P0/P1 vertical slice.
- Endpoint examples in the source documents are not proof of current service availability or authorization. Verify official access contracts when implementing each adapter; credentials stay outside source code and reports.

## Conflicts and decisions still to settle

- Geography: the technical specification explicitly restricts data to Kherson; server notes name Kharkiv as the main RAG region and discuss other locations. A knowledge collection's region is distinct from a scientific model's valid region.
- Agronomic input boundaries: technical §1 excludes machinery/fertilizer capacity from MVP ranking, while questionnaire Q21/Q22 and the dashboard journey include operational/business constraints. Collection, hard feasibility gates and ranking weights need distinct definitions.
- Objective definitions: §§11 and 20.7 contain different illustrative components/weights. Neither is a calibrated scientific constant; choose a single documented model/version and sensitivity policy before scoring.
- Example rotations: §7 and §20.3 contain different example B/C sequences. They must not be used as a feasible-result shortcut; the implemented gates must validate any candidate.
- Questionnaire priorities: soil knowledge is originally required, with a later proposed change to optional. Asking whether results are known is different from requiring a laboratory report; unknown values remain allowed.
- Showcase inputs: John currently has an illustrative undated crop history, synthetic field and incomplete management/soil/economic inputs. Actual supplied inputs or explicitly declared demo assumptions are needed for any otherwise blocked output.
- Delivery: the deadline is settled above. The exact first acceptance demonstration follows the prescribed P0/P1 vertical slice; erosion remains conditional on all factor validation gates.

## Current implementation baseline

The application has chat orchestration, persistence, private browser guest workspaces, provider limits, startup service, shared John demonstration fixtures, and a fixture dashboard/download. No scientific acquisition/calculation pipeline is connected. `RAG/rag/scripts/ingest_data.py` is a separate ingestion entry point, not an operational Croptato science tool.

## Showcase input completion

The user authorized all missing John farmer inputs to be filled with explicitly synthetic assumptions.
The complete file is `input_data/john_showcase.json`, with a matching GeoJSON boundary and Q01–Q26 mapping.
The UI and Soily use the fixture. No API observations, calibrated scientific parameters or computed outputs
were invented. Farmer-assumption provenance remains separate from future retrieved environmental data.
