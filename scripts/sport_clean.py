"""Sports facilities for chapter 05 - cleaning a team member's extract of the Ministry of Culture & Sport facilities register
(data.gov.il dataset #408, version 25.7.2021) and counting facilities per 1,000 young people (6-18) in the 18 towns.

Inputs: sport_facilities_negev.geojson and town_youth_summary.csv (team member), data_dir
Cleaning
  * drop points outside the Be'er Sheva subdistrict / beyond the Green Line band (same rule as clip_to_negev.py):
    18 mis-geocoded points (Aqaba listed under Eilat, Segev Shalom and Kuseife points outside the Negev, one in Saudi Arabia)
  * drop facilities marked "לא פעיל" or "לא תקין ולא פעיל"
  * full facilities only = sports halls, pitches/courts, pools, stadiums. Street fitness stations, "other" and gyms are
    kept on the map as light points but NOT counted (a pull-up bar is not a sports hall).
  * a facility = a register row; several rows can share one site (same coordinates) - both counts are kept.
Youth 6-18 per town: the team member's table (population registry). Councils (al-Kasum, Neve Midbar) have no youth figure.
Outputs: data/sport_facilities.geojson (k = f full / l light), data/sport_stats.json
"""
import json, sys, os, csv, collections
src_geo, src_csv, data_dir = sys.argv[1:4]
J = lambda f: json.load(open(os.path.join(data_dir, f), encoding='utf-8'))
g = J('negev_nafa.geojson')['features'][0]['geometry']; PS = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
def in_ring(x, y, r):
    ins = False; j = len(r) - 1
    for i in range(len(r)):
        xi, yi = r[i][0], r[i][1]; xj, yj = r[j][0], r[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: ins = not ins
        j = i
    return ins
def ok_place(x, y): return not (y > 31.345 and 34.95 <= x <= 35.30) and any(in_ring(x, y, p[0]) for p in PS)
FULL = ('אולם', 'מגרש', 'בריכ', 'אצטדיון')
feats = json.load(open(src_geo, encoding='utf-8'))['features']
drop = collections.Counter(); out = []
for f in feats:
    p = f['properties']; x, y = f['geometry']['coordinates'][:2]
    if not ok_place(x, y): drop['outside'] += 1; continue
    if p.get('condition') in ('לא פעיל', 'לא תקין ולא פעיל'): drop['inactive'] += 1; continue
    k = 'f' if any(w in (p.get('type') or '') for w in FULL) else 'l'
    out.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(x, 6), round(y, 6)]},
                'properties': {'k': k, 'town': p['town'], 'nm': p.get('name') or '', 'type': p.get('type') or '', 'loc': p.get('locality') or p.get('authority') or ''}})
print('register rows', len(feats), 'kept', len(out), 'dropped', dict(drop), 'full', sum(o['properties']['k'] == 'f' for o in out))
youth = {}
for r in csv.DictReader(open(src_csv, encoding='utf-8-sig')):
    try: youth[r['key']] = int(r['age_6_18'])
    except (ValueError, KeyError): pass
ist = {r['key']: r for r in J('industry_stats.json')['rows']}
rows = []
for key in list(ist) + ['al kasum', 'neve midbar']:
    F = [o for o in out if o['properties']['town'] == key and o['properties']['k'] == 'f']
    sites = len({tuple(o['geometry']['coordinates']) for o in F})
    r = ist.get(key, {}); y = youth.get(key)
    rows.append({'key': key, 'grp': r.get('grp', 'arab_council'), 'ar': r.get('ar'), 'he': r.get('he'), 'en': r.get('en', key), 'full': len(F), 'sites': sites,
                 'youth_6_18': y, 'per_1000_youth': round(len(F) / y * 1000, 2) if y else None})
def grp(gname):
    R = [r for r in rows if r['grp'] == gname and r['youth_6_18']]
    n, y = sum(r['full'] for r in R), sum(r['youth_6_18'] for r in R)
    return {'towns': len(R), 'full': n, 'youth': y, 'per_1000_youth': round(n / y * 1000, 2)}
S = {'arab_towns': grp('arab'), 'jewish_towns': grp('jewish')}
for r in rows: print(f"{r['en']:15} {r['grp']:12} full={r['full']:4} sites={r['sites']:4} youth={r['youth_6_18']} per1000={r['per_1000_youth']}")
print(S)
json.dump({'type': 'FeatureCollection', 'features': out}, open(os.path.join(data_dir, 'sport_facilities.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
json.dump({'source': 'Ministry of Culture & Sport facilities register, data.gov.il #408 (25.7.2021), extracted by a team member; youth 6-18 from the team member\'s population-registry table',
           'cleaning': dict(drop), 'groups': S, 'towns': rows}, open(os.path.join(data_dir, 'sport_stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
