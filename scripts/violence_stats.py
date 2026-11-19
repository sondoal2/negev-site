"""Chapter 06: lethal-violence and bodily-harm files per resident, Israel Police open data (data.gov.il, crime_records_data).
Compares the 7 Bedouin towns with the 11 Jewish towns used elsewhere in the atlas (populations: CBS Local Authorities 2023, as in bagrut.json).
A file (תיק) is opened when an offense is reported or found by the police: these are files, not victims and not convictions.
  python scripts/violence_stats.py <site_dir> <crime_south.json from crime_fetch.py> <crime_lethal.json from crime_lethal_fetch.py>"""
import sys, os, json, collections
site, south_p, lethal_p = sys.argv[1:4]
S = json.load(open(south_p, encoding='utf8')); LR = json.load(open(lethal_p, encoding='utf8'))
B = json.load(open(os.path.join(site, 'data', 'bagrut.json'), encoding='utf8'))['rows']
TOWNS = {r['he']: r for r in B if r['grp'] in ('arab', 'jewish') and r.get('pop')}
norm = lambda s: (s or '').strip().replace('-', ' ').replace('"', '').replace("''", '')
BY = {norm(he): he for he in TOWNS}
BY[norm('כסיפה')] = 'כסייפה'   # police spelling vs CBS spelling
LETHAL = {'רצח', 'נסיון לרצח', 'הריגה'}
BEDOUIN_STATIONS = {'תחנת העיירות רותם', 'תחנת ערוער רותם', 'תחנת שגב שלום רותם', 'תחנת רהט נגב'}
YEARS = ['2023', '2024', '2025']

lethal = collections.Counter(); lethal_y = collections.defaultdict(collections.Counter); noloc_bedouin = 0; bed_station_total = 0
for r in LR:
    if r['StatisticType'] not in LETHAL: continue
    he = BY.get(norm(r['Yeshuv']))
    if he: lethal[he] += 1; lethal_y[str(r['Year'])][he] += 1
    if r['PoliceStation'] in BEDOUIN_STATIONS:
        bed_station_total += 1
        if not he: noloc_bedouin += 1
body = collections.Counter()
for y in YEARS:
    for key, g in S[y]['by_locality'].items():
        he = BY.get(norm(key.split('|')[1]))
        if he: body[he] += g.get('עבירות נגד גוף', 0)

rows = []
for he, t in TOWNS.items():
    rows.append({'he': he, 'ar': t['ar'], 'en': t['en'], 'grp': t['grp'], 'pop': t['pop'], 'lethal_3y': lethal[he],
                 'lethal_per10k_yr': round(lethal[he] / t['pop'] * 1e4 / 3, 2), 'body_per1k_yr': round(body[he] / t['pop'] * 1e3 / 3, 1),
                 'lethal_by_year': {y: lethal_y[y][he] for y in YEARS}})
def grp(g):
    R = [r for r in rows if r['grp'] == g]; pop = sum(r['pop'] for r in R); L = sum(r['lethal_3y'] for r in R); Bd = sum(body[r['he']] for r in R)
    return {'towns': len(R), 'pop': pop, 'lethal_3y': L, 'lethal_per10k_yr': round(L / pop * 1e4 / 3, 2), 'body_per1k_yr': round(Bd / pop * 1e3 / 3, 1)}
A, J = grp('arab'), grp('jewish')
out = {'source': 'Israel Police open crime data, data.gov.il dataset crime_records_data, files 2023-2025 (resources e311b6a1, 5fc13c50, 32aacfc9)',
       'population': 'CBS Local Authorities 2023 (as in bagrut.json)', 'years': YEARS,
       'lethal_types': sorted(LETHAL), 'note': 'files, not victims; a file is opened per reported or detected offense',
       'arab_towns': A, 'jewish_towns': J, 'ratio_lethal': round(A['lethal_per10k_yr'] / J['lethal_per10k_yr'], 1),
       'ratio_body': round(A['body_per1k_yr'] / J['body_per1k_yr'], 1),
       'bedouin_stations_lethal': bed_station_total, 'bedouin_stations_lethal_no_locality': noloc_bedouin,
       'rows': sorted(rows, key=lambda r: -r['lethal_per10k_yr'])}
json.dump(out, open(os.path.join(site, 'data', 'violence.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print({k: v for k, v in out.items() if k not in ('rows',)})
for r in out['rows']: print(r['he'], r['grp'], r['pop'], r['lethal_3y'], r['lethal_per10k_yr'], r['body_per1k_yr'])
