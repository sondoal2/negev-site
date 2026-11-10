"""Official socio-economic profile for the 18 comparison towns:
CBS population 2024 + SES cluster 2019 (data.gov.il) + MoI audited municipal finance 2024 (own revenue, business arnona, grants, spend per resident)."""
import json, sys, os, urllib.parse, subprocess
raw, data = sys.argv[1], sys.argv[2]
FIN = '6e153ddd-d4d4-4450-a78c-20f594a7986a'
ist = json.load(open(os.path.join(data, 'industry_stats.json'), encoding='utf-8'))
cbs = {f['properties']['he']: f['properties'] for f in json.load(open(os.path.join(data, 'cbs_localities.geojson'), encoding='utf-8'))['features']}
MOI = {'שגב שלום':['שגב שלום','שגב-שלום'],'ערערה בנגב':['ערערה בנגב','ערערה-בנגב','ערערה נגב'],'כסייפה':['כסייפה','כסיפה'],'לקיה':['לקיה','לקייה'],'תל שבע':['תל שבע','תל-שבע'],'מצפה רמון':['מצפה רמון','מצפה-רמון'],'באר שבע':['באר שבע','באר-שבע']}
ALIAS = {'כסייפה':'כסיפה','לקיה':'לקיה','שגב שלום': 'שגב-שלום', 'ערערה בנגב': 'ערערה-בנגב', 'מצפה רמון': 'מצפה רמון', 'תל שבע': 'תל שבע'}
ses = json.load(open(os.path.join(raw, 'ds_7c860e04-9f8d-41c2-9f24-6249958d2081.json'), encoding='utf-8'))['result']['records']
ses_by = {int(r['LOCALITY SYMBOL']): r['ESHKOL 2019'] for r in ses if r.get('LOCALITY SYMBOL')}
CODES = {4951: 'pop_moi', 2988: 'own_rev', 2989: 'own_share', 3013: 'total_rev', 3008: 'grants', 4135: 'arnona_res', 4143: 'arnona_other', 3073: 'spend_pc'}
out = []
for r in ist['rows']:
    he = r['he']; c = cbs.get(he) or cbs.get(ALIAS.get(he, he))
    if not c: print('no CBS match', r['en']); continue
    code = c['code']
    recs = []
    for nm in MOI.get(he, [he]):
        f = json.dumps({'שם_רשות': nm}, ensure_ascii=False)
        url = f'https://data.gov.il/api/3/action/datastore_search?resource_id={FIN}&limit=32000&filters=' + urllib.parse.quote(f)
        tmp = os.path.join(raw, f'fin_{code}_{len(recs)}.json')
        subprocess.run(['curl', '-s', '-A', 'Mozilla/5.0', '-o', tmp, url])
        recs = json.load(open(tmp, encoding='utf-8'))['result']['records']
        if recs: break
    vals = {}
    if recs:
        k = list(recs[0].keys()); kc, kv = k[11], k[12]
        for x in recs:
            try: cc = int(float(x[kc]))
            except Exception: continue
            if cc in CODES and CODES[cc] not in vals:
                try: vals[CODES[cc]] = float(x[kv])
                except Exception: pass
    pop = c.get('pop') or vals.get('pop_moi')
    row = {'key': r['key'], 'grp': r['grp'], 'he': he, 'ar': r['ar'], 'en': r['en'], 'cbs_code': code, 'pop_cbs_2024': c.get('pop'),
           **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in vals.items()}}
    if vals.get('own_rev') and pop: row['own_rev_pc'] = round(vals['own_rev'] * 1000 / pop)        # ₪ per resident (report is in k₪)
    if vals.get('arnona_other') and pop: row['biz_arnona_pc'] = round(vals['arnona_other'] * 1000 / pop)
    if vals.get('arnona_res') and vals.get('arnona_other'): row['biz_share'] = round(vals['arnona_other'] / (vals['arnona_res'] + vals['arnona_other']), 3)
    out.append(row)
    print(f"{r['en']:14} {r['grp']:6} pop={pop} own_pc={row.get('own_rev_pc')} biz_pc={row.get('biz_arnona_pc')} own%={vals.get('own_share')} spend_pc={vals.get('spend_pc')}")
json.dump({'source': 'CBS localities 2024 (population) · Ministry of Interior audited financial reports 2024 (data.gov.il, k₪)',
           'rows': out}, open(os.path.join(data, 'town_profile.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
