#!/usr/bin/env python3
"""
Service Heartbeats & Supervision Module (Task D)
Records lifecycle states, last-success timestamps, and error summaries
for unattended background services:
- delivery_monitor
- diagnostic_sender
- daily_mailbox_planner
- founder_resolver
- scheduler
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")


def get_db(db_path: Optional[str] = None) -> sqlite3.Connection:
    p = db_path or os.environ.get("MINDMAXING_DB_PATH") or DEFAULT_DB_PATH
    conn = sqlite3.connect(p, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn


def record_heartbeat_start(service_name: str, db_path: Optional[str] = None):
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        conn = get_db(db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO service_heartbeats (
                service_name, status, started_at, completed_at, error_message, updated_at
            ) VALUES (?, 'RUNNING', ?, NULL, NULL, ?)
            ON CONFLICT(service_name) DO UPDATE SET
                status = 'RUNNING',
                started_at = excluded.started_at,
                completed_at = NULL,
                error_message = NULL,
                updated_at = excluded.updated_at
        """, (service_name, now_iso, now_iso))
        conn.commit()
        conn.close()
    except Exception:
        pass


def record_heartbeat_success(service_name: str, items_processed: int = 0, items_failed: int = 0, db_path: Optional[str] = None):
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        conn = get_db(db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO service_heartbeats (
                service_name, status, completed_at, last_success_at,
                items_processed, items_failed, error_message, updated_at
            ) VALUES (?, 'SUCCESS', ?, ?, ?, ?, NULL, ?)
            ON CONFLICT(service_name) DO UPDATE SET
                status = 'SUCCESS',
                completed_at = excluded.completed_at,
                last_success_at = excluded.last_success_at,
                items_processed = excluded.items_processed,
                items_failed = excluded.items_failed,
                error_message = NULL,
                updated_at = excluded.updated_at
        """, (service_name, now_iso, now_iso, items_processed, items_failed, now_iso))
        conn.commit()
        conn.close()
    except Exception:
        pass


def record_heartbeat_failure(service_name: str, error_message: str, items_processed: int = 0, items_failed: int = 0, db_path: Optional[str] = None):
    now_iso = datetime.now(timezone.utc).isoformat()
    safe_err = str(error_message)[:500]
    try:
        conn = get_db(db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO service_heartbeats (
                service_name, status, completed_at, items_processed, items_failed, error_message, updated_at
            ) VALUES (?, 'FAILED', ?, ?, ?, ?, ?)
            ON CONFLICT(service_name) DO UPDATE SET
                status = 'FAILED',
                completed_at = excluded.completed_at,
                items_processed = excluded.items_processed,
                items_failed = excluded.items_failed,
                error_message = excluded.error_message,
                updated_at = excluded.updated_at
        """, (service_name, now_iso, items_processed, items_failed, safe_err, now_iso))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_service_heartbeats(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        conn = get_db(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='service_heartbeats'")
        if not c.fetchone():
            conn.close()
            return []
        c.execute("""
            SELECT service_name, status, started_at, completed_at, last_success_at,
                   items_processed, items_failed, error_message, updated_at
            FROM service_heartbeats
            ORDER BY service_name ASC
        """)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []
