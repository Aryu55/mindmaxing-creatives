#!/usr/bin/env python3
"""
Mindmaxing Database Migration: Founder Resolution Columns
- Idempotently adds resolution columns to the `leads` table in mindmaxing_crm.db.
- Preserves all existing data, indexes, and triggers.
"""

import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")

NEW_COLUMNS = [
    ("resolved_name", "TEXT"),
    ("resolved_email", "TEXT"),
    ("resolved_role", "TEXT"),
    ("resolved_evidence", "TEXT"),        # JSON blob of discovery proof
    ("resolution_status", "TEXT DEFAULT 'UNRESOLVED'"),
    ("resolved_at", "TEXT"),
    ("original_contact_email", "TEXT")    # Backs up the scraped address
]


def run_migration(db_path: str = DB_PATH) -> bool:
    if not os.path.exists(db_path):
        print(f"[ERROR] Database file not found at: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Get existing columns
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(leads)").fetchall()}
    print(f"[*] Checking database: {db_path}")
    print(f"[*] Found {len(existing_cols)} existing columns in 'leads' table.")

    added_count = 0
    for col_name, col_type in NEW_COLUMNS:
        if col_name not in existing_cols:
            alter_sql = f"ALTER TABLE leads ADD COLUMN {col_name} {col_type};"
            print(f"  -> Adding column: {col_name} ({col_type})")
            c.execute(alter_sql)
            added_count += 1
        else:
            print(f"  -- Column already exists: {col_name}")

    conn.commit()
    conn.close()
    print(f"[✔] Migration complete. Added {added_count} new columns.\n")
    return True


if __name__ == "__main__":
    target_db = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    run_migration(target_db)
