# John’s showcase inputs

`john_showcase.json` is the complete fictional farmer-input fixture for Croptato. `john_field.geojson` contains its matching synthetic boundary in longitude/latitude (EPSG:4326). They are small public demonstration fixtures, not private farmer records.

The user authorized invented inputs for the showcase. **Every farmer fact, soil value, crop date, yield, price and cost is a synthetic assumption.** None was measured, surveyed, retrieved from an API, quoted by a market or supplied by a real farmer. The original pilot center, approximate 30-ha size and recent sunflower → sunflower → wheat ordering follow the technical specification; the remaining inputs complete the fictional example.

The dataset includes:

- A synthetic field near 46.7491 N, 32.7091 E, approximately 30 ha; verify projected/ellipsoidal area before spatial calculations.
- Dated 2016–2025 crop history and fictional harvest yields. Repeated sunflower in 2023–2024 is intentionally retained as an adverse historical example, not a valid recommendation.
- Rainfed management, minimum tillage, residue, conservation practices, erosion observations, fallow, shelterbelts, fertilizer and disease context.
- Synthetic soil layers at 0–5 and 5–15 cm, with explicit property units. They may be used only as labelled assumptions, not SoilGrids or laboratory evidence.
- An eight-year 2026–2033 planning request, allowed/excluded crops and the three objectives.
- Synthetic 2025 UAH prices/costs and yield assumptions for all included crops. Any resulting financial arithmetic is a demo scenario, not forecast profit. Fallow has zero marketable harvest and a nonzero management cost.
- Machinery, storage, budget, purchasing/access constraints and authorisation for synthetic-profile processing/publication. Real-person consent is deliberately null; synthetic fixture authorisation does not supply it.
- An explicit adverse current-practice comparison baseline and a Q01–Q26 map to structured fields.

## Inputs are not results

`external_data` entries are `not_retrieved` with null values. `computed_outputs` are null. Actual climate, soil rasters, elevation, precipitation intensity and HLS data must be retrieved through their documented sources. Scientific methods, calibrated thresholds, C/P tables and uncertainty are not manufactured as farmer inputs.

Historical weather is requested for 2016–2025, not forecast for 2026–2033. A real-data climate result can coexist with synthetic farmer assumptions; both provenances must remain visible in any resulting report. Missing erosion factors keep erosion uncomputed.

## Presentation and use

The frontend imports the fixture through `frontend/src/config/showcase.ts`. Soily receives the same presentation and relevant farmer inputs in its context. Personal info shows the assumptions, and the example dashboard downloads the complete input fixture. `presentation` contains the public description of this revision; keep it consistent when editing inputs.

The fixture remains a file-backed starting dataset. Conversational structured-profile persistence and automatic scientific reruns are separate pipeline work; creating this file does not implement them.

Run checks with:

```bash
.venv/bin/python -m pytest backend/tests/test_showcase_inputs.py -q
```
