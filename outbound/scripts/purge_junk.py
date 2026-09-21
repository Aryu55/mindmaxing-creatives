import json
import sqlite3

LEADS_FILE = "/root/outbound/data/icp1_shopify_dtc/leads.json"
DB_PATH = "/root/outbound/data/mindmaxing_crm.db"

with open(LEADS_FILE, "r", encoding="utf-8") as f:
    leads = json.load(f)

HIGH_SIGNAL_DOMAINS = {
    "framedcars.it",
    "tryvayora.co",
    "jureynco.com",
    "thepawsitivespace.com",
    "memarinedivesupply.com",
    "glorytheshop.com",
    "slumbrband.com",
    "grilldogsapparel.com",
    "riverzshop.ro"
}

purged_count = 0
clean_leads = []

for l in leads:
    dom = l.get("domain", "").lower().replace("www.", "").strip()
    if l.get("source") == "reddit":
        if dom in HIGH_SIGNAL_DOMAINS:
            l["status"] = "CANDIDATE"
            clean_leads.append(l)
        else:
            purged_count += 1
    else:
        clean_leads.append(l)

with open(LEADS_FILE, "w", encoding="utf-8") as f:
    json.dump(clean_leads, f, indent=2)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Delete non-high-signal Reddit leads
cur.execute("SELECT id, domain FROM leads WHERE source = 'reddit'")
all_reddit = cur.fetchall()
to_delete = [row[0] for row in all_reddit if row[1].lower().replace("www.", "").strip() not in HIGH_SIGNAL_DOMAINS]

for lead_id in to_delete:
    cur.execute("DELETE FROM leads WHERE id = ?", (lead_id,))

purged_db = len(to_delete)

# Set remaining Reddit leads to CANDIDATE
cur.execute("UPDATE leads SET status = 'CANDIDATE' WHERE source = 'reddit'")
conn.commit()

cur.execute("SELECT source, status, count(*) FROM leads GROUP BY source, status")
rows = cur.fetchall()

tp_cnt = sum(1 for l in clean_leads if l.get("source") != "reddit")
rd_cnt = sum(1 for l in clean_leads if l.get("source") == "reddit")

print(f"Purged {purged_count} junk Reddit leads from leads.json.")
print(f"Purged {purged_db} junk Reddit rows from CRM DB.")
print(f"\nFinal leads in leads.json: {len(clean_leads)}")
print(f"  Trustpilot leads: {tp_cnt}")
print(f"  Verified Reddit CANDIDATES: {rd_cnt}")
print("\n=== CRM DB Status Breakdown ===")
for r in rows:
    print(f"  source={r[0]}, status={r[1]} -> count={r[2]}")

conn.close()
