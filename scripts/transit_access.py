"""Walking access to a bus stop: straight-line distance from every house to the nearest bus stop that is actually served.

Inputs
  gtfs_zip  Israel MoT GTFS (gtfs.mot.gov.il/gtfsfiles/israel-public-transportation.zip)
  msb_dir   Microsoft Global ML Building Footprints, Israel tiles (*.csv.gz)
  data_dir  this site's data/ folder (offmap_buildings.json, muni.geojson, rahat.geojson, industry_stats.json, bld_offmap_grid.geojson)

Method
  * Served stop = a stop with >= 1 departure on the representative weekday (first Tuesday >= 2 days after the feed starts).
    Stops listed in stops.txt with no trip that day are dropped (they exist in the file but no bus calls there).
  * Houses outside recognition = data/offmap_buildings.json, per building (not per 250 m cell):
      'u' = unrecognized village, 'e' = built beyond a recognized Arab locality's blue line.
  * Recognized towns = Microsoft footprints whose centroid is inside the municipal limit (iplan) of the 18 comparison towns
    in industry_stats.json (7 Arab, 11 Jewish), kept only if they belong to the town's connected built-up area
    (adjacent 250 m cells with >= 3 buildings, reachable from the densest cell). This drops scattered structures inside large
    jurisdictions. It does NOT fully remove the Bedouin clusters inside Arad's limit (5-7 km west of the town) because a
    strip of houses along the road links them to the town; they stay counted as "Arad", which LOWERS the Jewish-town share.
    That is the conservative choice. Optional extra cut CORE_RF=2.2 (drop cells beyond 2.2x the radius of a circle with
    the core's area) removes them: Jewish towns within 400 m go from 90.3% to 94.6% - the gap only grows.
  * A town where the footprints cover < 30 buildings per 1,000 residents (Microsoft has almost no data for Netivot and Eilat)
    is reported but left out of the group totals.
  * Distance = straight line (local equirectangular, km/deg from latitude). Real walking distance is longer.
  * Classes: <400 m (MoT/planning walking standard for a stop), 400 m-1 km, 1-3 km, >3 km.

Outputs (data/)
  transit_stops.geojson   served stops in the Naqab: [lon,lat] + trips that day
  offmap_stopdist.json    distance in metres for each building in offmap_buildings.json (same order)
  grid_stopdist.json      median distance per cell of bld_offmap_grid.geojson (same order)
  transit_access.json     shares per group and per town
"""
import zipfile, csv, io, json, sys, os, math, gzip, glob, datetime, statistics
gtfs_zip, msb_dir, data_dir = sys.argv[1:4]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))
BBOX = (34.15, 29.4, 35.55, 31.75)   # Naqab + margin
RF = float(os.environ.get("CORE_RF", "0"))   # optional core radius factor; 0 = off (see docstring)

# ---------- served stops ----------
zf = zipfile.ZipFile(gtfs_zip)
R = lambda n: csv.DictReader(io.TextIOWrapper(zf.open(n), encoding='utf-8-sig'))
stops = {}
for s in R('stops.txt'):
    x, y = float(s['stop_lon']), float(s['stop_lat'])
    if BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3] and s.get('location_type', '0') in ('', '0'):
        stops[s['stop_id']] = {'x': x, 'y': y, 'name': s['stop_name'], 'trips': 0}
cal = list(R('calendar.txt'))
start = min(datetime.datetime.strptime(c['start_date'], '%Y%m%d') for c in cal)
day = start + datetime.timedelta(days=2)
while day.weekday() != 1: day += datetime.timedelta(days=1)
ds = day.strftime('%Y%m%d')
services = {c['service_id'] for c in cal if c['tuesday'] == '1' and c['start_date'] <= ds <= c['end_date']}
trips = {t['trip_id'] for t in R('trips.txt') if t['service_id'] in services}
for st in R('stop_times.txt'):
    s = stops.get(st['stop_id'])
    if s is not None and st['trip_id'] in trips: s['trips'] += 1
served = [s for s in stops.values() if s['trips'] > 0]
print('date', ds, 'stops in bbox', len(stops), 'served', len(served), 'unserved', len(stops) - len(served))

