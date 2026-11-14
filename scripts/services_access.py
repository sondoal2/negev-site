"""Distance from every house to the nearest elementary school and the nearest clinic - unrecognized villages vs towns.

Inputs
  msb_dir   Microsoft Global ML Building Footprints, Israel tiles (*.csv.gz)
  raw_dir   cache folder; Ministry of Education tables are downloaded here from data.gov.il if missing:
              מוסדות חינוך        resource 2055063b-93e8-4d6a-b2c5-c253d18c0cf6  (type, level, status, sector, ITM X/Y)
              קואורדינטות מוסדות  resource 5c5d6bb0-755d-470d-84b6-d7dd3135ba9c  (lon/lat per institution)
            and osm_health.json (Overpass: amenity=clinic|doctors|hospital, healthcare=clinic|doctor|centre|hospital)
  data_dir  this site's data/

Method (same building sets and town cores as transit_access.py)
  * Elementary school = active MoE institution of type "בית ספר" whose level includes "יסודי" (Arab, Bedouin and Jewish).
    Location: the MoE coordinates table; if missing, the ITM X/Y of the institutions table (converted here).
  * Clinic = OSM health facility (not pharmacy / dentist). OSM is incomplete, especially in unrecognized villages
    (some have a ministry or Clalit clinic that is not mapped) - distances there are an upper bound.
  * Straight-line distance from each building centroid. Classes: <500 m, 0.5-1 km, 1-3 km, >3 km.
Outputs (data/)
  services_points.geojson   schools (k = e elementary, h high school, o other) and clinics (k = c) in the subdistrict
  services_access.json      shares per group and per town, for 'school' and 'clinic'
  grid_svcdist.json         {school:[...], clinic:[...]} median distance per cell of bld_offmap_grid.geojson
"""
import json, sys, os, math, gzip, glob, statistics, urllib.request, urllib.parse
msb_dir, raw_dir, data_dir = sys.argv[1:4]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))
BBOX = (34.15, 30.4, 35.55, 31.75)

def datastore(rid, filters=None):
    cache = os.path.join(raw_dir, f'moe_{rid[:8]}.json')
    if os.path.exists(cache): return json.load(open(cache, encoding='utf-8'))
    out, off = [], 0
    while True:
        q = {'resource_id': rid, 'limit': 32000, 'offset': off}
        if filters: q['filters'] = json.dumps(filters, ensure_ascii=False)
        d = json.load(urllib.request.urlopen(urllib.request.Request('https://data.gov.il/api/3/action/datastore_search?' + urllib.parse.urlencode(q), headers={'User-Agent': 'Mozilla/5.0'})))['result']
        out += d['records']; off += 32000
        if len(out) >= d['total'] or not d['records']: break
    json.dump(out, open(cache, 'w', encoding='utf-8'), ensure_ascii=False); return out

def itm_to_wgs(E, N):
    """Israeli TM Grid (EPSG:2039) -> lon/lat on GRS80; the Israel 1993 / WGS84 difference (~1 m) is ignored."""
    a, f = 6378137.0, 1 / 298.257222101; e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    k0, lat0, lon0, FE, FN = 1.0000067, math.radians(31.7343936111), math.radians(35.2045169444), 219529.584, 626907.390
    def M(p): return a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * p - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * p)
                          + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * p) - (35 * e2 ** 3 / 3072) * math.sin(6 * p))
    m = M(lat0) + (N - FN) / k0; mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256)); e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
    C1 = ep2 * math.cos(p1) ** 2; T1 = math.tan(p1) ** 2; N1 = a / math.sqrt(1 - e2 * math.sin(p1) ** 2); R1 = a * (1 - e2) / (1 - e2 * math.sin(p1) ** 2) ** 1.5
    D = (E - FE) / (N1 * k0)
    lat = p1 - (N1 * math.tan(p1) / R1) * (D ** 2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720)
    lon = lon0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120) / math.cos(p1)
    return math.degrees(lon), math.degrees(lat)

def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
ng = J('negev_nafa.geojson')['features'][0]['geometry']; NPS = [ng['coordinates']] if ng['type'] == 'Polygon' else ng['coordinates']
in_negev = lambda x, y: any(in_ring(x, y, p[0]) for p in NPS)

