# Map data sources and honesty notes

| Item | Source | Status |
|---|---|---|
| Base map tiles | OpenStreetMap standard tiles (`tile.openstreetmap.org`), attribution shown on the map | Works for development/demos. The OSM tile policy forbids heavy production use; use a tile provider for a public launch. |
| City coordinates | `database/city_metadata.csv` | **Entered from general geographic knowledge (approximate city-centre points) because the dataset contains no coordinates. They could not be checked online while the project was generated.** Verify them against e.g. Open-Meteo's geocoding API or Wikipedia and edit the CSV, then re-run the import with `--replace`. |
| Weather values on the map | Your Excel dataset | Real observations as supplied (they look like Open-Meteo archive/reanalysis data; the original source is not recorded in the file). |
| State boundaries (choropleth) | **Not bundled** | See below. The option is disabled with an explanation until the file exists. |
| Live weather | Open-Meteo `forecast` API (no key) | Model-based "current" values, labelled LIVE. Not tested during generation (no network). |
| Hospitals | OpenStreetMap via the Overpass API (no key) | Real OSM data, may be incomplete. Not tested during generation (no network). |

## Adding state boundaries

1. Choose a source and check its licence/disclaimer (India's official borders are politically sensitive; many datasets differ). Common open options: *datameet/maps* (India states), *geoBoundaries* (India ADM1), *Natural Earth* admin-1.
2. Save it as `frontend/public/geo/india_states.geojson` (GeoJSON, WGS84).
3. The state-name property can be `NAME_1`, `ST_NM`, `state`, `STATE`, `name`… (see `geoStateName` in `frontend/src/features/heat-risk-map/colors.ts`; add your property name if different).
4. Tick "State boundaries" on the map. Each state is coloured by the **highest-scoring city in that state**; states with no city in the dataset stay uncoloured, and unmatched city states are listed. Old files that predate Telangana (2014) will not match Hyderabad.

## Interpolated heat surface

* Method: inverse-distance weighting (power 2) on a 0.75° grid, using only the cities that have data for the chosen layer and date.
* Coverage: a cell is drawn only if a city is within 300 km (adjustable up to 600 km in the API). Everything else stays blank.
* With only 10 points the surface is a rough visual aid. It is labelled INTERPOLATED, drawn faded, and never presented as a measurement.

## Risk score (informational project metric)

`score = Σ weight × sub-score`, each sub-score `clamp((value − low)/(high − low), 0, 1) × 100`, weights renormalised over the inputs that exist.

| Component | Weight | Low → High |
|---|---|---|
| Maximum temperature | 0.45 | 30 → 46 °C |
| Apparent maximum temperature | 0.30 | 32 → 50 °C |
| Night-time minimum temperature | 0.10 | 22 → 32 °C |
| Consecutive hot days (Tmax ≥ 40 °C; 37 °C for coastal Mumbai/Chennai) | 0.15 | 0 → 5 days |

Categories: Low 0–24, Moderate 25–49, High 50–74, Extreme 75–100. All numbers live in `backend/app/core/heat_config.py`.
These weights and thresholds are **chosen by the project, not calibrated against health outcomes**, and the score is not an official warning.
