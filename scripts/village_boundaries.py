"""Step 2 (arcpy): derive built-up envelopes of unrecognized villages from building footprints,
and package them with official recognized-locality limits into a File Geodatabase.
Method: buffer every footprint 40 m and dissolve -> shrink 20 m (morphological closing) -> explode -> keep blobs with >= 10 buildings
-> name by nearest candidate village point (OSM) within 2.5 km."""
import arcpy, json, os, sys
foot, data, gdb_dir, gdb_name = sys.argv[1:5]
arcpy.env.overwriteOutput = True
itm = arcpy.SpatialReference(2039)
gdb = os.path.join(gdb_dir, gdb_name)
if not arcpy.Exists(gdb): arcpy.management.CreateFileGDB(gdb_dir, gdb_name)
arcpy.env.workspace = gdb
print('license', arcpy.ProductInfo())

# --- building footprints -> ITM
arcpy.conversion.JSONToFeatures(foot, 'tmp_foot_wgs', 'POLYGON')
arcpy.management.Project('tmp_foot_wgs', 'Offmap_Buildings', itm)
arcpy.management.RepairGeometry('Offmap_Buildings', 'DELETE_NULL')
print('buildings', arcpy.management.GetCount('Offmap_Buildings')[0])

# --- envelopes: closing = buffer +40 dissolve, then -20
arcpy.analysis.PairwiseBuffer('Offmap_Buildings', 'memory/b40', '40 Meters', 'ALL')
arcpy.analysis.PairwiseBuffer('memory/b40', 'memory/b20', '-20 Meters', 'NONE')
arcpy.management.MultipartToSinglepart('memory/b20', 'memory/blobs')
arcpy.analysis.SpatialJoin('memory/blobs', 'Offmap_Buildings', 'memory/blobs_n', 'JOIN_ONE_TO_ONE', 'KEEP_ALL', match_option='INTERSECT')
arcpy.management.MakeFeatureLayer('memory/blobs_n', 'blobs_lyr', 'Join_Count >= 10')
arcpy.management.CopyFeatures('blobs_lyr', 'memory/vill')

# --- candidate village points (OSM, Arabic names outside every recognized limit) -> name the envelopes
places = json.load(open(os.path.join(data, 'buildings_summary.json'), encoding='utf-8'))['villages']
arcpy.management.CreateFeatureclass(gdb, 'tmp_pts_wgs', 'POINT', spatial_reference=arcpy.SpatialReference(4326))
for fld, ln in (('name_ar', 120), ('name_en', 120)): arcpy.management.AddField('tmp_pts_wgs', fld, 'TEXT', field_length=ln)
with arcpy.da.InsertCursor('tmp_pts_wgs', ['SHAPE@XY', 'name_ar', 'name_en']) as cur:
    for v in places: cur.insertRow([(v['lon'], v['lat']), v['ar'], v['en']])
arcpy.management.Project('tmp_pts_wgs', 'Candidate_Village_Points', itm)
arcpy.analysis.SpatialJoin('memory/vill', 'Candidate_Village_Points', 'memory/vill_named', 'JOIN_ONE_TO_ONE', 'KEEP_ALL',
                           match_option='CLOSEST', search_radius='2500 Meters', distance_field_name='dist_to_point_m')
# clean output schema
out = 'Unrecognized_Villages_Envelopes'
arcpy.management.CreateFeatureclass(gdb, out, 'POLYGON', spatial_reference=itm)
for fld, typ in (('name_ar', 'TEXT'), ('name_en', 'TEXT'), ('buildings', 'LONG'), ('area_dunam', 'DOUBLE'), ('dist_to_point_m', 'DOUBLE'), ('status', 'TEXT'), ('method', 'TEXT')):
    arcpy.management.AddField(out, fld, typ, field_length=200 if typ == 'TEXT' else None)
