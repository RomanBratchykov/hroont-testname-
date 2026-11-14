# AgroResilience — Farmer Interview Questionnaire

The chat should be adaptive: ask one short question at a time or a compact group. Required fields are distinguished from optional fields. **“Unknown” must be allowed**; never silently fill unknown values with false precision.

## Farmer interview: full question catalog

| ID | Priority | Farmer question | Model use |
|---|---|---|---|
| **Q01** | Required | Where is the field? Pin on map, coordinates, or upload GeoJSON/KML; confirm polygon and hectares. | Location, polygon, area; source geometry |
| **Q02** | Required | Is this field irrigated? If yes, how much reliable water is available and when? | Irrigation feasibility; baseline pilot = none |
| **Q03** | Required | Which crops were grown in each of the last 3–10 calendar years? Include harvest year and failed crops. | Predecessor and return intervals |
| **Q04** | Required | Which crops do you want to include or exclude? Any legal, market, or agronomic restrictions? | Candidate set and exclusions |
| **Q05** | Required | What planning horizon do you prefer: 3–5, 6–8, 10–12 years, or let the system compare? | Rotation length; compare horizons |
| **Q06** | Required | Do you know soil texture (sand, sandy loam, loam, clay), soil type, and test results? Upload if available. | K factor, suitability, confidence |
| **Q07** | Required | What tillage is used: conventional, minimum till, no-till, mixed? | C management assumptions |
| **Q08** | Required | How much residue remains after harvest: <10%, 10–30%, 30–60%, >60%, unknown? | Surface-cover component of C |
| **Q09** | Required | Which erosion controls are in place: contouring, strip cropping, terraces, waterways, none? | P factor; verify engineering applicability |
| **Q10** | Required | Have you observed sheet wash, rills, gullies, dust storms or windblown soil? When/where? | Model validation and wind-risk warning, NOT multiplier |
| **Q11** | Required | Do you use black fallow, mulch fallow or cover crops? How are weeds controlled and residues managed? | Fallow candidate and C assumptions |
| **Q12** | Optional | Are there shelterbelts or windbreaks, and are they intact? | Wind exposure context; not RUSLE P by default |
| **Q13** | Optional | Do you know slope, drainage problems, flooding or runoff pathways? | Cross-check DEM and runoff |
| **Q14** | Optional | What are your typical crop yields by year, with units and source? | Optional yield calibration; avoid invented projections |
| **Q15** | Optional | What are farmgate prices, variable costs and crop market access? Currency and year? | Economic objective; otherwise proxy only |
| **Q16** | Optional | What is the field’s organic carbon, pH, salinity, compaction, soil depth, drainage or lab report? | Soil suitability and K refinement |
| **Q17** | Optional | Are there known diseases/pests, particularly sunflower broomrape, Sclerotinia or root diseases? | Return constraints and disease breaks |
| **Q18** | Required | Which priority matters most: profitability, balanced sustainability, or resilience? | Personalization; still return all 3 strategies |
| **Q19** | Required | May we use your approximate field location and anonymized agronomic responses for analysis? | Consent, privacy, retention |
| **Q20** | Optional | Which field observations or model assumptions look wrong? | Post-result human validation |

## Proposed additional questions

| ID | Priority | Farmer question | Model use |
|---|---|---|---|
| **Q21** | Required | Which agricultural operations can you perform? Select available machinery or services: seeding, spraying, fertilizing, harvesting, irrigation, or contractor access. | Exclude crops that cannot realistically be cultivated or harvested |
| **Q22** | Required | What is your approximate annual production budget per hectare? Low / Medium / High / Unknown, or enter an amount. | Financial feasibility and investment constraints |
| **Q23** | Optional | Which fertilizers and soil amendments do you typically apply? Include approximate rates if known. | Nutrient-management assumptions and costs |
| **Q24** | Optional | Are there limitations on purchasing seeds, fertilizers, fuel, or crop protection products? | Input availability and operational constraints |
| **Q25** | Optional | Can you store harvested crops, or must they be sold immediately? | Marketing flexibility and economic assumptions |
| **Q26** | Optional | Are there accessibility, security, unexploded ordnance, or infrastructure restrictions affecting this field? | Operational feasibility and safety exclusions; not a numerical agronomic risk multiplier |

## Recommended questionnaire refinements

| Existing | Recommended change | Why |
|---|---|---|
| Q03 — 3–10 years of crop history | Ask for the last 3 years first; allow up to 10 | Easier to answer; additional years improve return-interval checks |
| Q05 — Preferred planning horizon | Default to comparing the three strategies over the same 8-year horizon; offer advanced customization | Makes scenario comparison more consistent |
| Q06 — Soil texture and laboratory results | Make optional, use SoilGrids estimates when unknown | Most farmers may not know detailed soil parameters |
| Q08 — Residue percentage | Add visual examples or descriptions | Percentages are difficult to estimate |
| Q09 — Erosion controls | Add “Not sure” | Avoids incorrectly assuming no conservation practices |
| Q14 — Historical yields | Ask for the last 3 harvests, if available | Helps calibrate yield assumptions |
| Q15 — Prices and costs | Ask whether to use farmer-provided values or clearly labeled regional assumptions | Prevents presenting proxy-based profitability as a reliable financial forecast |
| Q19 — Consent | Keep mandatory before processing, but separate consent from agronomic model inputs | Consent is a privacy requirement, not a model variable |

## Suggested adaptive flow

1. **Essential farm profile:** field location, irrigation, recent crops, crop restrictions, machinery, budget, priorities, and consent.
2. **Automatic data enrichment:** NASA POWER (climate), SoilGrids WCS (soil), NASADEM (terrain), GPM (rainfall), HLS (vegetation history).
3. **Targeted follow-ups:** ask only when an answer materially changes recommendations or reduces uncertainty.
4. **Results:** compare profitability, balanced sustainability, and climate resilience, with explicit uncertainty labels.

**Implementation note:** The original priorities above are preserved for traceability. The refinements section proposes changing Q06 to optional; the development team should reconcile this before implementation. Unknown values must remain explicit, including for budget and soil inputs. Consent is a prerequisite for processing, not an agronomic predictor. Field security cannot be inferred from satellite imagery.
