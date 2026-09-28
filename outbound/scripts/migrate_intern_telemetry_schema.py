#!/usr/bin/env python3
"""
Migration: Add Intern Outbound Telemetry and Approval Gate Schema
Extends mindmaxing_crm.db with tables for tracking intern activity,
founder review decisions, proof of send uploads, and daily KPI metrics.
"""

import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")

def migrate(db_path=DB_PATH):
    print(f"Connecting to database: {db_path}")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Intern Accounts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intern_accounts (
        intern_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        daily_quota INTEGER DEFAULT 100,
        active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Intern Command Logs (Every /outreach or /outbound invocation)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intern_command_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_ref_id TEXT UNIQUE NOT NULL,
        intern_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        target_handle TEXT NOT NULL,
        target_url TEXT,
        qualification_status TEXT NOT NULL,
        disqualification_reason TEXT,
        bottleneck_summary TEXT,
        generated_dm TEXT,
        generated_reply TEXT,
        generated_email TEXT,
        approval_status TEXT DEFAULT 'PENDING_APPROVAL',
        reviewed_at TIMESTAMP,
        reviewer_notes TEXT,
        dispatch_status TEXT DEFAULT 'NOT_SENT',
        proof_image_path TEXT,
        verified_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(intern_id) REFERENCES intern_accounts(intern_id)
    );
    """)

    # Indexes for fast querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_intern_logs_ref ON intern_command_logs(lead_ref_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_intern_logs_intern ON intern_command_logs(intern_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_intern_logs_approval ON intern_command_logs(approval_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_intern_logs_dispatch ON intern_command_logs(dispatch_status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_intern_logs_date ON intern_command_logs(created_at);")

    # 3. Intern Daily KPI Ledger
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS intern_daily_kpis (
        date TEXT NOT NULL,
        intern_id TEXT NOT NULL,
        total_screened INTEGER DEFAULT 0,
        disqualified_count INTEGER DEFAULT 0,
        approved_count INTEGER DEFAULT 0,
        rejected_count INTEGER DEFAULT 0,
        verified_sent_count INTEGER DEFAULT 0,
        quota_reached INTEGER DEFAULT 0,
        PRIMARY KEY (date, intern_id)
    );
    """)

    # Seed initial default intern account if table is empty
    cursor.execute("SELECT COUNT(*) FROM intern_accounts;")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO intern_accounts (intern_id, name, api_key, daily_quota, active)
        VALUES ('intern_1', 'Outreach Intern 1', 'mm_key_intern_default_2026', 100, 1);
        """)
        print("Seeded default intern account: intern_1 (API Key: mm_key_intern_default_2026)")

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    migrate(target)
