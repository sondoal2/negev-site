"""Slim two team members' data packages for the site (chapters 05 parks, 06 safety).
   safety_parks_prep.py <dir with the delivered files> <site data dir>
   Reads only; writes small site files. Numbers are copied from the packages, not recomputed,
   except the park grid, which aggregates the delivered per-home distances into 250 m cells."""
import sys, os, json, statistics
src, out = sys.argv[1], sys.argv[2]
J = lambda f: json.load(open(os.path.join(src, f), encoding='utf8'))
def dump(name, obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    open(os.path.join(out, name), 'w', encoding='utf8').write(s); print(name, len(s) // 1024, 'KB')
r5 = lambda c: [round(c[0], 5), round(c[1], 5)]
def rnd(g):
    if g['type'] == 'Point': return {'type': 'Point', 'coordinates': r5(g['coordinates'])}
    if g['type'] == 'Polygon': return {'type': 'Polygon', 'coordinates': [[r5(p) for p in ring] for ring in g['coordinates']]}
    return {'type': 'MultiPolygon', 'coordinates': [[[r5(p) for p in ring] for ring in poly] for poly in g['coordinates']]}

# ---------- 06 safety ----------
st = J('police_stations_negev.geojson'); pt = J('police_points_negev.geojson'); em = J('emergency_services_negev.geojson')
feats = [{'type': 'Feature', 'geometry': rnd(f['geometry']), 'properties': {'k': 'st', 'nm': f['properties']['name_he']}} for f in st['features']]
feats += [{'type': 'Feature', 'geometry': rnd(f['geometry']), 'properties': {'k': 'pt', 'nm': f['properties']['name_he']}}
          for f in pt['features'] if f['properties']['kind'] == 'police_point' or f['properties'].get('community_policing_center')]
feats += [{'type': 'Feature', 'geometry': rnd(f['geometry']), 'properties': {'k': {'fire_station': 'fire', 'general_hospital': 'hosp'}[f['properties']['kind']], 'nm': f['properties']['name_he']}}
          for f in em['features'] if f['properties']['kind'] in ('fire_station', 'general_hospital') and f['properties']['name_he']]
dump('safety_points.geojson', {'type': 'FeatureCollection', 'features': feats})

acc = J('police_accessibility_negev.geojson')
G = {'arab_town': 'a', 'jewish_town': 'j', 'unrecognized': 'u', 'expansion': 'e'}
dump('police_grid.geojson', {'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'geometry': rnd(f['geometry']), 'properties': {'g': G.get(f['properties']['group'], '?'), 'd': f['properties']['station_median_m'], 'n': f['properties']['n_buildings']}}
    for f in acc['features']]})

off = J('offmap_safety_data.json')['groups']
keep = ['n_buildings', 'station_median_m', 'station_pct_le2km', 'station_pct_le5km', 'station_pct_le10km', 'station_pct_gt10km',
        'fire_median_m', 'fire_pct_gt10km', 'hospital_median_m']
grp = {k: {x: off[k].get(x) for x in keep} for k in ('arab_town', 'jewish_town', 'unrecognized', 'expansion') if k in off}
for k in grp:
    for x in ('drive_min_median_of_towns', 'drive_min_median_weighted', 'drive_min_median', 'towns'):
        if x in off[k]: grp[k][x] = off[k][x]
dump('safety_stats.json', {'groups': grp, 'stations_south': 15,
     'source_date': '2026-11-20', 'note': 'copied from the team package (offmap_safety_data.json); scripts/safety_parks_prep.py'})

# ---------- 05 parks ----------
for a, b in (('parks_planned_final.geojson', 'parks_planned.geojson'), ('parks_actual_final.geojson', 'parks_actual.geojson')):
    P = J(a)
    dump(b, {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'geometry': rnd(f['geometry']), 'properties': {'a': round(f['properties'].get('area_m2') or 0)}} for f in P['features']]})

H = J('homes_park_access.geojson'); cells = {}
for f in H['features']:
    x, y = f['geometry']['coordinates']; key = (int(x // 0.0025), int(y // 0.0025))
    c = cells.setdefault(key, {'d': [], 'g': {}}); c['d'].append(f['properties']['dist_m']); g = f['properties']['group']; c['g'][g] = c['g'].get(g, 0) + 1
gf = []
for (i, j), c in cells.items():
    x0, y0 = round(i * 0.0025, 4), round(j * 0.0025, 4); x1, y1 = round(x0 + 0.0025, 4), round(y0 + 0.0025, 4)
    gf.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]},
               'properties': {'d': round(statistics.median(c['d'])), 'n': len(c['d']), 'g': max(c['g'], key=c['g'].get)}})
dump('parks_grid.geojson', {'type': 'FeatureCollection', 'features': gf})
print('groups in homes file:', sorted({f['properties']['group'] for f in H['features']}))

# parks summary table (team member's xlsx) -> parks_stats.json
import openpyxl
wb = openpyxl.load_workbook(os.path.join(src, 'parks_summary_final.xlsx'), data_only=True)
A = list(wb['access_500m'].iter_rows(values_only=True))[1:]
gk = {'بلدات يهودية': 'jewish', 'بلدات وقرى عربية معترف فيها': 'arab', 'بيوت خارج الخط الأزرق': 'expansion', 'قرى غير معترف فيها': 'unrec'}
acc5 = {gk[r[0]]: {'homes': r[1], 'ground_pct': r[2], 'ground_med': r[3], 'paper_pct': r[4], 'paper_med': r[5]} for r in A if r[0] in gk}
P = list(wb['per_resident'].iter_rows(values_only=True))[1:]
per = {'jewish': P[0][3:5], 'arab7': P[1][3:5], 'abubasma': P[2][3:5], 'jewish_rural': P[3][3:5]}
T = list(wb['by_town'].iter_rows(values_only=True))[1:]
towns = [{'en': r[0], 'he': r[1], 'grp': 'arab' if r[2] == 'عربية' else 'jewish', 'pop': r[3], 'paper_m2pc': r[5], 'ground_m2pc': r[7]} for r in T if r[0]]
dump('parks_stats.json', {'access500': acc5, 'per_resident': {k: {'paper': v[0], 'ground': v[1]} for k, v in per.items()}, 'towns': towns,
     'n_planned': 2248, 'n_actual': 1805, 'note': "team member's parks_summary_final.xlsx; scripts/safety_parks_prep.py"})

# Arabic town names for the parks bars
AR = {'Rahat': 'رهط', 'Tel Sheva': 'تل السبع', 'Hura': 'حورة', 'Kseyfe': 'كسيفة', "Ar'ara Banegev": 'عرعرة النقب', 'Lakiye': 'اللقية', 'Segev Shalom': 'شقيب السلام',
      "Be'er Sheva": 'بئر السبع', 'Netivot': 'نتيفوت', 'Eilat': 'إيلات', 'Ofakim': 'أوفاكيم', 'Dimona': 'ديمونا', 'Arad': 'عراد', 'Yeroham': 'يروحام',
      'Meitar': 'ميتار', 'Omer': 'عومر', 'Lehavim': 'لهافيم', 'Mitspe Ramon': 'متسبيه رامون'}
ps = json.load(open(os.path.join(out, 'parks_stats.json'), encoding='utf8'))
for t in ps['towns']: t['ar'] = AR[t['en']]
dump('parks_stats.json', ps)
