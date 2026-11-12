"""Cluster frames (padded bounding boxes) + compact red-house points for the web atlas; also adds Cluster_Frames to the GDB."""
import arcpy, json, os, sys
gdb, data = sys.argv[1], sys.argv[2]
arcpy.env.workspace = gdb; arcpy.env.overwriteOutput = True
wgs = arcpy.SpatialReference(4326); PAD = 30  # metres around each cluster
frames = []
arcpy.management.CreateFeatureclass(gdb, 'Cluster_Frames', 'POLYGON', spatial_reference=arcpy.SpatialReference(2039))
for f, t in (('name_ar', 'TEXT'), ('name_en', 'TEXT'), ('buildings', 'LONG'), ('area_dunam', 'DOUBLE')): arcpy.management.AddField('Cluster_Frames', f, t)
with arcpy.da.SearchCursor('Unrecognized_Villages_Envelopes', ['SHAPE@', 'name_ar', 'name_en', 'buildings', 'area_dunam']) as sc, \
     arcpy.da.InsertCursor('Cluster_Frames', ['SHAPE@', 'name_ar', 'name_en', 'buildings', 'area_dunam']) as ic:
    for shp, ar, en, n, a in sc:
        e = shp.extent
        box = arcpy.Polygon(arcpy.Array([arcpy.Point(e.XMin - PAD, e.YMin - PAD), arcpy.Point(e.XMax + PAD, e.YMin - PAD),
                                         arcpy.Point(e.XMax + PAD, e.YMax + PAD), arcpy.Point(e.XMin - PAD, e.YMax + PAD)]), shp.spatialReference)
        ic.insertRow([box, ar, en, n, a])
        bw = box.projectAs(wgs).extent
        frames.append({'type': 'Feature', 'geometry': {'type': 'Polygon', 'coordinates': [[[round(bw.XMin, 5), round(bw.YMin, 5)], [round(bw.XMax, 5), round(bw.YMin, 5)],
                       [round(bw.XMax, 5), round(bw.YMax, 5)], [round(bw.XMin, 5), round(bw.YMax, 5)], [round(bw.XMin, 5), round(bw.YMin, 5)]]]},
                       'properties': {'ar': ar, 'en': en, 'n': n, 'du': round(a)}})
json.dump({'type': 'FeatureCollection', 'features': frames}, open(os.path.join(data, 'cluster_frames.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
pts = []
with arcpy.da.SearchCursor('Offmap_Buildings', ['SHAPE@'], spatial_reference=wgs) as sc:
    for (shp,) in sc:
        c = shp.centroid; pts.append([round(c.X, 5), round(c.Y, 5), int(round(shp.getArea('PLANAR', 'SQUAREMETERS')))])
json.dump(pts, open(os.path.join(data, 'offmap_houses.json'), 'w'), separators=(',', ':'))
print('frames', len(frames), 'houses', len(pts), [round(os.path.getsize(os.path.join(data, f)) / 1024) for f in ('cluster_frames.geojson', 'offmap_houses.json')], 'KB')
