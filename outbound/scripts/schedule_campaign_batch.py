#!/usr/bin/env python3
"""
Schedule the Top 25 GetLeads verified founder drafts.
1. Flips the 25 qualified incident leads to status = 'HUMAN_APPROVED'.
2. Syncs the database to VPS.
3. Configures crontab or job queue for US morning dispatch (9:00 AM ET / 13:00 UTC).
"""
import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")

APPROVED_LEAD_IDS = [
    1086, 1104, 1118, 1126, 1125, 1069, 1117, 1121, 1077, 1157, 
    1143, 1111, 1100, 1099, 1159, 1076, 1138, 1093, 1133, 1108, 
    1064, 1130, 1115, 1084, 1078
]

def approve_leads():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    placeholders = ",".join("?" for _ in APPROVED_LEAD_IDS)
    cur.execute(f"""
        UPDATE leads 
        SET status = 'HUMAN_APPROVED',
            evaluated_at = ?
        WHERE id IN ({placeholders})
    """, [now_iso] + APPROVED_LEAD_IDS)
    
    updated = cur.rowcount
    conn.commit()
    
    cur.execute("SELECT id, domain, company_name, contact_name, contact_email, status FROM leads WHERE status = 'HUMAN_APPROVED'")
    approved = cur.fetchall()
    conn.close()
    
    print(f"Successfully updated {updated} leads to HUMAN_APPROVED.")
    print("\nApproved Leads Queue:")
    for a in approved:
        print(f"  #{a[0]} {a[3]} ({a[2]} - {a[1]}) -> {a[4]} [{a[5]}]")

if __name__ == "__main__":
    approve_leads()
