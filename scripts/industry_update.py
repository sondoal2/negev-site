"""Update data/industry_stats.json from the team member's final table (Negev_Arab_Jewish_Comparison.xlsx):
   industrial dunams after removing duplicate polygons and splitting Idan HaNegev 44/56 (the partners' 877.74 dunams lie outside the 18 towns),
   plus the share of workers who work outside their own town (CBS census 2022, layer Negev_18_OutCommuting_2022).
   industry_update.py <xlsx> <site data dir>"""
import sys, os, json, openpyxl
xlsx, out = sys.argv[1], sys.argv[2]
ws = openpyxl.load_workbook(xlsx, data_only=True).worksheets[0]
rows = [r for r in ws.iter_rows(values_only=True)]
ind, outc = {}, {}
sec = 0
for r in rows:
    if r[0] and str(r[0]).startswith('1.'): sec = 1
    elif r[0] and str(r[0]).startswith('2.'): sec = 2
    elif r[0] and str(r[0]).startswith('3.'): sec = 3
    for he, a, b in ((r[1], r[2], r[3]), (r[7] if len(r) > 7 else None, r[8] if len(r) > 8 else None, r[9] if len(r) > 9 else None)):
        if not he or not isinstance(b, (int, float)): continue
        if sec == 1: ind[he] = b
        if sec == 3: outc[he] = b
p = os.path.join(out, 'industry_stats.json'); d = json.load(open(p, encoding='utf8'))
for r in d['rows']:
    he = r['he']
    if he in ind:
        r['ind_dunam'] = round(ind[he], 2); r['ind_pct'] = round(ind[he] / r['total_dunam'] * 100, 2); r['ind_per1000'] = round(ind[he] * 1000 / r['pop'], 2)
    if he in outc: r['out_pct'] = round(outc[he] * 100, 1)
    else: print('no out-commuting for', he)
d['source'] = ("Team ArcGIS analysis (industrial zones ∩ municipal limits; duplicate polygons removed; Idan HaNegev split 44/56, partners' share outside the 18 towns not counted), "
               "population as in the team table; out-commuting: CBS census 2022 (team layer Negev_18_OutCommuting_2022)")
json.dump(d, open(p, 'w', encoding='utf8'), ensure_ascii=False, indent=1)
A = [r for r in d['rows'] if r['grp'] == 'arab']; J = [r for r in d['rows'] if r['grp'] == 'jewish']
w = lambda X, k: sum(r[k] * r['pop'] for r in X) / sum(r['pop'] for r in X)
print('ind per 1000:', round(sum(r['ind_dunam'] for r in A) * 1000 / sum(r['pop'] for r in A), 1), round(sum(r['ind_dunam'] for r in J) * 1000 / sum(r['pop'] for r in J), 1))
print('out %:', round(w(A, 'out_pct'), 1), round(w(J, 'out_pct'), 1))
