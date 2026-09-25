#!/usr/bin/env python3
"""
Mindmaxing Daily Diagnostic Sender v2.1 (Task D)
Sends one diagnostic message per sending mailbox per day, rotating evenly through the 8 test Gmail accounts.
Uses the production sending path (smtp.ionos.com:587 TLS) and dual-part MIME format.
Content contains NO prospect information.
Transactionally reserves quota via volume_controller.
Records message record in messages table with purpose='test' and smtp_status='accepted'.
Re-uses reservations on duplicate runs and derives seed deterministically from IST budget period.
"""

import os
import sys
import json
import uuid
import smtplib
import time
import random
import fcntl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

import volume_controller

try:
    from service_heartbeats import record_heartbeat_start, record_heartbeat_success, record_heartbeat_failure
except ImportError:
    try:
        from outbound.scripts.service_heartbeats import record_heartbeat_start, record_heartbeat_success, record_heartbeat_failure
    except ImportError:
        record_heartbeat_start = lambda s, **kw: None
        record_heartbeat_success = lambda s, **kw: None
        record_heartbeat_failure = lambda s, **kw: None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
MAILBOXES_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
TEST_INBOXES_FILE = os.path.join(BASE_DIR, "config", "test_inboxes.json")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "config", "credentials.env")
LOCK_FILE = "/tmp/mindmaxing_diagnostic_sender.lock"
SMTP_HOST = "smtp.ionos.com"
SMTP_PORT = 587


def get_ionos_password():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            for line in f:
                if line.startswith("IONOS_PASSWORD="):
                    return line.strip().split("=", 1)[1].strip().strip('"\'')
    return os.environ.get("IONOS_PASSWORD", "")


def load_mailboxes():
    with open(MAILBOXES_FILE, "r") as f:
        return json.load(f)


def load_test_inboxes():
    with open(TEST_INBOXES_FILE, "r") as f:
        return json.load(f)


