#!/usr/bin/env python3
"""
Private, durable outreach telemetry client for Mindmaxing.
Records intern commands, draft generation, and explicit send confirmations.
Never equates draft generation with message delivery.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

SKILL_VERSION = "3.0.0"
HOOK_VERSION = "3.0.0"
DEFAULT_CONFIG = Path.home() / ".config/mindmaxing-outreach/config.json"
DEFAULT_OUTBOX = Path.home() / ".local/share/mindmaxing-outreach/outbox.sqlite3"
ASSESSMENT_FIELDS = {
    "platform",
    "target_handle",
    "target_url",
    "qualification_status",
    "qualification_reason",
    "bottleneck_summary",
    "generated_dm",
    "generated_reply",
    "generated_email",
    "generated_whatsapp",
    "skill_version",
}


def normalize_url(value: str) -> str:
    value = value.strip().rstrip("/")
    for suffix in ("/api/v1/telemetry/log", "/api/v1/events"):
        if value.endswith(suffix):
            value = value[: -len(suffix)]
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme not in ("https", "http")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("A valid telemetry base URL is required")
    if parsed.scheme != "https" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Telemetry requires HTTPS except on localhost")
    return value


def load_config(path=None) -> dict:
    path = Path(path or os.environ.get("MM_TELEMETRY_CONFIG", DEFAULT_CONFIG)).expanduser()
    config = {}
    if path.exists():
        if os.name != "nt" and stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise PermissionError("Telemetry config must have mode 0600")
        config = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("Telemetry config must be a JSON object")
    url = os.environ.get("MM_TELEMETRY_URL", config.get("base_url", ""))
    key = os.environ.get("MM_INTERN_KEY", config.get("intern_key", ""))
    if not isinstance(key, str) or not key.strip():
        raise ValueError("MM_INTERN_KEY or a private per-intern config key is required")
    if not isinstance(url, str) or not url.strip():
        raise ValueError("MM_TELEMETRY_URL or a config base_url is required")
    outbox = os.environ.get("MM_OUTBOX_PATH", config.get("outbox_path", str(DEFAULT_OUTBOX)))
    return {
        "base_url": normalize_url(url),
        "intern_key": key.strip(),
        "outbox_path": str(Path(outbox).expanduser()),
    }


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward private intern credentials to a redirect destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TelemetryClient:
    def __init__(self, base_url: str, intern_key: str, outbox_path=DEFAULT_OUTBOX, timeout: float = 5.0):
        self.base_url = normalize_url(base_url)
        if not isinstance(intern_key, str) or not intern_key.strip():
            raise ValueError("A private per-intern key is required")
        self.intern_key = intern_key.strip()
        self.path = Path(outbox_path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Create file with strict mode 0600 before SQLite opens it
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        if os.name != "nt":
            self.path.chmod(0o600)
        self.timeout = timeout
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(
                    invocation_id TEXT PRIMARY KEY,
                    turn_key TEXT UNIQUE NOT NULL,
                    command TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events(
                    event_id TEXT PRIMARY KEY,
                    invocation_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    body TEXT NOT NULL,
                    synced INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT
                );
            """)
            db.execute("INSERT OR IGNORE INTO metadata VALUES (?, ?)", ("device_id", str(uuid.uuid4())))
            self.device_id = db.execute("SELECT value FROM metadata WHERE key=?", ("device_id",)).fetchone()[0]

    @classmethod
    def from_config(cls, path=None, **kwargs):
        return cls(**load_config(path), **kwargs)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        try:
            db.execute("PRAGMA synchronous = FULL;")
            with db:
                yield db
        finally:
            db.close()

    def _enqueue(self, db, invocation_id: str, kind: str, payload: dict, discriminator: str = "") -> str:
        invocation_id = str(uuid.UUID(invocation_id))
        event_id = str(uuid.uuid5(uuid.UUID(invocation_id), kind + ":" + discriminator))
        existing = db.execute("SELECT body FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if existing:
            prev = json.loads(existing[0])
            if prev.get("payload") != payload:
                raise ValueError("Stable event ID already exists with different payload")
            return event_id
        event = {
            "event_id": event_id,
            "invocation_id": invocation_id,
            "kind": kind,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        db.execute(
            "INSERT INTO events(event_id, invocation_id, kind, body) VALUES(?, ?, ?, ?)",
            (event_id, invocation_id, kind, canonical(event)),
        )
        return event_id

    def start_run(self, turn_key: str, command: str) -> str:
        if command not in ("/outreach", "/outbound", "/triage") or not turn_key:
            raise ValueError("An explicit supported command and user turn identity are required")
        invocation_id = str(uuid.uuid5(uuid.UUID(self.device_id), turn_key))
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO runs VALUES(?, ?, ?)", (invocation_id, turn_key, command))
            self._enqueue(
                db,
                invocation_id,
                "COMMAND_USED",
                {
                    "command": command,
                    "skill_version": SKILL_VERSION,
                    "device_id": self.device_id,
                },
            )
        return invocation_id

    def assess(self, invocation_id: str, payload: dict) -> str:
        if not isinstance(payload, dict) or set(payload) - ASSESSMENT_FIELDS:
            raise ValueError("Assessment contains unsupported fields")
        payload = dict(payload)
        payload.setdefault("skill_version", SKILL_VERSION)
        payload.setdefault("target_url", "")
        if payload.get("qualification_status") not in ("QUALIFIED", "DISQUALIFIED", "UNCERTAIN"):
            raise ValueError("A qualification status is required")
        for required in ("platform", "target_handle", "qualification_reason"):
            if not isinstance(payload.get(required), str) or not payload[required].strip():
                raise ValueError("Assessment requires " + required)
        for key, value in payload.items():
            if not isinstance(value, str):
                raise ValueError("Assessment values must be text")
            maximum = {
                "target_handle": 200,
                "target_url": 2000,
                "skill_version": 80,
                "qualification_reason": 4000,
                "bottleneck_summary": 4000,
            }.get(key, 12000)
            if len(value) > maximum:
                raise ValueError("Assessment field is too long: " + key)
        if payload["platform"] not in ("instagram", "x", "threads", "linkedin", "reddit", "email", "website", "google", "whatsapp"):
            raise ValueError("Unsupported assessment platform")
        if not payload["skill_version"].strip():
            raise ValueError("A skill version is required")
        if payload["target_url"]:
            parsed = urllib.parse.urlsplit(payload["target_url"])
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Target URL must be a public HTTP(S) profile or source URL")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM runs WHERE invocation_id = ?", (invocation_id,)).fetchone():
                # Allow recording run if created in CLI directly
                db.execute("INSERT OR IGNORE INTO runs VALUES(?, ?, ?)", (invocation_id, f"direct:{invocation_id}", "/outreach"))
                self._enqueue(
                    db,
                    invocation_id,
                    "COMMAND_USED",
                    {"command": "/outreach", "skill_version": SKILL_VERSION, "device_id": self.device_id},
                )
            disc = hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
            return self._enqueue(db, invocation_id, "DRAFT_GENERATED", payload, disc)

    def report_sent(self, invocation_id: str, notes: str = "") -> str:
        with self.connect() as db:
            inv_uuid = str(uuid.UUID(invocation_id))
            if not db.execute("SELECT 1 FROM runs WHERE invocation_id = ?", (inv_uuid,)).fetchone():
                raise ValueError("Unknown invocation ID; run must exist before reporting send")
            existing = db.execute(
                "SELECT event_id FROM events WHERE invocation_id = ? AND kind = 'SENT_REPORTED';",
                (inv_uuid,),
            ).fetchone()
            if existing:
                return existing[0]
            payload = {"notes": notes[:1000], "device_id": self.device_id}
            return self._enqueue(db, inv_uuid, "SENT_REPORTED", payload)

    def pending_events(self, limit: int = 1000) -> list:
        with self.connect() as db:
            return [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT body FROM events WHERE synced = 0 ORDER BY rowid ASC LIMIT ?",
                    (limit,),
                )
            ]

    def pending_count(self) -> int:
        with self.connect() as db:
            return db.execute("SELECT count(*) FROM events WHERE synced = 0;").fetchone()[0]

    def post(self, path: str, payload: dict) -> dict:
        url = self.base_url + path
        request = urllib.request.Request(
            url,
            data=canonical(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Intern-Key": self.intern_key,
            },
            method="POST",
        )
        with urllib.request.build_opener(NoRedirect).open(request, timeout=self.timeout) as response:
            return json.loads(response.read(65536).decode("utf-8"))

    def sync(self, limit: int = 100, heartbeat: bool = True) -> dict:
        last_error = None
        for event in self.pending_events(limit):
            try:
                # Try standard /api/v1/events first
                try:
                    response = self.post("/api/v1/events", event)
                except urllib.error.HTTPError as he:
                    if he.code == 404:
                        response = self.post("/api/v1/telemetry/log", event)
                    else:
                        raise
                if (
                    response.get("status") != "synced"
                    or response.get("event_id") != event["event_id"]
                    or response.get("invocation_id") != event["invocation_id"]
                ):
                    raise ValueError("Invalid telemetry acknowledgement from server")
                with self.connect() as db:
                    db.execute(
                        "UPDATE events SET synced = 1, attempts = attempts + 1, last_error = NULL WHERE event_id = ?;",
                        (event["event_id"],),
                    )
            except Exception as exc:
                last_error = "HTTP " + str(exc.code) if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__
                with self.connect() as db:
                    db.execute(
                        "UPDATE events SET attempts = attempts + 1, last_error = ? WHERE event_id = ?;",
                        (last_error, event["event_id"]),
                    )
                break  # Stop on failure to preserve FIFO ordering
        pending = self.pending_count()
        if heartbeat:
            try:
                payload = {
                    "device_id": self.device_id,
                    "pending_count": pending,
                    "hook_version": HOOK_VERSION,
                }
                if last_error:
                    payload["last_error"] = last_error
                self.post("/api/v1/sync", payload)
            except Exception as exc:
                if not last_error:
                    last_error = "HTTP " + str(exc.code) if isinstance(exc, urllib.error.HTTPError) else type(exc).__name__
        return {
            "status": "pending-sync" if pending or last_error else "synced",
            "pending_count": pending,
            "last_error": last_error,
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--sync-once", action="store_true", help="Sync pending events and exit")
    action.add_argument("--worker", action="store_true", help="Retry sync periodically until stopped")
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--invocation-id", help="Active invocation ID")
    parser.add_argument("--assessment-json", type=Path, help="Assessment JSON file (- for stdin)")
    parser.add_argument("--report-sent", action="store_true", help="Confirm message was sent for invocation-id")
    parser.add_argument("--notes", default="", help="Optional notes for report-sent")
    parser.add_argument("--handle")
    parser.add_argument("--platform", default="instagram")
    parser.add_argument("--status", choices=["QUALIFIED", "DISQUALIFIED", "UNCERTAIN"], default="UNCERTAIN")
    parser.add_argument("--url", default="")
    parser.add_argument("--bottleneck", default="")
    parser.add_argument("--dm", default="")
    parser.add_argument("--reply", default="")
    parser.add_argument("--email", default="")
    parser.add_argument("--whatsapp", default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)

    try:
        telemetry = TelemetryClient.from_config(args.config)
        if args.worker:
            if args.interval < 10:
                raise ValueError("Worker interval must be at least 10 seconds")
            while True:
                print(json.dumps(telemetry.sync()), flush=True)
                time.sleep(args.interval)
        if args.sync_once:
            result = telemetry.sync()
        elif args.report_sent:
            if not args.invocation_id:
                raise ValueError("--invocation-id is required for --report-sent")
            event_id = telemetry.report_sent(args.invocation_id, notes=args.notes)
            result = dict(telemetry.sync(), event_id=event_id, invocation_id=args.invocation_id, action="SENT_REPORTED")
        else:
            if not args.invocation_id:
                raise ValueError("--invocation-id from the outreach hook is required")
            if args.assessment_json:
                payload = json.load(sys.stdin) if str(args.assessment_json) == "-" else json.loads(args.assessment_json.read_text(encoding="utf-8"))
            else:
                payload = {
                    "platform": args.platform,
                    "target_handle": args.handle,
                    "target_url": args.url,
                    "qualification_status": args.status,
                    "qualification_reason": args.reason,
                    "bottleneck_summary": args.bottleneck,
                    "generated_dm": args.dm,
                    "generated_reply": args.reply,
                    "generated_email": args.email,
                    "generated_whatsapp": args.whatsapp,
                }
            event_id = telemetry.assess(args.invocation_id, payload)
            result = dict(telemetry.sync(), event_id=event_id, invocation_id=args.invocation_id, action="DRAFT_GENERATED")
            result["tracking_path"] = "/records/" + args.invocation_id
            result["tracking_url"] = telemetry.base_url + result["tracking_path"]
        print(json.dumps(result))
        return 0
    except KeyboardInterrupt:
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(
            json.dumps({
                "status": "tracking-failed",
                "error_type": type(exc).__name__,
                "message": "Tracking failed. Check private config, permissions, and invocation ID.",
            }),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
