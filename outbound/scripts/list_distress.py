import sqlite3
import json

conn = sqlite3.connect('/root/outbound/data/mindmaxing_crm.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('''
    SELECT * FROM leads 
    WHERE source != 'meta_pagespeed'
      AND contact_email IS NOT NULL AND contact_email != ''
      AND domain NOT LIKE '%.in' AND contact_email NOT LIKE '%.in'
    ORDER BY COALESCE(review_freshest_date, review_date, captured_at) DESC
''')
leads = [dict(r) for r in c.fetchall()]

valid_leads = []
for l in leads:
    email = l.get("contact_email", "").strip(".,;:'\"")
    if not email or "@" not in email or email.startswith("u003e") or len(email.split("@")[0]) < 2:
        continue
    prefix = email.split("@")[0].lower()
    if prefix in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"] or prefix.endswith("-sms"):
        continue
    valid_leads.append(l)

print(f"Total non-pagespeed valid leads: {len(valid_leads)}")
sources = {}
for l in valid_leads:
    s = l.get('source')
    sources[s] = sources.get(s, 0) + 1
print(f"By source: {sources}")

print("\n--- TOP 35 FRESHEST FOUNDER / CUSTOMER PAIN LEADS ---")
for i, l in enumerate(valid_leads[:35], 1):
    date = l.get('review_freshest_date') or l.get('review_date') or l.get('captured_at') or ''
    trigger = l.get('pain_trigger') or l.get('dominant_pattern')
    snip = (l.get('review_snippet') or l.get('post_title') or '')[:75].replace('\n', ' ')
    print(f"{i}. {l['domain']} ({l['company_name']}) | {l['contact_email']} | Src: {l['source']} | Date: {str(date)[:10]} | Trig: {trigger}")
    print(f"   Context: {snip}")
