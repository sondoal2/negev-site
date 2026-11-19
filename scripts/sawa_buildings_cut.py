"""Cut building footprints around Sa'wa from the VIDA Google+Microsoft Israel parquet.
usage: cut_sawa.py ISR.parquet out.geojson"""
import sys, json, struct
import pyarrow.parquet as pq, pyarrow.compute as pc

X0, Y0, X1, Y1 = 34.938, 31.232, 35.005, 31.274
src, out = sys.argv[1], sys.argv[2]
f = pq.ParquetFile(src)

def wkb_polys(b):
    """Return list of polygons (list of rings) from WKB Polygon/MultiPolygon."""
    def rd_poly(b, o, le):
        e = '<' if le else '>'
        nr, = struct.unpack_from(e + 'I', b, o); o += 4
        rings = []
        for _ in range(nr):
            n, = struct.unpack_from(e + 'I', b, o); o += 4
            pts = struct.unpack_from(e + '%dd' % (2 * n), b, o); o += 16 * n
            rings.append([[round(pts[i], 7), round(pts[i + 1], 7)] for i in range(0, 2 * n, 2)])
        return rings, o
    le = b[0] == 1; e = '<' if le else '>'
    t, = struct.unpack_from(e + 'I', b, 1)
    if t == 3:
        p, _ = rd_poly(b, 5, le); return [p]
    if t == 6:
        n, = struct.unpack_from(e + 'I', b, 5); o = 9; ps = []
        for _ in range(n):
            le2 = b[o] == 1; p, o = rd_poly(b, o + 5, le2); ps.append(p)
        return ps
    return []

feats, seen, cnt = [], set(), {}
for i in range(f.metadata.num_row_groups):
    t = f.read_row_group(i, columns=['bf_source', 'area_in_meters', 'geometry', 'bbox'])
    bb = t.column('bbox')
    xmin = pc.struct_field(bb, 'xmin'); ymin = pc.struct_field(bb, 'ymin')
    m = pc.and_(pc.and_(pc.greater_equal(xmin, X0), pc.less_equal(xmin, X1)),
                pc.and_(pc.greater_equal(ymin, Y0), pc.less_equal(ymin, Y1)))
    t = t.filter(m)
    if not t.num_rows: continue
    for s, a, g in zip(t.column('bf_source').to_pylist(), t.column('area_in_meters').to_pylist(), t.column('geometry').to_pylist()):
        if g in seen: continue
        seen.add(g)
        for p in wkb_polys(g):
            feats.append({'type': 'Feature', 'properties': {'s': s[0], 'a': round(a or 0, 1)},
                          'geometry': {'type': 'Polygon', 'coordinates': p}})
            cnt[s] = cnt.get(s, 0) + 1
json.dump({'type': 'FeatureCollection', 'features': feats}, open(out, 'w', encoding='utf8'), separators=(',', ':'))
print('features', len(feats), cnt)
