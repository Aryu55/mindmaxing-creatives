#!/usr/bin/env python3
"""
Additive Schema Migration: Reddit Signal Evaluator Columns
Adds:
- signal_decision TEXT
- signal_reasons TEXT
- signal_evidence TEXT
- signal_policy_version TEXT
- evaluated_at TEXT

Idempotent and safe to run multiple times.
"""

import os
import sqlite3
import sys

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mindmaxing_crm.db")


def run_migration(db_path: str = DEFAULT_DB_PATH) -> bool:
    print(f"[*] Running signal schema migration on: {db_path}")
    if not os.path.exists(db_path):
        print(f"[-] Database file does not exist at {db_path}, skipping.")
        return False

    conn = sqlite3.connect(db_path, timeout=30.0)
    c = conn.cursor()

    existing_cols = [row[1] for row in c.execute("PRAGMA table_info(leads)").fetchall()]

    new_columns = [
        ("signal_decision", "TEXT"),
        ("signal_reasons", "TEXT"),
        ("signal_evidence", "TEXT"),
        ("signal_policy_version", "TEXT"),
        ("evaluated_at", "TEXT")
    ]

    added = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
            print(f"  [+] Added column: leads.{col_name} ({col_type})")
            added += 1
        else:
            print(f"  [=] Column already exists: leads.{col_name}")

    conn.commit()
    conn.close()
    print(f"[✓] Migration complete. Added {added} columns.\n")
    return True


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    run_migration(db)
