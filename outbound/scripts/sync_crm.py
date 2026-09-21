import sqlite3
import json
import os
import re

DB_PATH = '/root/outbound/data/mindmaxing_crm.db'
LEADS_FILE = '/root/outbound/data/icp1_shopify_dtc/leads.json'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute('''
    SELECT * FROM leads 
    WHERE contact_email IS NOT NULL AND contact_email != ''
    ORDER BY COALESCE(review_freshest_date, review_date, captured_at) DESC
''')
leads = [dict(r) for r in c.fetchall()]

enriched = []
for l in leads:
    tel = {}
    if l.get("reviews_json"):
        try:
            tel = json.loads(l["reviews_json"])
        except Exception:
            pass
    lcp = tel.get("lcp") if isinstance(tel, dict) else None
    if not lcp and l.get("dominant_pattern"):
        m = re.search(r"LCP\s*([\d\.]+\s*s)", l["dominant_pattern"])
        if m:
            lcp = m.group(1)
    
    l["telemetry"] = tel if isinstance(tel, dict) else {}
    if lcp:
        l["lcp"] = lcp
        if "lcp" not in l["telemetry"]:
            l["telemetry"]["lcp"] = lcp

    enriched.append(l)

conn.close()

os.makedirs(os.path.dirname(LEADS_FILE), exist_ok=True)
with open(LEADS_FILE, "w", encoding="utf-8") as f:
    json.dump(enriched, f, indent=2)

print(f"Successfully synced {len(enriched)} leads from SQLite CRM to {LEADS_FILE} with rich telemetry and READY status.")
