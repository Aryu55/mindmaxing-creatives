#!/usr/bin/env python3
"""
Mindmaxing Delivery Monitor & IMAP Diagnostic Inspector
Polls:
1. 25 sending mailboxes on IONOS (every 10m):
   - Scans INBOX and Spam/Junk for bounce reports (mailer-daemon, multipart/report) and replies.
   - Matches bounces/replies to messages table via Message-ID / In-Reply-To / recipient.
   - Immediately suppresses invalid recipients.
2. 8 test Gmail inboxes (every 10m):
   - Strict read-only access (readonly=True, BODY.PEEK[]) preserving unread status.
   - Checks INBOX, [Gmail]/Spam, and Gmail labels (X-GM-LABELS) for Promotions.
   - Parses Gmail Authentication-Results header for SPF, DKIM, and DMARC passes.
   - Automatically pauses mailbox if diagnostic lands in Spam.
   - Automatically pauses domain if SPF/DKIM/DMARC fails.
Persists collector health and polling cursors in collector_health table.
"""

import os
import re
import json
import imaplib
import email
from email import policy
from datetime import datetime, timezone, timedelta

import volume_controller

BASE_DIR = "/root/outbound"
MAILBOXES_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
TEST_INBOXES_FILE = os.path.join(BASE_DIR, "config", "test_inboxes.json")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "config", "credentials.env")
IONOS_IMAP_HOST = "imap.ionos.com"
GMAIL_IMAP_HOST = "imap.gmail.com"

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

def parse_auth_results(auth_header: str) -> tuple[str, str, str]:
    """Parses Gmail Authentication-Results header for spf, dkim, dmarc."""
    if not auth_header:
        return "unknown", "unknown", "unknown"
    
    header_low = auth_header.lower()
    
    spf = "unknown"
    if "spf=pass" in header_low:
        spf = "pass"
    elif any(s in header_low for s in ["spf=fail", "spf=softfail"]):
        spf = "fail"
    elif "spf=neutral" in header_low:
        spf = "neutral"

    dkim = "unknown"
    if "dkim=pass" in header_low:
        dkim = "pass"
    elif "dkim=fail" in header_low:
        dkim = "fail"

    dmarc = "unknown"
    if "dmarc=pass" in header_low:
        dmarc = "pass"
    elif "dmarc=fail" in header_low:
        dmarc = "fail"

    return spf, dkim, dmarc

def update_collector_health(mailbox: str, mailbox_type: str, status: str, error_msg: str = None, scanned_cnt: int = 0):
    conn = volume_controller.get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    last_success = now_iso if status == "healthy" else None
    c.execute("""
    INSERT INTO collector_health (mailbox, mailbox_type, last_scan_at, status, error_message, messages_scanned, last_success_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(mailbox) DO UPDATE SET
        last_scan_at = excluded.last_scan_at,
        status = excluded.status,
        error_message = excluded.error_message,
        messages_scanned = messages_scanned + excluded.messages_scanned,
        last_success_at = COALESCE(excluded.last_success_at, collector_health.last_success_at)
    """, (mailbox, mailbox_type, now_iso, status, error_msg, scanned_cnt, last_success))
    conn.close()

