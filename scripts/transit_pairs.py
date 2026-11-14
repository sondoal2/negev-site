"""Same-scale pairs for the chapter 04 player: an unrecognized village next to a recognized town, both drawn in a
3.2 km x 3.2 km window at exactly the same scale, with every building coloured by its straight-line distance to the
nearest served bus stop and a 400 m walking circle around each stop.

Inputs: msb_dir (Microsoft footprints, Israel tiles *.csv.gz), data_dir (offmap_buildings.json, offmap_stopdist.json,
        cluster_frames.geojson, transit_stops.geojson, transit_access.json, muni.geojson, rahat.geojson)
Output: data/transit_pairs.json
  pairs[k].a / .j = {name{ar,he,en}, kind, pct_lt400, median_m, n, stops, b:[[cls, x0, y0, dx1, dy1, ...], ...], s:[[x, y], ...]}
  coordinates are metres from the window's south-west corner (y up); cls 0..3 = <400 m, 0.4-1 km, 1-3 km, >3 km.
Run after transit_access.py and clip_to_negev.py.
"""
import json, sys, os, math, gzip, glob, statistics
msb_dir, data_dir = sys.argv[1:3]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))
W = 3200   # window side, metres
# (village frame name in cluster_frames 'en', recognized town key in transit_access) - village frames are the largest named
# unrecognized clusters with no served stop within 400 m; the last pair compares two recognized towns
PAIRS = [('Al Danfiri', 'lehavim'), ('Al Walidi', 'meytar'), (None, 'hura', 'omer')]
TOWN_EN = {'lehavim': 'Lehavim', 'meytar': 'Meitar', 'omer': 'Omer', 'hura': 'Hura'}

stops = [f['geometry']['coordinates'] for f in J('transit_stops.geojson')['features']]
C = 0.02; idx = {}
for x, y in stops: idx.setdefault((int(x / C), int(y / C)), []).append((x, y))
def near_m(x, y):
    kx = 111.32 * math.cos(math.radians(y)); best = 1e9
    for di in range(-3, 4):
        for dj in range(-3, 4):
            for a, b in idx.get((int(x / C) + di, int(y / C) + dj), ()):
                best = min(best, math.hypot((a - x) * kx, (b - y) * 110.57))
    return best * 1000
cls = lambda d: 0 if d < 400 else 1 if d < 1000 else 2 if d < 3000 else 3

def window(cx, cy):
    kx = 111320 * math.cos(math.radians(cy)); ky = 110570
    hx, hy = W / 2 / kx, W / 2 / ky
    return {'x0': cx - hx, 'y0': cy - hy, 'x1': cx + hx, 'y1': cy + hy, 'kx': kx, 'ky': ky}
def local(w, ring):
    return [(round((x - w['x0']) * w['kx']), round((y - w['y0']) * w['ky'])) for x, y in ring]
def enc(c, pts):
    out = [c, pts[0][0], pts[0][1]]
    for (a, b), (p, q) in zip(pts, pts[1:]): out += [p - a, q - b]
    return out
def in_w(w, x, y): return w['x0'] <= x <= w['x1'] and w['y0'] <= y <= w['y1']
def stops_in(w):
    m = 450 / w['ky']   # keep stops just outside the window so their 400 m circles still show at the edge
    return [[round((x - w['x0']) * w['kx']), round((y - w['y0']) * w['ky'])] for x, y in stops
            if w['x0'] - m <= x <= w['x1'] + m and w['y0'] - m <= y <= w['y1'] + m]

# off-map houses
off = J('offmap_buildings.json'); od = J('offmap_stopdist.json'); OFF = []
for a, d in zip(off, od):
    x, y = a[2], a[3]; ring = [(x / 1e5, y / 1e5)]
    for i in range(4, len(a), 2): x += a[i]; y += a[i + 1]; ring.append((x / 1e5, y / 1e5))
    OFF.append((ring, sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring), d))
frames = {}
for f in J('cluster_frames.geojson')['features']:
    p = f['properties']
    if p['c'] == 'u' and (p['en'] not in frames or p['n'] > frames[p['en']]['properties']['n']): frames[p['en']] = f

