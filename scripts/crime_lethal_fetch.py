"""Southern District files in the group 'עבירות נגד אדם' (murder, attempted murder, manslaughter...) with locality and type.
  python scripts/crime_lethal_fetch.py <out.json>"""
import sys, json, urllib.request, urllib.parse
RES = {2025: 'e311b6a1-be5a-4a82-8298-f3afbee07b6b', 2024: '5fc13c50-b6f3-4712-b831-a75e0f91a17e', 2023: '32aacfc9-3524-4fba-a282-3af052380244'}
rows = []
for year, rid in RES.items():
    q = urllib.parse.urlencode({'resource_id': rid, 'filters': json.dumps({'PoliceDistrict': 'מחוז דרומי', 'StatisticGroup': 'עבירות נגד אדם'}, ensure_ascii=False),
                                'fields': 'Year,Quarter,YeshuvKod,Yeshuv,municipalName,PoliceStation,StatisticType', 'limit': 5000})
    req = urllib.request.Request('https://data.gov.il/api/3/action/datastore_search?' + q, headers={'User-Agent': 'offmap-atlas/1.0'})
    d = json.load(urllib.request.urlopen(req, timeout=180))['result']
    rows += d['records']; print(year, len(d['records']), 'of', d['total'])
json.dump(rows, open(sys.argv[1], 'w', encoding='utf8'), ensure_ascii=False)
