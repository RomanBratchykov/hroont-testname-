# **AgroResilience**

NASA-powered crop rotation decision-support platform

PRODUCT REQUIREMENTS • SCIENTIFIC METHODOLOGY • SYSTEM ARCHITECTURE • DEVELOPER IMPLEMENTATION SPECIFICATION

Version 1.0 \| 13 November 2026 \| Audience: NASA Space Apps jury, engineers, agronomists, product team

Reference pilot: synthetic 30-ha plot, Kherson Oblast, Ukraine (46.7491 N, 32.7091 E). Rainfed agriculture. The pilot polygon is NOT a verified cadastral field.

# **Executive summary**

AgroResilience interviews a farmer, retrieves reproducible NASA Earth-observation and independent soil datasets, screens agronomically feasible crop sequences, and returns exactly three contrasting rotation strategies: Economic, Balanced, and Climate/Soil Resilience. Recommendations are decision support, not forecasts of yields or guaranteed profit. The MVP quantifies observable climate exposure and a conditional RUSLE estimate of sheet/rill water erosion; it does not claim field-measured soil moisture, wind erosion tonnage, or validated future yield.

# **1\. Scope, objectives, and non-goals**

* Core workflow: conversational intake → validation → NASA data acquisition → climate/soil/erosion analytics → agronomic candidate generation → multi-objective selection → three explainable strategies → farmer feedback.  
* Primary objectives: climate suitability, historical drought/heat/frost exposure, crop sequence feasibility, modeled water-erosion consequences, crop diversity and soil cover, and economic potential when credible prices/costs are available.  
* No irrigation in the pilot. Other farms may specify irrigation; feasibility must reflect actual water access.  
* MVP excludes machinery capacity, fertilizer purchasing capacity, and military risk as ranking inputs; optional future modules must be explicitly separated.  
* No claim that 8–12-year rotations always outperform 3–5-year rotations; evaluate horizons by constraints and evidence.

# **2\. End-to-end user journey and orchestration**

![][image1]

# **3\. Farmer interview: full question catalog**

The chat should be adaptive, one short question at a time or a compact group. Required fields are distinguished from optional. “Unknown” must be allowed; never silently fill unknown values with false precision.

| ID | Priority | Farmer question | Model use |
| :---- | :---- | :---- | :---- |
| **Q01** | Required | Where is the field? Pin on map, coordinates, or upload GeoJSON/KML; confirm polygon and hectares. | Location, polygon, area; source geometry |
| **Q02** | Required | Is this field irrigated? If yes, how much reliable water is available and when? | Irrigation feasibility; baseline pilot \= none |
| **Q03** | Required | Which crops were grown in each of the last 3–10 calendar years? Include harvest year and failed crops. | Predecessor and return intervals |
| **Q04** | Required | Which crops do you want to include or exclude? Any legal, market, or agronomic restrictions? | Candidate set and exclusions |
| **Q05** | Required | What planning horizon do you prefer: 3–5, 6–8, 10–12 years, or let the system compare? | Rotation length; compare horizons |
| **Q06** | Required | Do you know soil texture (sand, sandy loam, loam, clay), soil type, and test results? Upload if available. | K factor, suitability, confidence |
| **Q07** | Required | What tillage is used: conventional, minimum till, no-till, mixed? | C management assumptions |
| **Q08** | Required | How much residue remains after harvest: \<10%, 10–30%, 30–60%, \>60%, unknown? | Surface-cover component of C |
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

# **4\. Data sources, APIs, coverage, provenance**

