"""Fetch Israel Police crime files (data.gov.il dataset crime_records_data) for the Southern District and count them
per locality x offense group x year. One row in the source = one crime file (תיק).
  python scripts/crime_fetch.py <out.json>
Writes {year: {yeshuv_code|yeshuv|municipal: {group: n, ...}}} plus the offense-type counts for homicide-related types."""
import sys, json, urllib.request, urllib.parse, collections, time
RES = {2025: 'e311b6a1-be5a-4a82-8298-f3afbee07b6b', 2024: '5fc13c50-b6f3-4712-b831-a75e0f91a17e', 2023: '32aacfc9-3524-4fba-a282-3af052380244'}
FIELDS = 'Year,Quarter,YeshuvKod,Yeshuv,municipalKod,municipalName,PoliceStation,StatisticGroupKod,StatisticGroup,StatisticTypeKod,StatisticType'
out = {}
for year, rid in RES.items():
    agg = collections.Counter(); types = collections.Counter(); offset = 0; total = None
    while True:
        q = urllib.parse.urlencode({'resource_id': rid, 'filters': json.dumps({'PoliceDistrict': 'מחוז דרומי'}, ensure_ascii=False),
                                    'fields': FIELDS, 'limit': 10000, 'offset': offset})
        req = urllib.request.Request('https://data.gov.il/api/3/action/datastore_search?' + q, headers={'User-Agent': 'offmap-atlas/1.0'})
        for attempt in range(4):
            try:
                d = json.load(urllib.request.urlopen(req, timeout=180))['result']; break
            except Exception as e:
                print('retry', year, offset, e); time.sleep(5)
        total = d['total']; recs = d['records']
        for r in recs:
            key = f"{r['YeshuvKod']}|{r['Yeshuv']}|{r['municipalName'] or ''}|{r['PoliceStation']}"
            agg[(key, r['StatisticGroup'])] += 1
            types[(r['StatisticGroup'], r['StatisticType'])] += 1
        offset += len(recs)
        print(year, offset, '/', total, flush=True)
        if not recs or offset >= total: break
    by = collections.defaultdict(dict)
    for (k, g), n in agg.items(): by[k][g] = n
    out[year] = {'total_files': total, 'by_locality': by, 'types': {f'{g}|{t}': n for (g, t), n in types.items()}}
json.dump(out, open(sys.argv[1], 'w', encoding='utf8'), ensure_ascii=False)
print('done')
