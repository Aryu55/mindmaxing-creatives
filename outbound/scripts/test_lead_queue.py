import sqlite3, json, re

conn = sqlite3.connect('/root/outbound/data/mindmaxing_crm.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('''
    SELECT * FROM leads 
    WHERE contact_email IS NOT NULL AND contact_email != ''
    ORDER BY COALESCE(review_freshest_date, review_date, captured_at) DESC
''')
leads = [dict(r) for r in c.fetchall()]

valid_queue = []
for l in leads:
    email = l.get('contact_email', '').strip('.,;:\'"')
    if not email or '@' not in email or email.startswith('u003e') or len(email.split('@')[0]) < 2:
        continue
    prefix = email.split('@')[0].lower()
    if prefix in ['legal', 'privacy', 'abuse', 'dmca', 'press', 'media', 'investor', 'careers', 'jobs', 'compliance', 'sms'] or prefix.endswith('-sms'):
        continue
    tel = {}
    if l.get('reviews_json'):
        try:
            tel = json.loads(l['reviews_json'])
        except Exception:
            pass
    lcp = tel.get('lcp') if isinstance(tel, dict) else None
    if not lcp and l.get('dominant_pattern'):
        m = re.search(r'LCP\s*([\d\.]+\s*s)', l['dominant_pattern'])
        if m:
            lcp = m.group(1)
    
    date_val = l.get('review_freshest_date') or l.get('review_date') or l.get('captured_at') or ''
    valid_queue.append({
        'domain': l['domain'],
        'company': l['company_name'],
        'email': email,
        'source': l['source'],
        'date': str(date_val)[:10],
        'lcp': lcp,
        'pattern': l.get('dominant_pattern')
    })

print(f'Total valid clean leads in CRM: {len(valid_queue)}')
sept_18_20 = [x for x in valid_queue if x['date'] >= '2026-09-18']
print(f'Valid clean leads from Sept 18-20: {len(sept_18_20)}')
sept_15_20 = [x for x in valid_queue if x['date'] >= '2026-09-15']
print(f'Valid clean leads from Sept 15-20: {len(sept_15_20)}')

print('\nTop 30 Freshest Clean Pain Leads:')
for i, x in enumerate(valid_queue[:30], 1):
    print(f"{i}. {x['domain']} ({x['company']}) | {x['email']} | Src: {x['source']} | Date: {x['date']} | Metric: {x['lcp'] or x['pattern']}")