# ---------- facilities ----------
inst = datastore('2055063b-93e8-4d6a-b2c5-c253d18c0cf6', {'SHEM_MAHUZ': 'דרום'})
co = {str(c['SEMEL_MOSAD']): c for c in datastore('5c5d6bb0-755d-470d-84b6-d7dd3135ba9c')}
schools = []; itm_used = 0
for r in inst:
    if r['TEUR_TAT_SUG_MISGERET'] != 'בית ספר' or r['TEUR_STATUS'] != 'פעיל': continue
    c = co.get(str(r['SEMEL_MOSAD']))
    if c and c.get('UTM_X'): x, y = float(c['UTM_X']), float(c['UTM_Y'])
    else: x, y = itm_to_wgs(float(r['X']), float(r['Y'])); itm_used += 1
    lvl = r['TEUR_SHLAV_HINUH'] or ''
    schools.append({'x': x, 'y': y, 'k': 'e' if 'יסודי' in lvl else 'h' if 'עליונה' in lvl else 'o', 'nm': r['SHEM_MOSAD'], 'loc': r['ISV_SHEM_ISHUV'], 'sec': r['TEUR_MIGZAR']})
print('schools', len(schools), 'elementary', sum(s['k'] == 'e' for s in schools), 'located from ITM', itm_used)
clinics = []
for e in json.load(open(os.path.join(raw_dir, 'osm_health.json'), encoding='utf-8'))['elements']:
    c = e.get('center') or ({'lon': e['lon'], 'lat': e['lat']} if 'lon' in e else None)
    if not c: continue
    t = e.get('tags', {}); clinics.append({'x': c['lon'], 'y': c['lat'], 'k': 'c', 'nm': t.get('name:' + 'ar') or t.get('name') or t.get('name:he') or '', 'loc': t.get('operator', '')})
clinics = [c for c in clinics if BBOX[0] <= c['x'] <= BBOX[2] and BBOX[1] <= c['y'] <= BBOX[3]]
print('clinics (OSM)', len(clinics), 'in subdistrict', sum(in_negev(c['x'], c['y']) for c in clinics))

def index(pts):
    C = 0.02; idx = {}
    for p in pts: idx.setdefault((int(p['x'] / C), int(p['y'] / C)), []).append((p['x'], p['y']))
    def near_m(x, y):
        kx, ky = 111.32 * math.cos(math.radians(y)), 110.57; i, j = int(x / C), int(y / C); best = 1e9; r = 0
        while True:
            for di in range(-r, r + 1):
                for dj in range(-r, r + 1):
                    if max(abs(di), abs(dj)) != r: continue
                    for a, b in idx.get((i + di, j + dj), ()):
                        d = math.hypot((a - x) * kx, (b - y) * ky)
                        if d < best: best = d
            if best <= r * C * min(kx, ky) or r > 60: return best * 1000
            r += 1
    return near_m
NEAR = {'school': index([s for s in schools if s['k'] == 'e']), 'clinic': index(clinics)}
CLS = [(500, 'lt500'), (1000, 'm500_1k'), (3000, 'k1_3'), (1e12, 'gt3k')]
def summary(ds):
    n = len(ds); c = {k: 0 for _, k in CLS}
    for d in ds: c[next(k for lim, k in CLS if d < lim)] += 1
    return {'n': n, **{'pct_' + k: round(c[k] / n * 100, 1) for k in c}, 'pct_lt1k': round((c['lt500'] + c['m500_1k']) / n * 100, 1),
            'median_m': round(statistics.median(ds)) if n else None}

# ---------- off-map houses ----------
cent = []
for a in J('offmap_buildings.json'):
    x, y = a[2], a[3]; xs, ys = [x], [y]
    for i in range(4, len(a), 2): x += a[i]; y += a[i + 1]; xs.append(x); ys.append(y)
    cent.append((sum(xs) / len(xs) / 1e5, sum(ys) / len(ys) / 1e5, a[0]))
grid = J('bld_offmap_grid.geojson')['features']; cell = {}
for k, f in enumerate(grid):
    r = f['geometry']['coordinates'][0]; cell[(round(min(p[0] for p in r) / .0025), round(min(p[1] for p in r) / .0025))] = k
res = {}; gridd = {}
for svc, near in NEAR.items():
    D = [near(x, y) for x, y, _ in cent]; bucket = {}
    for (x, y, _), d in zip(cent, D):
        k = cell.get((math.floor(x / .0025 + 1e-9), math.floor(y / .0025 + 1e-9)))
        if k is not None: bucket.setdefault(k, []).append(d)
    gridd[svc] = [round(statistics.median(bucket[k]) / 10) * 10 if k in bucket else None for k in range(len(grid))]
    res[svc] = {'groups': {'unrec': summary([d for (_, _, c), d in zip(cent, D) if c == 'u']), 'expansion': summary([d for (_, _, c), d in zip(cent, D) if c == 'e'])}}