def poll_ionos_mailbox(mailbox_info: dict):
    """Scans sending mailbox for bounce reports and human replies."""
    email_addr = mailbox_info["email"]
    ionos_pwd = get_ionos_password()
    scanned_cnt = 0

    try:
        mail = imaplib.IMAP4_SSL(IONOS_IMAP_HOST, 993, timeout=20)
        mail.login(email_addr, ionos_pwd)
    except Exception as e:
        update_collector_health(email_addr, "sender", "error", f"IMAP Login Failed: {str(e)}")
        return

    folders_to_check = ["INBOX"]
    # Check if Spam exists
    status, folder_list = mail.list()
    if status == "OK":
        for f in folder_list:
            decoded = f.decode("utf-8", errors="ignore")
            if any(s in decoded.lower() for s in ["spam", "junk"]):
                m = re.search(r'"([^"]+)"$', decoded) or re.search(r'([^\s]+)$', decoded)
                if m and m.group(1) not in folders_to_check:
                    folders_to_check.append(m.group(1))

    conn = volume_controller.get_db_connection()
    c = conn.cursor()

    try:
        for folder in folders_to_check:
            res, _ = mail.select(folder, readonly=True)
            if res != "OK":
                continue

            # Fetch messages from the last 7 days
            since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")
            res, data = mail.search(None, f'(SINCE "{since_date}")')
            if res != "OK" or not data[0]:
                continue

            msg_ids = data[0].split()
            scanned_cnt += len(msg_ids)

            for mid in msg_ids[-30:]: # Inspect last 30 messages in folder
                # Use PEEK so unread status is preserved
                res, msg_data = mail.fetch(mid, "(BODY.PEEK[])")
                if res != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_bytes = msg_data[0][1]
                msg = email.message_from_bytes(raw_bytes, policy=policy.default)
                from_hdr = str(msg.get("From", "")).lower()
                subj_hdr = str(msg.get("Subject", ""))
                in_reply_to = str(msg.get("In-Reply-To", "")).strip()
                now_iso = datetime.now(timezone.utc).isoformat()

                # Check 1: Hard Bounce Report (Mailer-Daemon / Delivery Status)
                is_bounce = any(b in from_hdr for b in ["mailer-daemon", "postmaster"]) or "failure notice" in subj_hdr.lower()
                if is_bounce:
                    body_text = str(raw_bytes[:4000], errors="ignore")
                    # Try to extract the failed recipient
                    recip_match = re.search(r"(?:for|to)[:\s]+<([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>", body_text, re.IGNORECASE)
                    failed_recip = recip_match.group(1) if recip_match else ""
                    
                    # Try to find corresponding message
                    c.execute("""
                    SELECT message_id, sender_domain, recipient_email FROM messages 
                    WHERE (recipient_email = ? OR notes LIKE ?) AND purpose = 'campaign'
                    ORDER BY sent_at DESC LIMIT 1
                    """, (failed_recip, f"%{failed_recip}%"))
                    matched = c.fetchone()

                    if failed_recip:
                        volume_controller.suppress_recipient(failed_recip, "Hard bounce reported by mailer-daemon", matched["message_id"] if matched else None)

                    if matched:
                        c.execute("""
                        UPDATE messages SET delivery_state = 'bounced', smtp_status = 'perm_failure', last_event_at = ?, notes = notes || ' | Bounced by mailer-daemon'
                        WHERE message_id = ?
                        """, (now_iso, matched["message_id"]))

                        c.execute("""
                        INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                        VALUES (?, 'bounce_report', ?, ?, ?, ?)
                        """, (matched["message_id"], now_iso, email_addr, folder, f"Mailer-daemon bounce for {failed_recip}"))

                # Check 2: Prospect Reply
                elif in_reply_to:
                    c.execute("SELECT message_id, delivery_state FROM messages WHERE message_id = ?", (in_reply_to,))
                    orig = c.fetchone()
                    if orig and orig["delivery_state"] not in ("replied", "auto_response"):
                        # Distinguish auto-deflection from human reply
                        body_snippet = str(raw_bytes[:2000], errors="ignore").lower()
                        is_auto = any(w in body_snippet for w in ["ticket", "auto-reply", "automated", "mimir", "zendesk", "gorgias", "do not reply"])
                        new_state = "auto_response" if is_auto else "replied"
                        
                        c.execute("""
                        UPDATE messages SET delivery_state = ?, last_event_at = ? WHERE message_id = ?
                        """, (new_state, now_iso, in_reply_to))

                        c.execute("""
                        INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (in_reply_to, f"reply_{new_state}", now_iso, email_addr, folder, f"From: {from_hdr} | Subj: {subj_hdr}"))

        mail.close()
        mail.logout()
        update_collector_health(email_addr, "sender", "healthy", None, scanned_cnt)

    except Exception as e:
        update_collector_health(email_addr, "sender", "error", f"Scan error: {str(e)}", scanned_cnt)
    finally:
        conn.close()

def poll_gmail_test_inbox(gmail_info: dict):
    """Scans test Gmail inbox in strict read-only mode to verify diagnostic placement and auth headers."""
    gmail_addr = gmail_info["email"]
    app_pwd = gmail_info["app_password"]
    scanned_cnt = 0

    try:
        mail = imaplib.IMAP4_SSL(GMAIL_IMAP_HOST, 993, timeout=20)
        mail.login(gmail_addr, app_pwd)
    except Exception as e:
        update_collector_health(gmail_addr, "test_inbox", "error", f"Gmail IMAP login failed: {str(e)}")
        return

    # Check INBOX and [Gmail]/Spam
    folders = ["INBOX", "[Gmail]/Spam"]
    conn = volume_controller.get_db_connection()
    c = conn.cursor()

    try:
        for folder in folders:
            res, _ = mail.select(f'"{folder}"', readonly=True) # Strict read-only mode!
            if res != "OK":
                continue

            # Search messages with Mindmaxing header or diagnostic subject
            since_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%d-%b-%Y")
            res, data = mail.search(None, f'(SINCE "{since_date}")')
            if res != "OK" or not data[0]:
                continue

            msg_ids = data[0].split()
            scanned_cnt += len(msg_ids)

            for mid in msg_ids[-30:]:
                # PEEK preserves unread status
                res, msg_data = mail.fetch(mid, "(BODY.PEEK[] X-GM-LABELS)")
                if res != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_bytes = msg_data[0][1]
                labels_str = str(msg_data[0][0]) if len(msg_data[0]) > 0 else ""
                
                msg = email.message_from_bytes(raw_bytes, policy=policy.default)
                subj = str(msg.get("Subject", ""))
                msg_id_header = str(msg.get("Message-ID", "")).strip()
                trace_id = str(msg.get("X-Mindmaxing-Trace", "")).strip()
                auth_results = str(msg.get("Authentication-Results", ""))
                from_addr = str(msg.get("From", "")).lower()

                # Identify if this is our diagnostic test
                if "Diagnostic Telemetry Ping" in subj or "diagnostic-test" in str(msg.get("X-Mindmaxing-Purpose", "")):
                    # Extract sender email
                    sender_match = re.search(r"([a-zA-Z0-9_.+-]+@mindmaxing\.[a-z]+)", from_addr)
                    sender_email = sender_match.group(1) if sender_match else ""
                    sender_domain = sender_email.split("@")[-1] if sender_email else ""

                    # Determine placement
                    if "spam" in folder.lower():
                        placement = "spam"
                    elif "promotions" in labels_str.lower() or "promotions" in folder.lower():
                        placement = "promotions" # Remains classified as inbox placement per Astra
                    else:
                        placement = "inbox"

                    spf, dkim, dmarc = parse_auth_results(auth_results)
                    now_iso = datetime.now(timezone.utc).isoformat()

                    # Find and update corresponding record in messages table
                    c.execute("""
                    SELECT message_id, delivery_state FROM messages 
                    WHERE (message_id = ? OR notes LIKE ?) AND purpose = 'test'
                    ORDER BY sent_at DESC LIMIT 1
                    """, (msg_id_header, f"%{trace_id}%" if trace_id else "%NONE%"))
                    matched = c.fetchone()

                    target_msg_id = matched["message_id"] if matched else msg_id_header

                    c.execute("""
                    UPDATE messages SET
                        delivery_state = ?,
                        auth_spf = ?,
                        auth_dkim = ?,
                        auth_dmarc = ?,
                        last_event_at = ?,
                        notes = notes || ' | IMAP observed in ' || ?
                    WHERE message_id = ?
                    """, (placement, spf, dkim, dmarc, now_iso, placement, target_msg_id))

                    c.execute("""
                    INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (target_msg_id, f"imap_observed_{placement}", now_iso, gmail_addr, folder, f"SPF={spf}, DKIM={dkim}, DMARC={dmarc}"))

                    # Circuit-Breaker Trigger 1: Diagnostic in Spam -> Pause mailbox
                    if placement == "spam" and sender_email:
                        volume_controller.pause_mailbox(sender_email, f"Diagnostic message {target_msg_id} placed in Gmail Spam folder on {gmail_addr}")

                    # Circuit-Breaker Trigger 2: Auth failure -> Pause sending domain
                    if (spf == "fail" or dkim == "fail" or dmarc == "fail") and sender_domain:
                        volume_controller.pause_domain(sender_domain, f"Authentication failure detected at Gmail (SPF={spf}, DKIM={dkim}, DMARC={dmarc}) on {target_msg_id}")

        mail.close()
        mail.logout()
        update_collector_health(gmail_addr, "test_inbox", "healthy", None, scanned_cnt)

    except Exception as e:
        update_collector_health(gmail_addr, "test_inbox", "error", f"Gmail scan error: {str(e)}", scanned_cnt)
    finally:
        conn.close()

def run_monitor_cycle():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_utc} UTC] Starting Delivery Monitor & Diagnostic Inspection cycle...")
    
    # 1. Poll 25 IONOS mailboxes
    mailboxes = load_mailboxes()
    print(f"  Scanning {len(mailboxes)} IONOS mailboxes for bounces and replies...")
    for m in mailboxes:
        poll_ionos_mailbox(m)

    # 2. Poll 8 Gmail test inboxes
    test_inboxes = load_test_inboxes()
    print(f"  Scanning {len(test_inboxes)} Gmail test inboxes for diagnostic telemetry...")
    for g in test_inboxes:
        poll_gmail_test_inbox(g)

    # 3. Mark unobserved diagnostics older than 24h as 'not_observed_24h'
    conn = volume_controller.get_db_connection()
    c = conn.cursor()
    twenty_four_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    c.execute("""
    UPDATE messages SET delivery_state = 'not_observed_24h', last_event_at = ?
    WHERE purpose = 'test' AND delivery_state = 'accepted' AND sent_at < ?
    """, (datetime.now(timezone.utc).isoformat(), twenty_four_hours_ago))
    conn.close()

    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC] Monitor cycle complete.")

if __name__ == "__main__":
    run_monitor_cycle()
