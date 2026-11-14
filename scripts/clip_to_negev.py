"""Fix (2026-11-14): keep off-map houses only inside the Be'er Sheva subdistrict (נפת באר שבע, iplan gvulot_retzef/4).

houses_v2.py selected the "Bedouin belt" with a lon/lat box (34.70-35.22 E, 31.02-31.42 N). That box crosses the Green Line,
so Palestinian buildings in the South Hebron hills (West Bank: Susiya, Yatta area ...) were counted as unrecognized-village
houses. The West Bank is not part of this atlas. This script clips every derived file to the subdistrict polygon:

  offmap_buildings.json   compact footprints  -> buildings with centroid inside the subdistrict
  bld_offmap_grid.geojson 250 m cells         -> rebuilt from the kept buildings (n, m2 = footprint area)
  cluster_frames.geojson  village frames      -> frames whose centre is outside are dropped
  buildings_summary.json  counts              -> outside_recognized / v2 counts updated, villages outside dropped

houses_v2.py now applies the same subdistrict test, so a rerun gives the same result.
Run: python clip_to_negev.py <data_dir>
"""
import json, sys, os, math
data = sys.argv[1]
P = lambda f: os.path.join(data, f)
J = lambda f: json.load(open(P(f), encoding='utf-8'))
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
g = J('negev_nafa.geojson')['features'][0]['geometry']
PS = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
# The subdistrict polygon itself runs a little past the Green Line in the south Hebron hills (Shani/Livne, Masafer Yatta
# hamlets such as Halaweh and al-Markaz stayed in). OSM's West Bank relation has gaps there, so the rule is explicit:
# nothing north of 31.345 N between 34.95 and 35.30 E is counted (the northernmost Negev village there, Atir, is at 31.32 N).
def beyond_green_line(x, y): return y > 31.345 and 34.95 <= x <= 35.30
def in_negev(x, y): return not beyond_green_line(x, y) and any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in PS)

# 1. buildings
off = J('offmap_buildings.json'); keep = []; ring_of = []
for a in off:
    x, y = a[2], a[3]; ring = [(x / 1e5, y / 1e5)]
    for i in range(4, len(a), 2): x += a[i]; y += a[i + 1]; ring.append((x / 1e5, y / 1e5))
    cx, cy = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    if in_negev(cx, cy): keep.append(a); ring_of.append((ring, cx, cy))
drop = len(off) - len(keep)
print('buildings', len(off), '-> kept', len(keep), 'dropped (outside subdistrict)', drop,
      '| dropped by class', {c: sum(1 for a in off if a[0] == c) - sum(1 for a in keep if a[0] == c) for c in 'ue'})
json.dump(keep, open(P('offmap_buildings.json'), 'w'), separators=(',', ':'))

# 2. 250 m grid
def area_m2(r):
    kx = 111320 * math.cos(math.radians(r[0][1])); ky = 110570
    return abs(sum((r[i][0] * kx) * (r[(i + 1) % len(r)][1] * ky) - (r[(i + 1) % len(r)][0] * kx) * (r[i][1] * ky) for i in range(len(r)))) / 2
cells = {}
for ring, cx, cy in ring_of:
    k = (math.floor(cx / .0025 + 1e-9), math.floor(cy / .0025 + 1e-9)); c = cells.setdefault(k, [0, 0.0]); c[0] += 1; c[1] += area_m2(ring)
feats = []
for (i, j), (n, m2) in sorted(cells.items()):
    x0, y0, x1, y1 = round(i * .0025, 5), round(j * .0025, 5), round((i + 1) * .0025, 5), round((j + 1) * .0025, 5)
    feats.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}, 'properties': {'n': n, 'm2': round(m2)}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(P('bld_offmap_grid.geojson'), 'w'), separators=(',', ':'))
print('grid cells', len(feats), 'sum n', sum(f['properties']['n'] for f in feats))

# 3. frames
fr = J('cluster_frames.geojson'); before = len(fr['features'])
def centre(f): r = f['geometry']['coordinates'][0]; return sum(p[0] for p in r[:-1]) / 4, sum(p[1] for p in r[:-1]) / 4
out = [f for f in fr['features'] if not in_negev(*centre(f))]
fr['features'] = [f for f in fr['features'] if in_negev(*centre(f))]
print('frames', before, '-> kept', len(fr['features']), '| dropped:', sorted(((f['properties']['en'], f['properties']['n']) for f in out), key=lambda t: -t[1])[:12])
json.dump(fr, open(P('cluster_frames.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

# 4. summary
S = J('buildings_summary.json')
S['outside_recognized'] = len(keep)
S['v2'].update({'houses': len(keep), 'unrecognized': sum(a[0] == 'u' for a in keep), 'expansion': sum(a[0] == 'e' for a in keep),
                'osm': sum(a[1] == 'o' for a in keep), 'ms': sum(a[1] == 'm' for a in keep), 'clusters': len(fr['features']),
                'clip': "centroid inside the Be'er Sheva subdistrict and south of the Green Line band (West Bank buildings removed 2026-11-14)"})
vb = len(S['villages']); S['villages'] = [v for v in S['villages'] if in_negev(v['lon'], v['lat'])]
print('summary villages', vb, '->', len(S['villages']))
json.dump(S, open(P('buildings_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
