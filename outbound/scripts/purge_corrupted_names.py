#!/usr/bin/env python3
"""
Mindmaxing Database Sanitizer: Purge Corrupted Founder Names
- Cleanses legacy database leads where scraper naively captured tokens like
  "Customerservice", "Team", "Services", "Ciao", "Hello", "Social" as founder names.
- Uses strict is_valid_founder_name() gate.
- Preserves active sequence email addresses while stripping corrupted greetings.
- Downgrades false FOUNDER_DIRECT/FOUNDER_NAMED_DESK to GENERIC_SUPPORT when email is a role account.
"""

import os
import sqlite3
import sys

try:
    from email_classifier import is_valid_founder_name, is_role_account
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from email_classifier import is_valid_founder_name, is_role_account

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")


def sanitize_database(db_path: str = DB_PATH, dry_run: bool = False):
    print(f"[*] Connecting to database: {db_path}")
    print(f"[*] Dry run mode: {dry_run}\n")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    leads = cur.execute("SELECT id, domain, contact_email, contact_name, contact_type, current_sequence_step FROM leads").fetchall()

    purged_count = 0
    preserved_count = 0
    type_downgraded = 0
    purged_samples = []

    for lead_id, domain, email, name, c_type, seq_step in leads:
        name_clean = (name or "").strip()
        if not name_clean:
            continue

        valid, clean_name = is_valid_founder_name(name_clean)

        if not valid:
            purged_count += 1
            new_type = c_type
            if is_role_account(email) and c_type in ("FOUNDER_DIRECT", "FOUNDER_NAMED_DESK"):
                new_type = "GENERIC_SUPPORT"
                type_downgraded += 1

            purged_samples.append((domain, name_clean, email, c_type, new_type))

            if not dry_run:
                cur.execute("""
                    UPDATE leads
                    SET contact_name = '',
                        contact_type = ?
                    WHERE id = ?
                """, (new_type, lead_id))
        else:
            preserved_count += 1
            # Standardize casing/trimming if needed
            if clean_name != name_clean and not dry_run:
                cur.execute("UPDATE leads SET contact_name = ? WHERE id = ?", (clean_name, lead_id))

    if not dry_run:
        conn.commit()
    conn.close()

    print("=" * 70)
    print("PURGE & SANITIZATION AUDIT REPORT")
    print("=" * 70)
    print(f"Total leads inspected:          {len(leads)}")
    print(f"Corrupted fake names purged:    {purged_count}")
    print(f"Legitimate human names kept:   {preserved_count}")
    print(f"False founder types downgraded: {type_downgraded}")
    print("-" * 70)
    print("Top Purged Corrupted Names Sample:")
    for d, n, em, old_t, new_t in purged_samples[:20]:
        print(f"  {d:30} | Name: {n:20} -> Cleared | Type: {old_t} -> {new_t}")
    print("=" * 70)


if __name__ == "__main__":
    dry_run_flag = "--dry-run" in sys.argv
    db_arg = None
    for i, a in enumerate(sys.argv):
        if a == "--db" and i + 1 < len(sys.argv):
            db_arg = sys.argv[i + 1]
    
    target_db = db_arg or DB_PATH
    sanitize_database(target_db, dry_run=dry_run_flag)
