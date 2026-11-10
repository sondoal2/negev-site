"""Classify Microsoft ML building footprints in the northern Naqab by recognized-locality status.
Outputs: offmap buildings (centroids outside every recognized locality), per-locality counts, per red-list village counts."""
import gzip, json, sys, os, glob, math
msb_dir, data_dir = sys.argv[1], sys.argv[2]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))

def polys(g):
    return [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
def prep(g):
    out = []
    for p in polys(g):
        xs = [c[0] for c in p[0]]; ys = [c[1] for c in p[0]]
        out.append((min(xs), min(ys), max(xs), max(ys), p))
    return out
def inside(x, y, pp):
    for x0, y0, x1, y1, p in pp:
        if x0 <= x <= x1 and y0 <= y <= y1 and in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]): return True
    return False

nafa = prep(J('negev_nafa.geojson')['features'][0]['geometry'])
REGIONAL = {'Neve Midbar','al Kasum','Merhavim','Sdot Negev','Ramat Negev','Hevel Eielot',"Ha'arava Hatihona","Bnei Shim'on",'Eshkol','Tamar'}
ARAB = {'Tel Sheva','Segev Shalom',"Ar'ara Banegev",'Lakiye','Kseyfe','Hura','Rahat','Neve Midbar','al Kasum'}
locs = []
for f in J('muni.geojson')['features'] + J('rahat.geojson')['features']:
    en = (f['properties'].get('Muni_Eng') or '').strip()
    if en in REGIONAL: continue
    locs.append({'name': en, 'grp': 'industrial' if en == 'Neot Hovav' else ('arab' if en in ARAB else 'jewish'), 'pp': prep(f['geometry']), 'n': 0, 'area': 0})
for f in J('vaadim.geojson')['features']:
    v = (f['properties'].get('Vaad_Eng') or '').strip(); m = (f['properties'].get('Muni_Eng') or '').strip()
    if not v or v.upper().startswith('GENERAL'): continue
    locs.append({'name': v.title(), 'grp': 'arab' if m in ARAB else 'jewish', 'pp': prep(f['geometry']), 'n': 0, 'area': 0})
for l in locs:
    l['bb'] = (min(p[0] for p in l['pp']), min(p[1] for p in l['pp']), max(p[2] for p in l['pp']), max(p[3] for p in l['pp']))

def ring_area(c):  # m², spherical approx
    a = 0
    for i in range(len(c) - 1):
        a += math.radians(c[i+1][0] - c[i][0]) * (2 + math.sin(math.radians(c[i][1])) + math.sin(math.radians(c[i+1][1])))
    return abs(a * 6378137 ** 2 / 2)

off = []; tot = 0
for fn in glob.glob(os.path.join(msb_dir, '*.csv.gz')):
    for line in gzip.open(fn, 'rt', encoding='utf-8'):
        f = json.loads(line); ring = f['geometry']['coordinates'][0]
        x = sum(c[0] for c in ring[:-1]) / (len(ring) - 1); y = sum(c[1] for c in ring[:-1]) / (len(ring) - 1)
        if not (34.25 <= x <= 35.5 and 30.4 <= y <= 31.6) or not inside(x, y, nafa): continue
        tot += 1; a = ring_area(ring); hit = None
        for l in locs:
            b = l['bb']
            if b[0] <= x <= b[2] and b[1] <= y <= b[3] and inside(x, y, l['pp']): hit = l; break
        if hit: hit['n'] += 1; hit['area'] += a
        else: off.append((round(x, 5), round(y, 5), round(a)))

# red-list village counts (nearest candidate village within 2 km)
un = []
places = J('osm_places.geojson')['features']
import re
ar = re.compile('[؀-ۿ]')
for f in places:
    p = f['properties']; c = f['geometry']['coordinates']
    if not c or not c[0] or not ar.search(p.get('name') or ''): continue
    if not inside(c[0], c[1], nafa) or any(inside(c[0], c[1], l['pp']) for l in locs): continue
    un.append({'name': p.get('ar') or p['name'], 'en': p.get('en') or p['name'], 'c': c, 'n': 0})
for x, y, a in off:
    best, bd = None, 2.0
    for u in un:
        d = math.hypot((x - u['c'][0]) * 95.5, (y - u['c'][1]) * 111.0)
        if d < bd: best, bd = u, d
    if best: best['n'] += 1

json.dump({'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [x, y]}, 'properties': {'a': a}} for x, y, a in off]},
          open(os.path.join(data_dir, 'bld_offmap.geojson'), 'w'), separators=(',', ':'))
summary = {'source': 'Microsoft Global ML Building Footprints (release 2026-02-03), centroid-in-polygon vs iplan locality limits',
           'total_in_negev_subdistrict': tot, 'outside_recognized': len(off),
           'by_group': {g: {'buildings': sum(l['n'] for l in locs if l['grp'] == g), 'roof_m2': round(sum(l['area'] for l in locs if l['grp'] == g))} for g in ('arab', 'jewish', 'industrial')},
           'localities': sorted([{'name': l['name'], 'grp': l['grp'], 'buildings': l['n']} for l in locs if l['n']], key=lambda d: -d['buildings']),
           'villages': sorted([{'ar': u['name'], 'en': u['en'], 'lon': u['c'][0], 'lat': u['c'][1], 'buildings': u['n']} for u in un], key=lambda d: -d['buildings'])}
json.dump(summary, open(os.path.join(data_dir, 'buildings_summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('total', tot, 'outside recognized', len(off), summary['by_group'])
print('top villages', [(v['en'], v['buildings']) for v in summary['villages'][:12]])