# ---------- nearest-stop index ----------
C = 0.02
idx = {}
for s in served: idx.setdefault((int(s['x'] / C), int(s['y'] / C)), []).append((s['x'], s['y']))
def near_m(x, y):
    kx, ky = 111.32 * math.cos(math.radians(y)), 110.57
    i, j = int(x / C), int(y / C); best = 1e9; r = 0
    while True:
        for di in range(-r, r + 1):
            for dj in range(-r, r + 1):
                if max(abs(di), abs(dj)) != r: continue
                for a, b in idx.get((i + di, j + dj), ()):
                    d = math.hypot((a - x) * kx, (b - y) * ky)
                    if d < best: best = d
        # every unvisited cell is at least r*C degrees away
        if best <= r * C * min(kx, ky) or r > 40: return best * 1000
        r += 1
CLS = [(400, 'lt400'), (1000, 'm400_1k'), (3000, 'k1_3'), (1e12, 'gt3k')]
def cls(d): return next(k for lim, k in CLS if d < lim)
def summary(ds_):
    n = len(ds_); c = {k: 0 for _, k in CLS}
    for d in ds_: c[cls(d)] += 1
    return {'n': n, **{k: c[k] for k in c}, **{'pct_' + k: round(c[k] / n * 100, 1) for k in c}, 'median_m': round(statistics.median(ds_)) if n else None}

# ---------- off-map houses (per building) ----------
off = J('offmap_buildings.json'); od = []; grp = {'u': [], 'e': []}; cent = []
for a in off:
    x, y = a[2], a[3]; xs, ys = [x], [y]
    for i in range(4, len(a), 2): x += a[i]; y += a[i + 1]; xs.append(x); ys.append(y)
    cx, cy = sum(xs) / len(xs) / 1e5, sum(ys) / len(ys) / 1e5
    d = near_m(cx, cy); od.append(round(d / 10) * 10); grp[a[0]].append(d); cent.append((cx, cy, d))
json.dump(od, open(os.path.join(data_dir, 'offmap_stopdist.json'), 'w'), separators=(',', ':'))
# per 250 m cell of the site grid
grid = J('bld_offmap_grid.geojson')['features']; cell = {}
for k, f in enumerate(grid):
    r = f['geometry']['coordinates'][0]; cell[(round(min(p[0] for p in r) / .0025), round(min(p[1] for p in r) / .0025))] = k
bucket = {}
for cx, cy, d in cent:
    k = cell.get((math.floor(cx / .0025 + 1e-9), math.floor(cy / .0025 + 1e-9)))
    if k is not None: bucket.setdefault(k, []).append(d)
gd = [round(statistics.median(bucket[k]) / 10) * 10 if k in bucket else None for k in range(len(grid))]
print('grid cells with a median', sum(v is not None for v in gd), '/', len(grid))
json.dump(gd, open(os.path.join(data_dir, 'grid_stopdist.json'), 'w'), separators=(',', ':'))

# ---------- the 18 recognized towns (Microsoft footprints inside municipal limits) ----------
KEYS = {'Arad': 'arad', "Be'er Sheva": 'beer sheva', 'Dimona': 'dimona', 'Eilat': 'eilat', 'Lehavim': 'lehavim', 'Meitar': 'meytar', 'Mitspe Ramon': 'mizpe ramon',
        'Netivot': 'netivot', 'Ofakim': 'ofakim', 'Omer': 'omer', 'Yeroham': 'yeruham', "Ar'ara Banegev": 'arara negev', 'Hura': 'hura', 'Kseyfe': 'kseifa',
        'Lakiye': 'lakia', 'Rahat': 'rahat', 'Segev Shalom': 'shegev shalom', 'Tel Sheva': 'tel sheva'}
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
towns = []
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    en = (f['properties'].get('Muni_Eng') or '').strip()
    if en in KEYS and not any(t['key'] == KEYS[en] for t in towns):
        g = f['geometry']; ps = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        xs = [c[0] for p in ps for c in p[0]]; ys = [c[1] for p in ps for c in p[0]]
        towns.append({'key': KEYS[en], 'ps': ps, 'bb': (min(xs), min(ys), max(xs), max(ys)), 'pts': []})