def send_diagnostic(mailbox_info: dict, target_gmail: dict, period_id: str = None) -> tuple[bool, str]:
    sender_email = mailbox_info["email"]
    sender_domain = mailbox_info["domain"]
    sender_name = mailbox_info.get("name", "Aryan Panchal")
    recipient_email = target_gmail["email"]

    if not period_id:
        period_id = volume_controller.get_current_period_id()

    # 1. Check existing reservation for this mailbox and period (Task D: reuse reservation on duplicate run)
    res_id = None
    conn = volume_controller.get_db_connection()
    c = conn.cursor()
    c.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='quota_reservations'
    """)
    if c.fetchone():
        c.execute("""
            SELECT reservation_id, status FROM quota_reservations
            WHERE mailbox = ? AND period_id = ? AND purpose = 'test'
            ORDER BY created_at DESC LIMIT 1
        """, (sender_email, period_id))
        existing_res = c.fetchone()
        if existing_res:
            if existing_res["status"] == "ACCEPTED":
                conn.close()
                return False, f"Quota skipped: Diagnostic already completed for period {period_id} (res={existing_res['reservation_id']})"
            elif existing_res["status"] == "RESERVED":
                res_id = existing_res["reservation_id"]
    conn.close()

    if not res_id:
        reserved, reason = volume_controller.reserve_quota(sender_email, purpose="test", period_id=period_id)
        if not reserved:
            return False, f"Quota skipped: {reason}"
        res_id = reason.split(": ")[-1].strip() if "res_" in reason else None

    # 2. Build message with production format (Dual-part MIME, strict CRLF)
    trace_id = str(uuid.uuid4())[:8]
    # Human-sounding diagnostic templates (rotate by trace_id hash)
    _DIAG_TEMPLATES = [
        ("quick note", "Hey — just checking if this comes through on your end. Let me know!"),
        ("can you see this?", "Testing something on my side. Did this land in your inbox?"),
        ("checking in", "Hey, wanted to make sure emails are going through. Ignore this one!"),
        ("test", "Quick test — checking email delivery. All good if you see this."),
        ("inbox check", "Making sure these are landing. Talk soon!"),
        ("hey", "Just a quick ping to make sure everything's working. Disregard!"),
        ("following up", "Checking that my emails are coming through properly. Thanks!"),
        ("real quick", "Hey — testing my email setup. You can ignore this one."),
    ]
    idx = hash(trace_id) % len(_DIAG_TEMPLATES)
    subject, plain_body = _DIAG_TEMPLATES[idx]
    html_body = (
        "<!DOCTYPE html><html><body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:14px;color:#222;line-height:1.5;'>"
        f"<p>{plain_body}</p>"
        "</body></html>"
    )

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg_id = make_msgid(domain=sender_domain)
    msg["Message-ID"] = msg_id
    msg["X-Mindmaxing-Purpose"] = "diagnostic-test"
    msg["X-Mindmaxing-Trace"] = trace_id

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    sent_at = datetime.now(timezone.utc).isoformat()
    sent_date = volume_controller.get_utc_date_str()
    ionos_pwd = get_ionos_password()

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25)
        server.starttls()
        server.login(sender_email, ionos_pwd)
        refusals = server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        if refusals:
            raise Exception(f"Recipient refused by server: {refusals}")
        
        # Record into messages table as accepted
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        c.execute("""
        INSERT INTO messages (
            message_id, sender_email, sender_domain, recipient_email, recipient_domain,
            recipient_provider, purpose, campaign_touch, prospect_domain, sent_at,
            sent_date, smtp_status, smtp_code, smtp_response, delivery_state,
            auth_spf, auth_dkim, auth_dmarc, last_event_at, notes, period_id
        ) VALUES (?, ?, ?, ?, 'gmail.com', 'gmail', 'test', NULL, NULL, ?, ?, 'accepted', 250, 'OK', 'accepted', 'unknown', 'unknown', 'unknown', ?, ?, ?)
        """, (
            msg_id, sender_email, sender_domain, recipient_email, sent_at,
            sent_date, sent_at, f"Diagnostic trace {trace_id}", period_id
        ))

        # Log event
        c.execute("""
        INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
        VALUES (?, 'smtp_accepted', ?, ?, 'OUTBOX', 'SMTP 250 OK accepted by IONOS')
        """, (msg_id, sent_at, sender_email))

        # Update reservation status to ACCEPTED
        if res_id:
            c.execute("""
                UPDATE quota_reservations
                SET status = 'ACCEPTED', message_id = ?, updated_at = ?
                WHERE reservation_id = ?
            """, (msg_id, sent_at, res_id))

        conn.commit()
        conn.close()
        return True, f"Sent successfully ({msg_id}) to {recipient_email}"

    except Exception as e:
        # Rollback quota reservation
        volume_controller.rollback_quota(sender_email, purpose="test", period_id=period_id, reservation_id=res_id)
        
        # Record failed attempt
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        c.execute("""
        INSERT INTO messages (
            message_id, sender_email, sender_domain, recipient_email, recipient_domain,
            recipient_provider, purpose, campaign_touch, prospect_domain, sent_at,
            sent_date, smtp_status, smtp_code, smtp_response, delivery_state,
            last_event_at, notes, period_id
        ) VALUES (?, ?, ?, ?, 'gmail.com', 'gmail', 'test', NULL, NULL, ?, ?, 'temp_failure', 0, ?, 'unknown', ?, 'Diagnostic SMTP error', ?)
        """, (
            msg_id, sender_email, sender_domain, recipient_email, sent_at,
            sent_date, str(e), sent_at, period_id
        ))
        conn.commit()
        conn.close()
        return False, f"SMTP Error on {sender_email}: {e}"


def run_diagnostic_rotation(limit: int = None):
    lock_fd = None
    try:
        lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (IOError, BlockingIOError):
        print(f"[{datetime.now(timezone.utc).isoformat()}] Another diagnostic sender run is currently active. Exiting.")
        if lock_fd:
            try:
                lock_fd.close()
            except Exception:
                pass
        return

    record_heartbeat_start("diagnostic_sender")

    try:
        mailboxes = load_mailboxes()
        test_inboxes = load_test_inboxes()
        print(f"[{datetime.now(timezone.utc).isoformat()}] Starting diagnostic rotation for {len(mailboxes)} mailboxes across {len(test_inboxes)} Gmail inboxes...")
        
        successful = 0
        skipped = 0
        errors = 0

        if not test_inboxes:
            print(f"[{datetime.now(timezone.utc).isoformat()}] HOLD: Zero test Gmail inboxes configured. Skipping diagnostic rotation.")
            record_heartbeat_failure("diagnostic_sender", "Zero test Gmail inboxes configured")
            return

        period_id = volume_controller.get_current_period_id()
        date_label = period_id.replace("-IST", "")
        try:
            dt_period = datetime.strptime(date_label, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            period_days = int(dt_period.timestamp() // 86400)
        except Exception:
            period_days = int(datetime.now(timezone.utc).timestamp() // 86400)

        for idx, m in enumerate(mailboxes):
            if limit and idx >= limit:
                break
            # Rotate evenly through test Gmails across days matching planner
            target_gmail = test_inboxes[(idx + period_days) % len(test_inboxes)]
            ok, reason = send_diagnostic(m, target_gmail, period_id=period_id)
            if ok:
                successful += 1
                print(f"  [OK] {m['email']} -> {target_gmail['email']}: {reason}")
                # Pacing delay between sends to prevent bulk rate-limiting on test Gmail seeds
                if idx < len(mailboxes) - 1 and (limit is None or idx < limit - 1):
                    delay = random.uniform(12, 20)
                    time.sleep(delay)
            elif "Quota skipped" in reason:
                skipped += 1
                print(f"  [SKIP] {m['email']}: {reason}")
            else:
                errors += 1
                print(f"  [ERROR] {m['email']}: {reason}")

        print(f"Diagnostic rotation complete: {successful} sent, {skipped} skipped (limit reached/paused), {errors} errors.")
        record_heartbeat_success("diagnostic_sender", items_processed=successful, items_failed=errors)

    except Exception as e:
        record_heartbeat_failure("diagnostic_sender", str(e))
        raise e
    finally:
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
            except Exception:
                pass


if __name__ == "__main__":
    max_send = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_diagnostic_rotation(max_send)