acc = {t['key']: t for t in J('transit_access.json')['towns']}
need = {k for pr in PAIRS for k in pr[1:] if k}
# town centre = mean of the town's own buildings (inside its municipal limit); windows filled with Microsoft footprints
KEYS = {'Lehavim': 'lehavim', 'Meitar': 'meytar', 'Omer': 'omer', 'Hura': 'hura'}
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
polys = {}
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    en = (f['properties'].get('Muni_Eng') or '').strip()
    if en in KEYS and KEYS[en] in need:
        g = f['geometry']; polys[KEYS[en]] = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
MS = []
for fn in glob.glob(os.path.join(msb_dir, '*.csv.gz')):
    for line in gzip.open(fn, 'rt', encoding='utf-8'):
        ring = json.loads(line)['geometry']['coordinates'][0]
        x = sum(c[0] for c in ring[:-1]) / (len(ring) - 1); y = sum(c[1] for c in ring[:-1]) / (len(ring) - 1)
        if 34.6 <= x <= 35.1 and 31.15 <= y <= 31.45: MS.append((ring[:-1], x, y))
centre = {}
for k, ps in polys.items():
    xs = [(x, y) for _, x, y in MS if any(in_ring(x, y, p[0]) for p in ps)]
    # densest 250 m cell as the centre (the municipal polygon can be far larger than the town)
    cells = {}
    for x, y in xs: cells.setdefault((math.floor(x / .0025), math.floor(y / .0025)), []).append((x, y))
    best = max(cells, key=lambda c: sum(len(cells.get((c[0] + i, c[1] + j), ())) for i in range(-3, 4) for j in range(-3, 4)))
    pts = [p for i in range(-3, 4) for j in range(-3, 4) for p in cells.get((best[0] + i, best[1] + j), ())]
    centre[k] = (statistics.median(p[0] for p in pts), statistics.median(p[1] for p in pts))

def town_panel(k):
    w = window(*centre[k]); t = acc[k]; b = []
    for ring, x, y in MS:
        if in_w(w, x, y): b.append(enc(cls(near_m(x, y)), local(w, ring)))
    return {'name': {'ar': t['ar'], 'he': t['he'], 'en': t['en']}, 'kind': 'arab_town' if t['grp'] == 'arab' else 'jewish_town',
            'pct_lt400': t['pct_lt400'], 'median_m': t['median_m'], 'n': t['n'], 'b': b, 's': stops_in(w)}
def village_panel(name):
    f = frames[name]; r = f['geometry']['coordinates'][0]
    x0, x1 = min(p[0] for p in r), max(p[0] for p in r); y0, y1 = min(p[1] for p in r), max(p[1] for p in r)
    w = window((x0 + x1) / 2, (y0 + y1) / 2)
    ds = [d for ring, x, y, d in OFF if x0 <= x <= x1 and y0 <= y <= y1]
    b = [enc(cls(d), local(w, ring)) for ring, x, y, d in OFF if in_w(w, x, y)]
    p = f['properties']
    return {'name': {'ar': p['ar'], 'he': p['en'], 'en': p['en']}, 'kind': 'unrec', 'pct_lt400': round(sum(d < 400 for d in ds) / len(ds) * 100, 1),
            'median_m': round(statistics.median(ds)), 'n': len(ds), 'b': b, 's': stops_in(w)}
out = []
for pr in PAIRS:
    a = village_panel(pr[0]) if pr[0] else town_panel(pr[1]); j = town_panel(pr[-1])
    out.append({'a': a, 'j': j}); print(a['name']['en'], a['pct_lt400'], a['median_m'], len(a['b']), 'bld', len(a['s']), 'stops |',
                                       j['name']['en'], j['pct_lt400'], j['median_m'], len(j['b']), 'bld', len(j['s']), 'stops')
json.dump({'window_m': W, 'classes_m': [400, 1000, 3000], 'source': 'MoT GTFS (served stops) · Microsoft footprints · OSM · iplan',
           'pairs': out}, open(os.path.join(data_dir, 'transit_pairs.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
