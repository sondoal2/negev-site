"""Night lights over the unrecognized villages only.
Downloads NASA VIIRS City Lights 2012 (GIBS, web-mercator z8 tiles), takes the light (red channel above the navy background),
keeps it only inside ~1 km cells around the unrecognized clusters (cluster_frames c='u'),
and writes a transparent PNG with soft red halos (they glow over a black & white night photo) + its corner coordinates for a MapLibre image source.
  night_villages.py <site_dir> <tile_cache_dir>   ->  data/night_villages.png, data/night_villages.json"""
import sys, os, json, math, urllib.request
from PIL import Image, ImageFilter
site, cache = sys.argv[1], sys.argv[2]; os.makedirs(cache, exist_ok=True)
Z, XS, YS = 8, range(152, 154), range(104, 108)
URL = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_CityLights_2012/default/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg'
big = Image.new('RGB', (256 * len(XS), 256 * len(YS)))
for a, x in enumerate(XS):
    for b, y in enumerate(YS):
        f = os.path.join(cache, f'{Z}_{x}_{y}.jpg')
        if not os.path.exists(f): urllib.request.urlretrieve(URL.format(z=Z, x=x, y=y), f)
        big.paste(Image.open(f).convert('RGB'), (a * 256, b * 256))
n = 2 ** Z
lon = lambda px: (XS[0] + px / 256) / n * 360 - 180
lat = lambda py: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (YS[0] + py / 256) / n))))
# village cells (open = a cluster in the cell or a neighbouring cell)
S, X0, Y0 = 0.012, 33.6, 29.2
fr = json.load(open(os.path.join(site, 'data', 'cluster_frames.geojson'), encoding='utf8'))
cells = set()
for f in fr['features']:
    if f['properties']['c'] != 'u': continue
    r = f['geometry']['coordinates'][0]; cx = sum(p[0] for p in r[:-1]) / (len(r) - 1); cy = sum(p[1] for p in r[:-1]) / (len(r) - 1)
    i, j = int((cx - X0) / S), int((cy - Y0) / S)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1): cells.add((i + di, j + dj))
# VIIRS pixels are ~0.5-0.75 km and city light blooms outward: drop village cells inside a town's glow radius
# (2 km for a town of 2,000, +1.5 km per tenfold population: Be'er Sheva ~5 km, Rahat ~4.4 km), so what remains is the villages' own light
cbs = json.load(open(os.path.join(site, 'data', 'cbs_localities.geojson'), encoding='utf8'))
towns = []
for f in cbs['features']:
    p = f['properties']; c = f['geometry'] and f['geometry']['coordinates']
    if c and p.get('pop') and p['pop'] >= 2000 and p.get('grp') in ('jewish', 'arab', 'bedouin_town', 'mixed') and 29.4 < c[1] < 31.7:
        towns.append((c[0], c[1], 2 + 1.5 * math.log10(p['pop'] / 2000)))
def glow(i, j):
    x, y = X0 + (i + .5) * S, Y0 + (j + .5) * S
    return any(math.hypot((x - a) * 95.0, (y - b) * 111.0) < r for a, b, r in towns)
dropped = {c for c in cells if glow(*c)}; cells -= dropped
print(len(towns), 'towns;', len(dropped), 'cells in town glow dropped;', len(cells), 'left')
K = 4  # upsample, so the cell edges and halos are smooth
W, H = big.size
up = big.resize((W * K, H * K), Image.BICUBIC)
alpha = Image.new('L', up.size, 0); A = alpha.load(); P = up.load()
lit = 0
for py in range(H * K):
    la = lat(py / K)
    for px in range(W * K):
        lo = lon(px / K)
        if (int((lo - X0) / S), int((la - Y0) / S)) not in cells: continue
        rr = P[px, py][0]
        v = int(max(0, rr - 70) * 1.6)  # navy background has red ~12-20; town glow spills ~1 km, so only clear lights pass
        if v: A[px, py] = min(255, v); lit += 1
alpha = alpha.filter(ImageFilter.GaussianBlur(K))
out = Image.new('RGBA', up.size, (255, 96, 52, 0)); out.putalpha(alpha)
out.save(os.path.join(site, 'data', 'night_villages.png'), optimize=True)
coords = [[lon(0), lat(0)], [lon(W), lat(0)], [lon(W), lat(H)], [lon(0), lat(H)]]
json.dump({'coordinates': [[round(a, 6), round(b, 6)] for a, b in coords], 'source': 'NASA VIIRS City Lights 2012 via GIBS, masked to ~1 km cells around the unrecognized villages'},
          open(os.path.join(site, 'data', 'night_villages.json'), 'w'))
print('lit pixels', lit, 'size', out.size, coords)
