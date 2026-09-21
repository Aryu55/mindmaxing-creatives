#!/usr/bin/env python3
"""
Mindmaxing Outbound Status & Reporting CLI v2.1 (Revised)
Strictly Read-Only:
- Never triggers SMTP
- Never rescans inboxes
- Never resets quotas
- Never promotes or demotes mailboxes

CLI Commands:
    python3 outbound_status.py report --today [--format text|json]
    python3 outbound_status.py report --date YYYY-MM-DD [--format text|json]
    python3 outbound_status.py (legacy summary)
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import daily_mailbox_planner

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
MAILBOXES_FILE = os.path.join(CONFIG_DIR, "mailboxes.json")


def get_ro_connection() -> sqlite3.Connection:
    """Returns a strictly read-only SQLite connection."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10.0)
    except Exception:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def load_mailboxes_config() -> List[Dict[str, Any]]:
    if os.path.exists(MAILBOXES_FILE):
        with open(MAILBOXES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def generate_period_report(period_id: str) -> Dict[str, Any]:
    """
    Builds an explainable status report for the specified IST budget period.
    Strictly read-only.
    """
    conn = get_ro_connection()
    c = conn.cursor()

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    start_utc, end_utc = daily_mailbox_planner.get_ist_budget_period_bounds_utc(period_id)
    start_utc_iso = start_utc.isoformat()
    end_utc_iso = end_utc.isoformat()

    mailboxes = load_mailboxes_config()

    # 1. Fetch latest decisions for this period
    c.execute("""
        SELECT d1.*
        FROM mailbox_daily_decisions d1
        JOIN (
            SELECT mailbox, MAX(revision) AS max_rev
            FROM mailbox_daily_decisions
            WHERE period_id = ?
            GROUP BY mailbox
        ) d2 ON d1.mailbox = d2.mailbox AND d1.revision = d2.max_rev
        WHERE d1.period_id = ?
    """, (period_id, period_id))
    decisions_by_mb = {r["mailbox"]: dict(r) for r in c.fetchall()}

    # 2. Fetch collector health
    c.execute("SELECT mailbox, status, last_scan_at, error_message FROM collector_health")
    health_by_mb = {r["mailbox"]: dict(r) for r in c.fetchall()}

    # 3. Message telemetry within this budget period
    c.execute("""
        SELECT sender_email, purpose, campaign_touch, delivery_state, smtp_status,
               auth_spf, auth_dkim, auth_dmarc, count(*) as count
        FROM messages
        WHERE sent_at >= ? AND sent_at < ?
        GROUP BY sender_email, purpose, campaign_touch, delivery_state, smtp_status, auth_spf, auth_dkim, auth_dmarc
    """, (start_utc_iso, end_utc_iso))
    period_messages = [dict(r) for r in c.fetchall()]

    # 4. Inbound replies within budget period
    c.execute("""
        SELECT source_mailbox, count(*) as count
        FROM delivery_events
        WHERE event_type = 'reply' AND detected_at >= ? AND detected_at < ?
        GROUP BY source_mailbox
    """, (start_utc_iso, end_utc_iso))
    inbound_events = [dict(r) for r in c.fetchall()]

    # 5. Outbound jobs status (due, deferred, uncertain)
    c.execute("""
        SELECT assigned_mailbox, status, count(*) as count
        FROM outbound_jobs
        GROUP BY assigned_mailbox, status
    """)
    job_counts: Dict[str, Dict[str, int]] = {}
    for r in c.fetchall():
        mb = r["assigned_mailbox"] or "unassigned"
        if mb not in job_counts:
            job_counts[mb] = {}
        job_counts[mb][r["status"]] = r["count"]

    # 6. Global stats
    c.execute("SELECT count(*) as count FROM recipient_suppressions")
    suppressions_total = c.fetchone()["count"]

    # 7. Seed telemetry label: personal Gmail evidence
    c.execute("""
        SELECT recipient_email, count(*) as tests_received,
               sum(case when delivery_state in ('inbox', 'promotions') then 1 else 0 end) as inbox_count,
               sum(case when delivery_state = 'spam' then 1 else 0 end) as spam_count
        FROM messages
        WHERE purpose = 'test'
        GROUP BY recipient_email
    """)
    seed_telemetry = [dict(r) for r in c.fetchall()]

    # 8. Historical campaign archive (pre-v2.1 or out-of-period records)
    c.execute("""
        SELECT count(*) as count, min(sent_at) as first_sent, max(sent_at) as last_sent,
               sum(case when smtp_status = 'accepted' then 1 else 0 end) as accepted_count
        FROM messages
        WHERE purpose = 'campaign' AND (sent_at < ? OR sent_at >= ?)
    """, (start_utc_iso, end_utc_iso))
    hist_row = c.fetchone()
    historical_campaign_count = hist_row["accepted_count"] if hist_row and hist_row["accepted_count"] else 0
    historical_first = hist_row["first_sent"] if hist_row else None
    historical_last = hist_row["last_sent"] if hist_row else None

    conn.close()

    # Compile per-mailbox telemetry
    mailbox_reports: List[Dict[str, Any]] = []
    total_active_capacity = 0

    for mb in mailboxes:
        email_addr = mb["email"]
        domain = mb["domain"]
        dec = decisions_by_mb.get(email_addr, {})
        hlth = health_by_mb.get(email_addr, {})

        baseline_cap = dec.get("baseline_cap", 1)
        effective_cap = dec.get("effective_campaign_cap", 0)
        action = dec.get("decision_action", "NO_DECISION")
        reason = dec.get("decision_reason", "No review decision recorded for this period")
        scope = dec.get("scope", "mailbox")
        recovery_condition = dec.get("recovery_condition")

        total_active_capacity += effective_cap

        # Period activity for this sender
        camp_sends = sum(r["count"] for r in period_messages if r["sender_email"] == email_addr and r["purpose"] == "campaign")
        new_contacts = sum(r["count"] for r in period_messages if r["sender_email"] == email_addr and r["purpose"] == "campaign" and r["campaign_touch"] == 1)
        follow_ups = sum(r["count"] for r in period_messages if r["sender_email"] == email_addr and r["purpose"] == "campaign" and (r["campaign_touch"] or 0) > 1)
        diag_sends = sum(r["count"] for r in period_messages if r["sender_email"] == email_addr and r["purpose"] == "test")
        definite_failures = sum(r["count"] for r in period_messages if r["sender_email"] == email_addr and r["smtp_status"] == "perm_failure")
        temp_failures = sum(r["count"] for r in period_messages if r["sender_email"] == email_addr and r["smtp_status"] == "temp_failure")

        # Job queue for this sender
        mb_jobs = job_counts.get(email_addr, {})
        pending_jobs = mb_jobs.get("PENDING", 0)
        claimed_jobs = mb_jobs.get("CLAIMED", 0)
        reserved_jobs = mb_jobs.get("RESERVED", 0)
        deferred_jobs = mb_jobs.get("DEFERRED", 0)
        uncertain_jobs = mb_jobs.get("UNCERTAIN", 0)

        remaining_allowance = max(0, effective_cap - camp_sends)

        # Recent clean diagnostic from evidence
        ev_summary = json.loads(dec.get("evidence_summary_json") or "{}")
        recent_clean_diag = ev_summary.get("recent_clean_diag", {})

        mailbox_reports.append({
            "mailbox": email_addr,
            "domain": domain,
            "baseline_cap": baseline_cap,
            "effective_allowance": effective_cap,
            "used": camp_sends,
            "reserved": reserved_jobs + claimed_jobs,
            "remaining": remaining_allowance,
            "action": action,
            "reason": reason,
            "scope": scope,
            "recovery_condition": recovery_condition,
            "campaign_submissions": camp_sends,
            "new_contacts": new_contacts,
            "follow_ups": follow_ups,
            "diagnostics": diag_sends,
            "failures": definite_failures + temp_failures,
            "uncertain_submissions": uncertain_jobs,
            "due_jobs": pending_jobs,
            "deferred_jobs": deferred_jobs,
            "latest_scan": hlth.get("last_scan_at"),
            "latest_diagnostic": recent_clean_diag.get("sent_at")
        })

    return {
        "period_id": period_id,
        "policy_version": "v2.1-revised",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_senders": len(mailboxes),
        "total_active_capacity": total_active_capacity,
        "suppressions_total": suppressions_total,
        "seed_telemetry": seed_telemetry,
        "historical_archive": {
            "accepted_count": historical_campaign_count,
            "first_sent": historical_first,
            "last_sent": historical_last
        },
        "mailboxes": mailbox_reports
    }


def format_text_report(rep: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append(f"  MINDMAXING NIGHTLY CAMPAIGN REVIEW & MAILBOX REPORT: {rep['period_id']}")
    lines.append(f"  Policy: {rep['policy_version']} | Generated: {rep['generated_at_utc']} (UTC)")
    lines.append(f"  Total Senders: {rep['total_senders']} | Total Effective Daily Capacity: {rep['total_active_capacity']} messages")
    lines.append("=" * 80)

    lines.append("\n## MAILBOX STATUS & DECISION LEDGER\n")
    lines.append(f"{'#':<3} {'Mailbox':<32} {'Base':<5} {'Eff':<5} {'Used':<5} {'Rem':<5} {'Action':<10} {'Reason'}")
    lines.append("-" * 80)

    for i, m in enumerate(rep["mailboxes"], 1):
        lines.append(
            f"{i:<3} {m['mailbox']:<32} {m['baseline_cap']:<5} {m['effective_allowance']:<5} "
            f"{m['used']:<5} {m['remaining']:<5} {m['action']:<10} {m['reason']}"
        )
        if m["recovery_condition"]:
            lines.append(f"    ↳ Recovery: {m['recovery_condition']}")

    lines.append("\n## WORKLOAD QUEUE & TELEMETRY")
    total_due = sum(m["due_jobs"] for m in rep["mailboxes"])
    total_def = sum(m["deferred_jobs"] for m in rep["mailboxes"])
    total_unc = sum(m["uncertain_submissions"] for m in rep["mailboxes"])
    lines.append(f"Pending Due Jobs: {total_due} | Deferred Jobs: {total_def} | Uncertain Submissions: {total_unc}")
    lines.append(f"Recipient Suppressions: {rep['suppressions_total']} (Globally Enforced)")

    lines.append("\n## HISTORICAL CAMPAIGN ARCHIVE (Pre-v2.1 / Out-of-Period)")
    hist = rep.get("historical_archive", {})
    if hist.get("accepted_count"):
        lines.append(f"Historical accepted campaign sends on record: {hist['accepted_count']} (From {str(hist['first_sent'])[:10]} to {str(hist['last_sent'])[:10]})")
        lines.append("Note: Preserved separately from active budget period accounting.")
    else:
        lines.append("No out-of-period historical campaign sends recorded.")

    lines.append("\n## CONTROLLED SEED TELEMETRY (Test Gmail Inboxes Only — Not Prospect Delivery)")
    lines.append("Note: Measures SPF/DKIM/DMARC and folder placement in controlled test accounts; does not guarantee founder inbox placement or Primary tab delivery.")
    if rep["seed_telemetry"]:
        for s in rep["seed_telemetry"]:
            lines.append(f"  * {s['recipient_email']}: {s['tests_received']} tests (Inbox: {s['inbox_count']}, Spam: {s['spam_count']})")
    else:
        lines.append("  * No seed diagnostic messages recorded yet.")

    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Mindmaxing Outbound Status & Reporting CLI (Strictly Read-Only)")
    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser("report", help="Generate status report for a budget period")
    period_group = report_parser.add_mutually_exclusive_group(required=True)
    period_group.add_argument("--today", action="store_true", help="Report for current IST budget period")
    period_group.add_argument("--date", help="Report for historical period (YYYY-MM-DD)")
    report_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text)")

    args = parser.parse_args()

    if args.command == "report":
        if args.today:
            period_id = daily_mailbox_planner.get_ist_budget_period()
        else:
            date_clean = args.date.strip()
            period_id = f"{date_clean}-IST" if not date_clean.endswith("-IST") else date_clean

        rep = generate_period_report(period_id)
        if args.format == "json":
            print(json.dumps(rep, indent=2))
        else:
            print(format_text_report(rep))
    else:
        # Default legacy status report
        period_id = daily_mailbox_planner.get_ist_budget_period()
        rep = generate_period_report(period_id)
        print(format_text_report(rep))


if __name__ == "__main__":
    main()
