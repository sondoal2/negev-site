"""Cut Microsoft footprints (VIDA Google+Microsoft Israel parquet, Microsoft 2024-05 release) for every recognized Bedouin
town and village (iplan limits in data/). Keeps buildings whose centroid lies inside the locality limit.
  python scripts/bedouin_buildings_cut.py <site_dir> <ISR.parquet> <out.json>
out: {locality: [[x,y,area_m2, ring...], ...]}  ring as flat [x0,y0,x1,y1,...] rounded to 1e-6"""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, geo_lite as geo
import pyarrow.parquet as pq, pyarrow.compute as pc

site, src, out = sys.argv[1:4]; D = os.path.join(site, 'data')
mu = json.load(open(os.path.join(D, 'muni.geojson'), encoding='utf8'))['features']
va = json.load(open(os.path.join(D, 'vaadim.geojson'), encoding='utf8'))['features']
ra = json.load(open(os.path.join(D, 'rahat.geojson'), encoding='utf8'))['features']
TOWNS = {'Tel Sheva', 'Segev Shalom', "Ar'ara Banegev", 'Lakiye', 'Kseyfe', 'Hura'}
LOC = [('Rahat', f['geometry']) for f in ra] + [(f['properties']['Muni_Eng'].strip(), f['geometry']) for f in mu if f['properties']['Muni_Eng'].strip() in TOWNS] + \
      [(f['properties']['Vaad_Eng'], f['geometry']) for f in va if f['properties']['Muni_Eng'].strip() in ('al Kasum', 'Neve Midbar') and f['properties']['Vaad_Eng'] != 'GENERAL']
def bbox(g):
    a = np.array([c for p in geo.polys(g) for c in p[0]]); return a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max()
BB = [(n, g, bbox(g)) for n, g in LOC]
X0 = min(b[0] for _, _, b in BB); Y0 = min(b[1] for _, _, b in BB); X1 = max(b[2] for _, _, b in BB); Y1 = max(b[3] for _, _, b in BB)

def ring(b):
    le = b[0] == 1; e = '<' if le else '>'; t, = struct.unpack_from(e + 'I', b, 1)
    o = 9 if t == 3 else 18  # polygon: skip nrings; multipolygon: skip count + first polygon header
    n, = struct.unpack_from(e + 'I', b, o); pts = struct.unpack_from(e + '%dd' % (2 * n), b, o + 4)
    return pts
f = pq.ParquetFile(src); cand = []; seen = set()
for i in range(f.metadata.num_row_groups):
    t = f.read_row_group(i, columns=['area_in_meters', 'geometry', 'bbox'])
    bb = t.column('bbox'); x = pc.struct_field(bb, 'xmin'); y = pc.struct_field(bb, 'ymin')
    m = pc.and_(pc.and_(pc.greater_equal(x, X0), pc.less_equal(x, X1)), pc.and_(pc.greater_equal(y, Y0), pc.less_equal(y, Y1)))
    t = t.filter(m)
    for a, g in zip(t.column('area_in_meters').to_pylist(), t.column('geometry').to_pylist()):
        if g in seen: continue
        seen.add(g); cand.append((a, ring(g)))
cx = np.array([np.mean(p[0:-2:2]) for _, p in cand]); cy = np.array([np.mean(p[1:-2:2]) for _, p in cand])
res = {}
for name, g, b in BB:
    pre = np.where((cx >= b[0]) & (cx <= b[2]) & (cy >= b[1]) & (cy <= b[3]))[0]
    inside = pre[geo.in_geom(cx[pre], cy[pre], g)]
    res.setdefault(name, [])
    res[name] += [[round(cx[k], 6), round(cy[k], 6), round(cand[k][0] or 0, 1), [round(v, 6) for v in cand[k][1]]] for k in inside]
    print(name, len(inside), flush=True)
json.dump(res, open(out, 'w', encoding='utf8'), separators=(',', ':'))
print('total', sum(len(v) for v in res.values()))
