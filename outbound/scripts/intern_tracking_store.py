#!/usr/bin/env python3
"""
Mindmaxing Intern Tracking Store
Append-only database ledger for tracking intern outreach activity.
Enforces SHA-256 token hashing, strict event separation:
- COMMAND_USED: Intern invoked /outreach, /outbound, or /triage
- DRAFT_GENERATED: Assistant generated copy for a prospect
- SENT_REPORTED: Intern explicitly confirmed manual dispatch
Never equates draft generation with message delivery.
"""

import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
from contextlib import contextmanager, closing
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def hash_token(token: str) -> str:
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()

def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

class StoreError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message

class TrackingStore:
    def __init__(self, db_path: str):
        self.path = Path(db_path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(str(self.path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.connect() as c:
            c.execute("PRAGMA journal_mode = WAL;")
            c.executescript("""
            CREATE TABLE IF NOT EXISTS intern_accounts (
                intern_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'intern',
                token_hash TEXT UNIQUE NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                daily_target INTEGER NOT NULL DEFAULT 100,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS intern_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                invocation_id TEXT NOT NULL,
                intern_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                occurred_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                FOREIGN KEY (intern_id) REFERENCES intern_accounts(intern_id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_invocation ON intern_events(invocation_id, seq);
            CREATE INDEX IF NOT EXISTS idx_events_owner ON intern_events(intern_id, kind);
            CREATE INDEX IF NOT EXISTS idx_events_kind ON intern_events(kind);

            CREATE TABLE IF NOT EXISTS intern_devices (
                intern_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                pending_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                hook_version TEXT,
                last_sync TEXT NOT NULL,
                PRIMARY KEY (intern_id, device_id),
                FOREIGN KEY (intern_id) REFERENCES intern_accounts(intern_id)
            );

            CREATE TABLE IF NOT EXISTS legacy_unverified (
                legacy_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'LEGACY_UNVERIFIED'
            );
            """)

            # Safe migration for existing tables
            cols = [r[1] for r in c.execute("PRAGMA table_info(intern_accounts);").fetchall()]
            if "token_hash" not in cols:
                c.execute("ALTER TABLE intern_accounts ADD COLUMN token_hash TEXT;")
            if "role" not in cols:
                c.execute("ALTER TABLE intern_accounts ADD COLUMN role TEXT NOT NULL DEFAULT 'intern';")
            if "daily_target" not in cols:
                if "daily_quota" in cols:
                    c.execute("ALTER TABLE intern_accounts ADD COLUMN daily_target INTEGER NOT NULL DEFAULT 100;")
                    c.execute("UPDATE intern_accounts SET daily_target = daily_quota;")
                else:
                    c.execute("ALTER TABLE intern_accounts ADD COLUMN daily_target INTEGER NOT NULL DEFAULT 100;")
            c.execute("UPDATE intern_accounts SET active = 0 WHERE intern_id = 'intern_1' AND (token_hash IS NULL OR token_hash = '');")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_intern_token_hash ON intern_accounts(token_hash) WHERE token_hash IS NOT NULL;")

    def create_account(self, intern_id: str, name: str, role: str = "intern", token: str = None, daily_target: int = 100) -> str:
        raw_token = token or secrets.token_urlsafe(32)
        thash = hash_token(raw_token)
        with self.connect() as c:
            cols = [r[1] for r in c.execute("PRAGMA table_info(intern_accounts);").fetchall()]
            if "api_key" in cols:
                placeholder = f"[HASHED_{thash[:16]}]"
                c.execute("""
                INSERT INTO intern_accounts (intern_id, name, role, token_hash, api_key, active, daily_target, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(intern_id) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    token_hash = excluded.token_hash,
                    api_key = excluded.api_key,
                    active = 1,
                    daily_target = excluded.daily_target;
                """, (intern_id.strip(), name.strip(), role.strip(), thash, placeholder, daily_target, now_utc()))
            else:
                c.execute("""
                INSERT INTO intern_accounts (intern_id, name, role, token_hash, active, daily_target, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(intern_id) DO UPDATE SET
                    name = excluded.name,
                    role = excluded.role,
                    token_hash = excluded.token_hash,
                    active = 1,
                    daily_target = excluded.daily_target;
                """, (intern_id.strip(), name.strip(), role.strip(), thash, daily_target, now_utc()))
        return raw_token

    def set_active(self, intern_id: str, active: bool):
        with self.connect() as c:
            c.execute("UPDATE intern_accounts SET active = ? WHERE intern_id = ?;", (1 if active else 0, intern_id))

    def authenticate(self, token: str):
        if not token or not isinstance(token, str):
            return None
        token = token.strip()
        founder_key = os.environ.get("MM_FOUNDER_KEY", "mm_founder_secure_2026").strip()
        if token == founder_key:
            return {"intern_id": "aryan", "name": "Aryan Panchal", "role": "admin", "daily_target": 0, "active": 1}
        thash = hash_token(token)
        with self.connect() as c:
            row = c.execute("""
            SELECT intern_id, name, role, daily_target, active
            FROM intern_accounts
            WHERE token_hash = ? AND active = 1;
            """, (thash,)).fetchone()
            return dict(row) if row else None

    def add_event(self, actor: dict, event_id: str, invocation_id: str, kind: str, occurred_at: str, payload: dict):
        allowed_kinds = ("COMMAND_USED", "DRAFT_GENERATED", "SENT_REPORTED")
        if kind not in allowed_kinds:
            raise StoreError(400, f"Unsupported event kind: {kind}. Must be one of {allowed_kinds}")

        content = canonical_json(payload)
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE;")
            # 1. Idempotency Check: check if event_id already exists
            prev = c.execute("SELECT * FROM intern_events WHERE event_id = ?;", (event_id,)).fetchone()
            if prev:
                if (prev["intern_id"], prev["invocation_id"], prev["kind"], prev["payload"]) == (actor["intern_id"], invocation_id, kind, content):
                    return {"status": "synced", "event_id": event_id, "invocation_id": invocation_id, "replay": True}
                raise StoreError(409, "Event ID already used for different content")

            # 2. Ownership & Prerequisite Validation
            start = c.execute("SELECT * FROM intern_events WHERE invocation_id = ? AND kind = 'COMMAND_USED';", (invocation_id,)).fetchone()
            if kind == "COMMAND_USED":
                if start:
                    if start["intern_id"] != actor["intern_id"] and actor["role"] != "admin":
                        raise StoreError(403, "Run ID belongs to another intern")
                    return {"status": "synced", "event_id": event_id, "invocation_id": invocation_id, "replay": True}
            else:
                # DRAFT_GENERATED or SENT_REPORTED requires COMMAND_USED first
                if not start:
                    raise StoreError(404, f"Run ID {invocation_id} not found. COMMAND_USED must precede {kind}")
                if start["intern_id"] != actor["intern_id"] and actor["role"] != "admin":
                    raise StoreError(403, "Run ID belongs to another intern")

            # 3. Confirmation Deduplication: SENT_REPORTED can only be recorded once per run
            if kind == "SENT_REPORTED":
                existing_send = c.execute("SELECT * FROM intern_events WHERE invocation_id = ? AND kind = 'SENT_REPORTED';", (invocation_id,)).fetchone()
                if existing_send:
                    # Repeating confirmation returns existing without counting duplicate
                    return {"status": "synced", "event_id": existing_send["event_id"], "invocation_id": invocation_id, "duplicate_confirmation": True}

            # 4. Insert new event
            c.execute("""
            INSERT INTO intern_events (event_id, invocation_id, intern_id, kind, occurred_at, received_at, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (event_id, invocation_id, actor["intern_id"], kind, occurred_at, now_utc(), content))

        return {"status": "synced", "event_id": event_id, "invocation_id": invocation_id}

    def update_device_sync(self, actor: dict, device_id: str, pending_count: int, hook_version: str = "3.0.0", last_error: str = None):
        with self.connect() as c:
            c.execute("""
            INSERT INTO intern_devices (intern_id, device_id, pending_count, last_error, hook_version, last_sync)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(intern_id, device_id) DO UPDATE SET
                pending_count = excluded.pending_count,
                last_error = excluded.last_error,
                hook_version = excluded.hook_version,
                last_sync = excluded.last_sync;
            """, (actor["intern_id"], device_id, pending_count, last_error, hook_version, now_utc()))

    def get_runs(self, actor: dict, limit: int = 100):
        with self.connect() as c:
            query = """
            SELECT e.seq, e.event_id, e.invocation_id, e.intern_id, a.name as intern_name,
                   e.kind, e.occurred_at, e.received_at, e.payload
            FROM intern_events e
            JOIN intern_accounts a ON e.intern_id = a.intern_id
            """
            params = []
            if actor.get("role") != "admin":
                query += " WHERE e.intern_id = ?"
                params.append(actor["intern_id"])
            query += " ORDER BY e.seq ASC;"
            rows = c.execute(query, params).fetchall()

        runs = {}
        for r in rows:
            inv = r["invocation_id"]
            if inv not in runs:
                runs[inv] = {
                    "run_id": inv,
                    "intern_id": r["intern_id"],
                    "intern_name": r["intern_name"],
                    "started_at": r["occurred_at"],
                    "received_at": r["received_at"],
                    "command": None,
                    "draft": None,
                    "sent_reported": False,
                    "sent_at": None,
                    "status": "COMMAND_USED",
                    "events": []
                }
            run = runs[inv]
            payload = json.loads(r["payload"])
            run["events"].append({
                "kind": r["kind"],
                "occurred_at": r["occurred_at"],
                "received_at": r["received_at"],
                "event_id": r["event_id"]
            })
            if r["kind"] == "COMMAND_USED":
                run["command"] = payload.get("command")
            elif r["kind"] == "DRAFT_GENERATED":
                run["draft"] = payload
                if not run["sent_reported"]:
                    run["status"] = "DRAFT_GENERATED"
            elif r["kind"] == "SENT_REPORTED":
                run["sent_reported"] = True
                run["sent_at"] = r["occurred_at"]
                run["status"] = "SENT_REPORTED"

        run_list = list(runs.values())
        run_list.reverse()
        return run_list[:limit]

    def get_kpi_summary(self, actor: dict, date_str: str = None):
        target_date = date_str or datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
        with self.connect() as c:
            if actor.get("role") == "admin":
                accounts = [dict(r) for r in c.execute("SELECT intern_id, name, daily_target, active FROM intern_accounts WHERE role = 'intern';").fetchall()]
            else:
                accounts = [dict(r) for r in c.execute("SELECT intern_id, name, daily_target, active FROM intern_accounts WHERE intern_id = ?;", (actor["intern_id"],)).fetchall()]

            devices = [dict(r) for r in c.execute("SELECT * FROM intern_devices;").fetchall()]

        all_runs = self.get_runs(actor, limit=5000)

        def is_target_day(iso_ts):
            if not iso_ts:
                return False
            dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Kolkata"))
            return dt.date().isoformat() == target_date

        summary = []
        for acc in accounts:
            iid = acc["intern_id"]
            intern_runs = [r for r in all_runs if r["intern_id"] == iid]
            day_runs = [r for r in intern_runs if is_target_day(r["started_at"])]

            commands_count = len(day_runs)
            drafts_count = sum(1 for r in day_runs if r["draft"] is not None)
            sends_count = sum(1 for r in intern_runs if r["sent_reported"] and is_target_day(r["sent_at"]))

            devs = [d for d in devices if d["intern_id"] == iid]
            pending_sync = sum(d["pending_count"] for d in devs)
            last_sync = max([d["last_sync"] for d in devs], default=None)
            has_error = any(bool(d["last_error"]) for d in devs)

            summary.append({
                "date": target_date,
                "intern_id": iid,
                "name": acc["name"],
                "daily_target": acc["daily_target"],
                "active": bool(acc["active"]),
                "commands_used": commands_count,
                "drafts_generated": drafts_count,
                "sends_reported": sends_count,
                "pending_sync": pending_sync,
                "last_sync": last_sync,
                "has_sync_error": has_error
            })

        return {"date": target_date, "summary": summary}
