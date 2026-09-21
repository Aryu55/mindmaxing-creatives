#!/usr/bin/env python3
"""
Mindmaxing Database Backup & Integrity Verification Service
- Uses SQLite Online Backup API (sqlite3.Connection.backup) for consistent, non-blocking snapshots.
- Strictly executes `PRAGMA integrity_check` on the resulting backup before committing it.
- Enforces rolling retention (default 14 backups), automatically purging older backups.
- Safe for crontab invocation without shell % escaping hazards.
"""

import os
import sys
import glob
import sqlite3
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")
DEFAULT_BACKUP_DIR = os.path.join(BASE_DIR, "data", "backups")


def backup_database(
    db_path: str = DEFAULT_DB_PATH,
    backup_dir: str = DEFAULT_BACKUP_DIR,
    max_backups: int = 14
) -> str:
    """
    Executes an atomic online SQLite backup, verifies PRAGMA integrity_check,
    and rotates retention to keep at most max_backups files.
    Returns the path to the verified backup file.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"mindmaxing_crm_backup_{ts}.db"
    backup_path = os.path.join(backup_dir, backup_filename)

    # 1. Execute online backup using sqlite3.Connection.backup API
    src_conn = sqlite3.connect(db_path)
    dest_conn = sqlite3.connect(backup_path)
    try:
        with dest_conn:
            src_conn.backup(dest_conn, pages=100)
    finally:
        dest_conn.close()
        src_conn.close()

    # 2. Run PRAGMA integrity_check on the backup
    check_conn = sqlite3.connect(backup_path)
    try:
        cursor = check_conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        row = cursor.fetchone()
        if not row or row[0] != "ok":
            raise RuntimeError(f"Integrity check failed: {row}")
    except Exception as e:
        if os.path.exists(backup_path):
            os.remove(backup_path)
        raise RuntimeError(f"Backup corrupted or integrity check failed: {e}")
    finally:
        check_conn.close()

    # 3. Rotate retention: keep max_backups latest
    pattern = os.path.join(backup_dir, "mindmaxing_crm_backup_*.db")
    existing_backups = sorted(glob.glob(pattern))
    if len(existing_backups) > max_backups:
        to_delete = existing_backups[:-max_backups]
        for f in to_delete:
            try:
                os.remove(f)
            except Exception:
                pass

    return backup_path


def main():
    try:
        path = backup_database()
        size_kb = os.path.getsize(path) / 1024.0
        print(f"[{datetime.now(timezone.utc).isoformat()}] Backup successful: {path} ({size_kb:.1f} KB)")
    except Exception as e:
        print(f"[{datetime.now(timezone.utc).isoformat()}] Backup failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
