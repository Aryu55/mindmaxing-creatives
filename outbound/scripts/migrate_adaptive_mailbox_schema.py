#!/usr/bin/env python3
"""
Mindmaxing Database Migration: Adaptive Mailbox Reporting & Daily Scheduling Schema
Creates:
1. `mailbox_daily_decisions`: Immutable ledger of daily volume decisions, reason codes, and evidence.
2. `outbound_jobs`: Queue for scheduled sequence touches enforcing follow-up priority and sender affinity.
3. `imap_cursors`: Durable UID / UIDVALIDITY tracking to prevent duplicate telemetry.
4. `unmatched_delivery_events`: Diagnostic quarantine for unparseable or ambiguous DSN reports.
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")


def run_migration(db_path: str = DB_PATH) -> bool:
    print(f"[*] Applying adaptive mailbox schema migration to: {db_path}")
    if not os.path.exists(db_path):
        print(f"[!] Database path does not exist: {db_path}")
        return False

    conn = sqlite3.connect(db_path, timeout=10.0)
    c = conn.cursor()

    try:
        c.execute("BEGIN TRANSACTION;")

        # 1. mailbox_daily_decisions (Append-only ledger with revision tracking and revised audit metadata)
        c.execute("PRAGMA table_info(mailbox_daily_decisions);")
        cols = [r[1] for r in c.fetchall()]
        if not cols:
            c.execute("""
                CREATE TABLE IF NOT EXISTS mailbox_daily_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT UNIQUE,
                    period_id TEXT NOT NULL,
                    decision_date_utc TEXT NOT NULL,
                    mailbox TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    policy_version TEXT NOT NULL DEFAULT 'v2.1-revised',
                    baseline_cap INTEGER NOT NULL DEFAULT 1,
                    current_level INTEGER NOT NULL,
                    effective_campaign_cap INTEGER NOT NULL,
                    effective_diagnostic_cap INTEGER NOT NULL,
                    decision_action TEXT NOT NULL,
                    decision_reason TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'mailbox',
                    recovery_condition TEXT,
                    evidence_summary_json TEXT,
                    evidence_ids TEXT,
                    campaign_name TEXT NOT NULL DEFAULT 'all',
                    revision INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_decisions_date_mb ON mailbox_daily_decisions (decision_date_utc, mailbox, revision);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_decisions_period_mb ON mailbox_daily_decisions (period_id, mailbox, revision);")
        else:
            # Table exists, add missing columns safely
            col_defs = [
                ("decision_id", "TEXT"),
                ("period_id", "TEXT"),
                ("policy_version", "TEXT NOT NULL DEFAULT 'v2.1-revised'"),
                ("baseline_cap", "INTEGER NOT NULL DEFAULT 1"),
                ("scope", "TEXT NOT NULL DEFAULT 'mailbox'"),
                ("recovery_condition", "TEXT"),
                ("evidence_ids", "TEXT"),
                ("campaign_name", "TEXT NOT NULL DEFAULT 'all'")
            ]
            for col_name, col_type in col_defs:
                if col_name not in cols:
                    c.execute(f"ALTER TABLE mailbox_daily_decisions ADD COLUMN {col_name} {col_type};")
            c.execute("CREATE INDEX IF NOT EXISTS idx_decisions_period_mb ON mailbox_daily_decisions (period_id, mailbox, revision);")

        # 2. outbound_jobs
        c.execute("""
            CREATE TABLE IF NOT EXISTS outbound_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                touch_number INTEGER NOT NULL,
                assigned_mailbox TEXT,
                recipient_email TEXT NOT NULL,
                parent_message_id TEXT,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                due_at TEXT NOT NULL,
                earliest_send_at TEXT NOT NULL,
                expires_at TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'RESERVED', 'CLAIMED', 'SENT', 'FAILED', 'DEFERRED', 'EXPIRED', 'UNCERTAIN')),
                worker_id TEXT,
                attempt_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(domain, touch_number),
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
        """)
        c.execute("PRAGMA table_info(outbound_jobs);")
        job_cols = [r[1] for r in c.fetchall()]
        job_col_defs = [
            ("campaign_name", "TEXT NOT NULL DEFAULT 'dealstrike-distributors'"),
            ("period_id", "TEXT"),
            ("decision_id", "TEXT")
        ]
        for col_name, col_type in job_col_defs:
            if col_name not in job_cols:
                c.execute(f"ALTER TABLE outbound_jobs ADD COLUMN {col_name} {col_type};")

        c.execute("CREATE INDEX IF NOT EXISTS idx_outbound_jobs_due ON outbound_jobs (status, due_at);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_outbound_jobs_mb ON outbound_jobs (assigned_mailbox);")

        # 3. messages (Campaign identity)
        c.execute("PRAGMA table_info(messages);")
        msg_cols = [r[1] for r in c.fetchall()]
        msg_col_defs = [
            ("campaign_name", "TEXT NOT NULL DEFAULT 'legacy_unattributed'"),
            ("period_id", "TEXT"),
            ("decision_id", "TEXT")
        ]
        for col_name, col_type in msg_col_defs:
            if col_name not in msg_cols:
                c.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type};")

        # 4. imap_cursors
        c.execute("""
            CREATE TABLE IF NOT EXISTS imap_cursors (
                mailbox TEXT NOT NULL,
                folder TEXT NOT NULL,
                uidvalidity INTEGER NOT NULL,
                last_uid INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (mailbox, folder)
            );
        """)

        # 5. unmatched_delivery_events
        c.execute("""
            CREATE TABLE IF NOT EXISTS unmatched_delivery_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_mailbox TEXT NOT NULL,
                folder TEXT NOT NULL,
                raw_headers_snippet TEXT,
                body_snippet TEXT,
                reason TEXT NOT NULL,
                detected_at TEXT NOT NULL
            );
        """)

        # 6. mailbox_quotas (add period_id for unified IST budget tracking)
        c.execute("""
            CREATE TABLE IF NOT EXISTS mailbox_quotas (
                mailbox TEXT NOT NULL,
                date_utc TEXT NOT NULL,
                campaign_sent INTEGER DEFAULT 0,
                diagnostic_sent INTEGER DEFAULT 0,
                period_id TEXT,
                PRIMARY KEY (mailbox, date_utc)
            );
        """)
        c.execute("PRAGMA table_info(mailbox_quotas);")
        quota_cols = [r[1] for r in c.fetchall()]
        if "period_id" not in quota_cols:
            c.execute("ALTER TABLE mailbox_quotas ADD COLUMN period_id TEXT;")
        c.execute("CREATE INDEX IF NOT EXISTS idx_mb_quotas_period ON mailbox_quotas (mailbox, period_id);")

        conn.commit()
        print("[+] Adaptive mailbox migration successfully applied.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[!] Migration failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    target_db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    success = run_migration(target_db)
    sys.exit(0 if success else 1)
