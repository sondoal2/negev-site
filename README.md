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
