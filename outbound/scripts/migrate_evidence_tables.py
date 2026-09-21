#!/usr/bin/env python3
"""
Mindmaxing Database Migration: Evidence Architecture & Persistent Queue
Creates:
1. `contact_candidates`: Preserves every candidate considered, its email origin, mailbox verification, and rejection reasons.
2. `contact_resolution_events`: Append-only audit ledger recording every resolution attempt, input, outcome, and state transition.
3. `contact_jobs`: Transactional job queue with lease tracking, exponential backoff retries, and duplicate prevention.
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")


def run_migration(db_path: str = DB_PATH) -> bool:
    print(f"[*] Applying evidence architecture migration to: {db_path}")
    if not os.path.exists(db_path):
        print(f"[!] Database path does not exist: {db_path}")
        return False

    conn = sqlite3.connect(db_path, timeout=10.0)
    c = conn.cursor()

    try:
        c.execute("BEGIN TRANSACTION;")

        # 1. contact_candidates
        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT,
                email TEXT,
                email_origin TEXT NOT NULL,
                mailbox_status TEXT NOT NULL DEFAULT 'UNCHECKED',
                mailbox_checked_at TEXT,
                identity_status TEXT NOT NULL DEFAULT 'UNCONFIRMED',
                identity_checked_at TEXT,
                evidence_json TEXT,
                rejection_reasons TEXT,
                is_selected BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_candidates_lead_id ON contact_candidates (lead_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_candidates_domain ON contact_candidates (domain);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_candidates_email ON contact_candidates (email);")

        # 2. contact_resolution_events
        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_resolution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                run_id TEXT NOT NULL,
                code_version TEXT NOT NULL,
                event_type TEXT NOT NULL,
                inputs_json TEXT,
                outcome TEXT NOT NULL,
                before_state_json TEXT,
                after_state_json TEXT,
                rejection_reasons TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_lead_id ON contact_resolution_events (lead_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_domain ON contact_resolution_events (domain);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_run_id ON contact_resolution_events (run_id);")

        # 3. contact_jobs
        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL UNIQUE,
                domain TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'RUNNING', 'COMPLETED', 'HELD_FOR_REVIEW', 'FAILED')),
                attempt_count INTEGER DEFAULT 0,
                worker_id TEXT,
                lease_expires_at TEXT,
                next_attempt_at TEXT,
                last_error TEXT,
                last_error_type TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_next ON contact_jobs (status, next_attempt_at);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_domain ON contact_jobs (domain);")

        # 4. Seed contact_jobs for any existing leads not yet registered in jobs table
        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute("""
            INSERT OR IGNORE INTO contact_jobs (lead_id, domain, status, attempt_count, next_attempt_at, created_at, updated_at)
            SELECT 
                id,
                domain,
                CASE 
                    WHEN resolution_status = 'FOUNDER_FOUND' THEN 'COMPLETED'
                    WHEN resolution_status = 'REVIEW_REQUIRED' THEN 'HELD_FOR_REVIEW'
                    ELSE 'PENDING'
                END,
                0,
                :now_iso,
                :now_iso,
                :now_iso
            FROM leads;
        """, {"now_iso": now_iso})

        conn.commit()
        
        # Verify counts
        job_count = c.execute("SELECT COUNT(*) FROM contact_jobs").fetchone()[0]
        print(f"[+] Migration successful. Registered {job_count} leads in contact_jobs.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[!] Migration failed: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
