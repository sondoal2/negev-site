"""Sa'wa: plan vs ground. Three measures from Xplan land use (approved Sa'wa neighbourhood plans) and Microsoft footprints.
usage: sawa_plan_vs_ground.py site_dir  -> prints table, writes data/sawa_planground.json"""
import sys, os, json, datetime, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, geo_lite as geo

site = sys.argv[1]; D = os.path.join(site, 'data')
vd = json.load(open(os.path.join(D, 'vaadim.geojson'), encoding='utf8'))
sw = [f for f in vd['features'] if (f['properties'].get('Vaad_Eng') or '').strip() == 'Sawa'][0]
B = json.load(open(os.path.join(D, 'sawa_buildings.geojson'), encoding='utf8'))['features']
cx, cy = np.array([geo.centroid(f['geometry']['coordinates']) for f in B]).T
area = np.array([f['properties']['a'] for f in B])
ins = geo.in_geom(cx, cy, sw['geometry'])
B = [b for b, k in zip(B, ins) if k]; cx, cy, area = cx[ins], cy[ins], area[ins]; N = len(B)
# all footprint vertices, with building index, for "plot touched by a building"
vx, vy, vi = [], [], []
for i, b in enumerate(B):
    r = b['geometry']['coordinates'][0][:-1]
    vx += [p[0] for p in r]; vy += [p[1] for p in r]; vi += [i] * len(r)
vx, vy, vi = np.array(vx), np.array(vy), np.array(vi)

P = json.load(open(os.path.join(D, 'xplan_sawa_plans.geojson'), encoding='utf-8-sig'))['features']
L = json.load(open(os.path.join(D, 'xplan_sawa_landuse.geojson'), encoding='utf-8-sig'))['features']
ym = lambda ms: datetime.datetime.utcfromtimestamp(ms / 1000).strftime('%Y-%m') if ms else None
plan_meta = {p['properties']['pl_number']: p['properties'] for p in P}

RES = {"מגורים א'", "מגורים ב'", 'מגורים ומסחר'}
GROUP = {'דרך מוצעת': 'road', 'דרך משולבת': 'road', 'דרך מאושרת': 'road', 'שביל': 'road', 'חניון': 'road',
         'דרך ו/או טיפול נופי': 'road', 'טיילת': 'road', 'שטח ציבורי פתוח': 'open', 'נחל/תעלת נחל': 'stream',
         'מבנים ומוסדות ציבור': 'public', 'קרקע חקלאית': 'agri'}

zone_of = np.array([None] * N, dtype=object)   # land-use name under each building centroid
plan_of = np.array([None] * N, dtype=object)
plots = []
for f in L:
    p = f['properties']
    if 'סעו' not in (p.get('pl_name') or '') or p.get('station_desc') != 'אישור': continue
    g = f['geometry']; name = p.get('mavat_name')
    m = geo.in_geom(cx, cy, g) & (zone_of == None)
    zone_of[m] = name; plan_of[m] = p.get('pl_number')
    if name in RES:
        touched = geo.in_geom(cx, cy, g).any() or geo.in_geom(vx, vy, g).any()
        plots.append((p.get('pl_number'), sum(geo.poly_area_m2(q) for q in geo.polys(g)), touched))

in_plan = zone_of != None
out = {'buildings': int(N), 'in_neigh_plan': int(in_plan.sum()), 'outside_neigh_plan': int((~in_plan).sum())}
print('buildings', N, '| inside approved neighbourhood land use', in_plan.sum(), '| outside', (~in_plan).sum(), round(100 * (~in_plan).mean(), 1), '%')

# 2) conflict: buildings on non-residential zones
g = np.array([GROUP.get(z, 'other' if z else None) if z not in RES else 'res' for z in zone_of], dtype=object)
cnt = collections.Counter(g[in_plan]); print('zones under buildings inside plans:', dict(cnt))
conf = np.isin(g, ['road', 'open', 'stream', 'public'])
print('conflict (road/open/stream/public)', conf.sum(), round(100 * conf.sum() / in_plan.sum(), 1), '% of buildings inside plans')
big = area >= 40
print('  same, footprints >=40 m2 only:', (conf & big).sum(), 'of', (in_plan & big).sum(), round(100 * (conf & big).sum() / (in_plan & big).sum(), 1), '%')
print('  on agricultural land', (g == 'agri').sum())
out.update(conflict=int(conf.sum()), conflict_by={k: int(cnt.get(k, 0)) for k in ('road', 'open', 'stream', 'public', 'agri', 'res', 'other')},
           conflict_pct=round(100 * conf.sum() / in_plan.sum(), 1))

# 3) planned & empty: residential plots touched by no footprint
pa = np.array([a for _, a, _ in plots]); pt = np.array([t for _, _, t in plots])
print('residential plots', len(plots), 'empty', (~pt).sum(), round(100 * (~pt).mean(), 1), '% by count;',
      round(100 * pa[~pt].sum() / pa.sum(), 1), '% by area;', round(pa[~pt].sum() / 1000, 1), 'of', round(pa.sum() / 1000, 1), 'dunam')
out.update(res_plots=len(plots), res_plots_empty=int((~pt).sum()), res_empty_pct_count=round(100 * (~pt).mean(), 1),
           res_empty_pct_area=round(100 * pa[~pt].sum() / pa.sum(), 1), res_dunam=round(pa.sum() / 1000, 1))

# per plan
per = []
for num in sorted({x for x, _, _ in plots}):
    sel = np.array([x == num for x, _, _ in plots]); m = plan_meta.get(num, {})
    row = dict(plan=num, name=m.get('pl_name'), approved=ym(m.get('date_saf')), plots=int(sel.sum()),
               empty_pct=round(100 * (~pt[sel]).mean(), 1), buildings=int((plan_of == num).sum()),
               conflict=int((conf & (plan_of == num)).sum()))
    per.append(row); print(row)
out['per_plan'] = per
out['sources'] = {'footprints': 'Microsoft GlobalML Building Footprints 2024-05-28 via VIDA/source.coop (imagery 2014-2023)',
                  'plans': 'iplan Xplan layer 1 & 4, downloaded 2026-11-19', 'limit': 'iplan gvulot_retzef/2 (vaadim) Sawa'}
json.dump(out, open(os.path.join(D, 'sawa_planground.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)

# per-building category for the 3D view: o = outside every neighbourhood plan, c = conflict zone, a = agricultural, i = inside (residential/other)
kk = np.where(~in_plan, 'o', np.where(conf, 'c', np.where(g == 'agri', 'a', 'i')))
fc = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'k': str(k), 'a': b['properties']['a']}, 'geometry': b['geometry']} for b, k in zip(B, kk)]}
json.dump(fc, open(os.path.join(D, 'sawa_bld_cat.geojson'), 'w', encoding='utf8'), separators=(',', ':'))
print('wrote sawa_bld_cat.geojson', collections.Counter(kk.tolist()))