# ---------- town cores (identical rule to transit_access.py) ----------
KEYS = {'Arad': 'arad', "Be'er Sheva": 'beer sheva', 'Dimona': 'dimona', 'Eilat': 'eilat', 'Lehavim': 'lehavim', 'Meitar': 'meytar', 'Mitspe Ramon': 'mizpe ramon',
        'Netivot': 'netivot', 'Ofakim': 'ofakim', 'Omer': 'omer', 'Yeroham': 'yeruham', "Ar'ara Banegev": 'arara negev', 'Hura': 'hura', 'Kseyfe': 'kseifa',
        'Lakiye': 'lakia', 'Rahat': 'rahat', 'Segev Shalom': 'shegev shalom', 'Tel Sheva': 'tel sheva'}
towns = []
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    en = (f['properties'].get('Muni_Eng') or '').strip()
    if en in KEYS and not any(t['key'] == KEYS[en] for t in towns):
        g = f['geometry']; ps = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        xs = [c[0] for p in ps for c in p[0]]; ys = [c[1] for p in ps for c in p[0]]
        towns.append({'key': KEYS[en], 'ps': ps, 'bb': (min(xs), min(ys), max(xs), max(ys)), 'pts': []})
for fn in glob.glob(os.path.join(msb_dir, '*.csv.gz')):
    for line in gzip.open(fn, 'rt', encoding='utf-8'):
        ring = json.loads(line)['geometry']['coordinates'][0]
        x = sum(c[0] for c in ring[:-1]) / (len(ring) - 1); y = sum(c[1] for c in ring[:-1]) / (len(ring) - 1)
        for t in towns:
            b = t['bb']
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in t['ps']):
                t['pts'].append((x, y)); break
def core(pts):
    cells = {}
    for x, y in pts: cells.setdefault((math.floor(x / .0025), math.floor(y / .0025)), []).append((x, y))
    if not cells: return []
    seed = max(cells, key=lambda c: len(cells[c])); seen = {seed}; todo = [seed]
    while todo:
        i, j = todo.pop()
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                c = (i + di, j + dj)
                if c in cells and c not in seen and len(cells[c]) >= 3: seen.add(c); todo.append(c)
    return [p for c in seen for p in cells[c]]
ist = {r['key']: r for r in J('industry_stats.json')['rows']}
for t in towns:
    t['core'] = core(t['pts']); t['ok'] = len(t['pts']) / ist[t['key']]['pop'] * 1000 >= 30
for svc, near in NEAR.items():
    rows = []; pool = {'arab': [], 'jewish': []}
    for t in towns:
        r = ist[t['key']]; ds = [near(x, y) for x, y in t['core']]
        rows.append({'key': t['key'], 'grp': r['grp'], 'ar': r['ar'], 'he': r['he'], 'en': r['en'], 'in_totals': t['ok'], **(summary(ds) if ds else {'n': 0})})
        if t['ok']: pool[r['grp']] += ds
    res[svc]['groups'].update({'arab_towns': {**summary(pool['arab']), 'towns': sum(1 for t in towns if t['ok'] and ist[t['key']]['grp'] == 'arab')},
                               'jewish_towns': {**summary(pool['jewish']), 'towns': sum(1 for t in towns if t['ok'] and ist[t['key']]['grp'] == 'jewish')}})
    res[svc]['towns'] = rows
    for k, v in res[svc]['groups'].items(): print(svc, k, 'n', v['n'], '<500', v['pct_lt500'], '<1km', v['pct_lt1k'], 'median', v['median_m'])

pts = [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(p['x'], 5), round(p['y'], 5)]}, 'properties': {'k': p['k'], 'nm': p['nm'], 'loc': p['loc']}}
       for p in schools + clinics if in_negev(p['x'], p['y'])]
json.dump({'type': 'FeatureCollection', 'features': pts}, open(os.path.join(data_dir, 'services_points.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump(gridd, open(os.path.join(data_dir, 'grid_svcdist.json'), 'w'), separators=(',', ':'))
json.dump({'source': {'school': 'Ministry of Education - institutions and coordinates (data.gov.il), active elementary schools',
                      'clinic': 'OpenStreetMap health facilities (Overpass ' + json.load(open(os.path.join(raw_dir, 'osm_health.json'), encoding='utf-8'))['osm3s']['timestamp_osm_base'][:10] + ')'},
           'counts': {'schools_elementary': sum(s['k'] == 'e' for s in schools), 'clinics': len(clinics)}, **res},
          open(os.path.join(data_dir, 'services_access.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
