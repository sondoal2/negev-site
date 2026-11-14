"""Off-map houses v2.
- Footprints: OSM buildings (traced on imagery, precise) + Microsoft ML footprints only where OSM has nothing.
- Region: Bedouin belt only (inside Neve Midbar / al-Kasum councils, or the Be'er Sheva-Arad-Dimona siyag box) -> drops Arava farms etc.
- Outside every recognized limit:  'e' = expansion (<= 400 m from a recognized Arab locality), 'u' = unrecognized village.
  Buildings <= 300 m from a Jewish locality are dropped (farms / outskirts).
- Clusters: buildings whose centroids are <= 60 m apart; frame = padded bbox; named only if an OSM place is <= 1.2 km away."""
import gzip, json, sys, os, glob, math
msb_dir, osm_file, data_dir = sys.argv[1:4]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))
KX, KY = 95.3, 111.0   # km per degree at 31°N
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
def polys(g): return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
def prep(g):
    ps = polys(g); xs = [c[0] for p in ps for c in p[0]]; ys = [c[1] for p in ps for c in p[0]]
    return {'ps': ps, 'bb': (min(xs), min(ys), max(xs), max(ys))}
def inside(x, y, P):
    b = P['bb']
    return b[0] <= x <= b[2] and b[1] <= y <= b[3] and any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in P['ps'])
def dist_km(x, y, P, maxkm):
    b = P['bb']; m = maxkm / KY
    if not (b[0] - m <= x <= b[2] + m and b[1] - m <= y <= b[3] + m): return 99
    if inside(x, y, P): return 0
    best = 99
    for p in P['ps']:
        r = p[0]
        for i in range(len(r) - 1):
            ax, ay = (r[i][0] - x) * KX, (r[i][1] - y) * KY; bx, by = (r[i+1][0] - x) * KX, (r[i+1][1] - y) * KY
            dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
            t = 0 if L2 == 0 else max(0, min(1, -(ax * dx + ay * dy) / L2))
            best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best
REGIONAL = {'Neve Midbar','al Kasum','Merhavim','Sdot Negev','Ramat Negev','Hevel Eielot',"Ha'arava Hatihona","Bnei Shim'on",'Eshkol','Tamar'}
ARAB = {'Tel Sheva','Segev Shalom',"Ar'ara Banegev",'Lakiye','Kseyfe','Hura','Rahat','Neve Midbar','al Kasum'}
arab, jew, rc = [], [], []
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    en = (f['properties'].get('Muni_Eng') or '').strip()
    if en in ('Neve Midbar', 'al Kasum'): rc.append(prep(f['geometry']))
    if en in REGIONAL: continue
    (arab if en in ARAB else jew).append(prep(f['geometry']))
for f in J('vaadim.geojson')['features']:
    v = (f['properties'].get('Vaad_Eng') or '').strip(); m = (f['properties'].get('Muni_Eng') or '').strip()
    if v and not v.upper().startswith('GENERAL'): (arab if m in ARAB else jew).append(prep(f['geometry']))
SIYAG = (34.70, 31.02, 35.22, 31.42)
NAFA = prep(J('negev_nafa.geojson')['features'][0]['geometry'])   # the box crosses the Green Line: keep the Be'er Sheva subdistrict only (fix 2026-11-14)
def in_region(x, y): return inside(x, y, NAFA) and ((SIYAG[0] <= x <= SIYAG[2] and SIYAG[1] <= y <= SIYAG[3]) or any(inside(x, y, P) for P in rc))
def classify(x, y):
    if not in_region(x, y): return None
    if any(inside(x, y, P) for P in arab) or any(inside(x, y, P) for P in jew): return None
    if any(dist_km(x, y, P, 0.3) <= 0.3 for P in jew): return None
    return 'e' if any(dist_km(x, y, P, 0.4) <= 0.4 for P in arab) else 'u'
cen = lambda r: (sum(c[0] for c in r[:-1]) / (len(r) - 1), sum(c[1] for c in r[:-1]) / (len(r) - 1))
B = []   # [ring, x, y, cls, src]
# OSM
osm_rings = []
for el in json.load(open(osm_file, encoding='utf-8'))['elements']:
    g = el.get('geometry')
    if not g or len(g) < 4: continue
    ring = [[p['lon'], p['lat']] for p in g]
    if ring[0] != ring[-1]: ring.append(ring[0])
    osm_rings.append(ring)
cell = 0.0005; grid = {}
for ring in osm_rings:
    x, y = cen(ring); grid.setdefault((int(x / cell), int(y / cell)), []).append(ring)
    c = classify(x, y)
    if c: B.append([ring, x, y, c, 'o'])
