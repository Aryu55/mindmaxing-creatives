#!/usr/bin/env python3
"""
Mindmaxing Delivery Monitor & IMAP Diagnostic Inspector v2.0
Polls:
1. 25 sending mailboxes on IONOS (every 10m):
   - Scans INBOX and Spam/Junk for bounce reports (RFC 3464 DSN parser) and inbound replies.
   - Strictly matches bounces/replies to messages table via exact recipient / Message-ID / In-Reply-To.
   - Quarantines unparseable / ambiguous notices to unmatched_delivery_events table.
   - Immediately suppresses invalid recipients and sets lead status to BOUNCED.
   - Explicit opt-out suppresses recipient globally and sets lead status to SUPPRESSED.
   - Genuine human replies set lead status to REPLIED, halting sequence automation, and supersede auto-responses.
2. 8 test Gmail inboxes (every 10m):
   - Strict read-only access (readonly=True, BODY.PEEK[]) preserving unread status.
   - Checks INBOX, [Gmail]/Spam, and Gmail labels (X-GM-LABELS) for Promotions.
   - Deduplicates observations to prevent inflating telemetry counts.
   - Parses RFC 8601 Authentication-Results header for SPF, DKIM, and DMARC passes.
   - Automatically pauses mailbox if diagnostic lands in Spam.
   - Automatically pauses domain if SPF/DKIM/DMARC fails.
Persists collector health and polling status in collector_health table.
"""

import os
import re
import json
import imaplib
import email
from email import policy
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)

try:
    import volume_controller
except ImportError:
    from outbound.scripts import volume_controller

try:
    import delivery_events
    from delivery_events import BounceCategory, ReplyType
except ImportError:
    from outbound.scripts import delivery_events
    from outbound.scripts.delivery_events import BounceCategory, ReplyType

MAILBOXES_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
TEST_INBOXES_FILE = os.path.join(BASE_DIR, "config", "test_inboxes.json")
CREDENTIALS_FILE = os.path.join(BASE_DIR, "config", "credentials.env")
IONOS_IMAP_HOST = "imap.ionos.com"
GMAIL_IMAP_HOST = "imap.gmail.com"


def get_ionos_password() -> str:
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            for line in f:
                if line.startswith("IONOS_PASSWORD="):
                    return line.strip().split("=", 1)[1].strip().strip('"\'')
    return os.environ.get("IONOS_PASSWORD", "")


def load_mailboxes():
    if os.path.exists(MAILBOXES_FILE):
        with open(MAILBOXES_FILE, "r") as f:
            return json.load(f)
    return []


