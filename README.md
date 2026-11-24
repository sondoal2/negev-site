# OFF—MAP · Naqab / Negev spatial-justice atlas

Static site (GitHub Pages ready, no build step). Open `index.html` through any static server.

## Layers
| Layer | Source | Mode |
|---|---|---|
| Streets, buildings, wadis, place names | OpenStreetMap via OpenFreeMap vector tiles | live |
| B/W aerial | Esri World Imagery | live |
| Before/after swipe 2014→2026 | Esri World Imagery **Wayback** archive | live |
| Negev mask (נפת באר שבע) | iplan `gvulot_retzef/4` | `data/negev_nafa.geojson` |
| Municipal limits (גבולות שיפוט) | iplan `gvulot_retzef/1` | `data/muni.geojson`, `data/rahat.geojson` |
| Locality limits (ועדים מקומיים) | iplan `gvulot_retzef/2` | `data/vaadim.geojson` |
| Xplan blue lines, land use | iplan `Xplan` layers 1, 4 | live (ArcGIS export) |
| District plan 4/14 South | iplan `compilation_tmm_darom` | live |
| VATMAL compounds | iplan `vatmal_mitchamim_muchrazim` | live |
| "Red list" – villages outside recognized limits | OSM places (Arabic names) ∖ recognized locality polygons | `data/osm_places.geojson`, computed in browser |

**Caveat:** the red-list layer is a spatial *candidate* list, not an official list — verify against RCUV / Negev Coexistence Forum (Dukium) data before publishing claims.

Arab/Jewish classification is by council (see `ARAB` set in `index.html`).

## Demolition tool
Compare view → "Mark demolished building" → click vertices, double-click to close → Export GeoJSON. Drawings are saved in the browser until exported.

