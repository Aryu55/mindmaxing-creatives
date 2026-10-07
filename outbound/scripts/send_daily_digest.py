#!/usr/bin/env python3
"""
Mindmaxing Nightly Executive Outbound Digest
Compiles daily sending volume, mailbox health, replies, and pipeline inventory.
Dispatches a clean summary email to Aryan (aryupanchal1647@gmail.com).
Scheduled to run at 22:30 IST (17:00 UTC) right after Wave 2 completes.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "mailboxes.json")

try:
    from alert_notifier import notify_daily_digest
except ImportError:
    from outbound.scripts.alert_notifier import notify_daily_digest


def compile_and_send_digest():
    if not os.path.exists(DB_PATH):
        print(f"[DIGEST] Error: Database not found at {DB_PATH}")
        return False

    today_str = datetime.now().strftime("%Y-%m-%d")
    now_utc = datetime.now(timezone.utc)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Daily Message Counts
    cur.execute("SELECT count(*) FROM messages WHERE (sent_date = ? OR date(sent_at) = ?) AND smtp_status = 'accepted'", (today_str, today_str))
    sent_today = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM messages WHERE (sent_date = ? OR date(sent_at) = ?) AND smtp_status != 'accepted'", (today_str, today_str))
    failed_today = cur.fetchone()[0]

    # 2. Replies detected today
    cur.execute("SELECT count(*) FROM delivery_events WHERE date(detected_at) = ? AND event_type LIKE '%reply%'", (today_str,))
    replies_today = cur.fetchone()[0]

    # 3. Mailbox Fleet Health
    active_mbs = 0
    paused_mbs = 0
    fleet_capacity = 0
    cur.execute("SELECT mailbox, status FROM mailbox_levels")
    for row in cur.fetchall():
        if row[1] == "active":
            active_mbs += 1
            fleet_capacity += 3
        else:
            paused_mbs += 1

    # 4. Pipeline Inventory
    cur.execute("SELECT count(*) FROM leads WHERE status = 'HUMAN_APPROVED'")
    approved_touch1 = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM leads WHERE status = 'CANDIDATE'")
    candidates = cur.fetchone()[0]

    # Ready for Touch 2 (3+ days since Touch 1)
    cur.execute("SELECT last_contacted_at FROM leads WHERE status = 'TOUCH_1_SENT'")
    ready_touch2 = 0
    for r in cur.fetchall():
        if r[0]:
            try:
                dt = datetime.fromisoformat(r[0].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if (now_utc - dt) >= timedelta(days=3):
                    ready_touch2 += 1
            except Exception:
                pass

    conn.close()

    pipeline_health = "HEALTHY"
    if approved_touch1 == 0 and ready_touch2 == 0:
        pipeline_health = "CRITICAL: Pipeline is DRY (0 Leads Ready)"
    elif approved_touch1 == 0:
        pipeline_health = f"ATTENTION: No new Touch 1 leads (Refill needed). {ready_touch2} follow-ups ready."

    report_data = {
        "total_sent_today": sent_today,
        "total_failed_today": failed_today,
        "replies_today": replies_today,
        "active_mailboxes": active_mbs,
        "paused_mailboxes": paused_mbs,
        "fleet_capacity": fleet_capacity,
        "approved_touch1": approved_touch1,
        "ready_touch2": ready_touch2,
        "candidate_count": candidates,
        "pipeline_health": pipeline_health
    }

    print(f"[DIGEST] Compiled daily report: {report_data}")
    return notify_daily_digest(report_data)


if __name__ == "__main__":
    compile_and_send_digest()
