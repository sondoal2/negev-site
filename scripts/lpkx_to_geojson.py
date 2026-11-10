import arcpy, json, os, sys
base, outdir = sys.argv[1], sys.argv[2]
arcpy.env.overwriteOutput = True
wgs = arcpy.SpatialReference(4326)
for name in ['Jewish_Industrial', 'Arab_Industrial', 'arab_negev_7']:
    lyr = json.load(open(os.path.join(base, name, 'p30', name + '.lyrx'), encoding='utf-8'))
    ld = [d for d in lyr['layerDefinitions'] if d.get('type') == 'CIMFeatureLayer'][0]
    ft = ld['featureTable']; ds = ft['dataConnection']['dataset']; dq = ft.get('definitionExpression', '')
    gdb = os.path.join(base, name, 'commondata', 'cityscience.gdb')
    fc = os.path.join(gdb, ds)
    d = arcpy.Describe(fc)
    print('==', name, '| fc:', ds, '| geom:', d.shapeType, '| sr:', d.spatialReference.name, '| query:', dq or '-')
    fields = [f.name for f in arcpy.ListFields(fc) if f.type not in ('Geometry', 'OID', 'Blob', 'Raster') and f.name.lower() not in ('shape_length', 'shape_area')]
    print('   fields:', fields)
    tmp = arcpy.management.MakeFeatureLayer(fc, name + '_lyr', dq or None)
    print('   count:', arcpy.management.GetCount(tmp)[0])
    proj = os.path.join('memory', name + '_wgs')
    arcpy.management.Project(tmp, proj, wgs)
    feats = []
    with arcpy.da.SearchCursor(proj, ['SHAPE@'] + fields) as cur:
        for row in cur:
            g = row[0]
            if g is None: continue
            gj = json.loads(g.generalize(0.00003).JSON if d.shapeType == 'Polygon' else g.JSON)
            if 'rings' in gj: geom = {'type': 'MultiPolygon', 'coordinates': [[ [[round(x, 5), round(y, 5)] for x, y, *_ in r] ] for r in gj['rings']]}
            elif 'paths' in gj: geom = {'type': 'MultiLineString', 'coordinates': [[[round(x, 5), round(y, 5)] for x, y, *_ in p] for p in gj['paths']]}
            elif 'x' in gj: geom = {'type': 'Point', 'coordinates': [round(gj['x'], 5), round(gj['y'], 5)]}
            else: continue
            props = {}
            for k, v in zip(fields, row[1:]):
                if v is None or v == '': continue
                props[k] = v if isinstance(v, (int, float, str)) else str(v)
            feats.append({'type': 'Feature', 'geometry': geom, 'properties': props})
    if feats: print('   sample props:', json.dumps(feats[0]['properties'])[:600])
    out = os.path.join(outdir, name.lower() + '.geojson')
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('   ->', out, round(os.path.getsize(out) / 1024), 'KB')
