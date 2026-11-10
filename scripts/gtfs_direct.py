"""Direct (no-transfer) public-transport connectivity from Naqab localities to Be'er Sheva, Tel Aviv-Yafo, Jerusalem
on one representative weekday, from the Israel MoT GTFS feed."""
import zipfile, csv, io, json, sys, os, datetime, urllib.request, urllib.parse
gtfs_zip, data_dir = sys.argv[1], sys.argv[2]
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

# zones: Negev localities (cities/local councils + village committees) and the three destinations
REGIONAL = {'Neve Midbar','al Kasum','Merhavim','Sdot Negev','Ramat Negev','Hevel Eielot',"Ha'arava Hatihona","Bnei Shim'on",'Eshkol','Tamar'}
ARAB = {'Tel Sheva','Segev Shalom',"Ar'ara Banegev",'Lakiye','Kseyfe','Hura','Rahat','Neve Midbar','al Kasum'}
zones = []
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    en = (f['properties'].get('Muni_Eng') or '').strip()
    if en in REGIONAL or en == 'Neot Hovav': continue
    zones.append({'id': en, 'grp': 'arab' if en in ARAB else 'jewish', 'g': f['geometry'], 'he': f['properties'].get('Muni_Heb')})
for f in J('vaadim.geojson')['features']:
    v = (f['properties'].get('Vaad_Eng') or '').strip(); m = (f['properties'].get('Muni_Eng') or '').strip()
    if not v or v.upper().startswith('GENERAL'): continue
    zones.append({'id': v.title(), 'grp': 'arab' if m in ARAB else 'jewish', 'g': f['geometry'], 'he': f['properties'].get('Vaad_Heb')})
for f in json.load(open(sys.argv[3], encoding='utf-8'))['features']:
    zones.append({'id': f['properties']['Muni_Eng'].strip(), 'grp': 'dest', 'g': f['geometry']})
for z in zones:
    ps = [z['g']['coordinates']] if z['g']['type'] == 'Polygon' else z['g']['coordinates']
    xs = [c[0] for p in ps for c in p[0]]; ys = [c[1] for p in ps for c in p[0]]
    z['bb'] = (min(xs), min(ys), max(xs), max(ys))
for z in zones:
    i = z['id'].lower()
    if i.startswith("be'er sheva"): z['dest'] = 'bs'
    elif i.startswith('tel aviv'): z['dest'] = 'ta'
    elif i.startswith('yerushalayim'): z['dest'] = 'jm'
print('zones', len(zones), 'dest', [(z['id'], z.get('dest')) for z in zones if z.get('dest')])

zf = zipfile.ZipFile(gtfs_zip)
R = lambda n: csv.DictReader(io.TextIOWrapper(zf.open(n), encoding='utf-8-sig'))
stop_zone = {}
for s in R('stops.txt'):
    x, y = float(s['stop_lon']), float(s['stop_lat'])
    for z in zones:
        b = z['bb']
        if b[0] <= x <= b[2] and b[1] <= y <= b[3] and inside(x, y, z['g']): stop_zone[s['stop_id']] = z['id']; break
print('stops in zones', len(stop_zone))

# representative weekday: first Tuesday at least 2 days after the feed starts
cal = list(R('calendar.txt'))
start = min(datetime.datetime.strptime(c['start_date'], '%Y%m%d') for c in cal)
day = start + datetime.timedelta(days=2)
while day.weekday() != 1: day += datetime.timedelta(days=1)
ds = day.strftime('%Y%m%d')
services = {c['service_id'] for c in cal if c['tuesday'] == '1' and c['start_date'] <= ds <= c['end_date']}
routes = {r['route_id']: r for r in R('routes.txt')}
trips = {}
for t in R('trips.txt'):
    if t['service_id'] in services: trips[t['trip_id']] = t['route_id']
print('date', ds, 'active trips', len(trips))

seq = {}
for st in R('stop_times.txt'):
    tid = st['trip_id']
    if tid not in trips: continue
    z = stop_zone.get(st['stop_id'])
    if z: seq.setdefault(tid, []).append((int(st['stop_sequence']), z, st['departure_time']))
def mins(t): h, m, s = map(int, t.split(':')); return h * 60 + m
dest_of = {z['id']: z['dest'] for z in zones if z.get('dest')}
res = {z['id']: {'grp': z['grp'], 'he': z.get('he'), 'departures': 0, 'bs': [], 'ta': [], 'jm': []} for z in zones if z['grp'] != 'dest'}
for tid, s in seq.items():
    s.sort(); seen_origin = {}
    for _, z, t in s:
        if z in res and z not in seen_origin: seen_origin[z] = mins(t); res[z]['departures'] += 1
        d = dest_of.get(z)
        if d:
            for o, t0 in seen_origin.items():
                if dest_of.get(o) == d: continue
                if len(res[o][d]) == 0 or res[o][d][-1][0] != tid: res[o][d].append((tid, mins(t) - t0, routes[trips[tid]].get('route_short_name')))
out = []
for zid, r in res.items():
    row = {'id': zid, 'he': r['he'], 'grp': r['grp'], 'departures': r['departures']}
    for d in ('bs', 'ta', 'jm'):
        row[d + '_trips'] = len(r[d]); row[d + '_min'] = min((x[1] for x in r[d]), default=None)
        row[d + '_lines'] = sorted({x[2] for x in r[d] if x[2]})[:12]
    out.append(row)
json.dump({'date': ds, 'source': 'Israel MoT GTFS (gtfs.mot.gov.il), direct trips without transfer', 'rows': out},
          open(os.path.join(data_dir, 'transit_direct.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in sorted(out, key=lambda r: -r['departures'])[:25]: print(r['id'], r['grp'], r['departures'], 'BS', r['bs_trips'], 'TA', r['ta_trips'], r['ta_min'], 'JM', r['jm_trips'], r['jm_min'])