## Six chapters (v3)
| # | Chapter | Data | Method |
|---|---|---|---|
| 01 | Land & recognition | Microsoft ML building footprints 2026, iplan limits, OSM | Buildings outside every recognized limit, ≤2.5 km from a candidate village or inside Neve Midbar / al-Kasum → 250 m grid (`bld_offmap_grid.geojson`, `buildings_summary.json`) |
| 02 | Housing & settlement | CBS localities file 2024 (`cbs_localities.geojson`) | Timeline of localities by founding year; Arab localities without a CBS year treated as pre-1948; township years from historical sources, Abu Basma villages ≈2004 |
| 03 | Economy | Team ArcGIS layers | Gross industrial area by sector |
| 04 | Mobility | MoT GTFS (`transit_direct.json`) | Direct trips on one weekday; only stops inside locality limits |
| 04b | Walking access to a bus stop | MoT GTFS (served stops only), Microsoft footprints, iplan limits (`transit_access.json`, `transit_stops.geojson`, `offmap_stopdist.json`, `grid_stopdist.json`) | Straight-line distance from every off-map house and every building in the 18 comparison towns' built-up core to the nearest stop with ≥1 weekday trip (`scripts/transit_access.py`). Netivot and Eilat left out of totals (no Microsoft footprints). Bedouin clusters inside Arad's limit stay counted as Arad — conservative. |
| 05 | Education & services | MoE institutions + coordinates (data.gov.il), CBS Local Authorities 2023 profiles, OSM clinics (`services_access.json`, `services_points.geojson`, `grid_svcdist.json`, `bagrut.json`) | Distance from every home to the nearest active elementary school (`scripts/services_access.py`); bagrut 2022/23 per town incl. the Bedouin regional councils (`scripts/cbs_education.py`). Sports halls, pitches and pools per 1,000 young people and distance from village homes (Ministry of Culture & Sport register 2021, extracted by a team member, cleaned in `scripts/sport_clean.py`: 18 mis-located and 31 inactive removed, street fitness / "other" not counted). Clinics shown on the map only — OSM too incomplete for a gap figure. |
| 05+ | Public parks | Team member's package: Xplan land use code 670 (approved plans, ≥500 m², ≥15 m wide, 2,248 plots), OSM park + recreation_ground (Geofabrik 11.2026, 1,805 parks), Microsoft footprints (Arab) + OSM buildings (Jewish), CBS 2024 (`parks_planned.geojson`, `parks_actual.geojson`, `parks_grid.geojson`, `parks_stats.json`) | Planning Administration standard (public-needs guide 2016, p. 116): park within 500 m of home, 3–5 m² per resident. Share of homes within 500 m on paper vs on the ground; m² per resident. `scripts/safety_parks_prep.py` slims the files and aggregates per-home distances to 250 m cells. OSM may under-map parks in Arab towns — not yet checked on aerial photos. |
| 07 | Plan vs ground (Sa'wa) | iplan Xplan layers 1 & 4 (`xplan_sawa_plans.geojson`, `xplan_sawa_landuse.geojson`, downloaded 2026-11-19 in a browser), Microsoft footprints 2024-05 release via VIDA/source.coop (`sawa_buildings.geojson`, cut by `scripts/sawa_buildings_cut.py`) | Building centroids vs the land use of the five approved Sa'wa neighbourhood plans (`scripts/sawa_plan_vs_ground.py` → `sawa_planground.json`): share of buildings outside every neighbourhood plan; buildings on land zoned road/path/open space/stream/public; residential plots touched by no footprint. Imagery ≤2023 precedes or overlaps approval, so empty plots describe the state at approval. |
| 07+ | Plan vs ground, all recognized Bedouin localities | Microsoft footprints (VIDA/source.coop, 2024-05) for the 7 towns and 11 al-Kasum / Neve Midbar villages (`scripts/bedouin_buildings_cut.py`); iplan Xplan layers 1 and 4 for their bounding boxes, downloaded in a browser 2026-11-19 | `scripts/bedouin_noplan.py` → `bedouin_noplan.json`, `bedouin_noplan_pts.json`: a building is covered if its centroid is inside an approved plan boundary (not a policy document, under 30 km², so regional umbrella plans do not count) or an approved land-use plot. Land use alone undercounts the towns, whose older plans have boundaries but no digital plots. Homes outside every recognized limit count as having no plan. |
| 06 | Violence | Israel Police open crime data, data.gov.il `crime_records_data` 2023–2025 (`violence.json`) | Southern District files fetched with `scripts/crime_fetch.py` and `scripts/crime_lethal_fetch.py`, counted per locality by `scripts/violence_stats.py`: murder + attempted murder + manslaughter files per 10,000 residents a year, 7 Bedouin towns vs 11 Jewish towns (CBS 2023 population, as in bagrut.json); ordinary bodily-harm files per 1,000 shown too. Files, not victims or convictions. Lethal files at Bedouin-serving stations with no locality are counted as a data gap (unrecognized villages have no locality code). Police, fire and hospital access from a team member's package (data.gov.il `police_receptions`, `yeshuv_by_station`, `israel_fire_rescue_stations` 2026; OSM hospitals; OSRM drive times): straight-line distance from every building to the nearest station on a 250 m grid (`police_grid.geojson`, `safety_points.geojson`, `safety_stats.json`, via `scripts/safety_parks_prep.py`). Not response times. Street-image audit not done. |

**Scope:** the atlas covers the Be'er Sheva subdistrict only. Off-map houses are clipped to it (`scripts/clip_to_negev.py`); an earlier version wrongly counted 3,949 West Bank buildings (Masafer Yatta, Susiya, Shani/Livne area) as unrecognized-village houses; because the subdistrict polygon itself overshoots the Green Line in the south Hebron hills, nothing north of 31.345 N between 34.95 and 35.30 E is counted.

Processing scripts are in `scripts/` (run with ArcGIS Pro Python): `lpkx_to_geojson.py`, `localities.py`, `buildings.py`, `gtfs_direct.py`, `transit_access.py`, `clip_to_negev.py`, `transit_pairs.py`, `services_access.py`, `cbs_education.py`, `sport_clean.py` (chapter 04 player: an unrecognized village beside a recognized town, both 3.2 km windows at the same scale).

Every chapter ends with a **gap card**: one Arab line vs one Jewish line in the same unit, and the ratio (×N) in red.

## GIFs (one story each)

`gifs/ar/`, `gifs/he/`, `gifs/en/` — nine 1200×675 GIFs per language, each a single story: the map on the left (camera never moves), and on the right the topic, one question,
the two sides in identical units, the gap ×N and the source.

| file | story |
|---|---|
| `00-layer-on-layer` | one fixed camera over Omer and the Bedouin towns around it; six sources added one per frame (limits, buildings, approved plans, bus catchments, schools, lethal-violence files) — drawn by `layers.html`, exported by `scripts/make_layers_gif.py` |
| `05b-parks-paper-vs-ground` | homes within 500 m of a public park: on paper (Xplan) vs on the ground (OSM, under verification in Arab towns); hatched = on paper only |
| `06-police-station-2km` | buildings within 2 km of a police station: unrecognized villages vs the 7 Bedouin towns (team member's package) |
| `06-lethal-violence` | murder and attempted-murder files per 100,000 residents a year, 2023–2025, circle area per town |
| `07-no-approved-plan` | Bedouin buildings with no approved plan over them (56%; 28% even inside recognized localities) |
| `01-homes-off-the-map` | homes outside every recognized limit |
| `02-new-localities-since-1948` | new localities founded since 1948, Jewish vs Arab |
| `03-industrial-land` | industrial land per 1,000 residents, drawn as a yellow block (dunams) |
| `03-business-tax` | business arnona per resident |
| `04-bus-stop-walking-distance` | homes within 400 m of a served bus stop |
| `05-elementary-school-1km` | homes within 1 km of an elementary school |
| `05-bagrut-university` | twelfth-graders with a university-level bagrut |
| `05-sport-facilities-per-youth` | sports halls, pitches and pools per 10,000 aged 6–18 |
| `05-sport-facility-1km` | homes within 1 km of a hall or pitch |

The frames are drawn by `gif.html` from the same data files and formulas as the site (`gif.html?g=bus&lang=ar` plays one live).
`python scripts/make_gifs.py . ar` re-exports them (headless Edge/Chrome screenshot + Pillow; `he` / `en` also work as the language).

## Added 24.11.2026

- **Compare button** (header): the red side of the gap cards switches between the unrecognized villages and the recognized Arab towns (ch. 04 bus, 05 school, 06 police, and the ch. 04 pairs player). Where the towns are not behind, the card says so instead of showing ×1.
- **Night mode** (moon button, or the first row of the layers panel): NASA Black Marble 2016 lights (GIBS tiles, z≤8, so they blur into soft halos close up), street map hidden; light strength slider and black & white switch.
- **Demolitions 2026** (ch. 01): `data/demolitions_2026.json`, one dashed ring per village (not per house), size ∝ √structures reported, red = demolished by the authorities, orange = self-demolished under orders, white = orders served. Each ring links to its news / NGO source; "Play 2026 month by month" in the card. Sources count different things, so they are not added up.
- **Ch. 04**: a note on Segev Shalom and Hura (stops only on the main road), from the per-town numbers already in `transit_access.json`.
- **Ch. 02**: the 1948→2024 timeline runs in about 5 s, starting on the whole country and closing in on the Naqab.
- Mobile: header and chapter tabs no longer overlap.
