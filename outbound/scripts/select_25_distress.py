import sqlite3
import json

conn = sqlite3.connect('/root/outbound/data/mindmaxing_crm.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Reddit founder distress leads
c.execute('''
    SELECT * FROM leads 
    WHERE source = 'reddit'
      AND contact_email IS NOT NULL AND contact_email != ''
      AND domain NOT LIKE '%.in' AND contact_email NOT LIKE '%.in'
    ORDER BY captured_at DESC
''')
reddit_leads = [dict(r) for r in c.fetchall()]

# 2. Trustpilot leads (Sept 18-20, technical friction)
c.execute('''
    SELECT * FROM leads 
    WHERE source = 'trustpilot'
      AND contact_email IS NOT NULL AND contact_email != ''
      AND domain NOT LIKE '%.in' AND contact_email NOT LIKE '%.in'
      AND pain_trigger IN ('cart', 'checkout', 'payment', 'cancel', 'order', 'discount', 'slow')
    ORDER BY COALESCE(review_freshest_date, review_date, captured_at) DESC
''')
tp_leads = [dict(r) for r in c.fetchall()]

selected = []
seen_domains = set()

for l in reddit_leads:
    email = l.get("contact_email", "").strip(".,;:'\"")
    if not email or "@" not in email:
        continue
    prefix = email.split("@")[0].lower()
    if prefix in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"] or prefix.endswith("-sms"):
        continue
    d = l.get("domain")
    if d not in seen_domains:
        seen_domains.add(d)
        selected.append(l)

for l in tp_leads:
    if len(selected) >= 25:
        break
    email = l.get("contact_email", "").strip(".,;:'\"")
    if not email or "@" not in email or email.startswith("u003e") or len(email.split("@")[0]) < 2:
        continue
    prefix = email.split("@")[0].lower()
    if prefix in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"] or prefix.endswith("-sms"):
        continue
    d = l.get("domain")
    if d not in seen_domains:
        seen_domains.add(d)
        selected.append(l)

print("Selected exactly", len(selected), "leads:")
for i, l in enumerate(selected, 1):
    date = l.get('review_freshest_date') or l.get('review_date') or l.get('captured_at') or ''
    trig = l.get('pain_trigger') or l.get('dominant_pattern')
    print(f"{i}. [{l.get('source').upper()}] {l['domain']} ({l['company_name']}) -> {l['contact_email']} | Trig: {trig} | Date: {str(date)[:10]}")
