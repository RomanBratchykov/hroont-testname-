# AgroResilience — External API data specification (MVP)

**Scope:** Data retrieved from NASA, ISRIC and FAOSTAT only. No farmer questionnaire. Coordinates and dates in links are examples for the pilot field; replace them dynamically.

## 1. External data — exact variables and API access

| Source | Variables to extract | Model use | How to call / starting endpoint | Integration caveat |
|---|---|---|---|---|
| **NASA POWER Daily** | `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN` | Climate, ET₀, water balance | **Direct JSON GET:** [daily API](https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M%2CT2M_MAX%2CT2M_MIN%2CPRECTOTCORR%2CRH2M%2CWS2M%2CALLSKY_SFC_SW_DWN&community=AG&longitude=32.7091&latitude=46.7491&start=20160101&end=20251231&format=JSON) | Replace coordinates/dates; gridded regional estimates |
| **ISRIC SoilGrids WCS** | `sand`, `silt`, `clay`, `soc`, `phh2o`, `bdod`; depth and quantile | Soil suitability, approximate K, water parameters | **WCS:** [GetCapabilities](https://maps.isric.org/mapserv?map=/map/clay.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities); [WCS docs](https://docs.isric.org/globaldata/soilgrids/wcs.html) | Call `DescribeCoverage` then `GetCoverage` for each property/depth; raster, not JSON; 250 m, modeled; verify layer IDs/CRS and availability |
| **NASADEM** | DEM elevation → computed slope, flow accumulation, LS | Terrain / water erosion | **CMR metadata JSON:** [granule search](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=NASADEM_HGT&point=32.7091,46.7491&page_size=10) | Search returns granule metadata/download URLs, not slope/LS; retrieve raster and compute locally; verify collection identifier |
| **NASA HLS** | S30: `B04` red, `B8A` NIR, `Fmask`; L30: `B04` red, `B05` NIR, `Fmask`; derive NDVI | Vegetation cover / phenology proxy | **CMR metadata JSON:** [HLS search](https://cmr.earthdata.nasa.gov/search/granules.json?short_name=HLSS30&version=2.0&point=32.7091,46.7491&temporal=2025-04-01T00:00:00Z,2025-09-30T23:59:59Z&page_size=10) | Metadata first, then read cloud-masked raster bands; NDVI ≠ crop residue |
| **GPM IMERG Final V07** | Half-hourly `precipitation` (mm/h) | Rainfall intensity; approximate R erosivity | **OPeNDAP catalog:** [IMERG](https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGHH.07/); [dataset](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGHH_07/summary) | Catalog is **not** one ready-to-use JSON call; select granules/time/area, extract values, calculate R; coarse ~0.1° |
| **FAOSTAT** *(optional)* | Country/year crop production, harvested area, yield | Broad benchmark only | **REST example:** [QCL query](https://fenixservices.fao.org/faostat/api/v1/en/data/QCL?area=230&item=15&element=5510&year=2023) | Verify endpoint/filters; not field-level prices, costs or profit |

**Not APIs:** [FAO-56](https://www.fao.org/4/X0490E/x0490e00.htm) is the ET₀ / crop-water calculation methodology; [USDA RUSLE2](https://www.nrcs.usda.gov/resources/tech-tools/water-erosion-rusle2) is erosion methodology. Implement and document the chosen formulas locally; do not claim that RUSLE2 software outputs are reproduced by a simplified RUSLE model.

## 2. Backend output contract

For each retrieved variable store: `name`, `value`, `unit`, `date_or_period`, `geometry`, `source`, `source_url`, `resolution`, `retrieved_at`, `quality_flag`, `uncertainty_or_limitations`. Cache raw responses and derived results. Return `missing` explicitly on failure. **Do not silently substitute synthetic data.**

Before production, test each endpoint, access permissions, dataset identifiers, spatial subset, units and scale factors. Example links above are integration starting points, not a claim that every request has been live-tested.
