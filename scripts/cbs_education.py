"""Bagrut (matriculation) and related education indicators for the 18 comparison towns + the two Bedouin regional councils,
read from the CBS publication 1987 "Local Authorities in Israel 2023" (הרשויות המקומיות בישראל 2023), one profile PDF per
authority: https://www.cbs.gov.il/he/publications/DocLib/2026/local_authorities23/<name>.pdf
The education block of the profile is for the school year 2022/23 (תשפ"ג); its source is the Ministry of Education.

Read from page 3 (layout text, Hebrew comes out reversed):
  bagrut      eligible for a bagrut certificate, % of 12th-grade pupils           (זכאים לתעודת בגרות מבין תלמידי כיתות יב)
  bagrut_univ eligible AND meeting university entrance thresholds, % of 12th graders (... שעמדו בדרישות הסף של האוניברסיטאות)
  dropout     pupils who dropped out, grades 7-12, %                               (תלמידים נושרים, סך הכל)
  students_20_25  university/college students among residents aged 20-25, %
The two bagrut values are the two bars of a small chart; the larger is always the general eligibility.
Run: python cbs_education.py <dir with the PDFs> <data_dir>
"""
import pypdf, re, glob, json, os, sys, logging
logging.getLogger('pypdf').setLevel(logging.ERROR)
pdf_dir, data_dir = sys.argv[1:3]
KEY = {'ערד': 'arad', 'באר_שבע': 'beer sheva', 'דימונה': 'dimona', 'אילת': 'eilat', 'להבים': 'lehavim', 'מיתר': 'meytar', 'מצפה_רמון': 'mizpe ramon',
       'נתיבות': 'netivot', 'אופקים': 'ofakim', 'עומר': 'omer', 'ירוחם': 'yeruham', 'ערערה_בנגב': 'arara negev', 'חורה': 'hura', 'כסיפה': 'kseifa',
       'לקיה': 'lakia', 'רהט': 'rahat', 'שגב_שלום': 'shegev shalom', 'תל_שבע': 'tel sheva', 'נווה_מדבר': 'neve midbar', 'אל_קסום': 'al kasum'}
COUNCIL = {'neve midbar': {'ar': 'نفيه مدبار (مجلس إقليمي بدوي)', 'he': 'נווה מדבר (מ"א)', 'en': 'Neve Midbar (Bedouin regional council)'},
           'al kasum': {'ar': 'القسوم (مجلس إقليمي بدوي)', 'he': 'אל-קסום (מ"א)', 'en': 'al-Kasum (Bedouin regional council)'}}
rev = lambda t: t[::-1]
ist = {r['key']: r for r in json.load(open(os.path.join(data_dir, 'industry_stats.json'), encoding='utf-8'))['rows']}
out = []
for f in sorted(glob.glob(os.path.join(pdf_dir, '*.pdf'))):
    nm = os.path.basename(f)[:-4]; k = KEY.get(nm)
    if not k or open(f, 'rb').read(4) != b'%PDF': continue
    row = {'key': k}
    if k in ist: row.update({'grp': ist[k]['grp'], 'ar': ist[k]['ar'], 'he': ist[k]['he'], 'en': ist[k]['en'], 'pop': ist[k]['pop']})
    else: row.update({'grp': 'arab_council', **COUNCIL[k]})
    for p in pypdf.PdfReader(f).pages:
        t = p.extract_text(extraction_mode='layout') or ''
        if rev('זכאים לתעודת בגרות מבין תלמידי כיתות יב') not in t: continue
        L = t.split('\n'); i = next(j for j, l in enumerate(L) if rev('זכאים לתעודת בגרות מבין') in l)
        # decimals below the chart title; the right-hand table (education attainment) sits in the right-most column,
        # the two chart bars sit clearly left of it
        cv = [(m.start(), float(m.group())) for l in L[i + 1:i + 9] for m in re.finditer(r'\d+\.\d', l)]
        maxc = max(c for c, _ in cv)
        vals = [v for c, v in cv if c < maxc - 15]
        if len(vals) == 2: row['bagrut'], row['bagrut_univ'] = max(vals), min(vals)
        else: row['parse_warning'] = f'chart values {vals}'
        j = next((j for j, l in enumerate(L) if rev('תלמידים נושרים') in l), None)
        if j is not None:
            for l in L[j:j + 4]:
                m = re.search(r'(\d+\.\d+)\s*' + rev('סך הכל'), l)
                if m: row['dropout'] = float(m.group(1)); break
        for l in L:
            if rev('סטודנטים מתוך אוכלוסיית בני') in l:
                m = re.findall(r'\d+\.\d', l)
                if m: row['students_20_25'] = float(m[0]); break
        break
    out.append(row); print(row)
json.dump({'source': 'CBS, Local Authorities in Israel 2023 (publication 1987), authority profiles; education data 2022/23 from the Ministry of Education',
           'url': 'https://www.cbs.gov.il/he/publications/DocLib/2026/local_authorities23/', 'year': '2022/23', 'rows': out},
          open(os.path.join(data_dir, 'bagrut.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
