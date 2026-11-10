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

## Five chapters (v2)
| # | Chapter | Data | Method |
|---|---|---|---|
| 01 | Land & recognition | Microsoft ML building footprints 2026, iplan limits, OSM | Buildings outside every recognized limit, ≤2.5 km from a candidate village or inside Neve Midbar / al-Kasum → 250 m grid (`bld_offmap_grid.geojson`, `buildings_summary.json`) |
| 02 | Housing & settlement | CBS localities file 2024 (`cbs_localities.geojson`) | Timeline of localities by founding year; Arab localities without a CBS year treated as pre-1948; township years from historical sources, Abu Basma villages ≈2004 |
| 03 | Economy | Team ArcGIS layers | Gross industrial area by sector |
| 04 | Mobility | MoT GTFS (`transit_direct.json`) | Direct trips on one weekday; only stops inside locality limits |
| 05 | Violence | — (being collected with Sikkuy-Aufoq / Abraham Initiatives) | Planned: victims by locality, distance to police, AI street-image audit |

Processing scripts are in `scripts/` (run with ArcGIS Pro Python): `lpkx_to_geojson.py`, `localities.py`, `buildings.py`, `gtfs_direct.py`.
