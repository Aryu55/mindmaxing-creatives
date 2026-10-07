#!/usr/bin/env python3
"""
Mindmaxing Proactive Outbound Alerting Service
Dispatches transactional email alerts directly to Aryan's personal inbox (aryupanchal1647@gmail.com)
for critical pipeline events:
  - Wave completion summaries (sent count, failures, remaining queue)
  - Pipeline dry alerts (0 eligible leads remaining)
  - Immediate reply alerts (human replies and auto-responders)
  - Nightly executive digests
Enforces strict zero em-dash invariant across all alert templates.
"""

import os
import smtplib
import json
import urllib.request
from datetime import datetime, timezone
from email.mime.text import MIMEText
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

SMTP_HOST = os.getenv("IONOS_SMTP_HOST", "smtp.ionos.com")
SMTP_PORT = int(os.getenv("IONOS_SMTP_PORT", 587))
SMTP_PASSWORD = os.getenv("IONOS_SMTP_PASSWORD", "")
DEFAULT_SENDER = os.getenv("ALERT_SENDER", "founder@mindmaxing.info")
DEFAULT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "aryupanchal1647@gmail.com")
WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")


def send_email_alert(subject: str, body: str, recipient: str = DEFAULT_RECIPIENT) -> bool:
    """Sends a plain-text email alert via IONOS SMTP to Aryan's personal inbox."""
    if not SMTP_PASSWORD:
        print(f"[ALERT_NOTIFIER] WARNING: IONOS_SMTP_PASSWORD missing. Cannot send alert: {subject}")
        return False

    clean_subject = subject.replace("—", "-").replace("–", "-")
    clean_body = body.replace("—", "-").replace("–", "-")

    msg = MIMEText(clean_body, "plain", "utf-8")
    msg["From"] = f"Mindmaxing Radar <{DEFAULT_SENDER}>"
    msg["To"] = recipient
    msg["Subject"] = f"[Mindmaxing Radar] {clean_subject}"

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo("mindmaxing.info")
            server.starttls()
            server.ehlo("mindmaxing.info")
            server.login(DEFAULT_SENDER, SMTP_PASSWORD)
            server.send_message(msg)
            print(f"[ALERT_NOTIFIER] Alert sent successfully to {recipient}: '{clean_subject}'")

        # Optional Webhook Mirror
        if WEBHOOK_URL:
            try:
                payload = json.dumps({"content": f"**[Mindmaxing Radar] {clean_subject}**\n\n```\n{clean_body[:1800]}\n```"}).encode("utf-8")
                req = urllib.request.Request(WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json", "User-Agent": "MindmaxingAlert/1.0"})
                urllib.request.urlopen(req, timeout=5)
            except Exception as we:
                print(f"[ALERT_NOTIFIER] Webhook warning: {we}")

        return True
    except Exception as e:
        print(f"[ALERT_NOTIFIER] Failed to send email alert: {e}")
        return False


def notify_wave_completed(wave_label: str, total_sent: int, failed_count: int, remaining_queue: int, sent_details: list = None) -> bool:
    """Triggered immediately after a live campaign wave completes."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    subject = f"{wave_label} Completed: {total_sent} Sent, {failed_count} Failed"

    lines = [
        f"Mindmaxing Outbound Dispatch Report",
        f"Wave: {wave_label}",
        f"Time: {ts}",
        "",
        f"Summary:",
        f"  * Messages Sent: {total_sent}",
        f"  * Failed Submissions: {failed_count}",
        f"  * Remaining Approved Queue: {remaining_queue}",
        ""
    ]

    if sent_details:
        lines.append("Dispatched Items:")
        for idx, item in enumerate(sent_details, 1):
            brand = item.get("brand", "Unknown")
            recipient = item.get("recipient", "")
            sender = item.get("sender", "")
            status = item.get("status", "SENT")
            lines.append(f"  {idx}. {brand} -> {recipient} (via {sender}) [{status}]")
        lines.append("")

    if remaining_queue == 0:
        lines.append("WARNING: Approved pipeline is now EMPTY. No leads remain for future waves.")
        lines.append("Please refill the database with fresh verified GetLeads candidates.")
    else:
        lines.append(f"Next wave has {remaining_queue} approved candidate(s) ready.")

    body = "\n".join(lines)
    return send_email_alert(subject, body)


def notify_pipeline_dry(wave_label: str = "Campaign Dispatch", details: str = "") -> bool:
    """Triggered when dispatcher finds 0 eligible leads."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    subject = f"WARNING: Outbound Pipeline is EMPTY (0 Leads Eligible)"

    body = f"""Mindmaxing Outbound Critical Alert

Timestamp: {ts}
Trigger: {wave_label}

The automated outbound dispatcher executed, but found ZERO eligible leads to contact.
No emails were dispatched during this cycle.

Root Cause:
  * All approved GetLeads have been contacted.
  * Active leads are in cooldown for Touch 2 / Touch 3.
  * No new leads have 'HUMAN_APPROVED' status.

Action Required:
  1. Review pending candidates in CRM.
  2. Run 'python3 scripts/ingest_getleads_batch.py <file.csv>' to refill pipeline with fresh DTC brands.
  3. Approve candidates so the fleet resumes sending.

Details:
{details}
"""
    return send_email_alert(subject, body)


def notify_reply_detected(source_mailbox: str, prospect_email: str, subject: str, snippet: str, reply_type: str = "HUMAN_REPLY") -> bool:
    """Triggered when delivery_monitor catches an incoming reply."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    is_auto = "auto" in reply_type.lower()
    type_label = "Auto-Responder / Deflection" if is_auto else "HUMAN LEAD REPLY"
    alert_subj = f"{'REPLY' if not is_auto else 'AUTO-REPLY'}: {prospect_email} on {source_mailbox}"

    body = f"""Mindmaxing Reply Notification

Type: {type_label}
Detected: {ts}
Prospect: {prospect_email}
Target Mailbox: {source_mailbox}
Subject: {subject}

Message Snippet:
--------------------------------------------------
{snippet[:1000]}
--------------------------------------------------

Action:
  * If Human Reply: Check mailbox {source_mailbox} or reply directly from your authenticated desk.
  * If Auto-Responder / Inactive: Verified and suppressed in CRM automatically.
"""
    return send_email_alert(alert_subj, body)


def notify_daily_digest(report_dict: dict) -> bool:
    """Triggered nightly at 22:30 IST to give full daily telemetry."""
    ts = datetime.now().strftime("%Y-%m-%d")
    subject = f"Daily Outbound Digest: {ts}"

    lines = [
        f"Mindmaxing Executive Outbound Digest ({ts})",
        "==================================================",
        "",
        f"Daily Performance:",
        f"  * Total Emails Delivered Today: {report_dict.get('total_sent_today', 0)}",
        f"  * Total Errors / Failures: {report_dict.get('total_failed_today', 0)}",
        f"  * Replies Received Today: {report_dict.get('replies_today', 0)}",
        "",
        f"Mailbox Fleet Health:",
        f"  * Active Sending Mailboxes: {report_dict.get('active_mailboxes', 0)}",
        f"  * Paused Mailboxes: {report_dict.get('paused_mailboxes', 0)}",
        f"  * Daily Effective Fleet Capacity: {report_dict.get('fleet_capacity', 0)}/day",
        "",
        f"Pipeline Queue:",
        f"  * Ready for Touch 1 (Approved): {report_dict.get('approved_touch1', 0)}",
        f"  * Ready for Touch 2 (Unlocking): {report_dict.get('ready_touch2', 0)}",
        f"  * Unreviewed Candidates: {report_dict.get('candidate_count', 0)}",
        f"  * Status: {report_dict.get('pipeline_health', 'HEALTHY')}",
        "",
        "==================================================",
        "Mindmaxing Outbound Engine (VPS 72.62.230.37)"
    ]

    body = "\n".join(lines)
    return send_email_alert(subject, body)


if __name__ == "__main__":
    import sys
    print("Testing Mindmaxing Alert Notifier...")
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RECIPIENT
    test_ok = send_email_alert(
        subject="Test Alert: VPS Outbound Radar Online",
        body="This is a test notification confirming that the Mindmaxing Outbound Radar alerting service is active and capable of reaching your inbox.\n\nYou will now receive automatic notifications for wave completions, replies, and empty queue warnings.",
        recipient=target
    )
    print("Test result:", "SUCCESS" if test_ok else "FAILED")
