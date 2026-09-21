#!/usr/bin/env python3
"""
Mindmaxing Daily Diagnostic Sender
Sends one diagnostic message per sending mailbox per day, rotating evenly through the 8 test Gmail accounts.
Uses the production sending path (smtp.ionos.com:587 TLS) and dual-part MIME format.
Content contains NO prospect information.
Transactionally reserves quota via volume_controller.
Records message record in messages table with purpose='test' and smtp_status='accepted'.
"""

import os
import sys
import json
import uuid
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

import volume_controller

BASE_DIR = "/root/outbound"
MAILBOXES_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
TEST_INBOXES_FILE = os.path.join(BASE_DIR, "config", "test_inboxes.json")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "config", "credentials.env")
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

def send_diagnostic(mailbox_info: dict, target_gmail: dict) -> tuple[bool, str]:
    sender_email = mailbox_info["email"]
    sender_domain = mailbox_info["domain"]
    sender_name = mailbox_info.get("name", "Aryan Panchal")
    recipient_email = target_gmail["email"]

    # 1. Transactionally reserve daily diagnostic quota
    reserved, reason = volume_controller.reserve_quota(sender_email, purpose="test")
    if not reserved:
        return False, f"Quota skipped: {reason}"

    # 2. Build message with production format (Dual-part MIME, strict CRLF)
    trace_id = str(uuid.uuid4())[:8]
    subject = f"Diagnostic Telemetry Ping #{trace_id}"
    plain_body = (
        f"Automated diagnostic verification ping from {sender_email}.\r\n\r\n"
        f"Trace ID: {trace_id}\r\n"
        f"Target Inbox: {recipient_email}\r\n"
        f"Timestamp: {datetime.now(timezone.utc).isoformat()}\r\n\r\n"
        "This is an automated production telemetry ping to inspect SPF, DKIM, DMARC, and mailbox placement.\r\n"
    )
    html_body = (
        "<!DOCTYPE html><html><body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:14px;color:#222;line-height:1.5;'>"
        f"<p>Automated diagnostic verification ping from <strong>{sender_email}</strong>.</p>"
        f"<p style='color:#666;'>Trace ID: <code>{trace_id}</code><br>Target Inbox: {recipient_email}<br>Timestamp: {datetime.now(timezone.utc).isoformat()}</p>"
        "<p>This is an automated production telemetry ping to inspect SPF, DKIM, DMARC, and mailbox placement.</p>"
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
            auth_spf, auth_dkim, auth_dmarc, last_event_at, notes
        ) VALUES (?, ?, ?, ?, 'gmail.com', 'gmail', 'test', NULL, NULL, ?, ?, 'accepted', 250, 'OK', 'accepted', 'unknown', 'unknown', 'unknown', ?, ?)
        """, (
            msg_id, sender_email, sender_domain, recipient_email, sent_at,
            sent_date, sent_at, f"Diagnostic trace {trace_id}"
        ))

        # Log event
        c.execute("""
        INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
        VALUES (?, 'smtp_accepted', ?, ?, 'OUTBOX', 'SMTP 250 OK accepted by IONOS')
        """, (msg_id, sent_at, sender_email))

        conn.close()
        return True, f"Sent successfully ({msg_id}) to {recipient_email}"

    except Exception as e:
        # Rollback quota reservation
        volume_controller.rollback_quota(sender_email, purpose="test")
        
        # Record failed attempt
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        c.execute("""
        INSERT INTO messages (
            message_id, sender_email, sender_domain, recipient_email, recipient_domain,
            recipient_provider, purpose, campaign_touch, prospect_domain, sent_at,
            sent_date, smtp_status, smtp_code, smtp_response, delivery_state,
            last_event_at, notes
        ) VALUES (?, ?, ?, ?, 'gmail.com', 'gmail', 'test', NULL, NULL, ?, ?, 'temp_failure', 0, ?, 'unknown', ?, 'Diagnostic SMTP error')
        """, (
            msg_id, sender_email, sender_domain, recipient_email, sent_at,
            sent_date, str(e), sent_at
        ))
        conn.close()
        return False, f"SMTP Error on {sender_email}: {e}"

def run_diagnostic_rotation(limit: int = None):
    mailboxes = load_mailboxes()
    test_inboxes = load_test_inboxes()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting diagnostic rotation for {len(mailboxes)} mailboxes across {len(test_inboxes)} Gmail inboxes...")
    
    successful = 0
    skipped = 0
    errors = 0

    for idx, m in enumerate(mailboxes):
        if limit and idx >= limit:
            break
        # Rotate evenly through test Gmails
        target_gmail = test_inboxes[idx % len(test_inboxes)]
        ok, reason = send_diagnostic(m, target_gmail)
        if ok:
            successful += 1
            print(f"  [OK] {m['email']} -> {target_gmail['email']}: {reason}")
        elif "Quota skipped" in reason:
            skipped += 1
            print(f"  [SKIP] {m['email']}: {reason}")
        else:
            errors += 1
            print(f"  [ERROR] {m['email']}: {reason}")

    print(f"Diagnostic rotation complete: {successful} sent, {skipped} skipped (limit reached/paused), {errors} errors.")

if __name__ == "__main__":
    max_send = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_diagnostic_rotation(max_send)
