"""Chapter 07, every recognized Bedouin locality: which buildings stand with NO approved plan over them.
Covered = centroid inside the boundary of an approved plan (Xplan layer 1; not a policy document; under 30 km2, so regional umbrella
plans do not count) OR inside an approved land-use plot (layer 4; a real use, under 3 km2). Land use alone is not enough: the towns'
older plans have boundaries in Xplan but no digital plots (Rahat: 79% inside an approved boundary, 20% inside digital plots).
  python scripts/bedouin_noplan.py <work_dir>
work_dir holds bedouin_bld.json (scripts/bedouin_buildings_cut.py), xplan_bedouin_plans.geojson and xplan_bedouin_landuse.geojson
(downloaded in a browser). Writes noplan.json and noplan_pts.json there (copied to data/bedouin_noplan*.json)."""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, geo_lite as geo
S = sys.argv[1]
BLD = json.load(open(os.path.join(S, 'bedouin_bld.json'), encoding='utf8'))
P = json.load(open(os.path.join(S, 'xplan_bedouin_plans.geojson'), encoding='utf-8-sig'))['features']
LU = json.load(open(os.path.join(S, 'xplan_bedouin_landuse.geojson'), encoding='utf-8-sig'))['features']
def bbox(f):
    xy = np.array([c for q in geo.polys(f['geometry']) for c in q[0]]); return (f, xy[:, 0].min(), xy[:, 1].min(), xy[:, 0].max(), xy[:, 1].max())
COVER = []
for f in P:
    p = f['properties']
    if p.get('internet_short_status') != 'התכנית אושרה' or p.get('entity_subtype_desc') == 'מסמך מדיניות': continue
    if sum(geo.poly_area_m2(q) for q in geo.polys(f['geometry'])) > 3e7: continue
    COVER.append(bbox(f))
nb = len(COVER)
for f in LU:
    p = f['properties']; nm = p.get('mavat_name') or ''
    if p.get('station_desc') != 'אישור' or 'תכנית' in nm or not nm: continue
    if sum(geo.poly_area_m2(q) for q in geo.polys(f['geometry'])) > 3e6: continue
    COVER.append(bbox(f))
print('approved plan boundaries', nb, '+ approved land-use plots', len(COVER) - nb)
res = {}; T = collections.Counter(); PTS = {}
for loc, B in BLD.items():
    cx = np.array([b[0] for b in B]); cy = np.array([b[1] for b in B]); ar = np.array([b[2] for b in B]); m = np.zeros(len(B), bool)
    for f, x0, y0, x1, y1 in COVER:
        if x1 < cx.min() or x0 > cx.max() or y1 < cy.min() or y0 > cy.max(): continue
        sel = ~m & (cx >= x0) & (cx <= x1) & (cy >= y0) & (cy <= y1)
        if sel.any(): idx = np.where(sel)[0]; m[idx[geo.in_geom(cx[idx], cy[idx], f['geometry'])]] = True
    PTS[loc] = [[int(round(x * 1e5)), int(round(y * 1e5)), int(not k)] for x, y, k in zip(cx, cy, m)]
    res[loc] = {'buildings': len(B), 'no_plan': int((~m).sum()), 'no_plan_pct': round(100 * (~m).mean(), 1), 'no_plan_ge40': int(((~m) & (ar >= 40)).sum())}
    T['buildings'] += len(B); T['no_plan'] += int((~m).sum())
    print(f"{loc:16s} no approved plan: {res[loc]['no_plan']:6d} of {len(B):6d} ({res[loc]['no_plan_pct']}%)")
print('TOTAL', dict(T), round(100 * T['no_plan'] / T['buildings'], 1))
json.dump({'rows': res, 'totals': dict(T)}, open(os.path.join(S, 'noplan.json'), 'w', encoding='utf8'), ensure_ascii=False)
json.dump(PTS, open(os.path.join(S, 'noplan_pts.json'), 'w', encoding='utf8'), separators=(',', ':'))
