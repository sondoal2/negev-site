"""Tiny geometry helpers (no shapely): local metres, ring area, point-in-polygon."""
import math
import numpy as np

LAT0 = 31.25
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110540

def polys(geom):
    """Polygon/MultiPolygon -> list of polygons, each a list of rings [[x,y],...]."""
    if geom is None: return []
    if geom['type'] == 'Polygon': return [geom['coordinates']]
    if geom['type'] == 'MultiPolygon': return list(geom['coordinates'])
    return []

def ring_area_m2(r):
    a = np.asarray(r, float); x = a[:, 0] * KX; y = a[:, 1] * KY
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

def poly_area_m2(p):
    return ring_area_m2(p[0]) - sum(ring_area_m2(h) for h in p[1:])

def centroid(p):
    a = np.asarray(p[0], float); return a[:-1, 0].mean(), a[:-1, 1].mean()

def _in_ring(px, py, r):
    a = np.asarray(r, float); x1, y1 = a[:-1, 0], a[:-1, 1]; x2, y2 = a[1:, 0], a[1:, 1]
    inside = np.zeros(len(px), bool)
    for i in range(len(x1)):
        c = ((y1[i] > py) != (y2[i] > py))
        with np.errstate(divide='ignore', invalid='ignore'):
            xi = (x2[i] - x1[i]) * (py - y1[i]) / (y2[i] - y1[i]) + x1[i]
        inside ^= c & (px < xi)
    return inside

def in_poly(px, py, p):
    """Boolean mask of points inside polygon p (outer ring minus holes), with bbox prefilter."""
    px = np.asarray(px); py = np.asarray(py)
    o = np.asarray(p[0], float)
    m = (px >= o[:, 0].min()) & (px <= o[:, 0].max()) & (py >= o[:, 1].min()) & (py <= o[:, 1].max())
    res = np.zeros(len(px), bool); idx = np.where(m)[0]
    if not len(idx): return res
    q = _in_ring(px[idx], py[idx], p[0])
    for h in p[1:]: q &= ~_in_ring(px[idx], py[idx], h)
    res[idx] = q; return res

def in_geom(px, py, geom):
    m = np.zeros(len(px), bool)
    for p in polys(geom): m |= in_poly(px, py, p)
    return m
