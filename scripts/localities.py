import pandas as pd, json, sys, arcpy
df = pd.read_excel(sys.argv[1]); c=list(df.columns)
NAME,CODE,DIST,NAFA,REL,POP,YR,FORM,XY,EN = c[0],c[1],c[4],c[6],c[11],c[12],c[17],c[18],c[20],c[25]
itm=arcpy.SpatialReference(2039); wgs=arcpy.SpatialReference(4326)
feats=[]; stats={}
for _,r in df.iterrows():
    f=r[FORM]
    if pd.isna(f) or f>=500 or pd.isna(r[XY]): continue
    s=str(int(r[XY])).zfill(10); h=len(s)//2; x,y=int(s[:h]),int(s[h:])
    if x<1000000 and h==5: x*=10; y*=10
    p=arcpy.PointGeometry(arcpy.Point(x,y),itm).projectAs(wgs).firstPoint
    rel=r[REL]; negev = str(r[NAFA]).strip()=='באר שבע'
    if f==460: grp='tribe'
    elif rel==1: grp='jewish'
    elif rel==4: grp='mixed'
    elif negev and rel==2: grp='bedouin_town'
    else: grp='arab'
    yv=pd.to_numeric(r[YR],errors='coerce'); year=None if pd.isna(yv) else int(yv)
    old = (str(r[YR]).strip()=='ותיק') or (year is None and grp in ('arab','mixed'))
    pop=pd.to_numeric(r[POP],errors='coerce')
    feats.append({'type':'Feature','geometry':{'type':'Point','coordinates':[round(p.X,5),round(p.Y,5)]},
      'properties':{'he':str(r[NAME]).strip(),'en':str(r[EN]).strip(),'code':int(r[CODE]),'grp':grp,'year':year,'old':old,'form':int(f),'pop':None if pd.isna(pop) else int(pop),'negev':negev}})
    k=(grp, 'pre48' if (old or (year and year<1948)) else ('unknown' if year is None else 'post48')); stats[k]=stats.get(k,0)+1
json.dump({'type':'FeatureCollection','features':feats},open(sys.argv[2],'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(len(feats)); [print(k,v) for k,v in sorted(stats.items())]
neg=[f['properties'] for f in feats if f['properties']['negev']]
print('negev total',len(neg),{g:sum(1 for p in neg if p['grp']==g) for g in ('jewish','bedouin_town','tribe','arab')})
print('negev jewish post48', sum(1 for p in neg if p['grp']=='jewish' and p['year'] and p['year']>=1948))
print('bedouin towns', [(p['en'],p['year'],p['form']) for p in neg if p['grp']=='bedouin_town'])