missing = set(KEYS.values()) - {t['key'] for t in towns}
if missing: print('WARNING towns without a polygon:', missing)
for fn in glob.glob(os.path.join(msb_dir, '*.csv.gz')):
    for line in gzip.open(fn, 'rt', encoding='utf-8'):
        ring = json.loads(line)['geometry']['coordinates'][0]
        x = sum(c[0] for c in ring[:-1]) / (len(ring) - 1); y = sum(c[1] for c in ring[:-1]) / (len(ring) - 1)
        if not (BBOX[0] <= x <= BBOX[2] and BBOX[1] <= y <= BBOX[3]): continue
        for t in towns:
            b = t['bb']
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in t['ps']):
                t['pts'].append((x, y)); break
ist = {r['key']: r for r in J('industry_stats.json')['rows']}
def core(pts):
    cells = {}
    for x, y in pts: cells.setdefault((math.floor(x / .0025), math.floor(y / .0025)), []).append((x, y))
    if not cells: return [], 0
    seed = max(cells, key=lambda c: len(cells[c])); seen = {seed}; todo = [seed]
    while todo:
        i, j = todo.pop()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                c = (i + di, j + dj)
                if c in cells and c not in seen and len(cells[c]) >= 3: seen.add(c); todo.append(c)
    # optional (CORE_RF>0): also cut cells farther than RF x the radius of a circle with the core's area (strips of houses along a road
    # can chain a separate settlement to the town)
    rmax = RF * math.sqrt(len(seen) * 0.0625 / math.pi)   # km; one cell = 0.0625 km2
    kx = 111.32 * math.cos(math.radians(seed[1] * .0025))
    if RF > 0: seen = {c for c in seen if math.hypot((c[0] - seed[0]) * .0025 * kx, (c[1] - seed[1]) * .0025 * 110.57) <= rmax}
    keep = [p for c in seen for p in cells[c]]
    return keep, len(pts) - len(keep)
rows = []
for t in towns:
    r = ist[t['key']]; keep, dropped = core(t['pts']); t['d'] = [near_m(x, y) for x, y in keep]
    cover = len(t['pts']) / r['pop'] * 1000; t['ok'] = cover >= 30
    s = summary(t['d']) if t['d'] else {'n': 0}
    rows.append({'key': t['key'], 'grp': r['grp'], 'he': r['he'], 'ar': r['ar'], 'en': r['en'], **s, 'outside_core': dropped, 'bld_per_1000': round(cover), 'in_totals': t['ok']})
    print(f"{r['en']:15} {r['grp']:6} n={s['n']:6} dropped={dropped:5} cover={cover:5.0f}/1000 ok={t['ok']} <400={s.get('pct_lt400')}% median={s.get('median_m')} m")
pool = lambda g: [d for t in towns if ist[t['key']]['grp'] == g and t['ok'] for d in t['d']]
groups = {'unrec': summary(grp['u']), 'expansion': summary(grp['e']), 'arab_towns': summary(pool('arab')), 'jewish_towns': summary(pool('jewish'))}
for g in ('arab', 'jewish'): groups[g + '_towns']['towns'] = sum(1 for t in towns if ist[t['key']]['grp'] == g and t['ok'])
for k, v in groups.items(): print(k, v)
# served stops layer (compact)
fs = [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(s['x'], 5), round(s['y'], 5)]}, 'properties': {'t': s['trips'], 'nm': s['name']}} for s in served]
json.dump({'type': 'FeatureCollection', 'features': fs}, open(os.path.join(data_dir, 'transit_stops.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump({'date': ds, 'stops_in_bbox': len(stops), 'stops_served': len(served),
           'source': 'Israel MoT GTFS (gtfs.mot.gov.il) · Microsoft Global ML Building Footprints · iplan municipal limits · OSM',
           'method': 'straight-line distance from each building centroid to the nearest stop with >=1 departure on the weekday',
           'groups': groups, 'towns': rows},
          open(os.path.join(data_dir, 'transit_access.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
