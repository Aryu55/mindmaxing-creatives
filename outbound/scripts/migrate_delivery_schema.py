#!/usr/bin/env python3
"""
Mindmaxing Delivery Tracking Schema Migration
Extends mindmaxing_crm.db with tables for:
- messages (every outgoing email, campaign or test, with Message-ID)
- delivery_events (audit log of SMTP responses, IMAP observations, bounces, replies)
- collector_health (polling cursors, scan timestamps, error tracking)
- mailbox_quotas (UTC transactional daily counters)
- mailbox_levels (graduated volume control, Level 1-3, auto-pause states)
- recipient_suppressions (hard bounce and opt-out suppression)
Imports existing 25 records from sent_history.json without inventing historical delivery results.
"""

import os
import json
import sqlite3
from datetime import datetime

BASE_DIR = "/root/outbound"
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")
HISTORY_FILE = os.path.join(BASE_DIR, "data", "sent_history.json")
MAILBOXES_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")

def detect_provider(email_addr: str) -> str:
    domain = email_addr.split("@")[-1].lower().strip()
    if "gmail.com" in domain:
        return "gmail"
    elif any(d in domain for d in ["outlook.com", "hotmail.com", "live.com", "office365.com"]):
        return "microsoft"
    elif "yahoo.com" in domain:
        return "yahoo"
    else:
        return "other"

def migrate():
    print(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        message_id TEXT PRIMARY KEY,
        sender_email TEXT NOT NULL,
        sender_domain TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        recipient_domain TEXT NOT NULL,
        recipient_provider TEXT NOT NULL,
        purpose TEXT NOT NULL CHECK(purpose IN ('campaign', 'test')),
        campaign_touch INTEGER,
        prospect_domain TEXT,
        sent_at TEXT NOT NULL,
        sent_date TEXT NOT NULL,
        smtp_status TEXT NOT NULL,
        smtp_code INTEGER,
        smtp_response TEXT,
        delivery_state TEXT NOT NULL,
        auth_spf TEXT DEFAULT 'unknown',
        auth_dkim TEXT DEFAULT 'unknown',
        auth_dmarc TEXT DEFAULT 'unknown',
        last_event_at TEXT NOT NULL,
        notes TEXT
    )
    """)

    # 2. delivery_events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delivery_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        detected_at TEXT NOT NULL,
        source_mailbox TEXT NOT NULL,
        folder TEXT,
        details TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(message_id)
    )
    """)

    # 3. collector_health table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collector_health (
        mailbox TEXT PRIMARY KEY,
        mailbox_type TEXT NOT NULL, -- 'sender' or 'test_inbox'
        last_scan_at TEXT,
        status TEXT NOT NULL DEFAULT 'unknown', -- 'healthy', 'error', 'setup_incomplete', 'unknown'
        error_message TEXT,
        messages_scanned INTEGER DEFAULT 0,
        last_success_at TEXT
    )
    """)

    # 4. mailbox_quotas table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mailbox_quotas (
        mailbox TEXT NOT NULL,
        date_utc TEXT NOT NULL,
        campaign_sent INTEGER DEFAULT 0,
        diagnostic_sent INTEGER DEFAULT 0,
        PRIMARY KEY (mailbox, date_utc)
    )
    """)

    # 5. mailbox_levels table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mailbox_levels (
        mailbox TEXT PRIMARY KEY,
        domain TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        level_updated_at TEXT NOT NULL,
        status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused')),
        paused_reason TEXT,
        paused_at TEXT
    )
    """)

    # 6. recipient_suppressions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recipient_suppressions (
        recipient_email TEXT PRIMARY KEY,
        reason TEXT NOT NULL,
        suppressed_at TEXT NOT NULL,
        source_message_id TEXT
    )
    """)

    conn.commit()
    print("Core delivery tables created successfully.")

    # Populate mailbox_levels for all 25 mailboxes at Level 1 (initially)
    now_iso = datetime.utcnow().isoformat()
    if os.path.exists(MAILBOXES_FILE):
        with open(MAILBOXES_FILE, "r") as f:
            mailboxes = json.load(f)
            for m in mailboxes:
                cursor.execute("""
                INSERT OR IGNORE INTO mailbox_levels (mailbox, domain, level, level_updated_at, status)
                VALUES (?, ?, 1, ?, 'active')
                """, (m["email"], m["domain"], now_iso))
        conn.commit()
        print(f"Initialized {len(mailboxes)} mailboxes at Level 1.")

    # Import sent_history.json records without inventing delivery states
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = json.load(f)
            imported = 0
            for h in history:
                msg_id = h.get("message_id") or f"<historical-{h['domain']}@mindmaxing.online>"
                sender = h.get("sender_email", "aryan@mindmaxing.online")
                sender_domain = sender.split("@")[-1]
                recipient = h.get("recipient_email", "")
                recip_domain = recipient.split("@")[-1] if "@" in recipient else h.get("domain", "")
                recip_provider = detect_provider(recipient)
                sent_at = h.get("timestamp") or f"{h.get('sent_date', '2026-09-19')}T20:00:00"
                sent_date = h.get("sent_date", "2026-09-19")
                touch = h.get("touch", 1)

                # Assign delivery state accurately based on observed replies
                if "kilgourmd" in recip_domain:
                    state = "replied"
                    notes = "Human response from Ramchell (KilgourMD Support Team) polite pass"
                elif "shapellx" in recip_domain:
                    state = "auto_response"
                    notes = "Automated Zendesk ticket #444636"
                elif "norseorganics" in recip_domain:
                    state = "auto_response"
                    notes = "Automated Mimir AI deflection bot"
                else:
                    # As Astra strictly required: unknown outcome, never assumed inbox
                    state = "unknown"
                    notes = "Historical dispatch. Awaiting response/monitoring."

                cursor.execute("""
                INSERT OR IGNORE INTO messages (
                    message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                    recipient_provider, purpose, campaign_touch, prospect_domain, sent_at,
                    sent_date, smtp_status, smtp_code, smtp_response, delivery_state,
                    auth_spf, auth_dkim, auth_dmarc, last_event_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, 'campaign', ?, ?, ?, ?, 'accepted', 250, 'Historical send', ?, 'unknown', 'unknown', 'unknown', ?, ?)
                """, (
                    msg_id, sender, sender_domain, recipient, recip_domain,
                    recip_provider, touch, h.get("domain"), sent_at,
                    sent_date, state, sent_at, notes
                ))
                imported += 1
        conn.commit()
        print(f"Imported {imported} historical records into messages table.")

    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
