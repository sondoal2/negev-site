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
| 06 | Violence | — (being collected with Sikkuy-Aufoq / Abraham Initiatives) | Planned: victims by locality, distance to police, AI street-image audit |

**Scope:** the atlas covers the Be'er Sheva subdistrict only. Off-map houses are clipped to it (`scripts/clip_to_negev.py`); an earlier version wrongly counted 3,949 West Bank buildings (Masafer Yatta, Susiya, Shani/Livne area) as unrecognized-village houses; because the subdistrict polygon itself overshoots the Green Line in the south Hebron hills, nothing north of 31.345 N between 34.95 and 35.30 E is counted.

Processing scripts are in `scripts/` (run with ArcGIS Pro Python): `lpkx_to_geojson.py`, `localities.py`, `buildings.py`, `gtfs_direct.py`, `transit_access.py`, `clip_to_negev.py`, `transit_pairs.py`, `services_access.py`, `cbs_education.py`, `sport_clean.py` (chapter 04 player: an unrecognized village beside a recognized town, both 3.2 km windows at the same scale).

Every chapter ends with a **gap card**: one Arab line vs one Jewish line in the same unit, and the ratio (×N) in red.