def load_test_inboxes():
    if os.path.exists(TEST_INBOXES_FILE):
        with open(TEST_INBOXES_FILE, "r") as f:
            return json.load(f)
    return []


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
    # Check if Spam / Junk exists
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
    folder_errors = []

    try:
        for folder in folders_to_check:
            folder_arg = f'"{folder}"' if (' ' in folder or '[' in folder) and not folder.startswith('"') else folder
            res, _ = mail.select(folder_arg, readonly=True)
            if res != "OK":
                folder_errors.append(f"Select failed for {folder} ({res})")
                continue

            # Fetch UIDVALIDITY from untagged response
            uv_res, uv_data = mail.response('UIDVALIDITY')
            current_uidvalidity = int(uv_data[0]) if (uv_res == 'OK' and uv_data and uv_data[0]) else 1

            # Check cursor
            c.execute("SELECT uidvalidity, last_uid FROM imap_cursors WHERE mailbox = ? AND folder = ?", (email_addr, folder))
            cursor_row = c.fetchone()

            if cursor_row and cursor_row["uidvalidity"] == current_uidvalidity:
                last_uid = cursor_row["last_uid"]
                res, data = mail.uid('search', None, f"UID {last_uid + 1}:*")
                if res != "OK":
                    folder_errors.append(f"UID search failed for {folder} ({res})")
                    continue
                raw_uids = data[0].split() if data and data[0] else []
                uids = sorted([int(u) for u in raw_uids if int(u) > last_uid])
            else:
                last_uid = 0
                since_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%d-%b-%Y")
                res, data = mail.uid('search', None, f'(SINCE "{since_date}")')
                if res != "OK":
                    folder_errors.append(f"Search failed for {folder} ({res})")
                    continue
                raw_uids = data[0].split() if data and data[0] else []
                uids = sorted([int(u) for u in raw_uids])
                if not uids:
                    res, data = mail.uid('search', None, 'ALL')
                    raw_uids = data[0].split() if (res == "OK" and data and data[0]) else []
                    uids = sorted([int(u) for u in raw_uids])[-30:]

            if not uids:
                if not cursor_row:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    c.execute("""
                        INSERT INTO imap_cursors (mailbox, folder, uidvalidity, last_uid, updated_at)
                        VALUES (?, ?, ?, 0, ?)
                        ON CONFLICT(mailbox, folder) DO UPDATE SET
                            uidvalidity = excluded.uidvalidity,
                            updated_at = excluded.updated_at
                    """, (email_addr, folder, current_uidvalidity, now_iso))
                    conn.commit()
                continue

            uids_to_process = uids[:50]
            scanned_cnt += len(uids_to_process)
            max_uid_processed = last_uid

            for uid in uids_to_process:
                max_uid_processed = max(max_uid_processed, uid)
                res, msg_data = mail.uid('fetch', str(uid), "(BODY.PEEK[])")
                if res != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_bytes = msg_data[0][1]
                msg = email.message_from_bytes(raw_bytes, policy=policy.default)
                from_hdr = str(msg.get("From", "")).lower()
                subj_hdr = str(msg.get("Subject", ""))
                now_iso = datetime.now(timezone.utc).isoformat()

                # Check 1: DSN / Delivery Failure Report
                is_bounce = (
                    any(b in from_hdr for b in ["mailer-daemon", "postmaster"]) or
                    "failure notice" in subj_hdr.lower() or
                    msg.get_content_type() == "multipart/report"
                )

                if is_bounce:
                    dsn = delivery_events.parse_dsn_report(raw_bytes)

                    # Reject ambiguous or empty matching
                    if dsn.is_ambiguous or not dsn.recipient:
                        header_snip = f"From: {from_hdr} | Subj: {subj_hdr}"
                        c.execute("""
                            SELECT id FROM unmatched_delivery_events 
                            WHERE source_mailbox = ? AND folder = ? AND raw_headers_snippet = ?
                        """, (email_addr, folder, header_snip))
                        if not c.fetchone():
                            c.execute("""
                                INSERT INTO unmatched_delivery_events (source_mailbox, folder, raw_headers_snippet, body_snippet, reason, detected_at)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                email_addr, folder,
                                header_snip,
                                str(raw_bytes[:1000], errors="ignore"),
                                "Ambiguous DSN: missing recipient or unparseable status",
                                now_iso
                            ))
                        continue

                    failed_recip = dsn.recipient.lower().strip()

                    # Exact match on recipient_email only (never LIKE '%%')
                    c.execute("""
                        SELECT message_id, sender_domain, recipient_email FROM messages 
                        WHERE recipient_email = ? AND purpose = 'campaign'
                        ORDER BY sent_at DESC LIMIT 1
                    """, (failed_recip,))
                    matched = c.fetchone()

                    if dsn.category == BounceCategory.HARD_BOUNCE:
                        # 1. Suppress recipient globally
                        volume_controller.suppress_recipient(
                            failed_recip,
                            f"Hard bounce ({dsn.status_code}): {dsn.diagnostic_code}",
                            matched["message_id"] if matched else None
                        )
                        # 2. Update CRM lead state
                        c.execute("UPDATE leads SET status = 'BOUNCED' WHERE contact_email = ?", (failed_recip,))

                        # 3. Update campaign message record
                        if matched:
                            c.execute("""
                                UPDATE messages 
                                SET delivery_state = 'bounced', smtp_status = 'perm_failure', last_event_at = ?,
                                    notes = COALESCE(notes, '') || ' | Hard Bounce: ' || ?
                                WHERE message_id = ?
                            """, (now_iso, f"{dsn.status_code} {dsn.diagnostic_code}", matched["message_id"]))

                            # Deduplicate bounce event
                            c.execute("""
                                SELECT id FROM delivery_events
                                WHERE message_id = ? AND event_type = 'bounce_report' AND source_mailbox = ?
                            """, (matched["message_id"], email_addr))
                            if not c.fetchone():
                                c.execute("""
                                    INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                                    VALUES (?, 'bounce_report', ?, ?, ?, ?)
                                """, (matched["message_id"], now_iso, email_addr, folder, f"Hard bounce ({dsn.status_code}): {dsn.diagnostic_code}"))

                    elif dsn.category == BounceCategory.POLICY_BLOCKED:
                        if matched:
                            c.execute("""
                                UPDATE messages 
                                SET notes = COALESCE(notes, '') || ' | Policy Block: ' || ?, last_event_at = ?
                                WHERE message_id = ?
                            """, (f"{dsn.status_code} {dsn.diagnostic_code}", now_iso, matched["message_id"]))
                            volume_controller.pause_domain(matched["sender_domain"], f"Policy block detected: {dsn.diagnostic_code}")

                    elif dsn.category == BounceCategory.TEMP_FAILURE:
                        if matched:
                            c.execute("""
                                UPDATE messages 
                                SET notes = COALESCE(notes, '') || ' | Temp Delivery Delay: ' || ?, last_event_at = ?
                                WHERE message_id = ?
                            """, (f"{dsn.status_code} {dsn.diagnostic_code}", now_iso, matched["message_id"]))

                # Check 2: Prospect Inbound Reply
                else:
                    reply = delivery_events.parse_inbound_reply(raw_bytes)

                    # Match message via In-Reply-To, References, or sender email
                    matched_msg = None
                    if reply.in_reply_to:
                        c.execute("SELECT message_id, delivery_state, recipient_email FROM messages WHERE message_id = ?", (reply.in_reply_to,))
                        matched_msg = c.fetchone()

                    if not matched_msg and reply.references:
                        for ref in reply.references:
                            c.execute("SELECT message_id, delivery_state, recipient_email FROM messages WHERE message_id = ?", (ref,))
                            matched_msg = c.fetchone()
                            if matched_msg:
                                break

                    if not matched_msg and reply.from_email:
                        c.execute("""
                            SELECT message_id, delivery_state, recipient_email FROM messages 
                            WHERE recipient_email = ? AND purpose = 'campaign' 
                            ORDER BY sent_at DESC LIMIT 1
                        """, (reply.from_email,))
                        matched_msg = c.fetchone()

                    if matched_msg:
                        target_mid = matched_msg["message_id"]
                        orig_state = matched_msg["delivery_state"]
                        target_recip = matched_msg["recipient_email"]

                        # Case A: Explicit Opt-Out
                        if reply.is_opt_out:
                            volume_controller.suppress_recipient(
                                reply.from_email,
                                f"Explicit opt-out in reply: {reply.body_excerpt}",
                                target_mid
                            )
                            c.execute("UPDATE leads SET status = 'SUPPRESSED' WHERE contact_email = ? OR contact_email = ?", (target_recip, reply.from_email))
                            c.execute("UPDATE messages SET delivery_state = 'opt_out', last_event_at = ? WHERE message_id = ?", (now_iso, target_mid))
                            c.execute("""
                                SELECT id FROM delivery_events 
                                WHERE message_id = ? AND event_type = 'reply_opt_out' AND source_mailbox = ?
                            """, (target_mid, email_addr))
                            if not c.fetchone():
                                c.execute("""
                                    INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                                    VALUES (?, 'reply_opt_out', ?, ?, ?, ?)
                                """, (target_mid, now_iso, email_addr, folder, f"Opt-out: {reply.body_excerpt[:100]}"))

                        # Case B: Human Reply (supersedes auto-response!)
                        elif reply.reply_type == ReplyType.HUMAN_REPLY:
                            c.execute("UPDATE leads SET status = 'REPLIED' WHERE contact_email = ? OR contact_email = ?", (target_recip, reply.from_email))
                            c.execute("UPDATE messages SET delivery_state = 'replied', last_event_at = ? WHERE message_id = ?", (now_iso, target_mid))
                            c.execute("""
                                SELECT id FROM delivery_events 
                                WHERE message_id = ? AND event_type = 'reply_human' AND source_mailbox = ?
                            """, (target_mid, email_addr))
                            if not c.fetchone():
                                c.execute("""
                                    INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                                    VALUES (?, 'reply_human', ?, ?, ?, ?)
                                """, (target_mid, now_iso, email_addr, folder, f"From: {reply.from_email} | Subj: {reply.subject[:100]}"))

                        # Case C: Out of Office
                        elif reply.reply_type == ReplyType.OUT_OF_OFFICE:
                            if orig_state not in ("replied", "opt_out"):
                                c.execute("UPDATE messages SET delivery_state = 'auto_response', last_event_at = ? WHERE message_id = ?", (now_iso, target_mid))
                                c.execute("""
                                    SELECT id FROM delivery_events 
                                    WHERE message_id = ? AND event_type = 'reply_ooo' AND source_mailbox = ?
                                """, (target_mid, email_addr))
                                if not c.fetchone():
                                    c.execute("""
                                        INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                                        VALUES (?, 'reply_ooo', ?, ?, ?, ?)
                                    """, (target_mid, now_iso, email_addr, folder, f"OOO from {reply.from_email}"))

                        # Case D: Bot Auto-Response / Support Ticket Deflection
                        elif reply.reply_type in (ReplyType.AUTO_RESPONSE, ReplyType.TICKET_DEFLECTION):
                            if orig_state not in ("replied", "opt_out"):
                                c.execute("UPDATE messages SET delivery_state = 'auto_response', last_event_at = ? WHERE message_id = ?", (now_iso, target_mid))
                                c.execute("""
                                    SELECT id FROM delivery_events 
                                    WHERE message_id = ? AND event_type = 'reply_auto_response' AND source_mailbox = ?
                                """, (target_mid, email_addr))
                                if not c.fetchone():
                                    c.execute("""
                                        INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
                                        VALUES (?, 'reply_auto_response', ?, ?, ?, ?)
                                    """, (target_mid, now_iso, email_addr, folder, f"Auto-reply from {reply.from_email}"))

            # Update IMAP cursor for folder
            now_iso = datetime.now(timezone.utc).isoformat()
            c.execute("""
                INSERT INTO imap_cursors (mailbox, folder, uidvalidity, last_uid, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mailbox, folder) DO UPDATE SET
                    uidvalidity = excluded.uidvalidity,
                    last_uid = excluded.last_uid,
                    updated_at = excluded.updated_at
            """, (email_addr, folder, current_uidvalidity, max_uid_processed, now_iso))
            conn.commit()

        mail.close()
        mail.logout()
        if folder_errors:
            update_collector_health(email_addr, "sender", "error", f"Folder errors: {'; '.join(folder_errors)}", scanned_cnt)
        else:
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

    folders = ["INBOX", "[Gmail]/Spam"]
    conn = volume_controller.get_db_connection()
    c = conn.cursor()
    folder_errors = []

    try:
        for folder in folders:
            folder_arg = f'"{folder}"' if (' ' in folder or '[' in folder) and not folder.startswith('"') else folder
            res, _ = mail.select(folder_arg, readonly=True) # Strict read-only mode!
            if res != "OK":
                folder_errors.append(f"Select failed for {folder} ({res})")
                continue

            # Fetch UIDVALIDITY from untagged response
            uv_res, uv_data = mail.response('UIDVALIDITY')
            current_uidvalidity = int(uv_data[0]) if (uv_res == 'OK' and uv_data and uv_data[0]) else 1

            # Check cursor
            c.execute("SELECT uidvalidity, last_uid FROM imap_cursors WHERE mailbox = ? AND folder = ?", (gmail_addr, folder))
            cursor_row = c.fetchone()

            if cursor_row and cursor_row["uidvalidity"] == current_uidvalidity:
                last_uid = cursor_row["last_uid"]
                res, data = mail.uid('search', None, f"UID {last_uid + 1}:*")
                if res != "OK":
                    folder_errors.append(f"UID search failed for {folder} ({res})")
                    continue
                raw_uids = data[0].split() if data and data[0] else []
                uids = sorted([int(u) for u in raw_uids if int(u) > last_uid])
            else:
                last_uid = 0
                since_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%d-%b-%Y")
                res, data = mail.uid('search', None, f'(SINCE "{since_date}")')
                if res != "OK":
                    folder_errors.append(f"Search failed for {folder} ({res})")
                    continue
                raw_uids = data[0].split() if data and data[0] else []
                uids = sorted([int(u) for u in raw_uids])
                if not uids:
                    res, data = mail.uid('search', None, 'ALL')
                    raw_uids = data[0].split() if (res == "OK" and data and data[0]) else []
                    uids = sorted([int(u) for u in raw_uids])[-30:]

            if not uids:
                if not cursor_row:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    c.execute("""
                        INSERT INTO imap_cursors (mailbox, folder, uidvalidity, last_uid, updated_at)
                        VALUES (?, ?, ?, 0, ?)
                        ON CONFLICT(mailbox, folder) DO UPDATE SET
                            uidvalidity = excluded.uidvalidity,
                            updated_at = excluded.updated_at
                    """, (gmail_addr, folder, current_uidvalidity, now_iso))
                    conn.commit()
                continue

            uids_to_process = uids[:50]
            scanned_cnt += len(uids_to_process)
            max_uid_processed = last_uid

            for uid in uids_to_process:
                max_uid_processed = max(max_uid_processed, uid)
                # PEEK preserves unread status
                res, msg_data = mail.uid('fetch', str(uid), "(BODY.PEEK[] X-GM-LABELS)")
                if res != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_bytes = msg_data[0][1]
                labels_str = str(msg_data[0][0]) if len(msg_data[0]) > 0 else ""
                
                msg = email.message_from_bytes(raw_bytes, policy=policy.default)
                subj = str(msg.get("Subject", ""))
                msg_id_header = str(msg.get("Message-ID", "")).strip()
                trace_id = str(msg.get("X-Mindmaxing-Trace", "")).strip()
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

                    auth_parsed = delivery_events.parse_auth_results(msg)
                    spf = auth_parsed.spf_result
                    dkim = auth_parsed.dkim_result
                    dmarc = auth_parsed.dmarc_result
                    now_iso = datetime.now(timezone.utc).isoformat()

                    # Find corresponding record in messages table
                    c.execute("""
                        SELECT message_id, delivery_state FROM messages 
                        WHERE (message_id = ? OR notes LIKE ?) AND purpose = 'test'
                        ORDER BY sent_at DESC LIMIT 1
                    """, (msg_id_header, f"%{trace_id}%" if trace_id else "%NONE%"))
                    matched = c.fetchone()

                    target_msg_id = matched["message_id"] if matched else msg_id_header

                    # Deduplication check: Do not insert duplicate event if already recorded
                    c.execute("""
                        SELECT id FROM delivery_events 
                        WHERE message_id = ? AND event_type = ? AND source_mailbox = ? AND folder = ?
                    """, (target_msg_id, f"imap_observed_{placement}", gmail_addr, folder))
                    existing_evt = c.fetchone()

                    if not existing_evt:
                        c.execute("""
                            UPDATE messages SET
                                delivery_state = ?,
                                auth_spf = ?,
                                auth_dkim = ?,
                                auth_dmarc = ?,
                                last_event_at = ?,
                                notes = COALESCE(notes, '') || ' | IMAP observed in ' || ?
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

            # Update IMAP cursor for folder
            now_iso = datetime.now(timezone.utc).isoformat()
            c.execute("""
                INSERT INTO imap_cursors (mailbox, folder, uidvalidity, last_uid, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mailbox, folder) DO UPDATE SET
                    uidvalidity = excluded.uidvalidity,
                    last_uid = excluded.last_uid,
                    updated_at = excluded.updated_at
            """, (gmail_addr, folder, current_uidvalidity, max_uid_processed, now_iso))
            conn.commit()

        mail.close()
        mail.logout()
        if folder_errors:
            update_collector_health(gmail_addr, "test_inbox", "error", f"Folder errors: {'; '.join(folder_errors)}", scanned_cnt)
        else:
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
    conn.commit()
    conn.close()

    print(f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC] Monitor cycle complete.")


if __name__ == "__main__":
    run_monitor_cycle()
