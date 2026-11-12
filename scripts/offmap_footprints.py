"""Step 1: write the actual building footprints (polygons) that lie outside every recognized locality,
using the same rule as the site (<=2.5 km from a candidate village OR inside Neve Midbar / al-Kasum)."""
import gzip, json, sys, os, glob, math
msb_dir, data_dir, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
def prep(g):
    ps = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
    return [(min(c[0] for c in p[0]), min(c[1] for c in p[0]), max(c[0] for c in p[0]), max(c[1] for c in p[0]), p) for p in ps]
def inside(x, y, pp):
    return any(x0 <= x <= x1 and y0 <= y <= y1 and in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for x0, y0, x1, y1, p in pp)
REGIONAL = {'Neve Midbar','al Kasum','Merhavim','Sdot Negev','Ramat Negev','Hevel Eielot',"Ha'arava Hatihona","Bnei Shim'on",'Eshkol','Tamar'}
nafa = prep(J('negev_nafa.geojson')['features'][0]['geometry'])
locs = []
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    if (f['properties'].get('Muni_Eng') or '').strip() not in REGIONAL: locs.append(prep(f['geometry']))
for f in J('vaadim.geojson')['features']:
    v = (f['properties'].get('Vaad_Eng') or '').strip()
    if v and not v.upper().startswith('GENERAL'): locs.append(prep(f['geometry']))
bbs = [(min(p[0] for p in l), min(p[1] for p in l), max(p[2] for p in l), max(p[3] for p in l), l) for l in locs]
rc = [prep(f['geometry']) for f in J('muni.geojson')['features'] if (f['properties'].get('Muni_Eng') or '').strip() in ('Neve Midbar', 'al Kasum')]
V = [(v['lon'], v['lat']) for v in J('buildings_summary.json')['villages']]
n = 0
with open(out_path, 'w', encoding='utf-8') as o:
    o.write('{"type":"FeatureCollection","features":[')
    for fn in glob.glob(os.path.join(msb_dir, '*.csv.gz')):
        for line in gzip.open(fn, 'rt', encoding='utf-8'):
            f = json.loads(line); ring = f['geometry']['coordinates'][0]
            x = sum(c[0] for c in ring[:-1]) / (len(ring) - 1); y = sum(c[1] for c in ring[:-1]) / (len(ring) - 1)
            if not (34.25 <= x <= 35.5 and 30.4 <= y <= 31.6) or not inside(x, y, nafa): continue
            if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] and inside(x, y, b[4]) for b in bbs): continue
            if not (any(math.hypot((x - a) * 95.5, (y - b) * 111.0) < 2.5 for a, b in V) or any(inside(x, y, g) for g in rc)): continue
            o.write((',' if n else '') + json.dumps({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[round(c[0], 6), round(c[1], 6)] for c in ring]]}, 'properties': {}}, separators=(',', ':')))
            n += 1
    o.write(']}')
print('footprints', n)
