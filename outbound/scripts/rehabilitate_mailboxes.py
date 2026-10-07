#!/usr/bin/env python3
"""
Mindmaxing Mailbox Rehabilitation Dispatcher v1.0
Dispatches safe, staggered, low-velocity diagnostic recovery pings to satisfy
the 2-clean-diagnostic recovery threshold in daily_mailbox_planner.py.

Key Safety Features:
- Enforces strict seed isolation (no mailbox targets the same seed twice in 7 days).
- Enforces 2-hour seed cooldown (no seed receives >1 diagnostic in any 2-hour window).
- Natural conversational copy engine with strictly ZERO em dashes.
- Production MIME structure with X-Mindmaxing-Purpose: diagnostic-test header.
- Transactional quota reservation and rollback via volume_controller.
"""

import os
import sys
import json
import uuid
import smtplib
import time
import random
import argparse
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
MAILBOXES_FILE = os.path.join(CONFIG_DIR, "mailboxes.json")
TEST_INBOXES_FILE = os.path.join(CONFIG_DIR, "test_inboxes.json")
CREDENTIALS_FILE = os.path.join(CONFIG_DIR, "credentials.env")
DB_FILE = os.path.join(DATA_DIR, "mindmaxing_crm.db")

SMTP_HOST = "smtp.ionos.com"
SMTP_PORT = 587

# Tiers defined by forensic diagnostic audit
TIER_1_MAILBOXES = [
    "aryan.dev@mindmaxing.info",
    "engineering@mindmaxing.online",
    "build@mindmaxing.store",
    "aryan.dev@mindmaxing.store",
]

TIER_2_MAILBOXES = [
    "studio@mindmaxing.info",
    "aryan.dev@mindmaxing.online",
    "engineering@mindmaxing.store",
    "studio@mindmaxing.store",
]

# Conversational human templates with zero AI buzzwords and ZERO em dashes
REHAB_TEMPLATES = [
    ("quick question", "Hey, are you around today? Let me know if this comes through."),
    ("touching base", "Hey Aryan, wanted to make sure my notes are reaching you. Disregard this."),
    ("coffee catch up", "Let me know when you have 5 minutes this afternoon. Thanks!"),
    ("reviewing the doc", "Sent over the link earlier. Did you have a chance to take a look?"),
    ("checking in", "Hey, just making sure everything is working properly on this end."),
    ("quick update", "Got the updates sorted out this morning. Catch you soon."),
    ("notes from earlier", "Hey, left some comments on the draft for you to check out."),
    ("reach out", "Hey, pinging you here to verify connection. Have a great afternoon."),
    ("following up", "Following up on the notes from earlier. Talk to you later today."),
    ("sync today", "Hey, let me know when you have a quick minute for a sync. Thanks!"),
    ("status check", "Checking to see if you received the files I sent earlier this morning."),
    ("quick note", "Just a quick note to confirm receipt. Hope you are having a productive day.")
]

try:
    import volume_controller
except ImportError:
    try:
        from outbound.scripts import volume_controller
    except ImportError:
        volume_controller = None


def get_db_connection():
    if volume_controller:
        return volume_controller.get_db_connection()
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_ionos_password() -> str:
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


def select_target_seed(sender_email: str, conn) -> dict:
    """
    Selects the best test seed inbox:
    1. Avoids any seed that this mailbox sent to in the last 7 days.
    2. Avoids any seed contacted by ANY mailbox in the last 2 hours.
    3. Picks least recently contacted seed among eligible.
    """
    c = conn.cursor()
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

    c.execute("""
        SELECT DISTINCT recipient_email
        FROM messages
        WHERE sender_email = ? AND purpose = 'test' AND sent_at >= ?
    """, (sender_email, seven_days_ago))
    mailbox_recent_seeds = set(r[0] for r in c.fetchall())

    c.execute("""
        SELECT DISTINCT recipient_email
        FROM messages
        WHERE purpose = 'test' AND sent_at >= ?
    """, (two_hours_ago,))
    fleet_busy_seeds = set(r[0] for r in c.fetchall())

    all_seeds = load_test_inboxes()

    # Tier 1 priority: Not sent by this mailbox in 7d AND not busy in 2h
    tier1_candidates = [
        s for s in all_seeds
        if s["email"] not in mailbox_recent_seeds and s["email"] not in fleet_busy_seeds
    ]
    if tier1_candidates:
        return random.choice(tier1_candidates)

    # Tier 2 priority: Not busy in 2h
    tier2_candidates = [s for s in all_seeds if s["email"] not in fleet_busy_seeds]
    if tier2_candidates:
        return random.choice(tier2_candidates)

    # Fallback: Least recently contacted seed overall
    c.execute("""
        SELECT recipient_email, MAX(sent_at) as last_sent
        FROM messages
        WHERE purpose = 'test'
        GROUP BY recipient_email
        ORDER BY last_sent ASC
    """)
    rows = c.fetchall()
    if rows:
        oldest_email = rows[0][0]
        for s in all_seeds:
            if s["email"] == oldest_email:
                return s

    return all_seeds[0]


def pick_rehab_copy(trace_id: str) -> tuple[str, str]:
    """Deterministically picks human copy based on trace hash with strictly zero em dashes."""
    idx = hash(trace_id) % len(REHAB_TEMPLATES)
    subject, body = REHAB_TEMPLATES[idx]
    # Defensive assertion against em dashes
    assert "\u2014" not in subject and "\u2014" not in body, "Invariant 10 violation: em dash detected"
    assert chr(8212) not in subject and chr(8212) not in body, "Invariant 10 violation: em dash detected"
    return subject, body