n = 0
with arcpy.da.SearchCursor('memory/vill_named', ['SHAPE@', 'name_ar', 'name_en', 'Join_Count', 'dist_to_point_m']) as sc, \
     arcpy.da.InsertCursor(out, ['SHAPE@', 'name_ar', 'name_en', 'buildings', 'area_dunam', 'dist_to_point_m', 'status', 'method']) as ic:
    for shp, ar, en, cnt, d in sc:
        ic.insertRow([shp, ar or 'غير مسمّى', en or 'unnamed', cnt, round(shp.area / 1000, 1), d if d is not None and d >= 0 else None,
                      'candidate unrecognized (to verify against RCUV list)',
                      'Built-up envelope: MS ML footprints 2026, buffer 40m dissolve, -20m, >=10 buildings; outside every recognized iplan limit'])
        n += 1
print('envelopes', n)

# --- official limits (Planning Administration): recognized Arab localities + Jewish localities for comparison
REGIONAL = {'Neve Midbar','al Kasum','Merhavim','Sdot Negev','Ramat Negev','Hevel Eielot',"Ha'arava Hatihona","Bnei Shim'on",'Eshkol','Tamar'}
ARAB = {'Tel Sheva','Segev Shalom',"Ar'ara Banegev",'Lakiye','Kseyfe','Hura','Rahat','Neve Midbar','al Kasum'}
feats = []
for f in json.load(open(os.path.join(data, 'muni.geojson'), encoding='utf-8'))['features'] + json.load(open(os.path.join(data, 'rahat.geojson'), encoding='utf-8'))['features']:
    p = f['properties']; en = (p.get('Muni_Eng') or '').strip()
    if en in REGIONAL or en == 'Neot Hovav': continue
    feats.append((f['geometry'], p.get('Muni_Heb'), en, 'arab' if en in ARAB else 'jewish', 'municipal limit (town / local council)'))
for f in json.load(open(os.path.join(data, 'vaadim.geojson'), encoding='utf-8'))['features']:
    p = f['properties']; v = (p.get('Vaad_Eng') or '').strip(); m = (p.get('Muni_Eng') or '').strip()
    if not v or v.upper().startswith('GENERAL'): continue
    feats.append((f['geometry'], p.get('Vaad_Heb'), v.title(), 'arab' if m in ARAB else 'jewish', f'village committee in {m} regional council'))
for name, grp in (('Recognized_Arab_Localities', 'arab'), ('Jewish_Localities', 'jewish')):
    arcpy.management.CreateFeatureclass(gdb, 'tmp_' + grp, 'POLYGON', spatial_reference=arcpy.SpatialReference(4326))
    for fld in ('name_he', 'name_en', 'kind'): arcpy.management.AddField('tmp_' + grp, fld, 'TEXT', field_length=150)
    with arcpy.da.InsertCursor('tmp_' + grp, ['SHAPE@', 'name_he', 'name_en', 'kind']) as ic:
        for g, he, en, gg, kind in feats:
            if gg == grp: ic.insertRow([arcpy.AsShape(g), he, en, kind])
    arcpy.management.Project('tmp_' + grp, name, itm)
    arcpy.management.AddField(name, 'area_dunam', 'DOUBLE')
    arcpy.management.CalculateField(name, 'area_dunam', 'round(!shape.area! / 1000, 1)', 'PYTHON3')
    print(name, arcpy.management.GetCount(name)[0])

# GeoJSON copies for the web atlas
for fc, fn in (('Unrecognized_Villages_Envelopes', 'unrecognized_envelopes.geojson'),):
    arcpy.conversion.FeaturesToJSON(fc, os.path.join(sys.argv[5], fn), geoJSON='GEOJSON', outputToWGS84='WGS84')
print('done', gdb)
for t in ('tmp_foot_wgs', 'tmp_pts_wgs', 'tmp_arab', 'tmp_jewish'):
    if arcpy.Exists(t): arcpy.management.Delete(t)
print('cleaned temp')