| Dataset | Variables / role | Resolution and caveat | Official link |
| :---- | :---- | :---- | :---- |
| **NASA POWER Daily** | T2M, T2M\_MAX, T2M\_MIN, PRECTOTCORR; optional WS2M, RH2M, ALLSKY\_SFC\_SW\_DWN | Coarse gridded reanalysis; historical 2016–2025; not field weather station | Karyna\_khomutova 2g/s6GY)uqN6mGS [https\://urs.earthdata.nasa.gov/](https://urs.earthdata.nasa.gov/) API https\://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M\_MAX,T2M\_MIN,PRECTOTCORR,RH2M,WS2M,ALLSKY\_SFC\_SW\_DWN\&community=AG\&longitude=32.7091\&latitude=46.7491\&start=20160101\&end=20251231\&format=JSON\&utm\_source=chatgpt.com  |
| **NASA GPM IMERG Final V07** | Half-hourly precipitation intensity; rainfall erosivity R | \~0.1°; 30 min; satellite retrieval is not a rain gauge; validate local applicability | [https\://gpm.nasa.gov/data/directory](https://gpm.nasa.gov/data/directory) Karyna\_khomutova 2g/s6GY)uqN6mGS |
| **NASADEM / SRTMGL1** | DEM elevation, slope, flow accumulation, LS | \~30 m; low-relief artifacts can dominate a 30-ha field | [https\://search.earthdata.nasa.gov/search?q=NASADEM](https://search.earthdata.nasa.gov/search?q=NASADEM) Karyna\_khomutova 2g/s6GY)uqN6mGS |
|  |  |  |  |
| **NASA HLS** | Reflectance, NDVI, phenology, cover proxies | 30 m; clouds, bare soil vs residue ambiguity; historical actual cover only | [https\://hls.gsfc.nasa.gov/](https://hls.gsfc.nasa.gov/) Karyna\_khomutova 2g/s6GY)uqN6mGS |
| **ISRIC SoilGrids** | sand, silt, clay, SOC, pH, bulk density, uncertainty quantiles | 250 m, six depth intervals; NOT NASA; weak intra-field differentiation | https\://docs.isric.org/globaldata/soilgrids/ |
| **ISRIC WCS** | SoilGrids spatial subsets | Prefer WCS; check service availability and units | https\://docs.isric.org/globaldata/soilgrids/wcs.html |
| **USDA NRCS RUSLE2** | RUSLE factors, practice science, conservation interpretation | RUSLE2 is a separate calibrated system; MVP implements transparent RUSLE-style approximation | https\://www\.nrcs.usda.gov/resources/tech-tools/water-erosion-rusle2 |
| **FAO-56** | ET0, Kc, crop water stress, water balance | Reference methodology; needs weather and crop parameters | https\://www\.fao.org/4/X0490E/x0490e00.htm |
| **NASA SMAP (optional)** | Surface soil moisture for regional context | Too coarse for independent 30-ha root-zone moisture measurement | https\://smap.jpl.nasa.gov/ |
| **FAOSTAT (optional)** | Crop prices/yields macro context | Not farm-level net margins | https\://www\.fao.org/faostat/en/\#home |

Karyna\_khomutova  
2g/s6GY)uqN6mGS

Обмежити данні по Херсонський області only\!\!\!\!

| Dataset | Variables  | Resolution and caveat | Official link | API endpoint / developer documentation | API URL string / example |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **NASA POWER Daily** | T2M, T2M\_MAX, T2M\_MIN, PRECTOTCORR; optional WS2M, RH2M, ALLSKY\_SFC\_SW\_DWN.  | Coarse gridded meteorological data; historical 2016–2025; not a field weather station | [NASA POWER](https://power.larc.nasa.gov/?utm_source=chatgpt.com) | [Daily REST API documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/?utm_source=chatgpt.com) | [JSON API request](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,WS2M,ALLSKY_SFC_SW_DWN&community=AG&longitude=32.7091&latitude=46.7491&start=20160101&end=20251231&format=JSON&utm_source=chatgpt.com) |
| **NASA GPM IMERG Final V07** | Half-hourly precipitation intensity (`precipitation`, mm/h) | \~0.1°; 30 min; satellite retrieval is not a rain gauge; R must be calculated from precipitation data | [GPM Data Directory](https://gpm.nasa.gov/data/directory?utm_source=chatgpt.com) | [IMERG dataset](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary?utm_source=chatgpt.com) · [Harmony API](https://harmony.earthdata.nasa.gov/docs?utm_source=chatgpt.com) | `https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGHH.07/` |
| **NASADEM / SRTMGL1** | DEM elevation; derived slope, flow accumulation, slope length | \~30 m; terrain artifacts can affect LS estimates on a 30-ha field | [NASA Earthdata Search](https://search.earthdata.nasa.gov/search?q=NASADEM&utm_source=chatgpt.com) | [CMR Search API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html?utm_source=chatgpt.com) | `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NASADEM_HGT&point=32.7091,46.7491&page_size=10` |
| **NASA HLS** | Surface reflectance: Red (`B04`), NIR (`B8A` for S30; `B05` for L30), `Fmask`; derived NDVI | 30 m; cloud contamination; NDVI cannot directly identify crop residues | [NASA HLS](https://hls.gsfc.nasa.gov/?utm_source=chatgpt.com) | [HLS data access](https://hls.gsfc.nasa.gov/data-access-and-tools/?utm_source=chatgpt.com) · [CMR-STAC](https://cmr.earthdata.nasa.gov/stac?utm_source=chatgpt.com) | `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=HLSS30&version=2.0&point=32.7091,46.7491&temporal=2025-04-01T00:00:00Z,2025-09-30T23:59:59Z&page_size=10` |
| **ISRIC SoilGrids WCS** | `sand`, `silt`, `clay`, `soc`, `phh2o`, `bdod`; soil depth layers and uncertainty quantiles | Soil texture, organic carbon, pH, bulk density; crop suitability, soil erodibility K, soil-water calculations | **250 m; modeled soil properties; WCS returns GeoTIFF rasters rather than JSON** | [**WCS documentation**](https://docs.isric.org/globaldata/soilgrids/wcs.html?utm_source=chatgpt.com) **· [Python examples](https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html?utm_source=chatgpt.com)** | [**`WCS GetCapabilities — clay`](https://maps.isric.org/mapserv?map=%2Fmap%2Fclay.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities&utm_source=chatgpt.com)** |
| **ISRIC WCS** | Spatial raster coverages of SoilGrids properties: `sand`, `silt`, `clay`, `soc`, `phh2o`, `bdod` | 250 m; returns raster data; check units, CRS and service availability | [ISRIC WCS documentation](https://docs.isric.org/globaldata/soilgrids/wcs.html?utm_source=chatgpt.com) | [WCS developer guide](https://docs.isric.org/globaldata/soilgrids/wcs.html?utm_source=chatgpt.com) | `https://maps.isric.org/mapserv?map=/map/clay.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities` |
| **USDA NRCS RUSLE2** | RUSLE factors R, K, LS, C, P; conservation practices and erosion-model methodology | RUSLE2 is a separate calibrated system; MVP uses a transparent RUSLE-style approximation | [USDA RUSLE2](https://www.nrcs.usda.gov/resources/tech-tools/water-erosion-rusle2?utm_source=chatgpt.com) | No general public REST calculation API identified | **N/A — methodology, not an API** |
| **FAO-56** | ET₀, crop coefficients (`Kc`), crop evapotranspiration (`ETc`), water-stress coefficient (`Ks`), soil-water balance parameters | Reference methodology; requires weather and crop parameters | [FAO-56](https://www.fao.org/4/X0490E/x0490e00.htm?utm_source=chatgpt.com) | [FAO-56 methodology](https://www.fao.org/4/X0490E/x0490e00.htm?utm_source=chatgpt.com) | **N/A — implement formulas locally** |
|  |  |  |  |  |  |
| **FAOSTAT (optional)** | Crop production, harvested area, yield, agricultural statistics | Country/year statistics; not farm-level net margins or live local crop prices | [FAOSTAT](https://www.fao.org/faostat/en/?utm_source=chatgpt.com#home) | [FAOSTAT API documentation](https://www.fao.org/faostat/en/docs/redoc-static.html?utm_source=chatgpt.com) | `https://fenixservices.fao.org/faostat/api/v1/en/data/QCL?area=230&item=15&element=5510&year=2023` |

Data contracts: store product/version, UTC timestamp, spatial support, CRS, units, source URL, retrieval date, quality flags, processing code version and license. Never combine a POWER point with a different field geometry without explicitly flagging the spatial mismatch.

# **5\. Pilot evidence and ground truth boundaries**

Pilot center: 46.7491 N, 32.7091 E; synthetic square ≈30 ha, not a surveyed or verified agricultural parcel. Historical crop sequence (sunflower → sunflower → wheat) is user-supplied hypothetical history; exact calendar years remain unknown. A previously studied nearby area was described as dark chestnut soils; do not automatically assume chernozem for this plot.

Available NASA POWER CSVs are from a DIFFERENT point (46.60 N, 32.60 E), 2016–2025. Their historical annual precipitation values (mm): 603.5, 375.2, 435.2, 456.0, 357.4, 605.8, 372.3, 481.7, 420.6, 315.9; mean ≈442.4 mm. These are valid for their source grid/point only, not a site-specific gauge for the new polygon.

Existing SRTM pilot preprocessing produced preliminary mean slope ≈1.04°, mean LS ≈0.431 and maximum LS ≈1.779 using 30-m terrain and an approximate flow-routing method. These are preliminary derived values requiring independent GIS verification and hydrological conditioning, not a measured slope survey.

# **6\. Climate feature engineering**

Calendar conventions: daily observations are in source-local time where applicable; convert to an explicit project calendar. Winter crop windows span two calendar years. Exclude incomplete years from historical annual statistics.

For crop c, historical season y and crop calendar window W(c,y):

* SeasonRain(c,y) \= Σ\[t ∈ W(c,y)\] P\_t   \[mm\]  
* HeatDays(c,y; θ) \= Σ\[t ∈ W(c,y)\] 1(Tmax\_t ≥ θ)   \[days\]  
* DrySpell(c,y; p0) \= max consecutive days with P\_t \< p0   \[days\]  
* FrostDays(c,y; θf) \= Σ\[t ∈ W(c,y)\] 1(Tmin\_t \< θf)   \[days\]  
* RainAnomaly(c,y) \= (SeasonRain(c,y) − median\_y SeasonRain(c,y)) / median\_y SeasonRain(c,y)   \[dimensionless\]

Defaults such as heat θ=35°C and dry-day p0=1 mm are transparent heuristic thresholds, not universal crop physiological stress limits. Use crop-stage-specific thresholds when evidence supports them. Report n, median, min/max, percentiles and confidence. Ten years is a short climatological baseline, not a 30-year climate normal.

# **7\. Candidate crop database and agronomic constraints**

| Crop / management | Indicative growing window (Kherson; adjust locally) | Key screening considerations |
| :---- | :---- | :---- |
| **Winter wheat** | Oct (previous year)–Jun | Autumn establishment, spring moisture, preceding crop |
| **Winter barley** | Oct (previous year)–Jun | Winter hardiness, earlier maturity |
| **Winter rye** | Oct (previous year)–Jun | Cold tolerance, market suitability |
| **Winter rapeseed** | Sep (previous year)–Jun | High risk of failed autumn establishment in dry years |
| **Peas** | Mar–Jun | Legume, spring moisture, disease interval |
| **Spring barley** | Mar–Jun | Early-season water and heat |
| **Chickpea** | Mar–Jul | Dryland option, establishment and heat |
| **Oil flax** | Mar–Jul | Crop-specific rotation and disease |
| **Millet** | May–Aug | Short-season, summer rainfall |
| **Grain sorghum** | May–Sep | Heat tolerance; drought not equal to zero water requirement |
| **Sunflower** | Apr–Sep | Long return interval and pathogen/soil-water concerns |
| **Maize** | May–Sep | High dryland risk; screen irrigation/soil-water constraints |
| **Black fallow** | Management year | No marketable harvest; exposed soil/erosion trade-off |
| **Mulch/conservation fallow** | Management year | Residue quantity and weed control critical |
| **Green-manure fallow** | Management year | Cover crop water use and termination timing critical |

Hard constraints: crop admissibility by climate/soil, irrigation requirement if relevant, planting/harvest date feasibility, known disease/return interval, rotation continuity across year N→1, and prior crop history. The system MUST ask for exact sunflower years before enforcing an exact return interval. A common 7–9-year interval is a region- and disease-dependent guideline, not a universal law. Crops sharing pathogen complexes require group-level rules.

Rotation lengths 3–5, 6–8, 10–12 years are configurable. Longer horizons allow more crop diversity and potentially longer breaks but impose greater forecast uncertainty and operational complexity; do not reward length automatically. Candidate 8-year sequences are illustrative only and require full agronomic review: A \= chickpea → winter wheat → millet → peas → winter wheat → sorghum → winter barley → oil flax; B \= black fallow → winter wheat → chickpea → winter barley → millet → peas → winter wheat → sorghum; C \= mulch fallow replacing black fallow in B. Check cyclic boundary and sowing-date feasibility.

# **8\. Crop climate suitability and risk model**

Use independent feature groups to avoid counting precipitation twice. Suggested explainable screening score (prototype, not probability):

Suitability(c) \= 0.35·TempFit(c) \+ 0.35·WaterClimateFit(c) \+ 0.20·SoilFit(c) \+ 0.10·RotationFit(c), each component ∈ \[0,100\].

Weights are configurable and must be calibrated against regional agronomic evidence. Hard constraints apply before weighted scoring. WaterClimateFit is based on historical seasonal rainfall distribution, dry spells and stage-specific exposure, NOT an asserted soil-water deficit. If soil data are missing, mark SoilFit “uncertain” and evaluate scenarios; do not fabricate a precise score.

Historical crop exposure can be summarized as median, lower-quartile and worst-year indicators. A crop with high average suitability but severe tail risk may be excluded from the resilience strategy. Distinguish “climate hazard” (observed) from “crop damage probability” (not calibrated).

# **9\. Water balance: optional research module, not MVP ranking ground truth**

Soil-water bucket: SW\[t+1\] \= clip(SW\[t\] \+ P\_eff\[t\] \+ I\[t\] − ETa\[t\] − Runoff\[t\] − Drainage\[t\], 0, AWC). ETc\[t\] \= Kc(stage,t)·ET0\[t\]; ETa is limited by soil water and stress response. FAO-56 Penman–Monteith ET0 needs radiation, temperature, humidity and wind; temperature-only Hargreaves is a fallback with higher uncertainty.

Unknown AWC, rooting depth, initial soil water, runoff, crop Kc and residue effects prevent trustworthy field-level millimeter forecasts. Therefore show this as a sensitivity sandbox only, with explicit assumptions, and do not use the earlier illustrative “mulch fallow \+27.8 mm” as evidence. Compare fallow types qualitatively unless calibrated.

# **10\. RUSLE water-erosion model — scientific specification**

RUSLE estimates long-term average sheet and rill erosion from rainfall-driven overland flow; it excludes gully erosion, wind erosion and sediment delivery to rivers. This MVP is a RUSLE-style factor implementation, NOT the official USDA RUSLE2 software.

A(x,y) \= R(y) · K(x) · LS(x) · C(x,y) · P(x,y)  \[metric tonnes ha⁻¹ yr⁻¹\], using mutually consistent SI-compatible R and K units.

| Factor | Data \+ calculation | Critical caveat |
| :---- | :---- | :---- |
| **R rainfall erosivity** | GPM IMERG Final half-hourly rainfall; segment storms; R\_y \= Σ\_events (E\_event × I30\_event), E \= Σ\_intervals e(i)·depth; average over years | IMERG rate vs depth conversion; sub-hourly extremes and storm segmentation are approximate; do not substitute annual precipitation |
| **K soil erodibility** | SoilGrids sand/silt/clay/SOC, depths 0–5 and 5–15 cm; validated EPIC/Williams or regional pedotransfer with documented unit conversion | SoilGrids 250 m; coarse vs 30-ha field; uncertainty quantiles; soil structure/permeability unknown |
| **LS slope-length/steepness** | SRTM/NASADEM 30 m → metric CRS EPSG:32636 → hydrologic conditioning → flow routing → slope → published LS formula → zonal stats | Flow contributing area from buffered catchment; DEM artifacts, field boundaries and microrelief matter |
| **C cover-management** | Crop-stage calendars \+ HLS seasonal cover \+ farmer residue, tillage, fallow; reference soil-loss ratios weighted by within-year rainfall erosivity | NDVI is NOT residue cover or C directly; future rotation C is modeled, not satellite observed |
| **P support practice** | Farmer-reported contouring/stripcropping/terraces, with slope-specific validated practice tables | No documented measure: P=1 as transparent baseline; no-till belongs primarily in C, not arbitrary P discount |

One compatible event energy approximation (when intensity i is mm/h and e is MJ ha⁻¹ mm⁻¹): e(i) \= 0.29·\[1 − 0.72·exp(−0.05·i)\]. Event erosivity EI30 \= E\_event \[MJ/ha\] × I30 \[mm/h\]. Only use this after checking publication-specific coefficients, IMERG 30-min sampling and event inclusion thresholds; apply a documented minimum erosive-storm criterion. Avoid interpreting half-hourly satellite rainfall as exact gauge-measured peak intensity.

Temporal weighting: C\_eff(y,x) \= Σ\_m \[R(y,m)·C(y,m,x)\] / Σ\_m R(y,m), if monthly C is represented by calibrated soil-loss ratios. A\_y(x) \= K(x)·LS(x)·P(y,x)·Σ\_m \[R(y,m)·C(y,m,x)\]. Average across historical weather scenarios and cycle phases, not a single arbitrary calendar alignment.

Field soil loss tonnes/year \= Σ\_pixels A(pixel) × area(pixel in ha); area-weighted mean \= total tonnes / 30 ha. A factor-average shortcut R·K·mean(LS)·mean(C)·P is only valid under restrictive spatial homogeneity assumptions.

Wind erosion: optional Wind Erosion Exposure Index \= Σ\_d 1(WS2M\_d ≥ threshold)·DrynessProxy\_d·BareSoilProxy\_d; a dimensionless, locally normalized exposure indicator. It is NOT tonnes/ha and cannot be added to RUSLE A. Wind erosion physics needs soil aggregation, friction velocity, surface roughness, residue and validated local models (e.g. WEPS).

# **11\. Rotation optimization: exactly three distinct strategies**

Generate feasible sequences via constraint programming / beam search / MILP. Score only after hard constraints. Use robust normalization against the SAME candidate pool, units and climate scenarios; do not interpret a normalized score as a probability. Candidate sequences are cyclic and must also be feasible given known historical predecessors.

Let Econ \= normalized expected gross margin or conservative economic proxy; Climate \= lower-tail climate suitability and hazard resilience; Soil \= diversity, legume role, soil cover, and rotation rule quality; Erosion \= relative improvement of modeled RUSLE A against an explicitly defined baseline; Feasibility is a hard constraint.

| Strategy | Illustrative objective (weights are product choices) | Trade-off / safeguard |
| :---- | :---- | :---- |
| **Economic** | 0.55 Econ \+ 0.20 Climate \+ 0.15 Soil \+ 0.10 Erosion | If farm-specific yields/costs/prices absent: label Economic Potential (proxy), do NOT call it predicted profit |
| **Balanced** | 0.25 Econ \+ 0.30 Climate \+ 0.25 Soil \+ 0.20 Erosion | Use robust Pareto screening and no catastrophic constraint failures |
| **Climate & Soil Resilience** | 0.10 Econ \+ 0.40 Climate \+ 0.30 Soil \+ 0.20 Erosion | Penalize worst historical drought exposure and low cover |

Select the best feasible sequence per objective, then enforce meaningful differentiation (e.g., distinct crop/fallow choices or material trade-offs). If fewer than three genuinely different feasible sequences exist, return fewer with an explanation rather than fabricate diversity. Expose sensitivity to weights, missing economic data, K and C uncertainty. When quantitative erosion inputs are unavailable, use a separately labeled qualitative erosion proxy and exclude RUSLE tonnage from the numeric objective.

Example outcome labels: “Highest economic potential”, “Best balance”, “Lowest climate/soil exposure”. The word “best” is conditional on objectives, input quality, and candidate universe.

# **12\. Scenario comparisons, fallow, and long-term rotation**

Compare each strategy against a credible current-practice baseline, using identical historical climate ensembles and consistent economic assumptions. Show crop-by-year plan, marketable harvest years, sequence constraints, water hazard exposure, average modeled water erosion, uncertainty range, and explicit soil cover assumptions.

Black fallow, mulch fallow and green manure are distinct management states. A year of fallow can lower marketable harvest frequency; black fallow can preserve water under some conditions but expose soil to wind/water erosion; mulch may reduce erosion if residue persists; green manure may consume stored water. Do not assert universal ranking or a fixed water-saving millimeter amount.

Run multiple weather-year alignments across the 2016–2025 historical sequence; repeat or bootstrap years only as scenario stress tests, clearly not as weather forecasts. Rotation horizon is independent of historical record length. Flag crop-return compliance at both ends of cyclic sequences.

# **13\. System architecture and components**

![][image2]

Recommended stack: React/Next.js UI, Python FastAPI, PostgreSQL/PostGIS, rasterio/xarray/geopandas, GDAL, NumPy/Pandas, a task queue (Celery/RQ), object storage, OR-Tools or equivalent constraint solver. LLM is restricted to interview, extraction and explanation; numerical results and feasibility must come from deterministic versioned code.

# **14\. API contracts and data model**

| Endpoint | Input | Output / behavior |
| :---- | :---- | :---- |
| **POST /v1/interviews** | field location, interview answers | session\_id, missing\_required\_fields, validation issues |
| **POST /v1/fields** | GeoJSON Polygon, area, CRS | field\_id, normalized geometry, measured area |
| **POST /v1/analysis** | field\_id, historical period, datasets | analysis\_job\_id, source manifest |
| **GET /v1/analysis/{id}** | analysis\_job\_id | status, climate features, erosion factors, confidence |
| **POST /v1/rotations/optimize** | field\_id, crop catalog, constraints, objectives | 3 differentiated candidates or justified fewer |
| **GET /v1/reports/{id}** | report\_id | source-linked narrative, charts, scenario assumptions |
| **POST /v1/feedback** | report\_id, farmer correction | versioned input update, rerun request |

Core tables: FarmerConsent; Field(id, geom, area, irrigation); CropHistory(year,crop); SoilProfile(property,depth,unit,source,quantile); WeatherDaily(date,grid\_id,variables,qa); ErosionFactors(pixel\_or\_field,R,K,LS,C,P,method\_version); CropRequirements; RotationCandidate(year,crop,management); OptimizationRun(objectives,weights,baseline,uncertainty); EvidenceLink; AuditLog.

Example report object: {"field\_id":"pilot\_30ha","strategies":\[{"type":"economic","rotation":\[\],"feasible":true,"economic\_label":"proxy","climate\_risk":null,"rusle\_t\_ha\_year":null,"erosion\_confidence":"insufficient inputs","explanations":\[\],"sources":\[\]}\],"assumptions":\[\],"warnings":\[\],"model\_version":"1.0"}. Null is mandatory for uncomputed values; never use 0 as a missing-value substitute.

# **15\. Algorithm pseudocode**

1. interview \= collect\_and\_validate\_farmer\_answers()  
2. field \= normalize\_polygon\_and\_confirm\_area(interview.location)  
3. datasets \= fetch\_versioned\_sources(field, period=2016..2025)  
4. features \= calculate\_historical\_climate\_features(datasets.POWER, crop\_calendar)  
5. terrain \= calculate\_LS(datasets.DEM, catchment\_buffer, validated\_method)  
6. soil \= calculate\_K(datasets.SoilGrids, interview.soil\_tests, unit\_checks)  
7. rain \= calculate\_R(datasets.IMERG, event\_segmentation, QA)  
8. cover \= estimate\_C(datasets.HLS, interview.tillage, residues, crop\_calendar)  
9. candidates \= enumerate\_feasible\_rotations(crop\_history, rules, horizon)  
10. for candidate in candidates: simulate\_cover\_and\_RUSLE(candidate, rain, soil, terrain, cover)  
11. for objective in \[economic, balanced, resilience\]: select\_robust\_optimum()  
12. report\_three\_distinct\_options\_with\_evidence\_and\_uncertainty()

# **16\. Validation, scientific governance, and acceptance criteria**

* Unit tests: precipitation mm/day and IMERG mm/h conversions; temperature missing codes; winter crop year crossing; soil depth conversion; area-weighted raster integration; metric RUSLE units.  
* Spatial QA: compare field polygon with DEM and soil grid; CRS, nodata, buffers, catchment edge effects; confirm mean LS from independent method and slope checks.  
* Model QA: compare NASA rainfall against local stations when available; compare R with regional erosivity literature; K with local soil lab or published map; C/P with observed management; erosion with field evidence if available.  
* Counterfactual tests: higher cover should generally reduce C-driven erosion holding other factors fixed; all else equal R=0 gives A=0; no phantom precision for unknown factors.  
* Explainability: every number has unit, dataset, time window, formula version, assumption and confidence. Observed erosion is never added directly as a RUSLE factor.  
* MVP acceptance: completes farmer interview; obtains real NASA climate; returns climate-window metrics; validates hard rotation rules; produces three objective-specific options; displays erosion only when factor data pass QA; otherwise clearly shows “not computed”.  
* Security/privacy: consent, minimize precise field sharing, encrypted storage, deletion workflow, safe LLM prompts, no unsupported agronomic guarantees.  
* Scientific review: regional agronomist signs off crop requirements, disease-return intervals, soil assumptions and C/P tables before public field-level recommendations.

# **17\. Risk register and honest claims for the NASA jury**

| Risk | Mitigation |
| :---- | :---- |
| **Satellite pixels larger than field** | Display grid footprint and representativeness; do not imply field-scale precision |
| **Synthetic polygon vs real farm** | Prominent demo label; seek farmer-verified boundaries |
| **Incomplete farmer history** | Require exact years or conditional recommendations |
| **No farm economics** | Show Economic Potential proxy, not profit |
| **Unvalidated crop scores** | Document heuristics and run sensitivity tests |
| **RUSLE uncertainty** | Quantify factor ranges, show intervals, no wind/gully claims |
| **Overfitting 10-year weather** | Historical scenarios only, no predictive guarantee |
| **LLM hallucination** | Deterministic scientific engine; LLM may not invent data or scores |

# **18\. Implementation roadmap**

| Phase | Deliverable | Exit criterion |
| :---- | :---- | :---- |
| **P0 — Interview \+ POWER** | Farmer intake, field polygon, 2016–2025 climate analytics | Reproducible observed metrics with QA |
| **P1 — Rules \+ 3 strategies** | Crop catalog, sequence validation, 3 objective profiles | Feasible differentiated rotations with explainability |
| **P2 — RUSLE** | GPM R, SoilGrids K, DEM LS, HLS/farmer C, P | Spatial erosion estimates with uncertainty or null |
| **P3 — Validation** | Local agronomy review, observed management, local station comparison | Documented calibration and limitations |
| **P4 — Advanced** | Optional FAO-56 bucket, wind model, economics calibration | Independent validation before claims |

# **19\. References — official source links**

NASA POWER Daily API — https\://power.larc.nasa.gov/docs/services/api/temporal/daily/

NASA GPM IMERG data and access — https\://gpm.nasa.gov/data/directory

NASA IMERG algorithm overview — https\://gpm.nasa.gov/data/imerg

NASA Earthdata NASADEM catalog — https\://search.earthdata.nasa.gov/search?q=NASADEM

NASA HLS project — https\://hls.gsfc.nasa.gov/

NASA SMAP mission — https\://smap.jpl.nasa.gov/

ISRIC SoilGrids documentation — https\://docs.isric.org/globaldata/soilgrids/

ISRIC SoilGrids WCS — https\://docs.isric.org/globaldata/soilgrids/wcs.html

USDA NRCS RUSLE2 overview — https\://www\.nrcs.usda.gov/resources/tech-tools/water-erosion-rusle2

USDA RUSLE2 science documentation — https\://www\.ars.usda.gov/ARSUserFiles/60600505/RUSLE/RUSLE2\_Science\_Doc.pdf

FAO Irrigation and Drainage Paper 56 — https\://www\.fao.org/4/X0490E/x0490e00.htm

FAOSTAT — https\://www\.fao.org/faostat/en/\#home

NASA Harvest field boundaries portal — https\://data.harvestportal.org/dataset/ukraine-field-boundary-delineation-2023

# **Appendix A. Pilot files and reproducibility**

Available working assets in project environment: agroresilience\_kherson\_30ha\_pilot.geojson; N46E032.SRTMGL1.hgt.zip; kherson\_30ha\_ls\_factor.tif; kherson\_30ha\_slope\_deg.tif; kherson\_30ha\_dem.tif; kherson\_30ha\_ls\_summary.csv; POWER\_Point\_Daily\_20160101\_20241231\_046d60N\_032d60E\_LST.csv; POWER\_Point\_Daily\_20250101\_20251231\_046d60N\_032d60E\_LST.csv. Treat derived pilot LS as preliminary. The NASA POWER coordinates differ from the synthetic pilot center.

# **Appendix B. Required disclosures in every recommendation**

“Historical climate exposure is derived from gridded NASA data, not a field weather station. Crop suitability is a rule-based comparative score, not a yield probability. RUSLE estimates sheet/rill water erosion only and depends on uncertain soil, rainfall, management and DEM inputs. The polygon used in this demonstration is synthetic. Economic estimates require verified local yield, price and cost inputs. Please validate recommendations with a local agronomist.”

# **20\. Recommendation Results & Farmer Dashboard**

Purpose: define the exact user-facing outputs of the decision engine after the farmer interview, NASA data analysis, agronomic constraint checks, and three-objective optimization. The following is a PRODUCT MOCKUP, not a completed field-specific scientific evaluation. Every numerical score in Section 20 is illustrative unless explicitly identified as a verified input.

# **20.1 User journey and results page**

13. 1\. Farmer completes guided chat: field polygon, irrigation, soil knowledge, crop history with years, tillage, residue management, conservation practices, business constraints and observed erosion.  
14. 2\. System validates inputs, asks follow-up questions for missing critical information and records data provenance and uncertainty.  
15. 3\. NASA POWER provides historical weather; GPM IMERG supports rainfall erosivity; NASADEM/SRTM supports terrain LS; HLS supports historical cover; SoilGrids provides provisional soil properties.  
16. 4\. Engine generates feasible 3–12-year rotations, checks predecessor and cyclic return constraints, estimates climate exposure and erosion under stated assumptions, then ranks alternatives by three separate objectives.  
17. 5\. Results page presents three strategy cards, annual crop timelines, score explanations, soil-impact indicators, confidence, trade-offs, and a side-by-side comparison against a defined baseline.

# **20.2 Demonstration field and data status**

| Attribute | Example / value | Provenance |
| :---- | :---- | :---- |
| **Location** | Kherson Oblast, Ukraine; 46.7491 N, 32.7091 E | Synthetic pilot geometry |
| **Field size** | \~30 ha | Synthetic polygon; not cadastral |
| **Irrigation** | None | Assumed scenario |
| **Soil** | Unknown field-specific texture; research-area soil may be dark chestnut | SoilGrids/farmer confirmation required |
| **Recent crops** | Sunflower → sunflower → wheat | Illustrative history; exact years missing |
| **Historical weather** | NASA POWER 2016–2025 | Observed gridded dataset |
| **Mean terrain LS** | 0.431 (preliminary) | Earlier SRTM GIS estimate; method/DEM uncertainty |
| **RUSLE R and K** | Not yet measured or computed for pilot | Pending GPM/SoilGrids |
| **Market prices, yields, costs** | Not supplied | Economic score not empirically estimable |

The initial cropping history is a constraint only after actual crop years are supplied. Sunflower is excluded from the demonstration candidates pending verification of return interval, disease risk and predecessor history. A fallow year does not produce a saleable crop.

# **20.3 Three example rotation cards (8-year planning horizon)**

## **Option A — Economic Performance**

Maximize risk-adjusted gross margin subject to mandatory agronomic and erosion limits. Economic winner is provisional until local prices, expected yields, production costs and risk preferences are provided.

| Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Year 6 | Year 7 | Year 8 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Chickpea | Winter wheat | Millet | Peas | Winter wheat | Grain sorghum | Winter barley | Oil flax |

Land-use intensity: 8 productive years / 0 fallow. Expected soil implications: Higher cropping intensity and revenue opportunity; less idle land, but potentially greater drought exposure and variable soil cover.

Agronomic gate: verify actual sowing/harvest windows, preceding-crop feasibility, water and disease carryover, return intervals, and the Year 8 → Year 1 transition before marking this rotation feasible.

## **Option B — Balanced Sustainability**

Balance climate suitability, crop diversity, modeled soil-cover protection and economic opportunity without overclaiming yield or soil improvement.

| Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Year 6 | Year 7 | Year 8 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Mulch fallow | Winter wheat | Chickpea | Winter barley | Millet | Peas | Winter wheat | Grain sorghum |

Land-use intensity: 7 productive years / 1 mulch-fallow year. Expected soil implications: Residue-retaining fallow may reduce bare-soil exposure and wind-erosion vulnerability; forgone harvest in fallow year.

Agronomic gate: verify actual sowing/harvest windows, preceding-crop feasibility, water and disease carryover, return intervals, and the Year 8 → Year 1 transition before marking this rotation feasible.

## **Option C — Climate & Soil Resilience**

Prioritize reduced dry-season exposure, longer protective cover, crop diversification and erosion constraints over maximum annual harvested area.

| Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Year 6 | Year 7 | Year 8 |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| Mulch fallow | Winter wheat | Peas | Winter rye | Chickpea | Winter barley | Oil flax | Winter wheat |

Land-use intensity: 7 productive years / 1 mulch-fallow year. Expected soil implications: More cool-season crops and residue-oriented management; moisture carryover and disease interactions require field-level verification.

Agronomic gate: verify actual sowing/harvest windows, preceding-crop feasibility, water and disease carryover, return intervals, and the Year 8 → Year 1 transition before marking this rotation feasible.

# **20.4 Example strategy comparison — presentation only**

IMPORTANT: the scores below are synthetic UI fixtures to demonstrate the output format. They are NOT computed from NASA data and MUST NOT appear in a production recommendation unless the relevant metric pipeline has executed and passed validation. A higher score is preferable; risk exposure is shown separately as a category.

| Indicator | A Economic | B Balanced | C Resilience | Calculation / display rule |
| :---- | :---- | :---- | :---- | :---- |
| **Overall objective score /100** | 82 | 85 | 88 | Each strategy uses its own weights; scores are not directly comparable as a single universal ranking |
| **Climate suitability /100** | 76 | 81 | 84 | Crop-by-crop NASA exposure with phenology and thresholds |
| **Rotation compatibility /100** | 80 | 85 | 88 | Validated agronomic rules; hard violations reject candidate |
| **Soil-cover protection /100** | 60 | 83 | 89 | Modeled seasonal cover/residue assumptions |
| **Erosion protection /100** | 58 | 80 | 87 | Derived from validated RUSLE scenario comparison; otherwise N/A |
| **Crop diversity /100** | 83 | 81 | 85 | Defined diversity metric, e.g., families, sequences and Shannon index |
| **Economic opportunity /100** | 90 | 76 | 68 | Requires yields, costs and prices; otherwise N/A |
| **Drought exposure** | High | Moderate | Lower | Relative climate exposure, not soil moisture or guaranteed yield |

# **20.5 Soil-impact assessment — required outputs**

| Soil indicator | Output | Method | Scientific guardrail |
| :---- | :---- | :---- | :---- |
| **Modeled water erosion** | t/ha/year; total t/year | R × K × LS(pixel) × C(month,scenario) × P; sum monthly erosivity-weighted contributions; report confidence interval | N/A until R, K and defensible C/P are available |
| **Relative erosion change** | % vs matched baseline | 100 × (A\_scenario − A\_baseline) / A\_baseline; same weather and field factors | Do not compute when baseline is zero or missing |
| **Bare-soil exposure** | days/year or % of days | Calendar \+ crop emergence/harvest \+ residue assumptions; HLS for retrospective validation | Label modeled, not satellite-observed future cover |
| **Wind erosion exposure** | relative index; unitless | Wind speed, dryness and bare-soil/residue proxies; separate from RUSLE | Do not present as t/ha/year |
| **Soil organic matter** | qualitative direction only | Residue inputs, disturbance and legumes as mechanistic context | No numeric SOC increase without calibrated carbon model |
| **Soil moisture carryover** | qualitative / N/A | Fallow, roots, rain and evaporation affect carryover | No mm claim without soil water balance and soil data |
| **Nutrient balance** | qualitative / N/A | Legume N contribution and crop removal require yield/management estimates | Do not promise fertilizer savings |
| **Disease / pest pressure** | constraint and warning | Crop family, return intervals, sunflower history, disease-specific rules | Not a quantitative disease forecast |

# **20.6 Soil erosion comparison: worked arithmetic, not a field estimate**

For illustration only, suppose R=500, K=0.03, LS=0.431, P=1.0 and scenario-average C\_A=0.20, C\_B=0.15, C\_C=0.12. Then A=R×K×LS×C×P gives A\_A=1.293, A\_B=0.970 and A\_C=0.776 t/ha/year. For exactly 30 ha these correspond to 38.79, 29.09 and 23.27 t/year. Relative to A, B is 25% lower and C is 40% lower. Every R, K and C value in this worked example is hypothetical; these are NOT the pilot field’s estimated losses. A physically consistent implementation uses monthly erosivity and scenario-specific cover and computes per-pixel erosion before aggregation.

# **20.7 Strategy objective functions and optimization**

For a feasible rotation x, define normalized scores E(x) economic performance, CL(x) climate suitability, SO(x) soil protection, DI(x) diversity, and RC(x) rotation compatibility. All scores are on 0–100 scales with published thresholds, provenance, missing-data rules and calibration. Weights below are illustrative defaults to be reviewed with agronomists and farmers.

* Economic(x) \= 0.50 E \+ 0.20 CL \+ 0.15 SO \+ 0.10 DI \+ 0.05 RC  
* Balanced(x) \= 0.25 E \+ 0.25 CL \+ 0.25 SO \+ 0.15 DI \+ 0.10 RC  
* Resilience(x) \= 0.10 E \+ 0.35 CL \+ 0.35 SO \+ 0.10 DI \+ 0.10 RC

If reliable economic inputs are missing, the economic objective is UNAVAILABLE rather than assigning invented profits. In demo mode the UI may show a labeled illustrative economic card; in operational mode request missing inputs or use a transparent non-monetary proxy without calling it profit. All candidates must pass hard agronomic constraints and minimum acceptable data coverage before scoring. The three outputs should be meaningfully distinct; use constrained re-ranking or Pareto selection to avoid three near-duplicates.

# **20.8 Farmer-facing explanation template**

RECOMMENDED FOR: \[farmer goal\]. WHY THIS ROTATION: \[top three data-backed drivers\]. EIGHT-YEAR PLAN: \[timeline\]. EXPECTED SOIL EFFECT: \[erosion estimate with interval OR qualitative direction; residue cover; crop diversity\]. TRADE-OFFS: \[fallow opportunity cost, crop establishment risks, market exposure\]. WHAT WE KNOW: \[NASA-derived values, field inputs\]. WHAT WE ASSUME: \[C/P/soil proxies\]. WHAT IS UNKNOWN: \[missing R/K, yield, SOC trend\]. CONFIDENCE: \[High/Medium/Low \+ reasons\]. ACTIONS: \[confirm history, soil test, field survey, agronomist review\].

# **20.9 Developer data contract — recommendation object**

{  
  "strategy": "balanced",  
  "status": "illustrative \| computed \| unavailable",  
  "rotation\_years": 8,  
  "sequence": \[{"year": 1, "crop": "mulch\_fallow"}\],  
  "metrics": {  
    "climate\_suitability": {"value": null, "unit": "score\_0\_100", "provenance": \[\]},  
    "water\_erosion": {"value": null, "unit": "t\_ha\_year", "ci": null},  
    "erosion\_change\_vs\_baseline": {"value": null, "unit": "percent"},  
    "wind\_exposure": {"value": null, "unit": "relative\_index"},  
    "soil\_cover\_days": {"value": null, "unit": "days\_per\_year"},  
    "economic\_margin": {"value": null, "unit": "UAH\_ha\_year"}  
  },  
  "assumptions": \[\], "hard\_constraint\_checks": \[\],  
  "uncertainty": {"level": "low", "reasons": \[\]},  
  "explanation": {"benefits": \[\], "tradeoffs": \[\], "next\_steps": \[\]}  
}

# **20.10 Acceptance criteria for result cards**

* The results screen shows exactly three distinct objectives, or explicitly marks unavailable objectives and explains why.  
* Every rotation displays every year, crop/fallow type, total productive years, and predecessor/cyclic constraint status.  
* All numeric values have units, method version, source, date window and uncertainty/provenance flags.  
* No modeled soil-organic-carbon gain, yield uplift, water savings or erosion percentage is shown as measured fact.  
* If RUSLE inputs are incomplete, soil loss displays N/A and an explanation; an illustrative fixture is visually labeled DEMO.  
* All soil impact claims identify whether they are measured, satellite-derived, model-estimated, literature-based or farmer-reported.  
* The user can compare the three rotations to the same explicit baseline and inspect trade-offs and assumptions.  
* Exported PDF/JSON contains the same disclosures as the dashboard.

## **1\. На чому науково базується AgroResilience**

Наша система складається з трьох різних рівнів.

**Scientific Data Layer**

NASA POWER · GPM · SRTM · HLS · SoilGrids

Реальні спостереження та супутникові/реаналізні оцінки

**Scientific & Agronomic Models**

RUSLE · Climate Risk · Crop Requirements · Rotation Rules

Фізичні моделі, статистика та агрономічні обмеження

**Decision-Support Layer**

Economic · Balanced · Resilience

Прозоре порівняння альтернатив за заданими пріоритетами

Це принципово: **NASA не рекомендує нам сівозміну безпосередньо**. NASA надає дані про природні умови, а ми застосовуємо агрономічні правила та математичну оптимізацію для вибору альтернатив.

## **2\. RUSLE: що це за модель і чому їй можна довіряти**

RUSLE розшифровується як *Revised Universal Soil Loss Equation*.

Вона походить від USLE, розробленої американськими дослідниками Walter Wischmeier і Dwight Smith на основі багаторічних експериментальних спостережень за ерозією ґрунтів.

RUSLE розроблялася та вдосконалювалася USDA Agricultural Research Service. Її використовують для оцінки довгострокових середньорічних втрат ґрунту від водної ерозії та планування ґрунтозахисних заходів.

ARS+1

### **Формула**

$A=R\times K\times LS\times C\times P$

| Фактор | Значення | Наша реалізація |
| ----- | ----- | ----- |
| R | Ерозійна сила опадів | NASA GPM IMERG |
| K | Сприйнятливість ґрунту до ерозії | SoilGrids \+ анкета |
| LS | Довжина та крутизна схилу | NASA SRTM |
| C | Рослинний покрив та обробіток | Культура, календар, рештки |
| P | Протиерозійні заходи | Відповіді фермера |

### **Що ми вже реально розрахували?**

Для нашого тестового поля площею 30 га:

LS-фактор

# **0.431**

Попередній розрахунок із SRTM

Середній нахил

# **1.04°**

За SRTM 30 м

LS має бути перевірений альтернативним гідрологічним алгоритмом. Інші фактори ще не визначені для цього поля.

**Ми ще не розрахували фактичну модельну втрату ґрунту в т/га/рік**, тому що R, K, C та P не отримані з необхідних джерел.

### **Які обмеження RUSLE?**

RUSLE не прогнозує всі можливі форми ерозії. Вона призначена передусім для площинної та дрібнострумкової водної ерозії, а не вітрової ерозії чи великих ярів. Це прямо зазначають FAO та USDA.

FAOHome+1

Також важливо: ми використовуємо **GIS-реалізацію формули RUSLE**, а не офіційне програмне забезпечення RUSLE2. Ці реалізації не можна називати тотожними.

ARS

### **Як це пояснити журі англійською**

> We use RUSLE, a scientifically established soil erosion model developed by USDA researchers, to estimate long-term average annual soil loss caused by rainfall and surface runoff. NASA elevation and precipitation datasets provide environmental inputs, while soil properties and farmer-reported management practices complete the model. We clearly distinguish modeled estimates from field measurements.

## **3\. Як ми оцінюємо економічну привабливість сівозміни**

Тут я пропоную замінити демонстраційні оцінки на **справжню економічну модель**.

Економічна привабливість — це не те саме, що висока ціна культури. Наприклад, соняшник може мати високу ринкову ціну, але й значні витрати, ризики врожайності та обмеження щодо повернення на те саме поле.

### **Основна формула**

$G{M}_{c,y}={Y}_{c,y}\times Pric{e}_{c,y}-V{C}_{c,y}$

де:

* $GM$ — валова маржа культури, грн/га;  
* $Y$ — урожайність, т/га;  
* $Price$ — ціна реалізації, грн/т;  
* $VC$ — змінні виробничі витрати, грн/га.

Це валова маржа, а не чистий прибуток: вона не включає всі постійні витрати, фінансування, амортизацію тощо.

Для восьмирічної сівозміни:

$G{M}_{rotation}=\sum\limits_{y=1}^{8}G{M}_{{c}_{y},y}$

Але для порівняння економічної ефективності краще також враховувати дисконтування:

$NPV=\sum\limits_{y=1}^{8}\frac{C{F}_{y}}{(1+r{)}^{y}}$

де $C{F}_{y}$ — чистий грошовий потік за рік, а $r$ — ставка дисконтування.

### **Приклад — умовні цифри**

| Показник | Пшениця | Сорго |
| ----- | ----- | ----- |
| Урожайність | 3,5 т/га | 4,0 т/га |
| Ціна | 8 000 грн/т | 6 500 грн/т |
| Виручка | 28 000 грн/га | 26 000 грн/га |
| Змінні витрати | 17 000 грн/га | 13 000 грн/га |
| Валова маржа | **11 000 грн/га** | **13 000 грн/га** |

За цих припущень сорго має вищу маржу, хоча його ціна за тонну нижча.

Але ці цифри лише демонструють формулу. Для реального порівняння потрібні актуальні локальні ціни, витрати та обґрунтовані сценарії врожайності.

### **Як врахувати ризик посухи?**

Замість одного прогнозу врожайності ми використовуємо сценарії:

$E(GM)=\sum\limits_{s}^{}{p}_{s}G{M}_{s}$

Наприклад, якщо маємо три погодні сценарії:

| Сценарій | Умовна ймовірність | Маржа |
| ----- | ----- | ----- |
| Сухий рік | 30% | 3 000 грн/га |
| Звичайний | 50% | 12 000 грн/га |
| Вологий | 20% | 18 000 грн/га |

Тоді:

$E(GM)=0.3(3000)+0.5(12000)+0.2(18000)$

$E(GM)=10500грн/га$

Ці ймовірності умовні. У реальному MVP ми можемо класифікувати історичні роки NASA POWER за опадами та спекою, але **частота погодного сценарію не дорівнює доведеній імовірності майбутнього врожаю**.

Крім того, NASA POWER не містить урожайності. Її потрібно отримувати з історичних даних фермера, регіональної статистики або окремої перевіреної моделі.

**Якщо даних про врожайність немає, ми не повинні показувати Economic Score 90/100 як результат реального розрахунку.** Краще показати `Economic Potential: Not yet quantified` або сценарний діапазон з позначкою низької впевненості.

## **4\. Як ми оцінюємо кліматичну придатність культур**

Це один із найважливіших компонентів AgroResilience.

Ми хочемо визначити, наскільки клімат конкретного поля відповідає потребам кожної культури.

### **4.1. Temperature Suitability**

Використовуємо NASA POWER:

* `T2M` — середньодобова температура.  
* `T2M_MAX` — максимальна температура.  
* `T2M_MIN` — мінімальна температура.

Для кожної культури в базі мають бути агрономічно обґрунтовані температурні межі для відповідних фаз розвитку.

Наприклад, під час цвітіння пшениці сильна спека може бути небезпечнішою, ніж на ранніх фазах розвитку.

Ми розраховуємо:

$HeatDay{s}_{c}=\sum\limits_{d\in {G}_{c}}^{}1(Tma{x}_{d}>Tcri{t}_{c})$

де ${G}_{c}$ — період розвитку культури, а $Tcri{t}_{c}$ — критичний температурний поріг.

**Наукова основа:** температурні потреби культур і реакція на тепловий стрес.

**Наша власна логіка:** як перетворити кількість несприятливих днів на оцінку 0–100.

Тобто сама кількість спекотних днів — розрахунковий показник на основі NASA, але `Temperature Suitability = 82/100` — уже наша система оцінювання, яку потрібно обґрунтувати та перевірити.

### **4.2. Water Risk**

Ми беремо опади протягом вегетації та аналізуємо їхню історичну мінливість.

Наприклад, у наших NASA POWER CSV за 2016–2025 роки:

Середні річні опади

# **442 мм**

Опади влітку 2025

# **26 мм**

Дані попередньої тестової точки 46.60° N, 32.60° E, не вимірювання на новому полі 30 га.

Це демонструє, чому недостатньо орієнтуватися лише на середньорічні опади: розподіл води протягом сезону може бути значно важливішим.

Для кожної культури ми можемо оцінити сезонні опади, тривалість сухих періодів та збіг посухи з критичними фазами.

Але **це індекс кліматичного впливу посухи, не вимірювання фактичного водного стресу рослин**. Для останнього потрібні дані про вологу ґрунту та водний баланс.

## **5\. Як ми оцінюємо вплив сівозміни на ґрунт**

Це місце, де важливо не обіцяти більше, ніж модель здатна визначити.

Я б розділила вплив на ґрунт на чотири компоненти.

| Компонент | Що оцінюємо | Чи можемо кількісно? |
| ----- | ----- | ----- |
| Ерозія | Модельна втрата ґрунту | Так, через RUSLE після отримання факторів |
| Ґрунтовий покрив | Періоди захищеної поверхні | Так, за календарем і припущеннями щодо решток |
| Різноманіття культур | Чергування ботанічних груп | Так |
| Родючість | Потенційний вплив на органічну речовину, азот, структуру | Переважно якісно в MVP |

### **5.1. Crop Diversity**

Найпростіший показник:

$Diversity=\frac{Numberofdistinctcropgroups}{Rotationyears}$

Але я б не використовувала його як єдиний індекс.

Наприклад, пшениця, ячмінь і жито — три різні культури, проте всі належать до злакових. Тому потрібно враховувати і ботанічні групи, і повторюваність культур.

Можна використати індекс Шеннона:

$H=-\sum\limits_{i=1}^{n}{p}_{i}\ln ({p}_{i})$

де ${p}_{i}$ — частка років, відведених певній групі культур.

Це математично визначений індекс різноманіття, але **високе значення H не доводить, що сівозміна агрономічно правильна**.

### **5.2. Rotation Compatibility**

Тут ми застосовуємо агрономічні правила.

Наприклад:

* Не рекомендувати соняшник занадто часто на одному полі.  
* Ураховувати спільні хвороби культур.  
* Перевіряти, чи можна вчасно посіяти наступну культуру після збирання попередньої.  
* Ураховувати вплив попередника на доступну вологу та рослинні рештки.

Для жорстких обмежень:

\\\[ Feasible(rotation)= \\begin{cases} 1,&\\text{усі обов'язкові правила виконані}\\\\ 0,&\\text{є порушення} \\end{cases} \\\]

Це краще, ніж просто знижувати рейтинг небезпечної сівозміни.

Наприклад, якщо повернення соняшнику порушує встановлений для нашої моделі мінімальний інтервал, алгоритм повинен **відхилити варіант**, а не дозволити його через високу економічну оцінку.

Інтервали повернення та правила попередників мають походити з агрономічних джерел і враховувати місцеві умови.

### **5.3. Soil Health**

Тут я б була особливо обережною.

Не можна на підставі самого чергування культур стверджувати:

> Soil fertility will increase by 15%.

Для такого прогнозу потрібні окремі моделі органічного вуглецю, поживних речовин, урожайності та управління рештками.

Натомість у MVP можна показувати:

**Soil Health Outlook: Favorable / Mixed / Unfavorable**

І пояснювати, які фактори вплинули на висновок: різноманіття культур, тривалість покриву, наявність бобових, обробіток, ерозійний ризик.

Це буде прозора експертна оцінка, а не лабораторний прогноз родючості.

## **6\. Як алгоритм обирає три найкращі сівозміни**

Це найважливіша частина для захисту перед журі.

Ми не просто беремо три випадкові сівозміни й призначаємо їм бали.

Правильна архітектура — **constrained multi-objective optimization**.

**Candidate Generation**

Створюємо можливі послідовності культур на 8 років

**Hard Constraint Filtering**

Відкидаємо агрономічно неможливі варіанти

**Scenario Evaluation**

Клімат · Економіка · Ерозія · Різноманіття · Покрив

**Three Optimization Objectives**

Economic / Balanced / Resilience

### **Три стратегії**

**A. Economic Performance**

$\max\limits_{}E(NPV)$

Максимізує очікувану економічну результативність за обов'язкових обмежень щодо кліматичної придатності, агрономії та прийнятного ерозійного ризику.

**B. Balanced Sustainability**

$\max\limits_{}\sum\limits_{j}^{}{w}_{j}{S}_{j}$

Зважена оцінка економіки, кліматичної стійкості, ерозії, ґрунтового покриву та різноманіття. Ваги ${w}_{j}$ — наші проєктні рішення, які потрібно відкрито показувати.

**C. Climate & Soil Resilience**

$\min\limits_{}\left({\alpha Ris{k}_{climate}+\beta Erosion+\gamma Ris{k}_{soil}}\right)$

Пріоритет мінімізації кліматичних та ґрунтових ризиків. Показники потрібно нормалізувати перед об'єднанням, оскільки вони мають різні одиниці.

Ці функції — **наша запропонована методологія оптимізації**, а не формули NASA чи FAO.

### **Чому три варіанти — це науково коректно?**

Тому що в агрономії існують компроміси.

Сівозміна з найвищою очікуваною маржею не обов'язково має найменший ерозійний ризик. А сівозміна з найкращим захистом ґрунту може вимагати року без товарного врожаю.

Тому ми не стверджуємо, що існує одна універсально найкраща сівозміна.

Ми показуємо **три оптимальні рішення для трьох різних цілей**.

Також потрібно перевіряти, що результати справді відрізняються. Якщо одна сівозміна оптимальна за кількома цілями, не варто штучно створювати три «переможці». Краще показати її повторне лідерство та найближчі змістовні альтернативи.

## **7\. Що означають оцінки 0–100**

Тут журі може поставити дуже слушне запитання:

*Why is Climate Suitability 84 and not 78?*

Наша відповідь повинна бути такою:

**Кожен бал має визначену формулу, діапазон, джерело даних і правила нормалізації.**

Наприклад:

${S}_{climate}=0.5{S}_{T}+0.5{S}_{W}$

де:

* ${S}_{T}$ — температурна придатність;  
* ${S}_{W}$ — показник водно-кліматичної придатності.

Але ваги 0,5 і 0,5 — лише приклад нашого вибору. Вони не є науковою константою.

Щоб захистити ці оцінки, нам потрібно:

1. Задокументувати, як обчислюється кожен компонент.  
2. Пояснити походження ваг.  
3. Перевірити чутливість рейтингу до зміни ваг.  
4. Не змішувати економічні показники, вимірювання та евристики без пояснення.  
5. Показувати рівень впевненості та відсутні дані.

Я б навіть дозволила журі змінити ваги в демо та побачити, як змінюється рейтинг.

Це демонструватиме, що алгоритм **пояснюваний**, а не чорна скринька.

## **8\. Які запитання журі можуть бути найскладнішими**

| Запитання журі | Як відповідати |
| ----- | ----- |
| Is this an AI model? | Це гібридна система: AI веде діалог, а рекомендації формує детермінований науково-агрономічний рушій. |
| Does NASA predict crop yields? | Ні. NASA надає кліматичні та супутникові дані. Урожайність потребує окремих джерел і моделювання. |
| Is RUSLE scientifically validated? | Так, це визнана USDA модель. Але наші локальні результати ще потребують валідації. |
| How do you calculate economic attractiveness? | Через урожайність, ціни, змінні витрати та сценарії ризику. Поки цих даних немає, показуємо лише демонстраційні оцінки. |
| Can you prove soil fertility improves? | Ні, не без додаткових даних. Ми оцінюємо потенційні переваги й ризики, а не гарантовану зміну родючості. |
| Why 8 years? | Довший горизонт дозволяє врахувати повернення культур, попередників і довгострокові компроміси, але не гарантує кращого результату, ніж коротка сівозміна. |
| Why should farmers trust the results? | Кожна рекомендація має пояснення, джерела, обмеження, припущення та рівень впевненості. |

## **9\. Як я б презентувала AgroResilience перед NASA**

Ось короткий варіант англійською, який можна використати на захисті:

> AgroResilience is an explainable agricultural decision-support system that combines NASA Earth observation data with agronomic knowledge and farmer-specific information.

> Our innovation is not inventing a new erosion or climate model. It is integrating established scientific methods into a practical crop rotation optimization workflow.

> We first collect field conditions and management practices through an AI-guided interview. We then analyze historical NASA climate and terrain data, assess crop suitability and environmental risks, and generate feasible multi-year crop rotations.

> Finally, we optimize the alternatives for three different objectives: economic performance, balanced sustainability, and climate and soil resilience.

> Every recommendation is accompanied by transparent calculations, assumptions, data provenance, and uncertainty. We distinguish validated scientific methods from our own decision-support scoring rules.

## **10\. Що я рекомендую обов'язково доробити до захисту**

Зараз у нас різний рівень готовності компонентів:

| Компонент | Поточна готовність |
| ----- | ----- |
| NASA POWER climate analysis | Реальні дані, розрахунки виконані |
| SRTM terrain / LS | Попередній розрахунок виконаний |
| RUSLE soil loss | Метод визначений, бракує R, K, C, P |
| Crop suitability | Логіка визначена, потребує перевірених порогів |
| Rotation compatibility | Правила потрібно формалізувати та перевірити |
| Economic optimization | Формули визначені, реальних економічних даних немає |
| Soil health outlook | Якісна експертна оцінка |
| Top 3 recommendations | Демонстраційні сценарії, не підтверджений результат оптимізації |

**Найголовніше для журі:** не потрібно доводити, що за час хакатону ми створили ідеальну агрономічну систему. Потрібно показати, що ми правильно визначили наукову проблему, використали відповідні NASA-дані, побудували відтворюваний алгоритм і чесно визначили межі його застосування.

Тоді AgroResilience виглядатиме не просто як AI-чатбот із рекомендаціями, а як прототип **науково обґрунтованої системи підтримки аграрних рішень**.

### **Офіційні джерела для захисту**

* [USDA Agricultural Research Service — RUSLE](https://www.ars.usda.gov/midwest-area/west-lafayette-in/national-soil-erosion-research/docs/rusle/?utm_source=chatgpt.com)  
* [USDA NRCS — RUSLE2](https://www.nrcs.usda.gov/resources/tech-tools/water-erosion-rusle2?utm_source=chatgpt.com)  
* [FAO — Universal Soil Loss Equation](https://www.fao.org/land-water/land/land-governance-and-planning/land-resources-planning-toolbox/detail/universal-soil-loss-equation/en?utm_source=chatgpt.com)  
* [NASA POWER — Meteorological Data Sources](https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/?utm_source=chatgpt.com)

Моя ключова порада: **до захисту замінити хоча б один демонстраційний рейтинг на повністю відтворюваний розрахунок**, із вхідними даними, формулою та результатом. Це буде набагато переконливіше, ніж десятки красивих, але умовних оцінок.

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnoAAAFfCAYAAADZI2EUAAB1wElEQVR4Xuy9h5scx3Xuff8JBcqybMuyZVtXlmxZliiKBEGAICIBAgSR4yIucs6LtMg555xzzjkQOeecE0GCAHwtX+l+ouqbtxant/p09+wuFg3sDN/zPL9nuk7Fru6derequud/GRqNRqPRaDRaWtr/0g4ajUaj0Wg0WnoYhR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamhqFHo1Go9FoNFqaGoUejUaj0Wg0WpoahR6NRqPRaDRamlrKCr0/f/ONmbZ5h6nQZ6h5v0s/QgghhJBXSqkeA82YNZvMH/74Ry1DUsZSUuiduXnbuwgNRk02C/ccMLvOXTAnbt4yJ2/dJoQQQgh5KU4kNMae85fM8gNHTPMJMzy9sebQMS1HUsJSTuhtOX7adviVR1+YR//1X4QQQgghsXL366+t9hi2fJ2WJUXeUk7ooaOnbtkZuAiEEEIIIXGx69xFq0H+509/0tKkSFtKCb3MCTNMmazBgc4nhBBCCImbdtPmmQ+69tfypEhbSgk9KOmBS1cHOp4QQgghJG5WHz5mtUgqWcoJvXHrtwQ6nhBCCCEkbnacPU+hF6dR6BFCCCHkTUGhF7NR6BFCCCHkTUGhF7NR6JH88Ktq9c133i1tfvRhRc/3VvFy1gfEN2jW/IAvGZI2a9L0QFxeIF/HkeMDfokTHjx7Fhmn80Wxbv9Bm37yirWBOF1uRp9BNvyLKnVsuExm+0Da/BLWVmmL65NwYeoiQXQ/u76XuWcLQ1hbiiK4B9FO3P86jpAwKPRiNgo9kh8mLFsVGGhcEXLv6VPr+8dyVW3436rWC5QRxssOmneffG3zaRGnywUV23Tx/BsOHPbF6XxR5EfozVq3ybL1yHEbLspCTwZj7Sd+dD8Duc77zpwLpI+TsLYURSj0SEGh0IvZKPRIfnj4/HlgoMFxjS5Z9nP4vMWeD4xdvNxL13PCNPNPFaqZH5eubNoMHe0rV9JD6H3Wqaf5qw8qmMyBwwP1a5Am2aAn5eo2Yxbyp+U/C/jBku27zK+rN7BpSjRq5Ytzhd6cDVusoP2Pag3Mxbv3AnUmm9GDMK3fK9v83UefmJ9VqmHGL13pq0cTdg5vQuidu33HVEoI5h+VrGh++Wld03/abF9822FjzD8k+uTHpauY9QcO+eLcttbt2d/8oHh5U71zViD+2JVrnk/+Yfi4dWfPh9lbXLuflP3UnLx2I7SO+0+fmY+atTXffa+M9eO+/XWNhub7xcraz3bDx5rL9x/YuOU795pqnXuZ//1JLXvN9X3n9r17DnLs/nNy5cFD2z8/LFHB/LxyLTN2yYrQsnD8du3G5m9KVTKjFi714i/du2/bJvcf7o3TN25FlhHG7pNnTMPeAxPXp4556/1ypk6PfvaFtG6aPafOmH+pWMOeM46j7oN36zWz7fiwSRvfPY77X9qBf+7+vkwV22bp0+NXrwX6LKx8Qlwo9GI2Cj2SX+RLe/qaDV741I2b9hMDk5tGZtoa9R0c+NJ3v/gl/M8fV/fFY8DU9eu21OzaO+DX5fadOst+QlBh0MPx/sSXim7HTxNCVLcRQCggXsSVbieACHLrTCb0dF6A9uj2h6UX35sQerrNkvfOkycBP4CoSpYXQBwhHsIMYQggnQfly3XT9J48M5DeJcqP2WnEYRuCjpN8UXldvyv0dDoAcanjcV+7aSatWGPj527cGsgPMAOty5Cwpkr77oH8QGbbw9qJf77cMq89ehRIA6asXGvjXaGnQTyFHnkZKPRiNgo9kl8w24Yv7XfqNrVh+QJ3v8z1FzuOf1apphfGf/863s1z9tZtL3zg3IVAG9x8IhTCCGuTCAp3MNLprz58ZMPzN22zYexNRFjElcwUge8VK2N96Be3jCihh+U+hCE+db26/TreTfO6hd5/1siwaVsMGuH5pO8xM4U4t1+kLTLrJuFu4ybb8My1G224cb/BNnzj8WPf+Ui8hEWM/P7FfeeWqcND5iz0fOKft2mrzyf31c3HXwbSAhGCYfW4PhF6TfsPtWGZrY6a/Qa4/xGWWWXMbiJ8+6uvfHVIHsyq6TJ0OkGfz9+W+sSmxwwywst27rHhf61cO7JMiFOERRzqf4pcoYc491xlJpdLt6SgUOjFbBR6JL8s2rrT+1LHMhoGEvizp8+1Psxs4bNYg0zrx8yfpNe4s4Kg69gcEeD6mmUPDbQBYFkV8drvImXg2N1fiMEnmdCLKkPElbskh2M3jRxHCT15oCUM3X7BnXUS38o9+wM+CScTerpOjU6v82m/G+f2i/iaZQ8LzS/iwG0rZgAljaSX5UDdTpdNh46E1iH0mzo7kGfjQX8ejVy/qHLFJ0IvLI3M/Oo82FuKcEafgb582Nqg26HL1WGNzieI4CrfspMNH7p4yctTorH/b0nndUG8K/R0Htm/SqFHCgqFXsxGoUcKgnypYyai9+QZ1ofZCPiwPwufs9dvtv7DFy/bcPsR4wLl6PJ+V6dJwDd64bJAeol3Z8XCiBqMsN+oMEKvaoceXjz2FLpp5DhK6NXrlW3DImDyQ9WO/joA+lP7JJxM6LkUZEZPynaXAHUc2ql9sv9Qt1V8blvP3cr5J2HckpWB9BIeMX9xoH6dRvtduoyZ5KXbeeJUII+ECyr0sOcN4fN37gbSRIVRh+uT46Xbd0fm0WGNxGO5G2Hs00NYBFfn0RNteOSC3L2BkkaXocsW8iP0ymZ28NVLSF5Q6MVsFHqkIMiXOrjxxeNQf1h6bBKftnq9Xb7Dhn4dD6auWmc3iYeVo8vUPo0u4+jlK+bA+Yv2OJnQwwMWaIfspZq0POfnAd3l0u7jp5peE6d7YczOuGVECT13rxlEMgZGWfbT7RfQx5Jn2NxFNp+Esflftz8OoTfDWUrNnj7HjFm03G7CRxz6QuJwbd0ZNMmvw+LTbZV0wN3/hmPxY/kY91G5FjliQud1yxM/lnP1vQWxLcd4CGPAjJxZaRAm9PBwEZbeXZ+08eCFS55v4rLV3syZ2x4djhJ62OaAe87dyxdVhkbi8ZT5iPlLvLAILuybFR9Ec+3ufQNlSrsww4jrDFFYsnFrL01+hJ48KAWwB1H6jZAoKPRiNgo9UhDchxZcP/ZohfkxCyR+F4mXcI8JuYIB4AlYXbebR/s0uh6XMKEns48ueApS4kXoYZbRTYMnTXWdUUIP4IEDXc+/f5b8VTTukrng7ldz69biKYqCCD2AGVzdBonDk7Q6DjN0Eq/Ti0+3FdsBwtKC5gNyxYPgvtMxKp/OA3YcP2XjflMzZ++hJkzoueXLsStGZa+iy9Id0bNzWujJnlChz5SZgTw6rHGFG5D7z51Zkxk8gL2lHzVrFygTT0S75QA86Yy4/Ai9sIdndFsJcaHQi9ko9EgqgVdiYBZM+wkhBUceKNJ+Ql4nFHoxG4UeIYR8O9AzbWDhlh2BdIS8Tij0YjYKPUII+XaAF11jHyqWcH9bq5F9+bdOQ8jrhkIvZqPQI4QQQsibgkIvZqPQI4Xh9M2bptmA5HvmFmzZFvC9DBl9BgR8r4Jtx3J+mzYZcdWdH35TK/dXJlzeZJtSifz0U1Qf5zfeBffTqIVLAv6XKQvl5Of+fJ0UpP2E5AcKvZiNQo8Uhtcp9OIiPwNpfsRCXHBgLRyv4toV5BpQ6BFSMCj0YjYKPVIYXKHXbdwk82HTVqb/9NneYLB6737TeuhIb+C7+vChjesxYYr5XZ1GXjk5vqlm4ZbtvoGkepde9vc3cSwDdkbfgdbfe/J0L+2hC7lv+4fv1pc5Pwe1cOt2X3tBxbadzdC5C8zHrTvZMNqN9kkbSzZpaQbMnGPLkZcEV2jVwcbjfBD+fb0mpuOocabFoOHmk3a577MTkP6zzj1smhKNW5ryiTDKdNMiHu1wz3fl7n3mnbqNbV+g3+BD/Dv1Gpva3fuY+ln9vbTSH4jX/S5+9HOt7r1NuxFjAm10qda5p6nbs69pOXiEfdUMfp4M/dyob86rRt6t39S2qcvYiebt2hnWBwGCa99qyEhLqaatrf+DRi0SbR9l+k2bZc9F1yVoESNtx2fJJq3MwJlzfedTOrOtaZCVbfpOzf2N27DrgDzFMzJt/l0nT3vX7sD5C2bPqTO2zThPXOewuisl7o/sGXPM2y/uT+SFX66/nD+YvWGTmbQi512Lgiv0cK8NmbPAtgHtkTpwP8BfrGEz754Ku6/dPvptot5hcxfa+8CtT4P7OTPRH0PmzLfhsi3bm6bZQ+y123P6jPWhPTW79TaDZs3z9XHtHn1Mza5Z9nqv2LXXa0NOeQtsW6UvAP6G0J/ZiXvvvQbNAm0hJD9Q6MVsFHqkMGihJ/7h8xaZHcdP2mN3Rs8dJDqNnuANku5gg5cbQyjgGAO++EXYVO3Y3SsD7xuTgX/pjl32+H5CnGHAOnntupfXBQP51iPHvLCeMZm/easVZ2gTBki3btB+5Fhbj7Th00R7dB0YSOVYiy85hvDDgAof2q7jw/K4x67QE5/0e6lmrb32gbwG4RqJwV2O2wzL+c1Wt+xT12+Yim062TDYfeq07bfu43N/uq5b4njz4aNWvKCPkEfX4+KKGLcu93xwLfE5Y+0GM3bJcl/+qOug+1DP6EFAy3kkq9vF9UOcbzx4OOAXXKE3csES2x9ufToPwrjn9X2NOLePkG7VC1GYDPwdQtDieNa6jVYES7lSN+5PvEAZx9uPnTCdx0ywL+eu0qGbr13SBvedgG77Ib4hAo8k2q/bQUh+odCL2Sj0SGGIEnruAKWFni4jzC9hGbCADNhth4fPTkHAuYMphKROI0BYSVpXbFy6d9/ObuEYP5fmzSI6YqFtQghh1kuX6ZKX0Ju4fLX9tQUcj1+20usj3Q/a5x6HCT3pd3e2Kj+45+deR7c/xZc1ebqtI0ro4RgzoRA5mIXSdQmjFy310kfVJYQJvajroPO75wYxeOLFPwCV23cN5NF5dbyAmcrF23cG2gRcoYdZUF2GLgth/P5s2H2txTAEJmYUZZY7DFw//F3iePqa9bbvdJqCCr0wQS6gnInLVwX8hOQXCr2YjUKPFIb8CD0Z9ECHkeOsyJEwficXn3qQwCzB+KUrfD5X2Li/uwpxJn4ROE36Dw6UCeRH5UHp5m1t+MilXLFw4e5du4SJYyy7SZ1Y+pTBEz+fJcuUQM7BJS+hh3PDbIv4ROgVa9jcLjHi+PydO5H5QTKhB0GAZU7xQ7TiE+2S83ApiNDDsQg97cen+9N4YfkFiPjG/XKWhjFDmCxtmD/qOuh0FVp39I6xvIv7Bb8HG9Z2nVfHC2Uy20WKWFfoyfIpxJRbh/wTgi0Hcg7w698Tdv+O7r8QZlh2RnmSR9fvCj3gtlPy4T5o+OKaY9nfvdcePn9u2/VBo8xAG3Sd8ren/YQUBAq9mI1CjxSG/Ag97ClyBwEIPSxZYnlWlub0IIFBW/tEjGDAw1417M9qnqhb9uOVbdHOm71whYMLBlLsWfqoeRtvuRS8n9HcS499Sygbab06E8fYVyXneOzKVTtYYokXe+N0PXkJPYBlYdQLkefOemJJEkti6z8/GMjjHicTejjGbBlEBAStzB66+8tc8hJ6KBNthQCXOkTQIC/2xMlSOWb8sE8PoursrduBNrp0HTvJ3gubDh3x0kSlhajA8rE7Wxl2HXR+9CfOG30MEYMlUsy0ueecV90QbNhTKn1z8voNe7/pdMAVepilw7L5sp27fXWcu33HnkfdXv28fPq+hs+9njgPiC/MnkmesOuphd61h4/MZ5162H8iZOkXfQa//jvA3xKuW+bAYZ5PC731Bw55Ww6wNw/bK3BduHxLXhYKvZiNQo+Qbw/Y7K99L4sraPJi6qq1AV8qg1lfEbFvCuzrk9nfguL+I0LIm4ZCL2aj0COEEELIm4JCL2azQm8dhR4hpGBM3Bh8PyK/SwghBWXHGQq9WA2dm7VgWaDjCSEkGfju+KT/CC/cacYC69PpCCEkGYv3HaTQi9Pw5VyiW+7TeYQQkh+KJ76Y8eV858WTzDim0COEFJSMMVNM6Z6DtDwp0pZSQu/Zf//BfjnfeJzz5CIhhOSH4zduebN6Mpu3cM+BQDpCCIkCT8Lju+PQpatanhRpSymhB7vx6Avb0SsOHglcBEIIiaLH3CXeTF7Vgbm/qEEIIXmx69xF+92x5fhpLUuKvKWc0IP99//9o/eFDTpMn2+GrVxvpm3ZaaZv3UUIIaHId8aUzTsCcYQQAqYlGLF6g+k2Z7FPa9x5/JWWIylhKSn0xM7fvmcGLlltinfNvRCEEEIIIa+CXnOXmGNXrmv5kVKW0kKPRqPRCmJP/uv/mFPXb2k3jUajpa1R6NFoNBqNRqOlqVHo0Wg0Go1Go6WpUejRaDQajUajpalR6NFoNBqNRqOlqVHo0Wg0Go1Go6WpUejRaDQajUajpamlhdA7d+uu2XHqnFmx/7BZTgghhBBSCLadPGNOXrup5UZKWsoKvebjZwRebEgIIYQQ8qqpNmiMliEpYykp9Er3HGQ7fs2R4/ZHhvVv0hFCCCGEvAq2nT5nSvUYaHXHn7/5RkuSIm8pJ/TKZQ2xna0vBCGEEEJIXJTulTPJlGqWUkLv3pdPbCc/ePYscAEIIYQQQuIEGmTT0VNanhRpSymhVzZrsGk8dlqg4wkhhBBC4mbUmo0pN6uXUkIPnTt6zaZAxxNCCCGExM2WU2cp9OI0dO649VsCHU8IIYQQEjc7zp6n0IvTKPQIIYQQ8qag0IvZKPQIIYQQ8qag0IvZKPRIKrHn1BnznXdLW35RpU4gXuI0hy5eCqTReV81r6uedCKsz3Cd4SuT2T6QnoQT1o+EFFUo9GI2Cj2SSmgBd/urr0Lj1+0/aMO9J8/wfHeffO1Lo8t+1byueuJi8oq1r739YX32KoQe8h+/ei3gT1fC+pGQogqFXsxGoUdShZuPv7SD13v1m5vvvlfGHlft2NOXRgY4EXqub/Oho76wLt+laf+hXrp/LFc1kKfVkFGeT3BnGHUcgHBC3Nu1G/v8/1a1npev/Yhx1nf/ac57LSXt+w1b2PBffVDBhruPmxJZzzt1m9q4n5T91Ibr9Mh9GbqkyZ4+13e+YRRU6Ol2gKOXrwbiJawFnM4LcB3ddH9d8mMvbtjcRYE2RIH0+RV6Vx8+CrRjwZbtvrJcvlesjBeH9oq/QqtO3vFPK1Tz0uBa6jJW7dnvxWdNmh4oX+4HnIP4G2QN8I5/9GHFyPYBfY6EFCUo9GI2Cj2SKlRq29UOWgcvXDJD5iwMHcTEJ0Kvz5SZnu/u1/mb0Tt6+YqXZvzSlb6BWdJA6GX0GWhGzF9iJixb5cX3mzrbxs9at8nz4Rgcu3LN/LpGQ88/Yv5i07jfYHsMQYd81x49smERMZJW6pbjW1/mzGSivN6TZ5ppq9eb7uOn+tKiPjecn3N3KajQk7aMW7LS/GeNjEBdOqyFXlifnb9z10sHKrXpYobMXhAoKy+QNr9CT8oG6NdP2nXzhN5HzdpZ/6+q1TdTVq71hPekFWtsvCv0IErdfxhw37rlQ2xPXLba1OiS5Qk91CfxKPPX1Rv4ztUVet8vVta2QcIrdu21acL6UZ8jIUUJCr2YjUKPpArugOeGj1y6EvBpflapZiCNLl8onpEj7HaeOJU0D0TdzyvX8mYXAWb/kuUR36Tlq71BWKfD8T+9mAHCsYiFe0+fBtJCPJRu3s78qGRFL06XBbYfO2H6T5ttj39curKvTS6ukAhDp3eRtkTl0WEt9MLSuOncmbOwdBrdjrA2aVzRruPcMqN8rtDT8QNnzvOF1+w7EFl+5YS41PfH6Ru3fNdHZvkk3HLQyEA5unxCiiIUejEbhR5JBQ6cuxAYvCT875/lLn2KT8CMyILNuctubhpdh4CZEh2v87jiThOVx/WFIWl+ULy8DUMIiB+fg2fNt58QdXmVJ/GYGUT47z76xIuTJewwXlbozVy7MZBW59Hhf6lYw4bzK/RKNm6dNJ1GtyOsTZpm2bkzcDrOLTPKl0zoYUkW4dZDRgfac+D8RV/aMKav2eC7Prr8jD6DAj7dfkKKIhR6MRuFHkkF9KCn0cuy7h49TV6DYJcxk2x8/V7ZNoyydR4JY9+gGw5LE1Z38wHDfX7Zcwc2HDhs08iyoC5/65HjvvLcPX7J6gTurFheFGTp9oclctoqbek8emKgLRLeePCIL5xfoZdXumQgbX6WbjFrJmXPXr/Z88tT2xKHJXaEF27ZYcPyz0Z+hN65W3d8dbrpsSSM478vU8WXZt6mrfaTQo+kIxR6MRuFHinq4MlaGbiwUd6NE3/Nrr194cIIPTeNJir+l5/m7iOLSgMfloO1X+dz8zbqO9iG6yVEZ7J0gjyA4aaZvWGzF489YG5cMgoi9EYtXOprB5bKdXtlplR4q3g5+xkm4Ny8r1PoATzso9she/TwcImOAw+fP7fx+RF6Oi/4sEkbG4dydJxbXn6Fnu5rfY6EFCUo9GI2Cj1S1KnaoUfkgFW3Rz9fnBwXVuiBH5euYh8wuHz/QWie8i072lm3ZtnDrAjRaXafPGP38Gn/g2fP7IMc2Cv3N6UqeQ9wuEgemUnan/gi1OUA7PXDE5dYosZMkYiiqPK0PxkFEXpA2oInhxEOq7N8y062z/AwS5iAW/f5IW9JV/KGpQsrOxlIm1+hB/adOWdKNG5lr1H1zln2HpC4RVt3mv+o1sC89X4580FGS987GvMj9CAasZcRD2ugv1C+rh8PtaCfflr+M3t/Sf35FXoQjJgV1GkJKYpQ6MVsFHqEBIFokWN3OU+nSxXQdiwLaj8hhLxpKPRiNgo9QoKIsHORJ2FTCbf98koWQggpSlDoxWwUeoQQQgh5U1DoxWwUeoS8fkYtXGK2Hct5ejajz4Ck8fnhN7UaBnwvy4lr103p5m3NB40y82xHVL1R/qKA9PeCLdssOv51Iv2UVz+7nL5503QbNyngJyRVodCL2Sj0SKpRsW1nOzA26jvIvFM35xclXicVWnUI+AqKO7CfvXU7aXwYWqQcu5L7U2OFxRVpVx48CPyecFTavPxuvyEe59hl7ER7PH1N/p8GLiwi9K5/8YUFx2HtfRkKWo6kz6ufXfDi7At379rjsH8SCEk1KPRiNgo9kmo0GzDUO3YH1ikr15j3GjQzDbJy3n8HIKJKNG5pGiYGRBFPWiS5ZfSYMNW8U6+xb8ak7fAx1lere287m4L0gtuuYg2b+8Lv1s/5zdmRC5aYUk1b+4RO1Ixex1HjEuU088VDBJVt2d60GTbaS6fb4LZl/uZttgx9jk36DzbFMzLtOYg/DCkXbXDbccj+8kVbUz5xHlcePAzUK3294/jJQN8ALfR0nbe+/NLcefLEVOvc017H9iPGBspwQV+hj93r7ZbrznzhtTa2zJFjAzN6OD8552QzfIg/f+eO+W3tDBvuPn6y7eea3XJe7eOWI+1Ys+9z80GjFqZqx+7m/rOcX7LQZeLT7Wf48DN8yAcBuPvUafN+RnN7byLePS+pS8LNE38buFfdPiGkqEOhF7NR6JFUI0rojViw2H7eePzYDnY6HsfJhF6F1h3NgfMX7LH8/NnAmXPtYO3WHzWjt+XIMdNnygwvvP7znFe8yEuVwdgly+1nmNDDYC3x0lYcQ1zg88ily1as4TjqHCCyqnToZo8/adfFht14fRyGGy/thLAr26JdIE1YuXM2bA6tI5nQw7UDEFEiiMKEURjoXywz63JFEOF1NiLO8NoRSeP2oW5PGEgDcaf9958+9WZldTlyr7r16jLxqYXetNXrvDxy/0EA49MVeu4/CW0T/wgcvJDzCxuEpBIUejEbhR5JNWTwnLRitSdqdp08ZQdFF/i7OQPzkDkLkgo9nR+/Dws/ZkkQrt29jw1HCT23LCxJur5OoyfYwVzyhgk9VwhIW3H8+3pNTMvBI2weSRN1DljWlpf3QuBUSoR12e5xGG68tBMCU/ePmxbC2O3rsDryEnqY+cTy5cetO9n47OnB9wsKVx8+tGn6TZvl6xe3XBFEYxcvNwtfvPAY1OnR136+jNCTY/xaCsK9J0/3Zj51GgnrPtPx+NRCT8cDaWuU0AOYuUaexv1y36lHSFGHQi9mo9AjqYY7o1cms50d+DCrgr1LOm2pZrm/j4oZLgyma/cfMKMXLvX8YSIhjDGLl9nPim06BeIELB/j56qkrIt379mZFolPJvSwDImlSxxLW3FcsklL+wkRJOUu2rbD+1ksIP4eE6aY5bv22OOlO3bbsBuvj8Nw46WdE5evMnM3Br8nJO3dJ197fQ2BGVZHMqGHsN6jppfCXbISAst9UXHYNYQwgiDCrCaEsvjfrtPIixfx9PaLGb9kuGWPX7bS3kcSFqGny8GDLbqcsDJfVuhFCTq57oSkAhR6MRuFHkk1XKEHYfS7FwM3BkUsrXUZk7PBHz4sN2JGrvXQUaZp9hDfYIplWeyxkrT4NQQcYyZJ9sO1HjrSioTBs+d76YbMmW8y+g60M0W6bQDLhA16+/eNDZg5x4rSZEIPG+yRdtjchYG2Zk2alhB8rbw2YEYLy5XSBi0OcA7aF3Ycdg5uvNtOCNEWg4bbWTTsGdNppa+xbO76BS30UHbXsZPs8cx1Gz0/ZkN7Jc5XyijXsr05d/uOryyEIdgGzZpnxZWkHTZvka0H9wH2VoogwkM7qKt2jz7eEqgr9LB3D+If+xClHbr9rg/LxQjjXkA7ROihHNwz7nXBXsKeE6d6AjOszJcVerMS/TY8cc4QndW79LT3Le7rsPYTUlSh0IvZKPTItwV3MCWpw+sWLes+P2jWHzgU8BNC4oFCL2aj0CPfFij0CCGk6EGhF7NR6BFCCCHkTUGhF7Ohc0et2RToeEIISQa+O9YcyZ0hPXX7jvXpdIQQkowtJ89Q6MVpFfoMNQ1H8wktQkjBwBezK+yKd+1PoUcIKTDDVq6n0IvTZmzZxS9nQkiB6TB9vv3uWLT3oDlx87Y9rthveCAdIYQkA98drSfP1vKkSFtKCT0YOjlrQc47wgghJL/IrJ7M5t1+8R5AQgjJD/hHEd8df/7mGy1NirSlnNCD4T9xdPasHXvsW9/1xSCEEM2By1c9sTdj2+5APCGEaB48f26W7j9kiie+N0p0yzZ/+ctftCQp8paSQg/Wa+4S70ubEEIIISQumo2brmVIyljKCj3XHn791Jy5ecfsOXvB7D5DCCHhyJe29hNCiMup67fM3S+/0nIjJS0thB6NRqPRaDQaLWgUejQajUaj0WhpahR6NBqNRqPRaGlqFHo0Go1Go9FoaWoUejQajUaj0WhpahR6NBqNRqPRaGlqFHo0Go1Go9FoaWppIfTwHr3TN26/eP/NeUIIIYSQl+bktZvmzmO+R++N2ZfPc3+3Ej9Jkr1klf1Jo+UHjpgVBwkhhBBCXg5oCfzE6tAV60yZXoM9vXHu1l0tR1LCUk7onb11x3b4rnMXAr9JRwghhBDyqjl567bVHkv3HtSypMhbygk9dHTWgmWBi0AIIYQQEheL9x20GuTPf/5GS5MibSkl9GZs2WU7WXc+IYQQQkjcQIO0njxby5MibSkl9Cr0GWoajp4S6HhCCCGEkLgZtnK9FXupZCkl9NC549ZvCXQ8IYQQQkjc7DhznkIvTqPQI4QQQsibYsdZCr1YjUKPEEIIIW8KCr2YjUKPfNuo3b2v+fsyVcxPK1QzzQcMN/efPgukKSi/qFLHfOfd0qZMZvtAXKqB8wDaHweop3zLTgG/xBW0HUif0WdQwE8IKbpQ6MVsFHrk28Ltr77yxINGpy0or0Povaq2ClHlRfnjAPWcunEz4Je4grYD6Sn0CEktKPRiNgo98m0hTDg8fP484HfDn3Xqab5frKwXt2LXXvN27cbmreLlzO/qNDGz12+2flfoHb181fzy07qmYpsugTbM37TN/Ee1BuYHxcubyu26mbtPvvbFdxo1wfxDuaqJ/HUSgmWg+fzFS8ylTS7r9h/01bvlyDHzvz+pZcMQTy0HjTS/qlbfvPV+OfOvlWuby/cfBM7RJWvS9MD5C5j5xCzoT8p+atoMHe2Lc/Mv27nHnluDrAG+NGFUSvSPriesXNe359QZ81795ubHpauYZtnDQvNA6G0/dsL8rFLNBDUCaTTXHj0yv63VyJRu3s53P0xesdbXDukf9HtY2wbMmGvr+5tSlUzT/kMD7ZK2IXz86rXQMkYuWGp+XrmW+VHJimb5zr2BthKSjlDoxWwUeuTbwKQVa0IHVgAhBD8GX4QlnQv8+xNfRtovcSK4fly6si8OZUs9e06fDeSV/AACSceVatomsk2u0PvbUp/44gbPmh9IDw5fvBxZXpTQ+3WNhoG0bryEf1iigi/+36rW89KEgTQdR44P+HW5Ev6oWdtAG4AWsP/8cXVf/HffKxMoW7jxxeNAeUJBhJ7OGxWfTOjpvAD/TOg2E5JuUOjFbBR65NsAZrf0wCqUaNTK+udsyPk7kHTVO2f50ol/35lznm/Vnv32UwRX2MAdFR6/dKUNL9iyPTQerNy9LzK/rvfG48ee/9aXX/nSSX7M+CUrT/tPXrthj3/0YUUvHsIJPiyFu+klT/b0OZFl63oePIveH+mWgfOR8I7jJ60PbUL4e8VyhZyuFzOrCGOmUZcPsE/TzeOK8YIKPczkSRizg/Dd/TpnxlbSRwm9zIHD7bErSiX+/J27gXYTkk5Q6MVsFHrk20D38VMDg7Pw6+oNrH/NvgM2HJUuyg9EcGHZLSq9hDUlGrey8VgWFR+WbgfNmp9n/VKvXqJcsn1XoB6dX4fD/Jhxw/G01eu9+N6TZ1rf6IU5P5so6Rv2HmjDhy5eiixb16N9Ol7SYElTlzl11bqAD8fuwx0bDhy2Pi3adR3NsnOXWsWXX6EH4S9hzdglK3xlRAk9nc+l69jJgXYTkk5Q6MVsFHrk28DRy1d8A6uL9utwXn4Q9jCGTq8HcAF5JQ1mCLF3z43X+fOq102LZUwsW89atymQX4fD/GFCr8+UcKEnQkiLmDCwn7Bm194Bv4tbRpjQQ5u0D8flW3b0wvkVeu6eOvFpoSeCa9Ly1b56o5b0gV4Or9sj5+cm8U+FW4bO58KHS0i6Q6EXs1HokW8L9Xple4PnkNkLTP9ps73whGWrvHTuAOzym5oZ1v/XJT+26UXwIC5McOly8GAEwniYA2IBbcD+N3dvYM2ufWzZFVp1CuSXMPbfQbhF1eum/c8aGbY8PFCiy5O9dxAwKE8vxeqy+k6dFTozKuGCCL1kcbpcHcY+yH5Tc6+dzCS6aZr0G2KGzlnohaNeodNjQu75QDi6s6oi9P7JWd6FT46BrrdGlyxbTq+J0+0DIxIv2wMArrsuA3snJfxx6852trJOQhS6dRCSrlDoxWwUeuTbhLt/TPj3z/wPDehBPCxOD9RhgiusHJ0XXLh7LzIOgkbyYi9afuoFI+Yv8aUNexjFFWTg3K07oe2G300H6vbsHzinuIXe9UdfBNqh38EHH2bA3DTjlqwMlO2C5XZJi5k/ORahd/Pxl77ywmYS3RlHF4nHXkTXv3jbzkAa7BHV+d14QtIVCr2YjUKPEPI6Gbt4eb4EzJsSOlKvCD1CSLxQ6MVsFHqEkKLE1iPH7YwhhR4h3w4o9GI2Cj1CSFHCXXptNWRUID5uKPQIeb1Q6MVsFHqEEEIIeVNQ6MVsFHqksJy+edP8plZDS+N+g8zJ6zcCaTTbjh0P+F6WCq06BHxg96nTZvDs+WbjwcOBOCGjT/Kf6sI5aV9hSFbegi3bLNpP4iGva/86GbVwySv9mxDwt9lt3KSAPy+S3aeEvGoo9GI2Cj1SWDCYNBuQ+x6yCq07mhHzFwfSubzKQS1K6HUfn/eLZvMa7F/1gPeqyyMvT17XnhDyeqDQi9ko9Ehh0UIPiKDBj9DjfXMtB48wJZu0tD7MWmGWAbMYCCNv5zETrGAbOHOu9R04f8G816CZ6T15uin/QshhphDldhk70RRr2Mz6UMYHjTK9stw2Ve/S0/rxo/V7Tp8xv6vTyM7wlWrW2suLOiUv6kYbh85dYEo3b+udx4dNW5n+02fnKdIQX65le5OdSPv5ufPmt7UzTNexk0xG34GmXq+c15EgDeqTOuV8Jq9c45vRwzm1HjrKtB8x1mvv7+s1MZ1Gjff1SRTobwjdmt16m7o9+3p1Fc/ItOeJn9VqPXSkGTRrninRuKWZsmqtTSP9CrJnzPFmQ5EXaXFN0JfwlclsZ6p06Gp6TJhiz1XytR0+xvYB8tx7+tTLj77pM2WG14945QiOcT7tR441q/fuN1cfPrQ+1F2ySSvr0+fmgrSoH/fP1MQ5jF+2MrR+tLN6l1623HfqNrY+3B/on06jJ5h36uX4dP26PpeoviqbOM+m2UPsdZW+wn1Wo2uW/VvA+wrRX7gXWw0ZaU5eu+6b0ZuSuBdwH37Srou9B+DD/QxhimuH9l26dz/QHviRD9dJ+tid0UN+fQ0A+gt9UKVDN/spZbnlIh/6Y+7GnLECr5yBv8uYifZe40w0KQwUejEbhR4pLMmEnstnnXt4x1EzepIPA9qmQ0dC4yQeL5nFcdSMnrtk5RvYho22P2aPY3dWJ6zNri+vJTCkvfLggReW32QFpZrmiDVdhxt2hd6YxTm/OgGkvTpvMnpOnOodv50QuPhEfvntVQnrY7fPxQfR7ZYtfjd/2DWAaOr2YlbVTYs+x+/yQlicSIgcN4+0VdcVRubAYWbr0fD7CEj9F+/eMxXbdg7Eu0IN/wTgU9e/7vODgXwC+qrftFn22O0rCE9JI370z6ELl+zx2v0HzLC5C31luUIv7Lrgb+zj1jnvDMQx7gk3v86388QpL60r9CRergGORy7I/Scp7NqGHWPWXsQmRC2FHikMFHoxG4UeKSzJhN6KXXtNuxFj7GDiigFX6NXsmmVnOzDYuYNK80SZCMtgjmOXhVu2W3+YyABa6LlsP3bC+t3BL6wctz161lDjppWwS1QaOXaFns6L9kI4YlYP4WQCB2w8lLsvsU6PvgkBmjNT5abBYC3Hbtz6hLjBjM2nHbvb8NglywPtsfmd/nL7EbM/mBVFf4nfLR/XRfZ1uu2RdBqdRhBx5gLhpetfvH1n6LULu/a67tELlwbyuUj7CtJXAH2AOLQV4SihJ/n0XruwZeewvooSenINcOz+LUoZbllhx65v9oZNFHqkUFDoxWwUeqSwaKEHASEDK5af8HnnyRPf4OAODOKHmJFjPEih4yFYlu3cbY+x7Cfx79Zv6h27uAMjljplhk2W84AWO5gFwvF9Z8lR4l2xEDaoal/l9l29Yywfh6XRfSL94p6TtBd9qPPp8gRZinz4/HlkWgmfvXXbJ5rgf9tZigXS70BEcpjQu3D3rndtMIuWTOjNXLfRNOk/2POj7zuMHGcmLl/t+WTpU7cdrD9wyDdLjBkmpMurfpmJChN6un75Wbiw+gHSQty5PncZO6yvjlzKmYkGK3bvtbOOrtDDtcDSOmZfpd78Cr1zt+/Y44Yv4uMSesPnLbJL7uKj0COFgUIvZqPQI4VFZmdAo77+p24hNCBa8Jui7kCDAdobxG7ctEubEBPiw4wUhBJmStzlUDzkUaxhc28vEeg1aVpgyQ3opVbs28KMmLusib1hrqhB+5EG+6sQdgc5EXoQbfWzcn8CTNBiYN+Zc3YfG/b4YYYJPgiX9zOahw6ortA7f+eOFcnYUyftxX4/5HX7RNcpYPCumkhXOrOtt0Sn00LM4ly1aID40uIZ/Q4f2rTqxb65MKFn/QnxjHQQqGFCyxUZ8zZttUuoSA/BCR/EE3xYqly0bUcgv8uqPfvsfkbUCQGFmciw+rH0jX16SCtLlWFCT9cfJvg1Ou7aw0fms0497H0a1ldHL1+xM9joe7lHXaEH0Db8jUj9+RV6E5attCJfZiLjEnoAf9PY44j9pXntpSQkGRR6MRuFHiEFY8ic+QHfmyJqgI3aA5mq4EEL7XudvOn684MWnK+LsH+yCCkIFHoxG4UeIelHugk9kjevW+jV6t7bzlbL8johLwuFXsxGoUcIIYSQNwWFXsyGzs1evCrQ8YQQkgx8d9QenrtXcuDS1dan0xFCSDJWHjxKoRentZ4023zUc2Cg4wkhJBn4YgYPnj/3hXU6QghJRqvJs02JbtlanhRpSymhd+/LJ/bL+b7zugpCCMkLWW7BrJ7M5k3YsDWQjhBCkoHvjk1HT2l5UqQtpYQerFzvIfxPnBBSYGQWj7N5hJCXoXSvQSm3bAtLOaEHK90zp7NXHz5u332mLwYhhGhkVo+zeYSQgrDt9DnzYY8B9rvjm2/+oiVJkbeUFHpiqw4cNfVHTgr8p04IIYQQUliqDRpjFu7ab/7852+0BEkZS2mhR6PRaAWxAxevmEkbtmk3jUajpa1R6NFoNBqNRqOlqVHo0Wg0Go1Go6WpUejRaDQajUajpalR6NFoNBqNRqOlqVHo0Wg0Go1Go6WpUejRaDQajUajpalR6NFoNBqNRqOlqaW00Dt3664ZsHhV4AWHhBBCCCGFpcecxebI5WtafqSUpaTQqzlknL0Ao9ZsMhfuPwj8XAkhhBBCSGG58eWXZuqWnVZz4LduU9FSTujVHJoj8vTFIIQQQgiJi+IJ7YHfvE01Symh9+y//2BF3o3HXwYuACGEEEJIXDx8/txqkEOXrmp5UqQtpYRepxkLTIlu2YHOJ4QQQgiJm4wxU0zpnqm1hJtSQg9KOmvBskDHE0IIIYTEzeJ9B60WSSVLOaE3bv2WQMcTQgghhMTNjrPnKfTiNAo9QgghhLwpKPRiNgo9QgghhLwpKPRiNgo9UpTZcOCw+c67pQP8Q7mqgbRFmaxJ0227j1+95vPL+ej0UfyiSh2bvkxm+0Ccy5YjxwpUrotukw7HQUafQbHXkargnnkd14CQNwWFXsxGoUeKMjLAfb9YWTNgxlwzYdkq8/dlqqTcoBcl9Gat22TR6aPIr9D7dY2G5q33ywX8+UGLioK28WWg0IvmxuPHr+UaEPKmoNCL2Sj0SFHlk3bd7OD/75/VC8RpHjx7Zv6jWgPzg+LlTeVEvrtPvvbF411NGX0Gmr/76BNTolErc+TSFV/86IXLzL9Wrm3eKl7O/K5OE9NjwlQvToTPuv0HTYnGrcyPSlY0vSfP9OXvM2WmzfejDyuan5T91GQOHO7FiTjTuGVL2o0Hj5ja3fuavy31iRW0EEBouy4rL6GHNCMXLA34XbKnz7Xn8stP65r+02b78rptShYum9nB/Lh0ZU+EbD1y3PzVBxVMh5HjfXWhP39bq5H5YYkK5h/LVTXtho8NlOeC85T4nhOmmX+qUM3W02boaF+5GvSL5D9x7bq9dyq16eJL44ru7uOn2r6evGKtjTt6+Yq9xrgPfl29ga/vhYa9BybaUsX888fVTasho3xx6POfV65l+7V+r+Brqxr3G2wFOO7VloNGmnO37lg/6qnbo5/5m1KV7Gx1+ZYdzeUXv1AUNqPnhn9Wqab5afnPbN+7da37/JD14/oeu3LNu3d0mwh501DoxWwUeqSoogc3IDMb7uwGZq+Qrkr77nbGDwMpwm/XbmzjP2rWzitr0Kz5Voi4Zd98/KU9LtYg00xbvd50HzfFigrdDjB11Trz1yU/DrQN4jF7+hybv/WQ0TYOs5CIW7xtp6nZtbf1jZi/xNd+Xc47dZualoNH2nI6jZrgxW86dMTGF0ToaZ8wY+1Gr1wIvFELl1qB4eZ180eFIdrQ3xIGENnffa+MPYboljxoL2ZkcV7NsofaeOlj9EXp5jnXSPoGfebW1W3cZDNw5rxAWzQi9ADE0vilK70wRBzSiNADzQcMt+Js/qZtng/3x5SVa60YQxhtQ75rjx55aXCNJ61YY+89xB29fNWLw/mhTN1WCUNU4j6ECIXQdON6T55hJi1fber27G/7FnHJhB7APxlyPHbJikBbcX3Lt+wUKIOQogKFXsxGoUeKKmEDkzvAaZ+IhInLVvvSyPGQOQsDeTCzh9k/HDfLHmYu3bsf2Y62w8YEfJ+fu2DDa/cdMO83bOETkW4bo5ZudTrQfsQ4K6Lccmp27WPj8iP0MMj/qlr9gF/XiZknHefG5xW++3XOrCkEtZsG/azzLNq607xbr5mdKXPPS+LDlm5xbeCDeJRrW6ltV+s7feOWL63gCj3d3uIZLWxYroWeHdT5tK9U0zb2eMWuvYF6MauGuF9+WsdrK2Y14Zu+ZoOvLMyu6fwSt2znnsAsYjKhd/XhI18Ys+AI1+rWx4YhYHUeXTchbxoKvZiNQo8UVWRgwrJsmF+Hw3DjD164FMiD2S2EZRZK53XTugO8+PQgrpH0+RV6Or8gwi4/Qq9Oj352CVj7dR0ym6SJalNUWIsrzFjpNO65uEh8mNBD3+r0gvS7RtqCZVXx4Rg+2bMo1+LQxdz7wW1jlE9minWdbrowMMOHNJip03EixPpNnR2Ik2uYTOjpsNwXmC1E2N3CIP2g207Im4ZCL2aj0CNFlYptutiBCXu7XH/UIKfz6/ihITN6hy9eDqSXem9/9ZUvrTsDJD7M6O08ccoey6ybGy9hLMkhnEzoYU+Wzifhggg9N38YUib2JOo4Nz6/4byEniyLYik6qoxGfQcH2o1rAx9mOF1/MnRbgIT1jF6yaxHmkxm9lbv3Ber9WaUaNu69+s0DcWGMmL84tD5w5cFDX9zLCD2Z0VuyfVcgja6PkDcNhV7MRqFHijIyOGEpc/i8xWbMouWBAQvLlAhjCRGzJkNmL/D27SH+o2ZtvTyDZ833LYtKGdjHh71MWPaVeJkNkbQgbI+eCDTMCsq+LV0+lvIQxvIujnccP+krG8eYuZQwzuODjJZeOL9CD8t+br1huHv0sK8QfYoHPyRetz2vsBZXWujtOXXGHqNfESeiyC0DD4Yg/HHrzrZ/DrxYEpd0eAAC+/uwVw8POrjn45Jsj548gJOX0EM7cZ3xMAbCuDcQ7+57wzI+zuX3dZvaOBGlcg7I33fqLN854hgPY+A8/rNGhpde4vAAD/YGyj8FEvcyQs9t69jFy22bdB5CigoUejEbhR4p6mDJFLMx2P+GJ1oxgN5/6l/OhUjC4IkHILBshaUwHd8ga4B9whICSi/bYXP9v1SsYb5XrIwtZ96mrV6cDJB46rZk49ZW6EEsuPnxZCjahwc6ZM+fHlQh3lA+/PJUrk6HvNjLBtF6/dEXgQE8L6FXkNeqQFxB1GBfmdtfuk15hfMSegBP2WJ/HmbFRIy68QB7+2QJHW0TP55wxrIjHu7AtZv5Yrk9DGkL+unUjZv2XoDIcdNECT0AwYYHa9CH+AdCbxsAeJoWT2/jSWA8OOPG4WEI1I37ENfQ3Y+HfZzYQ4d7AHv68HCKxGFvHh6YgIjF/YV9iRL3MkIP4KlbPOGMp25PXb9hnwjXfU5IUYBCL2aj0CMkOTKIQujpuKIG2pnXa1XSGVfo6bhvG3j/nhzjoQ0tDgkpKlDoxWwUeoQkJ5WE3rcdCr1c5L510e/aI6QoQKEXs1HoEZIcCr3UgUIvF7yk+t+q1rNL5tgOsHxn8LUwhBQFKPRiNgo9QgghhLwpKPRiNgq99OL0zZtm1MIlZtCseeY3tRp6T3fmF+TRvsKC9uDz7K3bgbj8cOzK1YCvMKA9w+YtMrW797HnK0/X4hhxgqR/u3aGGTBzjhdGurB+CvPlh4Lmy+gzIOCLi23Hjvv6QuNem4KeR2FBu9A+CVdo1SGQprC453Tx7j2v7+VewX3xYdNWXjt0H2w8dNg0H5DzHj0dVxi6jZtk/9a1v3L7rvZzwZZt5p16Ob8MI/yuTu5risLudeTBU8EII15+gg0s3bHbVOvc0/7dNMjKNr9N/E3ousN4ledM0hcKvZiNQi+9cL/88UVdrGEzezx/81Y7EJZo3NJsPZo7ODZMDFy/r9fEfsEjLCJGvqDxhOT7Gc1NzW69vTwywL5bP+fVEi4HL1w0ZVu0M6WbtzVr9x/w0uPTFSgYVCC0MEjKr1GgznO375iSTVqZer36e2mlLTg3DHAfNGrhtVdo0DvbtB85tsAiCH0k5UcNSugfiUP63pOnh6aFD+eC9tfp0df66mf1Nxfu3vWlwef9Z89MxbadLW5ZuEZ9p860/YNwRt+Btp+nrFzjpXHPsULrjqZU09a+9wGin3DdIfLDzu3k9RumafYQL6zB+wPLtmxvqnbs7hN6HUeNs23BQC9p3XLlOHPgMM+HBwJEfOh0q/fu94kRnAs+1+z73F5j1I9+gm/CspWmdGZbC9ov5Qg2f6Lv+k+fbctcsXuvVy767r0GzQLtnpzwazGkwbmjbhxroeemk/CibTtMt/GTPT/uHfkFEZ0H4G/xk3ZdfH9fAPW495FQrGFz27/5EXpVOuT2e3aiX1btyX3/X1hbkGf8i3PFk+4tBuU8GX7/6dPQ9JrrX3yRqLObvafP3Lxlz0Guj4jw9iPG2j5HeySf3PNvJ4Qozgk/VfdBo0x7vyG+cb9Bvt+exnsMcc/r7wCSulDoxWwUeumF++U/fukK78v69I1cf5nMnPeC1eyaFfjJL/2FLmEMVnKMwU8EpMb1Q7RJeny6AsWtR47x2Wl0zkt1D124ZL/M3XicmxzjhbMyKGGgwEuLdbn5xa1fz3IADNb9ps2yAz3ER1Q98OF3R3Esr2e58+SJqdimk5dm2up1XtpbX34ZKAvH8qJmzMDILKgrUqQfuzuCAvnkVSBSHsS9HE9cnvO7qQBi6V5i8JawBnlEYGFQ1jN6+G1gDMRuXe6x66vVvbdvZgi0HTba3nefde7hCS20FSJp8+GjptmLGTD8kyFlXX340MuPGVZ8hs3ohYmqEQsW20+ITqkP8fmdYZaykgk9/KOx9cixQFzUsSB/lxBTEDo6Le6jrMk5r/LRfz95CT20V+5HpMf7DN38+l53hR7E5KQVq+3x6EVLvT5Mhnt+uEe0DwIQM5w4Hjx7fkK8TfHSyD2Pc5K/kczEdxcEP44xmyjfVXmJc5J6UOjFbBR66YWIIYBZNfHjPVoQHBK3+9TpxOC/2oq+9QcOeencL2Y7s9MCLxLOGQwkDsdYytF1g10ncwSXS5jQw+Ahx5i1OnntemAglLB84tzaDMv5dQoMjPhP340HH7fOFVX5RdejgdDDJwZRVyjodGE+178/8WWmffrYnSV1/e7vn4aJDYj66WvWW4GMATKsDFlmjWqn4Ir1hVu2e9cPy5RoH/KH9ZkcD527wGw8mDOgh9V15NJlkzVpmo1D2RBguM8QV6pZa58AwUwc/BB0uJ/dusOEnhxjJhWfmB1yywtrd14s27nbzqAlE3odRo4zy3ftscfVu/T0+nrOhs1eGp0H4NwhYtzzAjUS/4TJsfyj4MbjbyYvoSd5zt+5Y6+dFno6L/JIO6T/QJ8pM8ys9ZvsMfpbt1XAeUDwuu8edNPpPBJ273n3nCD6ZcvE3I1bzOLtO7182JrilkVSGwq9mI1CL71wvygx6yVLJO6XLGYI3AESS2iIxyyOmw6DkF5SAnqAdYlb6GHA9fKFDLpxCj18bnghisPShvkARPGUVWu9WTCd1j12xYrrz1PoLVuZp9DDDOnYJcu9ATOKMKGHfwrwCwu63KjzeKduY1sP6tPlS9qWg0fY/ZGynxT+kk1aBtICVwyImNH3odt30kf6xdhC1LWKAumTCT0IUixd4hizjxCl7m8jh+XRPvfYtzz/4rx88fkUepg5wwwujvMj9GRGD1s68L2AYwgud0Y5Kj/AfYo24B8PnU7nkbB73dxzcrcNoG1yTgA/E4f8MvNMUhsKvZiNQi+90F/+mLHDniYMvBBJ2PuG5Vx8iUJ4YM8MxKB86dbu0cd0GTPRG9SRp8vYiXbfkWzA1gOsC2a82g4fY2dsWg/N+dWAMKGHQb7TqPGmUd9BdkkHPrShfOJLf8icBVZsyEAjbYsSehBfEAJ1e/WzsykSrwcWAe0Zjocxerx4GMNZ7nNnf7DsCr8IPZewssN8AvoO/SJhLLtClGJvkpvPHfSwtwz7tFwhBOS8sSSKWU30o8x8gY+at7Gb5t29hQDXUbcxbJ9Tk/6D7bJqz4lT7XVCX2AZHkuLaAuWTqUctzz3GEt9ui4XiA8Rr0gny5MSxv4s1C/LmfBh+bxS4l6Ra3zk8hVbjtyrYUJP8qK/cV+HtTssHAbSuEIP/YL+wD5T/dAT9hvqMnVY0kGY4zzd+DChh32Y7UaMsdcMM2f6bx1ooeeihZ57r0seEXoA9yxmznG8dMcu2++4r/BwSdjDGPChn4tnZJo1+3L258KHPpqxdoPdXoHvoWFzF9r6ZUm/oEKvXMv2gb8JktpQ6MVsFHrkTRA2EL2KL2535idsMHpTQLCF/ZxW3Mh+NoA9V9gL58aLyH3V4GGI/OzrKioUpXuFkG8bFHoxG4UeeRO8SqF34PwFu8H/047dvYclihIDZ861e8+0Py6w/Jk9Y47tT1m6xGzKy/ZvQcGy3euqixCS+lDoxWwUeoQQQgh5U1DoxWwUeoSQl+Hw1esB3+eXXu3LrQkh6Q+FXsz2Uc+BpvmEGYGOJ4SQZOCLGUj4o56DfGFCCMkPY9dtodCL08as2cQvZ0JIgWk4arL97th88oy58vCRPS7VY2AgHSGEJKNk9wH2+ySVLKWEHgxf0FO3JH+3FiGEuNifx3sxqyezeZcTgk+nI4SQKHadu2i/O/7nT3/S0qRIW8oJva0nTtuOxn/l+iIQQkgUMqvH2TxCSEG58/XX9rtj2Ip1WpYUeUs5oQc7c/OO94Vdf+Qks2DP52bn2Qvm+I1b5sTN24QQEgDfD/K9sefCpUA8IYTkcMvsPn/RLD9wxD4XIN8b6w4f13IkJSwlhZ5rf/nLX8yehMhbtu+QmbppR4LthBASinxhaz8hhLgs2XvQ7Dh11vx/f/6zlh0pZykv9Gg0Go1Go9Fo4UahR6PRaDQajZamRqFHo9FoNBqNlqZGoUej0Wg0Go2WpkahR6PRaDQajZamRqFHo9FoNBqNlqZGoUej0Wg0Go2WppY2Qu///un/mYdPnpoHT74mhBBCCHlp/vDHP2qZkbKWskJv7va93stPCSGEEELiYsTK9VqGpIylpNBrMnaa7fisBcvMgctXA79JRwghhBBSWPCTaEOWr7Wa45P+I7QcSQlLOaGHzm46bnrgYhBCCCGExMWIVRusBsFPr6aSpZTQw+/ZopN15xNCCCGExA00SM85S7Q8KdKWUkLv0wGjTO1h4wMdTwghhBASNwOWrLZiL5UspYQeOnfk6o2BjieEEEIIiZtNJ05T6MVp6Nxx67cEOp4QQgghJG52nD1PoRenUegRQggh5E1BoRezUeiRvPhdnSbmO++WtnQbNzkQn47gXH9RpU7AHzfSz9pfFEE7M/oMCvi/zZTJbP/G7p24kXuT15y8aij0YjYKPZIX8gWfSiKksLypwTqV+piDfhAKPUIKDoVezEahR/JCC73bX30VSENeDakk9F43EE/sG0LSDwq9mI1CjyTj5uMv7eD6Xv3m5rvvlbHHVTv29KVp2n+oJ1D+sVxV7xizG4h3Zzn+6oMK9vj41Ws2rlKbLgEheeOLx17Z4muQNcA7/tGHFX31T1u9PlDGyt37AmXMXr/ZO/6XijXMuVt3fHncMhF2Z2XO3LwVqGP3yTO+PMLkFWtt/My1G720WZOmm3X7D3rHum1RYfCTsp/66v24dedAnS6X7z8ItBVt0XXMcNoHLty956Up1iAzUAbQbXdndyTNW8XL+fK4bXu7dmNf3L9VrRdofxQFFXqZA4f76vpB8fJenFwLUKppG9+55HU/vfW+//zcNoXN6L3fsIUv7feKlTF3v/7aixd/hVadQssMQ9ev0/+8ci1fHP5+w9ro/j3qcu4/febzybF7zX9VrX5kO+Zv2haIu3TvfuBcCKHQi9ko9Egyvl+srPflHTYYdB490ee7++RrL6yFHjh/566XFwMefCLcdhw/6aWTWUMJj1uy0oazp8+x4d6TZ9qwKzIRfvj8uRfuN3W2r4xf12joC0ue/YkvGRyXzezgtQ1hGay3HjnuSy+cvXXbFxZE6On0LyP0JLz+wCEbrtcr24Zd0eJy+kaOIIWAFh/ShpUJQYawK7YR/iCjZWQ7dNvDhJ4Ol2uR068S7jt1lg2PX7oykCcZBRF6Py5d2ab9fd2mNoxr5dblCr0hcxZ6+fJ7P33aoXugTqCFnuSF8JI0+pwlLGKy+YAcgTp11bpA+aBZ9jAb33rIaM936sbNQHkS7j5uis8X9ffYqO9g6/tZpRo2LH3YdtgYX7lyzQfMmGvD//5ZUKyLyMY/h7pdbp2EAAq9mI1CjyRDDxoSlgH/x6Wr2LCIBjeNFnoQjWFlYwZF+0YvXBZa/6GLl2wYg5Ib784MyYzLT8t/5kuz8eARXxiDulvvLz/NnYVBWAbrml37BNqRDBF6EDKuv6BCDzObEg5D1ws6jhwfSCfcefLEV8ek5attGCLaLVOOy7fsFGiXbnsyoYdZU4SlX3V7XPR5CChfp81PPp3O5eCFSz6hF5YvP/cTwLkNmjXfSxsl9DYcOByoY+mO3b6wxEPwIdx78gxf24Qjl6742lCza2+feHLjNG4b9d+jbotul4TlmsvsPWb+osoJo+vYb8cDXST/UOjFbBR6JAo8Yau/pF2QRoSeO8Mk8Vro6Q3qkq4gQk9mFWWwkXh3VkGWDvXALMvFEtaixW2fG35ZoQcx4frXfX7I+t2BTpfrhm88LrjQ6zRqQiCdoM9f2qdnIOUYS4m6XbrPkgk9mYHToicMfR4CZlNnrdtkEWEhYaDT67aEgfPOS+glu58ePHtmryFmiCX9gi3bbZy+1yVe/slwfVFCL+wfAg1mztuPGGfbKfl3nTztKy+MsDa6yAz+pBVr7OcPS1Tw4qSMwgo9PsxBNBR6MRuFHolCf0FrkKbLmEm+MPYeSTgvoSdLt39TqpINY6CSvHrpVvJooaeX2tw8skQoYS10tGiJEnpRS7fY4+eGhSihd+Ladev/Tc0MG5bZybC26/D0NRs8H5YTsRyn6wWnrt+w6bHHzvW7e6OkzCihV6JRq8h26D57GaGHpUm3bVHnoinI0u3flvrEpnVnacGUlWvtZ5TQy8/9BKHn5kFcxRdL5fpel7z63gorX8J5Cb0dx0/5wnKu0q+6PEGWYHUbXWRfnQi+NfsOeHFSrl66/Y9qDQLlNMsO9iPYfOhoIC0hFHoxG4UeCQNCK+yLGmi/hDV5CT2ID50HYHO8LlvCWuhF1Q8RqeNfVuiBf61cO1BHXg9jaKHn1q3R8RJ2l1VddF+6/LZWo0D6sDqihB6EjM4r6D4Luw4S1kJv54lTgfJ0nmQUROi5e0U1iI8SekCnB2H3k8vKPfttnL7Xj16+GkgLanXrEyhPwnkJvbGLlwfKA5+fu2DjMVOo49w6dBs1Or32h13zsDzar+MJESj0YjYKPfKqkS907sVJH+Sarti1NxBHCCGFgUIvZqPQI4VF/svHXjt5Uo//uac2uH5Y6sOScY0uWbymhJDYoNCL2Sj0SGHRSzMAS1Y6HUkd9PXEazLc9xsSQsirgkIvZqPQI4QQQsibgkIvZqPQI+nG6Zs3TbdxkwL+KH5TK+dFynGC9qBd2l9QXkdbX4Ztx46bUQuXBPykaFJU7yPy7YRCL2aj0CNxgcHk5PUb9hhP8Q6ZsyCQpijwOga9VBN6GX0GBHyF4WXPf8GWbfbz2qNH9tzvO682kb5w+0T3z6o9Ob82of3iw6tqtF+XLfcwmPjiJdNumgqtcn9R5be1M974b0G/bF+7hPUXIXFBoRezUeiROBg+b5EZlkD7AQaRLmMnmskr19hXbvyuTiMzdO4CU7Ft7m+4ls5sayq372pKNmllpq/JfaGyUDwj5z1xU1at9Qal39drYj/dGT3ElWvZ3vSZMsNLh4EYx6jznbqNPf+URHtKNmlpBs2a5/naDBvtvYPOHfw+bp3zMmEM7N3GTza1u+e+LiMMtKft8DGm//TZvnLeqdfYDJ4937yd6AP8ni58mBl7t35TTxjjXNuNGGM/wwZg/JICzmPY3IXms049rK/10JHmk3ZdTO/J0708EE04H7QD7a2f1d/65Rx6TpxqGmRl2/ohXvB54PwFmw/XaMicnF+AeDuRPmvSNNvf+86csz53Rq9MZjtTpUNX02PCFFs2fNW79DTZiXOXNMiL/m+Yh6BE3Xg3oD7vKw8emOwZc+yxG6fT4XqG+aN8uuyoexhU79LLfrpCD+e972xOn4QR1VZcE/Qp7ve5G3O+j3HNy7ZoZ/v9g0YtrK9qx+72uqFvcU3ggyjPHDQ84ZtqFm7Z7vW1iOTPOvewfV2qaevIunH9yyfOQ84X8bhWYNG2HWbckhXWD8GNNkheQl4FFHoxG4UeiQMMeMeuhD+QETXYYVCWH3uPSqN9HzTKNF3H5oo6fGqhJ3kwIOLXJiDSLt69FyjLTSu/MnD44mWTNTnnfWbNBgw1Nx9/aeZt2moHP50nGWjP/M05Ay+O8bJknaZC6472010CxW+0Vuvc0x6j7rD68vJhkB6zeJkd+KWv3DRh+d0ZPREMYUCo4tMVem55IoL0LFNYnWGg7rC0rYeO8mb3EI+6IdA/ap77DkYAAS1pdBkQ9vCDvlNzfjtZlx11D09bvc6KYByLKIZgCqvHxY13j7cePR7wS9tdGvfLfYcd/gFa9/lBe63cFxvrvnbZfuyErw4g96Xr1+ch4Rpds8zVhw8D5RJSGCj0YjYKPRIHGX0Hmq1HjgX8IGqwwwC162TOW/9LN28bmkbAjNS9p0/tjBFmwmau22ia9B9s46KEngyAuryowc2Nx/vjMFOD2TfMskjcmn2f2wHZHYDDcAdfiAIIIxyj/RAo8En9rtBbvG2nGb1wqa8tuuwwn4hGgHrRNxBNrmiTfHIOaIuIl2RCD7NxLQeP8LXZFXruDJeUo8XHjuMnbd68ZkJRN0SMzNYKYffQ5fsPEv9gdPP8hy5csmJOpw+jz5SZof9kRN3DMpsG3PPNi7B2a8QftnyOOBfcG0jnLkG7fQ1RhnT9ps2y10eupVt3mADXbZO2aD8hrwIKvZiNQo/Ewclr182HTVv5fPi1AnxGDXZYtgobbMMGl40HD5uRC5bYpVCEUZfMwuUl9PIzo7fn1BlfvAgICKKw9mApbeOh3B+u10QJvZpds+znhbt3vXJf9Yze+GUrvRm9MKEXlg9LuOLTQk+WQ2UJHMd5CT30j7vXTUC7Zm+I/s1aqXvDgUPe7CGA0JRj9zywbCz9XLNb79A0UexPDDb4VRC3bH0PCyUa5/QBiEvohc3o1euVs9zuogWh29eYjXZnj19W6OHvEsvCE5ev8vkJeRVQ6MVsFHokTjDoYDam0+gJnk8PItiLhD1m2BslPgye2LOE/Ua6zLBysB9NjvMSejhG2dgHt2rvfl8aDJpor8wEAeyZkgG/afYQbykXtB851rzXoJlvAMQeNjkOq9sVehA5mL3EbJS0wxV6AMvHxRo2t5+67wS0A32YOXCYDd9/+tTuzXo/o7m3rBcl9OQc0NcQk+LDeeg8AHsCkd7dO5eX0AO4RpIeS8g4J3cPXNi56bpR7/Jde3w+nU/C7swrfC7w4cEKiH7cB3K/uPeRgHsYaTBLuvnwUdMrce9IP4EwoYe9bLIHUoPrhH9SdLsF8WOWrm7PvvacsdcSPohrCFi0xy4xJ66zFnoA5yF+3LO4D7YcOZZvobc+IaxRh5suqr2EFBYKvZiNQo8URcIGz1Tg6OUr3vInyT/YO7l6b87vxeYFZii1T4Pfe002wxpFfsRMftLIgyvpxPilOQ9kEPKqodCL2Sj0SFEkVYUeIekIZiG1j5BXBYVezEahRwghhJA3BYVezIbOHbN2c6DjCSEkGfjuOH4j591/4NZXX1mfTkcIIcnYdvochV6c9mH3AablpFmBjieEkGTgi9kVduV6D6HQI4QUmAkbtlHoxWnnb9/llzMhpMCsOHjEfne0mjzbTNyY80WdvZiv3yCEFAx8dyzctV/LkyJtKSX0YB907W9KdMt9bxYhhOQHmdXTs3uEEJIfPh04KuVm82ApJ/T+8pe/2I6u0HeYOXPnbuBCEEJIGCsPHvVEXvYSzuYRQvLHtS8em1rDxtvvjj/88Y9alhR5SzmhJ1a+99DAf+iEEEIIIa8arCSmqqWs0BP7nz/9yaw8cMRM2bjdDF66xgxaspoQQkKRL23tJ4QQl0kbtpmlew+ap//nv7XsSDlLeaFHo9FoNBqNRgs3Cj0ajUaj0Wi0NDUKPRqNRqPRaLQ0NQo9Go1Go9FotDQ1Cj0ajUaj0Wi0NDUKPRqNRqPRaLQ0NQo9Go1Go9FotDS1lBZ6f/x//88s23fINBw12fuRckIIIYSQwlCm12BTZ9h4M3f7XvPsv/+g5UdKWUoKvW++yfkZNKFy9kjTYuJM033OYtNj7hJCCCGEkJeie4JWk2eb6oPH+rRGKv78GSzlhB6UNTp8+KoNgd+jI4QQQgh51czcvsdqj7O37mhZUuQtpYQelmrR0adv3w1cBEIIIYSQuLjz9ddWg1y+90DLkyJtKSX0es1dYjtZdz4hhBBCSNzUGDLOfNx3mJYnRdpSSuhB5HWdvSjQ8YQQQgghcTN35z6rRVLJUk7ojVu3JdDxhBBCCCFxs+PMeQq9OM0KvfUUeoQQQgh5/ew4S6EXq1HoEUIIIeRNQaEXs1HokVTl4fPn5u/LVDHfebe0jyXbdwXS5oXkdX2/qFLH+spktg+kzy+vogwXaefxq9c8H47D2v9to6B9IOnX7T8YiHtZpMyMPoMCcTqNhJHWDWdNmh64xjoPIekEhV7MRqFHUhUZ/MDgWfPN7+o08cJTVq4NpE9G2EC6eNtOM2vdJrNm34FA+vzyKspwkXa6IuDG48e2DqDTx4nurzdN2DVMhvTZ+Tuv7tVS0oZkQk9fKy309p05Z+NxXXW5uixC0gEKvZiNQo+kIu83bBE6+JVo1Crgd8O1uvUxP6tUw+w5fTYQ74JZnrDZOIk/fPFyopya5lfV6pvL9x9Yfl29gfnHclXN5kNHvfS6DF2P2zbQZ8pMK1jfKl7OvFe/uVl/4FCgbp0vakZvyJyF9lz/uuTHpmrHnr44V1x0Hz/V/OjDiqZ4Rgtz/+kzX7pk6PryoueEaeafKlQzPy5d2bQZOtrzQ9To9v9tqU9sGH0hdUl8o76DzU8T5bh9o9OAaavX235HX6If+k+bHZpeZvQkPHnFWjNz7UZ7LVsMGuHLs3znXtsm9NdPyn5qMgcODy0T/bv92Anzg+LlTYOsAaFpJKyFnjujh7ZJehf846DLccu+/dVXPj8hRRkKvZiNQo+kIjKg/bxyLZ8fA5zEyayXHiSFlXv2R8bnJfTyAsIP6XUZOp2QrPxm2cMi4+APE3o6Hfh+sbJevIiLH5aoEEgnafKioGk1jfsN9uL//bN61nfji8dm2NxFgbZI+LvvlfGVMXHZ6kAaHXZx+0B8WujpPindvJ2XBwJPlwl0mf/8cXVfPNqt00j4ZYReWDkQttpHSCpAoRezUeiRVEQGtLo9+0fGzd6w2Re+8+SJDQ+ftzgwIOow0CItLF1U+JN23SLLAKdu3AzkBWv3HfDNVuo0Es5rjx6O33q/nBfecfyU9ZVq2saGRVxMWrEmULbbHhcRIFFE7XU7cumKja+c6BNZtqzUtqv1nb5xy0tXrkUHr6zvFcsVRm7bzt2+Y8MLt+wItFeHbz7+0lTr3MuKO7ed+xODipteCz1X2OkyAa7PX33gF4M6/U/LfxbwdR49MbTMZEJPl+G248D5i9Y3Z0PO97ekwb3lpiOkqEOhF7NR6JFURAa1ZDN6x674Z/QkzcELlwI+HQZhIk2niwpLnrAyMGsl6fpOneX5mw8Y7vk1uvxkQg/iCcclGrfy0kheLGPiWMTF3SdfB8p287i8rNCbvmZDIK2AODet+A9dvBTqlzBEu/a54SsPHgbqErSw0+FxS1aGlumGNTq+bo/cXxsSX4VWnULLfFmhJ36IYvee0mkIKepQ6MVsFHokFcH+tbCBDeJG+yUsM3rJlgbdssJEmk4XFY4SetgDJ2nq9cr21Sf+ml372PCqPfsjy08m9CSdiDqw6+Rp6/uwiX9GL6x+15eM/KbFfkakbT9iXCDOBfvupA26bPHJjN6CLdsD6dww9gBGxWthp8PYo6fz4HjniZxZUbk+Ot4Nv44ZPZA9fY71Y+YSn82yhwbSEFLUodCL2Sj0SKoigx8YMnuB76nbCctWBdJh5gNP40r4l5/WDaTB07vyRKQWaW66vMJRQk/i/+6jT7xlTKkP7UMc9nMNmDHXSxtWPpYPJV+U0APVO2eZsUtWeGHZO6jFRdi55EVB04KGvQfavWTdxk325ceDIwhPWr7a26/nztZKfkkjx3hoQ6fBsbs8j/Tuvjst7HQ4Suih73CM64Ml71/XaOiL1+1s0m+I+U3NDC8sD7roPPpaJBN6uH/109Vuna6fkFSBQi9mo9AjqcqDZ8/sE5zuQAewf8tNJ/5BCREnx+6mfCAiyx0wtUhzy8ornJfQ0yDuwt17Pt/uk2cC5WNWTOcLE3oQK7qOpTt2e/FaXISdS14UJG2PCVMD7cETqYjDa0R03RIWwS7hGWs3+spw69A+lC8+PM0sx1rY6XCU0AOucAt78lvC0r9CsuVgfS3ChB7+KXHLE79bnvvAByGpBIVezEahR9KdsMGRpBa8htHIk8iYKdVxhKQCFHoxG4UeSXcoElIfXsMg7kyuu4RNSKpBoRezUeiRdIciIfXhNQwiQq9m196BOEJSCQq9mI1CjxBCCCFvCgq9mI1Cj7xOflOrYcAXJ1H1RfnzS7dxk8zpm4V7MW3XsZPM27UzAv7CMmrhkoCP5E3UPRHlz298USPV2kvSHwq9mI1Cj8QBxAb4oFGmdwz/6x5kouo7duVqwJcXblkX7t41954+DaTJL3e//to0zR4S8L8M244d94m7Kw9yXqESF+gH1Fe9S09TonHLQHxBiLo+bwL3nsjok/v7tHndKxJfoVWHQFxRANcK94iE8zofQl43FHoxG4UeiRM9+GFgf7d+U9O43yBTsW1nz/9Zpx4me/ps8/m582bWuo1WQAyaNc/U65X7E2e/rZ1hZ8FQBoSSruvtOo1M9/GTTY2uWaZOj75efeUTbRgyZ4Ep1rCZWb035/dtXYHx+3pNzODZ863v2sNH1rdy9z7Tdtho+1qQ1kNH2nwicBAvM3oPnz83xTMyfeeHz6sPH5r6Wf0T+aeY3yXapduKc4VQQnl6dlDKkL5CP7jtRX3NBww1WZOne22BMEFZ1x498ok+5OudSPdJuy62reIr2aSVGThzrifUzt+5a96p29j2Ez51e13ctshxySYtzYCZc2y/iwBGmzIHDbd9iDBEf+uho0z7EWNNqWat7TlLn7r/COB80a4pq9YG6hYOnL9g3mvQzAydu8A0dESZ5EfcntNnrK9MZjtTpUNXey1wD8GHduL6IO0HjVr4zgVtwX2r/zlBeMn2XfYYYtq9x9Dv7j816GuE3Xbpc3Bpk7jX2g4fY2p372PbBR+uPfquy9iJ3swvBBv+QQAdRo6zdSEdrhvi36nX2L5KpuXgEebMzZyfl8N1wD2izwd/D1J/9ow5ZuPBw/a4bMv2gT5EH6GOZon77n4h/sEhJAwKvZiNQo/ESZjQCzvGABXmL9W0tf3snxBGO46ftMd4f17NbsEN6H2mzPCORVyhLBnw3LLlE2Ji0bbc9+592DTnZ8PCBmbX54oz8R+9fMUKGRxDdEra6WvWm3Wf+38eDHlRhi7LLc+tT2Zklu/aY8WuW5ae0ZPjMYuXmYnLc18cDXEt5aIP3TrQxjkvfhs4L5AHdVTv0ssKPB3fLSG28QmBsWbfAXu8KiGU0R5JAxEtZbl5954566tHly1ApG46dMTng/hzw2H9KPdjWNmuz53Rc/1yX9Xu0cebOZV4fa/LPb1m3+f2Hwk3TuNe07C29Zs2y97HuNY1E//IiN+97poKrTt6adwZPSkf/YdyXR/6EIJYpw1rEyGvCgq9mI1Cj8SJHvzcAcM91rMyLvBVats51O+y/dgJ7xgD9fk7dwLp9MDVpP/g0HJ1Pu1zxdmMtTm/14pzld+O1WWOXrjUV1ZBhZ7E95w41Tdogyih17jfYJ/IdcWvrgtgRgnhFbv2+srXRPWNzBqJSMKnzCKi3bpPospKVo8LZjWRBrNgCI9dsjy0DvcelLbht3BLZ7a1aUYvyrk2bn1RQk/Em+sLqwfIdXJFfxQLtmwLlIdZTdyfIxYstu1BeWDkguC1FjBj2W7EGJtGyokSenJ88/GX5tOO3W04qg/xM3Y4xsyoWx8hrwIKvZiNQo/EiR789CAjx1EDq4DZus2Hjwb8Oo0c53dGDzNeczcG7/+wNrg+Lc5OXrvui5clwihcoYfZKVek6jZKenxChOkZPcx0jpi/2AvnZ0ZP1+US5ksWv+fUGXsOEnaFnvgwEzls3qJAWfphlPzO6LngPGdv2OTL6xIm9FzC+rtBVu7vELv+VXv2mV0nT3nL0W58xTadAmXjvPOzjzFM6Ln1YmuDCL0wUS+4s32SH/2z5cixgN+W27mHFZNnb922YfRhp9ETfGW6YPYby+XaT0hhoNCL2Sj0SJy8jNCD8MK+Iyx3Yf+c+DEzgiU/7E+S/WkuiMeyE5Z1sbQmdeS1R0/2wWFfE/YgwYelRsxwZU2aZvfoSbr/v73zfo/iyNP4X3FhL+w9t/fc7eV77u652/XtrrFxAAwYDDYmOAACg4TISZgcLBCIJMCIFQgTRZIwCDBgMpicjW1yNBkc9n679dKnt4Zvz3eqq0caSW00w/s+z+eZ6erqqurqnq53qqq7i1asMd9to4d5beh5kWXM0UMjWrBoqZkf99WNrxPKqo3etQcPTHlQBuThauh1Xpijl5M/xczFwvLN774z9YQG/dLduwmNP9KAAW4zIC9hjp5ej0/MGUS9op5kOHZrlTlAr6DEtbexw2RuncvoAcwLhNnEfDAZIh8wrcjUr9SrpIMyzKtYZ8Ka5w7wzly7npAWtsHxkrmVl+/e87dHvWAeoJw7LqMHI475nPrOZ7tepBfW3l8ca6lLvR7HOmtsvr8vsg69YbKMOtVpCS6jh3xwjmCeaq+JhTUyetgWw7HSA46ww+fOm95LXccS39Xrjfqy61DmAeI3JqaQkPqCRi9i0eiRpxG7cSNBmmT3DYQ9CTAX0A5LF+zevIZSp4Q0JGj0IhaNHnnaQM8SeyVI1ODPBO9QJaR6aPQiFo0eIaQ2uJ4j6AojhJBk0OhFLFRuQXlloOIJISQZuHYMLo1PzC/dttuE2fEIISQZlUeO0+hFqa7Ti71W4woDFU8IIcnAhVkbO3uZEEJqQt5HZTR6UerRo0emgjcciT2MlhBCagKGacXcta76s4jPY5fjj7IhhJDqOHXthrl2PPzd/9r2pEErrYweVLJ5u6noW+qRAYQQUh2v50/3zd7zefHX1RFCSE3AtaNv8SLbljR4pZ3Rg9buP2IqvHHVxXpcWYV34NxF7+qDB4GDQgghgu7VY28eISQZ1x9+Y64Tk8srvSYj8s11o7B8g21H0kJpafSg+9//zhuyYJl/4SaEEEIIqW9yP1zonf/6lm1D0kZpa/QoiqJSVa85pebCTVEU9bSIRo+iKIqiKCpDRaNHURRFURSVoaLRoyiKoiiKylDR6FEURVEURWWoaPQoiqIoiqIyVDR6FEVRFEVRGSoaPYqiKIqiqAxV2hq9g2cveK0ev7OSEEIIISQKmo6Y6FUeOmbbkLRRWhq9SavWmcp/u3COt3TXPvNqI/v1JYQQQgghteX299975QcOez1mzzeeI3v2AtuOpIXSzuiNXLzSVLh9QAghhBBCogLeo2PBLNuWNHilldH7/Q8/mIo+dOFS4AAQQgghhETF5fv3jQe5dve+bU8atNLK6HWaPNt7I39GoPIJIYQQQqJm1LLVxuylk9LK6KFyC9duDFQ8IYQQQkjUbDx2kkYvSqFyZ23YEqh4QgghhJCo2f75FzR6UYpGjxBCCCFPChq9iEWjRwghhJAnBY1exKLRI3Xhj37T1MlPnm8eiFsbisvX+2na6zrmjQnkK1x78MDEaZYzILD9Hz/bLBDflf6PRU3yx3rsix1eGyr3HahRntVRH2mQ1JF6HzV3vlnGZ30cC/v3oNHPVbXXCT95rn5+8+Tpg0YvYtHokbogF3lpdLSJ2HzoaCB+qoQZvcIlK/zwziMnJKybWbYmqdGzl8FHGzcH8g7DtX1dqO/0qoNGLxzsD+rHDm9ISL1HZfTwm8Py2a9v+mE6bVnOGjPRLE9btioQh5BUoNGLWDR6pC7YjY4OG1/ykVmetHBpQoMBth876ccfXVwaWC/mzQ4HOvzPnm8RKJMmmdG7cPtOIH5NsNOrjtZ9hwb24fLde4H0+hcW+d9/+mKrQJ66R2/v6TOBNHefPO2vP33lamD9rhOnTeNshwO7zGD1jt2BeP/UumNCmTViEP7zzc6BdXgavr2//90hy/+O8J++1CqwHXptZbtb332XsO7TI8cTtq9JvVQH4tfU6En6pes3BcqB46fL0GXUB/661/oPC5Rxzuq1Zp3LhMuy1K8sy2/OTku2fa5rr0D42t37AvsRlg84c/V6Qpo6nhi98p17AnEISQUavYhFo0fqglzgpdHZsP+gH7blcKxHL94w5HtTl67wl298803C+g9Xf+xNXrTce+at7r7R6zVxqr9+YeUnBr0NTKKURdaDdXv3m7BkRk/AUO75W7cD+xaGnV4yuo7O9+OPmVfq/XWT1wLby/KfN27pzatY7/3za53M8is5AxPiiNG7+W3c8KA+u4+b5C/DDOk0/7TRK96M5auN6YbR23r4mDdiTom/XtepjcTpMHSUSePlHn19o4dt7DSOnr9ojqmEo9e129h42ex0/6RRM2/2qgovd+I0E/6zpm29CfMXeSUfb/D6FMwIbId9kbDpy+O9SK602w5435gnDCdiWeqlOhA3VaMH9H5I2M+atvGmLC7zlydW/eHR60cXL/DmrvnYe2fE+DoZvY55o/0w129kwvzF5reF45iq0dPh9rKN/rNHSCrQ6EUsGj1SF+yLvSBz9C7fu2eWf96inb/Nkk+2mjC71+7gV2cD6YcN3UpY0cryQBgQU+QyepsOHE6IKyTr+dHpuLDj22XqOzn+UHIJk0bXlYYdhu+yT6g3LMOgSsMu8XtOmOzcXuMyEy4kDnpk7XV6vQ5793HZln7yqR/2d83fMGFX7t0P3U5ALxQMr8TR8WR5x/FYb/DiTbHzyI6j6wUGB2FSLy50XjbHLlwMxLe3e2PgcD9MzncgZdBmX2+HHlPd0wlcx0aWw4xe2NCthMmfnuqw87HD7WUbuxeakJpCoxexaPRIXbAbHRsZSmuRO9gPO3npsgl7PquXH1a2dYf3H+3e9dNDY43w6ozeX7zQ0hmezOjZyBBgshtI0FjapkqWw3rEgMRFL5Udhl4yvezaTi/LPrmG5IR/a/u2c3uNy0yEgXmW7QaPSMhD1tnLoFGXHBN28vIVP6xF7iAT9tmZL0O3w1C2hE9dujKhnu38xByduBg7j1xxbKReXOjjiLjo8ZRlGDc7vp2X7gHcV9Vg2XlrJB7O6yY9+/nh//BqexNe+dnBQFxZTtXogaIVa7wXuvX21//6nR6BOGH5AD0FwI4nQ7c6LK+oOJAuIdVBoxexaPRIXbAbHRd2QwGDh2UxP/qmjRsP40N/WMZNEvb2QM/7wzCfnVcyo9e7YHpCWsgf6196r29CeBh2esnA8CTi/tXLrc3yzhOn/O3lhhFZXrZ5m1n+/Oq1QB56n+av2xhYDw6fPe+duXY9IU0Mpct6zLfCp2tumwvdK6fTDFsGOKYIa5yVGxrPXgYYUkaYmAf7PNDbSU+wNrx2HJ22rpfqwLapDt3a8SV8vepJw12r+aVLzPcj5y444+P78YuXEpbRyy3LYUYP6br2W463Kx8Xdj41vRlDTyVIdh0gJAwavYhFo0fqQk0u8LqxEP7yxVeTrpdHNVx/+DCwTrZzTWoXkhk9O64gQ4vVYaeXDLuxFDDfzU7PZs/pMwlx9M0YMI52fCBDjf/a5q3AOszRc+X5Xx26Bsptx9GErQ8LB4OmzQ6sTzW/4XN+mxD+9y3fDMSprl6qA3Ft4xaGpG3HHzarOJA/kONnhwPd42ivE8KMnuvGm7B0kv2ZseNqavJ4FWCnSUhNoNGLWDR6pC7IBT6Z0QOYeP7zqoYZ83j0nZRg88Ej3ptDRprJ9mi8MXSm1y/bss2f52U3JlfvPzA3I2AOINLHHLEDX8bn+rmM3icHD5sJ7EgTeeLmj5pO1gd2ejUBc8QwOR9DZ/qOYzu91v3yzJ3EuLHBjqNvzgAY7kaaMDe4+WDb0eMJ61Gvz3bONqb5Fx2zEowshgj/sVUHk26Y0cMwJOaX/W1VPf1Ns7aBnlAYx39pE7txRNcHbsjoNGyMuYsWx8Q+N+z4wqU7d838PAz/unr0AHo9cdPG0JlzvS+u33DGQb3gjl4cW0wHsOslGUjLNm5hSN6u+DD4+COCuscxwE0Xsg5z8zCVAb8F/OFpUxVPb4th7F926maGXPXNLWFGDyB9HCNdH/jdNM3ub/LAsWg/ZFSgnBrZFuC4ofyufdPxAM6P3EmxG1EIqQ00ehGLRo+Qhg16o9Cg5uQXBtY9TRw5d94YQFn+9zficzrtuISQ9IFGL2LR6BHScNE9J/a6p43tx04EepPQY2XHI4SkFzR6EYtGjxBCCCFPChq9iEWjRwghhJAnBY1exKLRyzx+0alrAp8ePRaIo8kaE389k52OHZYKyHf68pWB8CfB7NUVXteq/Uy1PHWtg/qmIdVpOhB2blfHj3Hca5KHK86pK1e8YbPmBsLTCdmvVdt3eR3yRqV8Ttf2uJKGCY1exKLRyzx6fhD+FgAXYRdNVyOTCg3JlLzaJ/7A5lSoax3UNw2pTtOBsHO7IVCTc8sVJxOMntBtbPyhy6nQkI8rSR0avYhFo5d5tOo3xJgBgNd66R69Z97u5n9vNyT26iZ90cx+bBLxoFZXI4O4bQbkme/43Pt57FlviItHQeBhv//zOA8xJXgMRtbYfD8NSRefNx8/1uQ3nWNP7MejJX797nvmOx55MnNF7O0RiIt3xert1+/b701YsChQRhcte8cfTYLyybtt0dNXXLEu4W7Ow2fPee+Nn5SQlwtZh33Ur2+TcDxi4+UefQLb6WPwq3e7m8+WfQZ5+7+IvTlCXvGFMj3zVlbCtrbR0+XDd3lMzCu5A/zwX1alIfV88c6dhPQ0+aWLvXV7PzPfpX5wLm06eCiQlz5npG5hPnS+dt0hzVd6xW+eGFeyMGG95ua33/r1pNORcpV8XBnYxlXvupz9pszwDnz5VUI6YehzVPLKmVjoNe4We5vLm0NGmHx0XDxrDnWNt8Fg+eWesTLgeOnf4LItsQdR6/2StMDyrdu8opVr/DjysGf0SONTG73BM+b42zWvqns8d1KWJe9GXXv6yzpPlAMgPfs80mkA5Hfu5i1/fZdRsYdW67hyjg2fM8/beSJ2DuPc6DM59ugVVx76+OjzAz19cn64ykOjl1nQ6EUsGr3Mw+7Rk0ZmYeUmr1dVYyUm0HWx1YRdYGHm8B0Pau08arz5/myXYGOiTYmEVeza601ZUma+6wYIjRs+Pyhd5K3ZuTuQli6LNAaX7t41DSv2y35nqI02ekhL6kA3hIOnz/Z+9U53s96Vr42s08Zr4/6Dpk7sOtaIkQViiu0ywUBPXLjEW7FtR8K2ttHLyZ/if5+9qtybvy72thH93l4YlPZDRyY89NbF7lOnzXH84vp1P0yXv8eEAt/Qhhk9yXfB+o2+WREGTCvyxv62NGndTFsWOx76GMDsvj+7OKFcqLelm+Nv7gird13O8p17vBe653pr98TeMZwM1/HffOiIOT/xffGmLf6x0XH098LH5znKU53RA6hfmFuEv9Z/aCCOGClt9PR5A9M3tzz+vD7JG6ZJlnV62uj1nRJ/u4xdLqB7EFHP+EOG79q4z6v6w/RcVrbZftTc2LMw9e9OrhU6D318ws4PfNrHLOyaRdITGr2IRaOXeYQZPZgANMB2/LCLpuuCX1ujh54zXKx1D1VtjZ5uPAB6wnSD48I2evZ6mCHpSdNxXHHtONp4oZcRBs2Oq0Gv2eTFy7wZy1f5jbArn5SNXlUdi9FD422n99b7Y/wGOBno2ZMeVl0unFdi9HSjrY2e5OsyeuhRO/TVuUB+Grz9Qr7rvPG6OF0uAFOJHjb0HoXVu+vc3nTgkNckO/wNEcB1/HXdi0my4+jvEndG2SpjEiXctV3jbjl+rx7+tEid6jhhRk/Wu7BNpo6PnkoxetrIudLU610mH72Yct3BcZH4+nent5M87B7XsPMDxwzXDumRdh1Xkr7Q6EUsGr3MI8zoAfSAyXd5Y4C+aNZl6BY9Rq6hW9kWF+qXevT2l7GNDDXqoVv5jgZPD93KdtJ4YIhVwsp37TGfaLRsI6i3ASifmFUAo4jeFElvzLwFzoYeLN8SM6QYVpJ1eh9lG+lhRC+ZXqfj6LRbVJUPz4nTcVxDtyhjWKOs61MbPWk8MYSOIWJ8R33YZnDXyVOBdDF0KybFzguf6AlyGT07PsDQnx7K1r2OQsGipeYT56Zsr4cj7TTRgwXDbK+Teu8/daYfputXHzv7+On1Os3aGj3sZ/dxsbloqGPZTv8Wcc7Lu4/fHj42weglG7odOG1WQm+2pKHLYBs9OUfwO6gvo4f9Qo8cvqPXtDZGL+z8EIObO2mqf82S85hkBjR6EYtGL/NIZvQu3r7jtRs83GvUNdsfDtEXWzS0GFrE0JTrgo+4aHgxH0h6jwDmVGHOn07LNnowM0fPx1/ofvX+fa9ZTn/v9UHvmyFdCUeDjJ4aGb4CuizSeOBNCbhjD+WVhmXd3v3+kJnGNn+Dps8yw7Qdq7aXMuE7jOjJS5f9/DbsP2gaYVlGI/zie71N74s2CzptNLYdh402N4CUfbo9UBaAfdPz2cCE+R+ZfWk7cJgfdqKqLIgn870A6hh5o4E+f+uW2TeUW/eGaMMFI9Q0p59v4oFtIAHm4sG843ggXQmHWUIeOgzGuml2P/NatTCjhzpq1XdwVX3l+mGoa8SHGZC5bJp+hTNN7/DqHbv8+s0rmmuGBHW5cA7juOh5fqh39BLresd5CUODsiFNGFf0nsnr4GBUXe/BrU+jB7APKC9evyfbIV+c59gGf5JwTuA3ousU6+asrjBzOcXQ2sYM5xrS7jN5utlfCZcy6N8/5sHheLwzYmzC0G1djR7A3DyU49TleHqpGD2A8wP7imuJnB8wkDhmH65Z68dDmKucJD2h0YtYNHokFewLc03AXLrRxfNNQ63DMUl75NwS07jr3g1CCCFPDzR6EYtGjxBCCCFPChq9iIXKLaqk0SOEEELIj8+20zR6kapx3nhvQEnwbjVCCCGEkKgp2bqTRi9KTSirMBVsVzwhhBBCSNS0Hlfovf7BdNueNGilldH7wx8eGaO380zsqfyEEEIIIT8GZ2/dNh7k9jff2vakQSutjB70f7//wVR09pwF3q1q3jBACCGEEFJXRixZlZYmD0o7oydChWuajZzktZ9U5HUomEUIIYQQUivaFxR5zUcXBHzGo0ePbCuSFkpboyc6feW6N2nVOm9gyRKv6/Rir8u0uYQQQgghtab/vMXe+LIK79DZC7btSDulvdGjKIqiKIqi3KLRoyiKoiiKylDR6FEURVEURWWoaPQoiqIoiqIyVDR6FEVRFEVRGSoaPYqiKIqiqAwVjR5FURRFUVSGikaPoiiKoigqQ0WjR1EURVEUlaGi0aMoiqIoispQ0ehRFEVRFEVlqGj0KIqiKIqiMlT/DyrTWAVyZUv2AAAAAElFTkSuQmCC>