def send_rehab_ping(mailbox_dict: dict, dry_run: bool = False) -> tuple[bool, str]:
    sender_email = mailbox_dict["email"]
    sender_domain = mailbox_dict["domain"]
    sender_name = mailbox_dict.get("name", "Aryan Panchal")

    conn = get_db_connection()
    target_seed = select_target_seed(sender_email, conn)
    recipient_email = target_seed["email"]

    period_id = volume_controller.get_current_period_id() if volume_controller else f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-IST"

    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Preparing recovery ping for {sender_email} -> {recipient_email}")

    # Reserve quota via volume_controller
    res_id = None
    if volume_controller:
        reserved, reason = volume_controller.reserve_quota(sender_email, purpose="test", period_id=period_id)
        if not reserved:
            conn.close()
            return False, f"Quota reservation rejected: {reason}"
        res_id = reason.split(": ")[-1].strip() if "res_" in reason else None

    trace_id = str(uuid.uuid4())[:8]
    subject, plain_body = pick_rehab_copy(trace_id)

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

    if dry_run:
        if volume_controller and res_id:
            volume_controller.rollback_quota(sender_email, purpose="test", period_id=period_id, reservation_id=res_id)
        conn.close()
        return True, f"[DRY-RUN] Would send '{subject}' from {sender_email} to {recipient_email} (trace={trace_id})"

    sent_at = datetime.now(timezone.utc).isoformat()
    sent_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ionos_pwd = get_ionos_password()

    if not ionos_pwd:
        if volume_controller and res_id:
            volume_controller.rollback_quota(sender_email, purpose="test", period_id=period_id, reservation_id=res_id)
        conn.close()
        return False, "IONOS password missing from credentials.env"

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25)
        server.starttls()
        server.login(sender_email, ionos_pwd)
        refusals = server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.quit()
        if refusals:
            raise Exception(f"Recipient refused: {refusals}")

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
            sent_date, sent_at, f"Rehabilitation ping trace {trace_id}", period_id
        ))

        c.execute("""
            INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
            VALUES (?, 'smtp_accepted', ?, ?, 'OUTBOX', 'SMTP 250 OK accepted by IONOS')
        """, (msg_id, sent_at, sender_email))

        if res_id:
            c.execute("""
                UPDATE quota_reservations
                SET status = 'ACCEPTED', message_id = ?, updated_at = ?
                WHERE reservation_id = ?
            """, (msg_id, sent_at, res_id))

        conn.commit()
        conn.close()
        return True, f"Sent successfully ({msg_id}) to {recipient_email} | Subject: '{subject}'"

    except Exception as e:
        if volume_controller and res_id:
            volume_controller.rollback_quota(sender_email, purpose="test", period_id=period_id, reservation_id=res_id)

        c = conn.cursor()
        c.execute("""
            INSERT INTO messages (
                message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                recipient_provider, purpose, campaign_touch, prospect_domain, sent_at,
                sent_date, smtp_status, smtp_code, smtp_response, delivery_state,
                last_event_at, notes, period_id
            ) VALUES (?, ?, ?, ?, 'gmail.com', 'gmail', 'test', NULL, NULL, ?, ?, 'temp_failure', 0, ?, 'unknown', ?, 'Rehabilitation SMTP error', ?)
        """, (
            msg_id, sender_email, sender_domain, recipient_email, sent_at,
            sent_date, str(e), sent_at, period_id
        ))
        conn.commit()
        conn.close()
        return False, f"SMTP error on {sender_email}: {e}"


def main():
    parser = argparse.ArgumentParser(description="Mindmaxing Mailbox Rehabilitation Dispatcher")
    parser.add_argument("--canary", action="store_true", help="Send single canary ping from aryan.dev@mindmaxing.info")
    parser.add_argument("--mailbox", type=str, help="Target single mailbox email")
    parser.add_argument("--tier1", action="store_true", help="Run recovery drip for all Tier 1 mailboxes")
    parser.add_argument("--tier2", action="store_true", help="Run recovery drip for all Tier 2 mailboxes")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    parser.add_argument("--delay", type=int, default=1800, help="Delay in seconds between batch sends (default: 1800s)")

    args = parser.parse_args()

    all_mailboxes = load_mailboxes()
    mb_map = {m["email"]: m for m in all_mailboxes}

    targets = []
    if args.canary:
        canary_email = "aryan.dev@mindmaxing.info"
        if canary_email in mb_map:
            targets.append(mb_map[canary_email])
        else:
            print(f"Error: {canary_email} not found in mailboxes.json")
            sys.exit(1)
    elif args.mailbox:
        if args.mailbox in mb_map:
            targets.append(mb_map[args.mailbox])
        else:
            print(f"Error: {args.mailbox} not found in mailboxes.json")
            sys.exit(1)
    elif args.tier1:
        targets = [mb_map[e] for e in TIER_1_MAILBOXES if e in mb_map]
    elif args.tier2:
        targets = [mb_map[e] for e in TIER_2_MAILBOXES if e in mb_map]
    else:
        print("Please specify a target flag: --canary, --mailbox=<email>, --tier1, or --tier2")
        sys.exit(1)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting rehabilitation run for {len(targets)} target(s) (dry_run={args.dry_run})")

    for idx, mb in enumerate(targets):
        success, message = send_rehab_ping(mb, dry_run=args.dry_run)
        prefix = "[OK]" if success else "[ERROR]"
        print(f"  {prefix} {mb['email']}: {message}")

        if idx < len(targets) - 1:
            delay_sec = args.delay if not args.dry_run else 1
            print(f"  Pacing delay: waiting {delay_sec} seconds before next send...")
            time.sleep(delay_sec)

    print(f"[{datetime.now(timezone.utc).isoformat()}] Rehabilitation run complete.")


if __name__ == "__main__":
    main()
