#!/usr/bin/env python3
"""
Mindmaxing Outbound Status & Daily Telemetry Summary
CLI command and daily reporter showing:
- Campaign sends & diagnostic sends (UTC daily counters)
- Inbox / Promotions / Spam observations
- Hard bounces and recipient suppressions
- Collector health across 25 senders and 8 Gmail test inboxes
- Current mailbox levels, daily caps, and active holds/pauses
- Prominently displays Gmail-only diagnostic test coverage.
Saves daily summary JSON to /root/outbound/data/daily_summary_YYYY-MM-DD.json.
"""

import os
import json
import sqlite3
from datetime import datetime, timezone

import volume_controller

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")

def generate_status_report(save_json: bool = True) -> dict:
    conn = volume_controller.get_db_connection()
    c = conn.cursor()
    utc_date = volume_controller.get_utc_date_str()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # 1. Quotas and Daily Activity (Today UTC)
    c.execute("""
    SELECT ml.domain, ml.mailbox, ml.level, ml.status, ml.paused_reason,
           COALESCE(mq.campaign_sent, 0) as campaign_sent,
           COALESCE(mq.diagnostic_sent, 0) as diagnostic_sent
    FROM mailbox_levels ml
    LEFT JOIN mailbox_quotas mq ON ml.mailbox = mq.mailbox AND mq.date_utc = ?
    ORDER BY ml.domain, ml.mailbox
    """, (utc_date,))
    mailbox_rows = c.fetchall()

    # 2. Delivery States Summary (All-Time and Today)
    c.execute("""
    SELECT purpose, delivery_state, count(*) as count
    FROM messages
    GROUP BY purpose, delivery_state
    """)
    state_counts = {(r["purpose"], r["delivery_state"]): r["count"] for r in c.fetchall()}

    # 3. Suppressions Count
    c.execute("SELECT count(*) as count FROM recipient_suppressions")
    suppressions_count = c.fetchone()["count"]

    # 4. Collector Health
    c.execute("""
    SELECT mailbox_type, status, count(*) as count
    FROM collector_health
    GROUP BY mailbox_type, status
    """)
    collector_summary = {(r["mailbox_type"], r["status"]): r["count"] for r in c.fetchall()}

    c.execute("SELECT mailbox, status, error_message, last_scan_at FROM collector_health WHERE status = 'error'")
    collector_errors = [dict(r) for r in c.fetchall()]

    # 5. Gmail Test Coverage Summary
    c.execute("""
    SELECT recipient_email, count(*) as tests_received,
           sum(case when delivery_state in ('inbox', 'promotions') then 1 else 0 end) as inbox_count,
           sum(case when delivery_state = 'spam' then 1 else 0 end) as spam_count
    FROM messages
    WHERE purpose = 'test'
    GROUP BY recipient_email
    """)
    gmail_coverage = [dict(r) for r in c.fetchall()]

    conn.close()

    # Organize by domain
    domains_data = {}
    for r in mailbox_rows:
        dom = r["domain"]
        if dom not in domains_data:
            domains_data[dom] = {
                "level": r["level"],
                "status": "active",
                "campaign_today": 0,
                "diagnostic_today": 0,
                "paused_count": 0,
                "mailboxes": []
            }
        domains_data[dom]["campaign_today"] += r["campaign_sent"]
        domains_data[dom]["diagnostic_today"] += r["diagnostic_sent"]
        if r["status"] == "paused":
            domains_data[dom]["paused_count"] += 1
            domains_data[dom]["status"] = "has_pauses"
        domains_data[dom]["mailboxes"].append(dict(r))

    report = {
        "generated_at": now_utc,
        "date_utc": utc_date,
        "domains": domains_data,
        "delivery_states": {f"{k[0]}_{k[1]}": v for k, v in state_counts.items()},
        "suppressions_total": suppressions_count,
        "collector_health": {f"{k[0]}_{k[1]}": v for k, v in collector_summary.items()},
        "collector_errors": collector_errors,
        "gmail_test_coverage": gmail_coverage
    }

    if save_json:
        out_path = os.path.join(DATA_DIR, f"daily_summary_{utc_date}.json")
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)

    return report

def print_status_cli():
    rep = generate_status_report(save_json=True)
    
    print("=" * 80)
    print(f"  MINDMAXING FORENSIC OUTBOUND & DELIVERY TELEMETRY STATUS")
    print(f"  Report Time: {rep['generated_at']} | UTC Date: {rep['date_utc']}")
    print("=" * 80)

    print("\n--- DOMAIN & MAILBOX VOLUME CONTROLLER ---")
    for dom, data in rep["domains"].items():
        dom_status_badge = "[ACTIVE]" if data["status"] == "active" else "[PAUSES DETECTED]"
        print(f"\n* Domain: {dom} | Level {data['level']} {dom_status_badge}")
        print(f"  Today UTC Sends: {data['campaign_today']} Campaign | {data['diagnostic_today']} Diagnostic")
        
        paused_boxes = [m for m in data["mailboxes"] if m["status"] == "paused"]
        if paused_boxes:
            for pb in paused_boxes:
                print(f"    ! PAUSED: {pb['mailbox']} - Reason: {pb['paused_reason']}")
        else:
            print(f"    All {len(data['mailboxes'])} mailboxes active and healthy.")

    print("\n--- DELIVERY OUTCOMES & REPUTATION ---")
    print(f"Campaign Messages: Accepted={rep['delivery_states'].get('campaign_accepted', 0)}, Replied={rep['delivery_states'].get('campaign_replied', 0)}, Auto-Deflected={rep['delivery_states'].get('campaign_auto_response', 0)}, Bounced={rep['delivery_states'].get('campaign_bounced', 0)}, Pending/Unknown={rep['delivery_states'].get('campaign_unknown', 0)}")
    print(f"Hard Bounces / Suppressions: {rep['suppressions_total']} recipient(s) permanently suppressed.")

    print("\n--- GMAIL DIAGNOSTIC TEST COVERAGE (Strict Read-Only) ---")
    if rep["gmail_test_coverage"]:
        for gc in rep["gmail_test_coverage"]:
            print(f"  * {gc['recipient_email']}: {gc['tests_received']} tests observed (Inbox={gc['inbox_count']}, Spam={gc['spam_count']})")
    else:
        print("  * No diagnostic tests recorded in test inboxes yet.")

    print("\n--- COLLECTOR HEALTH (Every 10m Polling) ---")
    senders_healthy = rep['collector_health'].get('sender_healthy', 0)
    tests_healthy = rep['collector_health'].get('test_inbox_healthy', 0)
    print(f"  Sending Mailboxes: {senders_healthy}/25 healthy")
    print(f"  Gmail Test Inboxes: {tests_healthy}/8 healthy")
    
    if rep["collector_errors"]:
        print("\n  ! Collector Errors:")
        for ce in rep["collector_errors"]:
            print(f"    - {ce['mailbox']} ({ce['status']}): {ce['error_message']}")

    print("=" * 80)
    print(f"Summary saved to: {os.path.join(DATA_DIR, f'daily_summary_{rep[\"date_utc\"]}.json')}\n")

if __name__ == "__main__":
    print_status_cli()
