# Field intelligence dashboard

Open **Field dashboard** in the sidebar. Click a point, drag the map to pan, zoom, or enter WGS84 coordinates. **Locate me** requests browser geolocation and shows a separate blue dot; it does not automatically change the field. Browser geolocation requires HTTPS or localhost. The selected point is saved in this browser, not attached to a user account. It is not a cadastral boundary. The default Kherson point is the synthetic saved example.

**Load NASA history** fetches all seven specified NASA POWER Daily variables for 2016–2025 through `/api/field-data`. Select a variable and year or inspect the whole decade; focus, hover, or tap a month for its value and coverage. A keyboard-accessible data table and JSON provenance download are available. A missing or invalid day makes that month's aggregate unavailable. Rainfall is summed only after validating mm/day units; other variables use the mean of all daily values. Leap days count toward required coverage. The service uses UTC dates and never substitutes example values. These are historical gridded estimates, not forecasts or field-station observations.

Raw successful responses and derived results are cached for six hours in `dashboard-cache.sqlite` beside the configured orchestrator database. The cache retains at most 64 locations. Changing fields cancels the browser request and clears the previous results. It does not modify the saved example's soil, crop history, or rotation cards. Precise coordinates are sent only to fixed provider endpoints when you request data/checks. OpenStreetMap supplies map tiles and receives viewport tile requests.

**Check API status** runs server-side requests through `/api/data-sources` for every provider in `AGENTS/AgroResilience_External_API_Data.md`:

| Provider | What is checked | Use in dashboard |
| --- | --- | --- |
| NASA POWER | Seven-variable, one-day JSON response | Historical charts use a separate full-period retrieval |
| ISRIC SoilGrids | WCS capabilities for sand, silt, clay, soc, phh2o, bdod | Access status only; no soil raster values |
| NASADEM | CMR granule search at selected point | Metadata only; no slope or LS |
| HLS S30 and L30 | Both CMR searches, Apr–Sep 2025 | Metadata only; no cloud-masked NDVI |
| GPM IMERG Final V07 | Specified OPeNDAP catalog | Catalog/access status only; no precipitation extraction or R |
| FAOSTAT | Specified Ukraine country/year query | Optional endpoint check; not field-specific data or profit |

Source cards expose exact requests, variables, resolution, limitations, and check timestamps. Successful metadata/catalog access never implies raster processing. Authentication failures, unavailable endpoints, partial checks, and empty search results have separate states. FAO-56 and RUSLE remain local methodologies, not APIs. The chat tools `get_climate_history` and `check_data_sources` use these same providers at confirmed coordinates worldwide (85°S–85°N). The climate tool returns one variable and year per call to keep model evidence bounded, with original provenance and coverage. **Ask Soily about this location** passes the selected coordinates explicitly. Place-name geocoding is not connected: the model must ask for a pin instead of inventing precise coordinates. Reference retrieval supports optional region filters when RAG is configured; missing regional reference evidence remains unavailable. Generic dashboard requests no longer implicitly select John's Kherson region. The legacy Python scientific pipeline remains Kharkiv-only; its scientific validation boundary is not widened. Raster analysis and agronomic recommendations remain unconnected.

Live smoke check on 2026-11-15 at 46.7491° N, 32.7091° E: NASA POWER yielded 120 complete months; all six SoilGrids capabilities and NASADEM/HLS metadata responded. The specified IMERG catalog and FAOSTAT endpoint were unavailable from the checking environment. These are observations at that time, not permanent availability guarantees; use the UI to recheck.

Provider references: [NASA POWER Daily API](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), [ISRIC WCS](https://docs.isric.org/globaldata/soilgrids/wcs.html), [NASA CMR API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html).

Validation: `npm run build --prefix frontend`, `npm run lint --prefix frontend`, `npm run test --prefix frontend`, `.venv/bin/python -m pytest backend/tests -q`. External requests are mocked in regression tests; no paid model is required.