n_osm = len(B)
# Microsoft where OSM has no building
def covered(x, y):
    i, j = int(x / cell), int(y / cell)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for ring in grid.get((i + di, j + dj), ()):
                if in_ring(x, y, ring): return True
                rx, ry = cen(ring)
                if math.hypot((rx - x) * KX, (ry - y) * KY) < 0.008: return True
    return False
for fn in glob.glob(os.path.join(msb_dir, '*.csv.gz')):
    for line in gzip.open(fn, 'rt', encoding='utf-8'):
        f = json.loads(line); ring = f['geometry']['coordinates'][0]; x, y = cen(ring)
        if not (SIYAG[0] - .3 <= x <= SIYAG[2] + .3 and SIYAG[1] - .3 <= y <= SIYAG[3] + .3): continue
        c = classify(x, y)
        if c and not covered(x, y): B.append([ring, x, y, c, 'm'])
print('houses', len(B), 'osm', n_osm, 'ms', len(B) - n_osm, 'unrec', sum(b[3] == 'u' for b in B), 'expansion', sum(b[3] == 'e' for b in B))
# clusters: union-find on centroids <= 60 m
par = list(range(len(B)))
def find(a):
    while par[a] != a: par[a] = par[par[a]]; a = par[a]
    return a
cs = 0.0007; G = {}
for k, b in enumerate(B): G.setdefault((int(b[1] / cs), int(b[2] / cs)), []).append(k)
for (i, j), ks in G.items():
    near = [k2 for di in (-1, 0, 1) for dj in (-1, 0, 1) for k2 in G.get((i + di, j + dj), ())]
    for a in ks:
        for b2 in near:
            if b2 > a and math.hypot((B[a][1] - B[b2][1]) * KX, (B[a][2] - B[b2][2]) * KY) <= 0.06: par[find(a)] = find(b2)
groups = {}
for k in range(len(B)): groups.setdefault(find(k), []).append(k)
import re
ar_re = re.compile('[؀-ۿ]')
places = [f for f in J('osm_places.geojson')['features'] if f['geometry']['coordinates'] and f['geometry']['coordinates'][0] and ar_re.search(f['properties'].get('name') or '')]
frames = []; PAD = 0.0003
for ks in groups.values():
    if len(ks) < 10: continue
    xs = [c[0] for k in ks for c in B[k][0]]; ys = [c[1] for k in ks for c in B[k][0]]
    cx, cy = sum(B[k][1] for k in ks) / len(ks), sum(B[k][2] for k in ks) / len(ks)
    best, bd = None, 1.2
    for f in places:
        px, py = f['geometry']['coordinates']; d = math.hypot((px - cx) * KX, (py - cy) * KY)
        if d < bd: best, bd = f['properties'], d
    nu = sum(B[k][3] == 'u' for k in ks)
    x0, y0, x1, y1 = min(xs) - PAD, min(ys) - PAD, max(xs) + PAD, max(ys) + PAD
    frames.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[round(x0, 5), round(y0, 5)], [round(x1, 5), round(y0, 5)], [round(x1, 5), round(y1, 5)], [round(x0, 5), round(y1, 5)], [round(x0, 5), round(y0, 5)]]]},
                   'properties': {'ar': (best.get('ar') or best.get('name')) if best else 'غير مسمّى', 'en': (best.get('en') or best.get('name')) if best else 'unnamed', 'n': len(ks), 'c': 'u' if nu >= len(ks) / 2 else 'e',
                                  'du': round((x1 - x0) * KX * (y1 - y0) * KY * 1000)}})
for k, b in enumerate(B): b.append(len(groups[find(k)]))
json.dump({'type': 'FeatureCollection', 'features': frames}, open(os.path.join(data_dir, 'cluster_frames.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
with open(os.path.join(data_dir, 'offmap_buildings.geojson'), 'w') as o:
    o.write('{"type":"FeatureCollection","features":[')
    o.write(','.join(json.dumps({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[round(c[0], 5), round(c[1], 5)] for c in b[0]]]}, 'properties': {'c': b[3], 's': b[4]}}, separators=(',', ':')) for b in B))
    o.write(']}')
S = J('buildings_summary.json'); S['v2'] = {'houses': len(B), 'unrecognized': sum(b[3] == 'u' for b in B), 'expansion': sum(b[3] == 'e' for b in B), 'osm': n_osm, 'ms': len(B) - n_osm, 'clusters': len(frames),
    'rule': 'OSM buildings + MS footprints where OSM is empty; Bedouin belt only; outside all recognized limits; >300 m from Jewish localities; e = <=400 m from recognized Arab locality'}
S['outside_recognized'] = len(B)
json.dump(S, open(os.path.join(data_dir, 'buildings_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('clusters', len(frames), 'named', sum(f['properties']['en'] != 'unnamed' for f in frames))
for f in sorted(frames, key=lambda f: -f['properties']['n'])[:12]: print(f['properties']['en'], f['properties']['n'], f['properties']['c'])
