"""Real route geometries (GTFS shapes) of direct, no-transfer trips from the 17 Naqab comparison towns
to Tel Aviv-Yafo and Jerusalem on one weekday. Output: transit_routes.geojson (one line per town x destination x shape)."""
import zipfile, csv, io, json, sys, os, datetime
gtfs_zip, data_dir, dest_file = sys.argv[1], sys.argv[2], sys.argv[3]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
def inside(x, y, g):
    ps = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    return any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in ps)
TOWNS = {'Rahat','Hura','Kseyfe','Lakiye','Tel Sheva','Segev Shalom',"Ar'ara Banegev",'Netivot','Ofakim','Dimona','Arad','Eilat','Omer','Yeroham','Lehavim','Meitar','Mitspe Ramon'}
ARAB = {'Rahat','Hura','Kseyfe','Lakiye','Tel Sheva','Segev Shalom',"Ar'ara Banegev"}
zones = []
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    en = (f['properties'].get('Muni_Eng') or '').strip()
    if en in TOWNS: zones.append({'id': en, 'g': f['geometry'], 'dest': None})
for f in json.load(open(dest_file, encoding='utf-8'))['features']:
    en = f['properties']['Muni_Eng'].strip().lower()
    zones.append({'id': en, 'g': f['geometry'], 'dest': 'ta' if en.startswith('tel aviv') else 'jm'})
for z in zones:
    ps = [z['g']['coordinates']] if z['g']['type'] == 'Polygon' else z['g']['coordinates']
    xs = [c[0] for p in ps for c in p[0]]; ys = [c[1] for p in ps for c in p[0]]; z['bb'] = (min(xs), min(ys), max(xs), max(ys))
zf = zipfile.ZipFile(gtfs_zip)
R = lambda n: csv.DictReader(io.TextIOWrapper(zf.open(n), encoding='utf-8-sig'))
stop_zone = {}
for s in R('stops.txt'):
    x, y = float(s['stop_lon']), float(s['stop_lat'])
    for z in zones:
        b = z['bb']
        if b[0] <= x <= b[2] and b[1] <= y <= b[3] and inside(x, y, z['g']): stop_zone[s['stop_id']] = z; break
cal = list(R('calendar.txt'))
start = min(datetime.datetime.strptime(c['start_date'], '%Y%m%d') for c in cal)
day = start + datetime.timedelta(days=2)
while day.weekday() != 1: day += datetime.timedelta(days=1)
ds = day.strftime('%Y%m%d')
services = {c['service_id'] for c in cal if c['tuesday'] == '1' and c['start_date'] <= ds <= c['end_date']}
trips = {t['trip_id']: t.get('shape_id') for t in R('trips.txt') if t['service_id'] in services}
seq = {}
for st in R('stop_times.txt'):
    if st['trip_id'] in trips and st['stop_id'] in stop_zone: seq.setdefault(st['trip_id'], []).append((int(st['stop_sequence']), stop_zone[st['stop_id']]))
count = {}
for tid, s in seq.items():
    s.sort(); seen = set()
    for _, z in s:
        if z['dest'] is None: seen.add(z['id'])
        else:
            for o in seen: k = (o, z['dest'], trips[tid]); count[k] = count.get(k, 0) + 1
            seen = set()  # count each trip once per destination reached after the origin
need = {k[2] for k in count if k[2]}
pts = {}
for r in R('shapes.txt'):
    if r['shape_id'] in need: pts.setdefault(r['shape_id'], []).append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat'])))
fs = []
for (o, d, sid), n in count.items():
    p = sorted(pts.get(sid, []))
    if len(p) < 2: continue
    step = max(1, len(p) // 120)
    line = [[round(x, 4), round(y, 4)] for _, x, y in p[::step]] + [[round(p[-1][1], 4), round(p[-1][2], 4)]]
    fs.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': line}, 'properties': {'o': o, 'd': d, 'n': n, 'grp': 'arab' if o in ARAB else 'jewish'}})
json.dump({'type': 'FeatureCollection', 'date': ds, 'features': fs}, open(os.path.join(data_dir, 'transit_routes.geojson'), 'w', encoding='utf-8'), separators=(',', ':'))
by = {}
for f in fs: by[f['properties']['o']] = by.get(f['properties']['o'], 0) + f['properties']['n']
print('date', ds, 'route lines', len(fs), 'size KB', round(os.path.getsize(os.path.join(data_dir, 'transit_routes.geojson')) / 1024))
print(sorted(by.items(), key=lambda kv: -kv[1]))
