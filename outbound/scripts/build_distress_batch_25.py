import sqlite3
import json
import re

DB_PATH = '/root/outbound/data/mindmaxing_crm.db'
MAILBOXES_FILE = '/root/outbound/config/mailboxes.json'

with open(MAILBOXES_FILE) as f:
    mailboxes = json.load(f)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# 1. Reddit leads
c.execute('''
    SELECT * FROM leads 
    WHERE source = 'reddit'
      AND contact_email IS NOT NULL AND contact_email != ''
      AND domain NOT LIKE '%.in' AND contact_email NOT LIKE '%.in'
    ORDER BY captured_at DESC
''')
reddit_leads = [dict(r) for r in c.fetchall()]

# Filter reddit
valid_reddit = []
for l in reddit_leads:
    email = l.get("contact_email", "").strip(".,;:'\"")
    prefix = email.split("@")[0].lower()
    if prefix in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"] or prefix.endswith("-sms"):
        continue
    valid_reddit.append(l)

# 2. Trustpilot leads with technical checkout / cart / payment / discount pain
keywords = ['checkout', 'cart', 'card', 'payment', 'declined', 'stuck', 'freeze', 'button', 'glitch', 'code', 'discount', 'charged twice', 'duplicate', 'unable to place', 'could not order']

c.execute('''
    SELECT * FROM leads 
    WHERE source = 'trustpilot'
      AND contact_email IS NOT NULL AND contact_email != ''
      AND domain NOT LIKE '%.in' AND contact_email NOT LIKE '%.in'
    ORDER BY COALESCE(review_freshest_date, review_date, captured_at) DESC
''')
all_tp = [dict(r) for r in c.fetchall()]

valid_tp = []
seen_domains = {l['domain'] for l in valid_reddit}

for l in all_tp:
    d = l['domain']
    if d in seen_domains:
        continue
    email = l.get("contact_email", "").strip(".,;:'\"")
    if not email or "@" not in email or email.startswith("u003e") or len(email.split("@")[0]) < 2:
        continue
    prefix = email.split("@")[0].lower()
    if prefix in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"] or prefix.endswith("-sms"):
        continue
    
    text = (l.get('review_snippet') or '') + ' ' + (l.get('reviews_json') or '')
    matched = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', text, re.I)]
    if matched:
        l['matched_keywords'] = matched
        valid_tp.append(l)
        seen_domains.add(d)

selected_leads = valid_reddit + valid_tp[:(25 - len(valid_reddit))]

print(f"Selected {len(selected_leads)} leads for 25 mailboxes:")

import sys
sys.path.append('/root/outbound/scripts')
import dispatcher

manifest = []
for i, (lead, mb) in enumerate(zip(selected_leads, mailboxes), 1):
    subj, body = dispatcher.generate_touch_1_copy(lead, mb)
    manifest.append({
        "num": i,
        "mailbox": mb["email"],
        "sender_name": mb["name"],
        "domain": lead["domain"],
        "company": lead["company_name"],
        "to_email": lead["contact_email"],
        "source": lead["source"],
        "subject": subj,
        "body": body,
        "lead_id": lead["id"]
    })

print(f"\nManifest built for {len(manifest)} sends:")
for item in manifest:
    print(f"{item['num']}. [{item['source'].upper()}] From: {item['mailbox']} -> To: {item['to_email']} ({item['domain']})")
    print(f"   Subject: {item['subject']}")
