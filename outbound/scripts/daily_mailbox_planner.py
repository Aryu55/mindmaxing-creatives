#!/usr/bin/env python3
"""
Mindmaxing Nightly Reviewer & Mailbox Control Engine v2.1 (Revised)
- Evaluates all 25 mailboxes against evidence for the 00:30-00:30 IST budget period.
- Produces explicit decisions: INCREASE, KEEP, DECREASE, or PAUSE with reason, scope, and recovery condition.
- CLI interface:
    review --apply   : Evaluates period and persists decisions to `mailbox_daily_decisions`.
    review --shadow  : Dry-run evaluation without mutating database or send allowances.
- Strictly idempotent: Repeated `--apply` runs with identical evidence do not create duplicate revisions.
"""

import argparse
import fcntl
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")
MAILBOXES_FILE = os.path.join(CONFIG_DIR, "mailboxes.json")
TEST_INBOXES_FILE = os.path.join(CONFIG_DIR, "test_inboxes.json")
LOCK_FILE = "/tmp/daily_mailbox_planner.lock"

POLICY_VERSION = "v2.1-revised"
IST_TZ = timezone(timedelta(hours=5, minutes=30))

LEVEL_BASE_CAPS = {
    1: {"campaign": 1, "diagnostic": 1},
    2: {"campaign": 2, "diagnostic": 1},
    3: {"campaign": 3, "diagnostic": 1}
}


def get_ist_budget_period(dt_utc: Optional[datetime] = None) -> str:
    """
    Computes the IST budget period identifier for a given UTC timestamp.
    Budget period runs from 00:30 IST to next 00:30 IST.
    Offsetting by -30 minutes maps [00:30 IST, next 00:30 IST) to the start day.
    Example: 2026-09-22 00:30 IST -> '2026-09-22-IST'
             2026-09-21 19:00 UTC -> '2026-09-22-IST'
    """
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    elif dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    dt_ist = dt_utc.astimezone(IST_TZ)
    shifted = dt_ist - timedelta(minutes=30)
    return f"{shifted.strftime('%Y-%m-%d')}-IST"


def get_ist_budget_period_bounds_utc(period_id: str) -> Tuple[datetime, datetime]:
    """
    Returns (start_utc, end_utc) for a given period_id (e.g. '2026-09-22-IST').
    """
    date_str = period_id.replace("-IST", "")
    start_ist = datetime.strptime(date_str, "%Y-%m-%d").replace(
        hour=0, minute=30, second=0, microsecond=0, tzinfo=IST_TZ
    )
    end_ist = start_ist + timedelta(days=1)
    return start_ist.astimezone(timezone.utc), end_ist.astimezone(timezone.utc)


def load_mailboxes_config() -> List[Dict[str, Any]]:
    if os.path.exists(MAILBOXES_FILE):
        with open(MAILBOXES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_seeds_config() -> List[Dict[str, Any]]:
    if os.path.exists(TEST_INBOXES_FILE):
        with open(TEST_INBOXES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def plan_day(
    conn: sqlite3.Connection,
    period_id: Optional[str] = None,
    shadow: bool = False,
    date_utc: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates all 25 mailboxes against evidence and computes volume decisions.
    If shadow=True, does not write to database or promote mailboxes.
    """
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    if not period_id:
        if date_utc:
            period_id = f"{date_utc}-IST" if not date_utc.endswith("-IST") else date_utc
        else:
            period_id = get_ist_budget_period(now)

    date_label = period_id.replace("-IST", "")

    # Historical time windows
    one_hour_ago_iso = (now - timedelta(hours=1)).isoformat()
    twenty_four_hours_ago_iso = (now - timedelta(hours=24)).isoformat()
    seventy_two_hours_ago_iso = (now - timedelta(hours=72)).isoformat()
    seven_days_ago_iso = (now - timedelta(days=7)).isoformat()
    forty_eight_hours_ago_iso = (now - timedelta(hours=48)).isoformat()

    mailboxes = load_mailboxes_config()
    seeds = load_seeds_config()

    # Seed health lookup (requires scan <= 60m)
    c.execute("SELECT mailbox, status, last_scan_at FROM collector_health WHERE mailbox_type = 'test_inbox'")
    seed_health_rows = {row["mailbox"]: dict(row) for row in c.fetchall()}
    healthy_seeds_count = sum(
        1 for s in seeds
        if seed_health_rows.get(s["email"], {}).get("status") == "healthy"
        and seed_health_rows.get(s["email"], {}).get("last_scan_at")
        and seed_health_rows.get(s["email"], {}).get("last_scan_at") >= one_hour_ago_iso
    )

    epoch_days = int(now.timestamp() // 86400)
    decisions: List[Dict[str, Any]] = []

    for idx, mb in enumerate(mailboxes):
        email_addr = mb["email"]
        domain = mb["domain"]

        # 1. Fetch current level & status
        c.execute("SELECT level, level_updated_at, status, paused_reason FROM mailbox_levels WHERE mailbox = ?", (email_addr,))
        m_level_row = c.fetchone()
        if not m_level_row:
            current_level = 1
            level_updated_iso = now_iso
            mb_status = "active"
            paused_reason = None
            if not shadow:
                c.execute("""
                    INSERT OR IGNORE INTO mailbox_levels (mailbox, domain, level, level_updated_at, status)
                    VALUES (?, ?, 1, ?, 'active')
                """, (email_addr, domain, now_iso))
        else:
            current_level = m_level_row["level"]
            level_updated_iso = m_level_row["level_updated_at"] or now_iso
            mb_status = m_level_row["status"]
            paused_reason = m_level_row["paused_reason"]

        baseline_cap = LEVEL_BASE_CAPS.get(current_level, {}).get("campaign", 1)
        base_diag_cap = LEVEL_BASE_CAPS.get(current_level, {}).get("diagnostic", 1)

        effective_camp_cap = baseline_cap
        effective_diag_cap = base_diag_cap
        action = "KEEP"
        reason = "Baseline allowance maintained"
        scope = "mailbox"
        recovery_condition: Optional[str] = None
        evidence_ids: List[str] = []

        evidence_summary: Dict[str, Any] = {
            "current_level": current_level,
            "baseline_cap": baseline_cap,
            "base_diagnostic_cap": base_diag_cap,
            "period_id": period_id
        }

        # Assigned rotating seed for diagnostic
        assigned_seed = seeds[(idx + epoch_days) % len(seeds)]["email"] if seeds else None
        evidence_summary["assigned_seed"] = assigned_seed

        # --- EVALUATION RULES IN PRIORITY ORDER ---

        # Rule 1: Manual or Circuit-Breaker Pause on Mailbox
        if mb_status == "paused":
            effective_camp_cap = 0
            action = "PAUSE"
            reason = f"Mailbox is paused: {paused_reason}"
            scope = "mailbox"
            recovery_condition = "Manual intervention or recorded administrative resumption"

        # Rule 2: Domain-level Pause
        if action != "PAUSE":
            c.execute("""
                SELECT mailbox, paused_reason FROM mailbox_levels 
                WHERE domain = ? AND status = 'paused' AND paused_reason LIKE '%DOMAIN%'
            """, (domain,))
            dom_paused = c.fetchone()
            if dom_paused:
                effective_camp_cap = 0
                action = "PAUSE"
                reason = f"Domain {domain} is paused: {dom_paused['paused_reason']}"
                scope = "domain"
                recovery_condition = "Recorded domain resolution and clean diagnostic"

        # Rule 3: Confirmed Domain Authentication Failure on Diagnostic (7d)
        if action != "PAUSE":
            c.execute("""
                SELECT message_id, recipient_email, auth_spf, auth_dkim, auth_dmarc, sent_at
                FROM messages
                WHERE sender_domain = ? AND purpose = 'test'
                  AND (auth_spf = 'fail' OR auth_dkim = 'fail' OR auth_dmarc = 'fail')
                  AND sent_at >= ?
                ORDER BY sent_at DESC LIMIT 1
            """, (domain, seven_days_ago_iso))
            auth_fail = c.fetchone()
            if auth_fail:
                effective_camp_cap = 0
                action = "PAUSE"
                reason = f"Confirmed authentication failure on domain {domain} (SPF={auth_fail['auth_spf']}, DKIM={auth_fail['auth_dkim']}, DMARC={auth_fail['auth_dmarc']})"
                scope = "domain"
                recovery_condition = "Recorded DNS/auth configuration resolution and clean diagnostic"
                evidence_ids.append(auth_fail["message_id"])
                evidence_summary["auth_failure"] = dict(auth_fail)

        # Rule 4: Diagnostic Test Observed in SPAM Folder (7d)
        if action != "PAUSE":
            c.execute("""
                SELECT m.message_id, m.recipient_email, de.detected_at, de.folder
                FROM messages m
                JOIN delivery_events de ON m.message_id = de.message_id
                WHERE m.sender_email = ? AND m.purpose = 'test' 
                  AND de.folder = 'SPAM' AND de.detected_at >= ?
                ORDER BY de.detected_at DESC LIMIT 1
            """, (email_addr, seven_days_ago_iso))
            spam_event = c.fetchone()
            if spam_event:
                effective_camp_cap = 0
                action = "PAUSE"
                reason = f"Diagnostic test observed in SPAM folder on {spam_event['detected_at']}"
                scope = "mailbox"
                recovery_condition = "Two clean recovery diagnostics on separate days and different seeds. Resumes at baseline 1."
                evidence_ids.append(spam_event["message_id"])
                evidence_summary["spam_event"] = dict(spam_event)

        # Rule 5: Sender Reply/Bounce Monitoring Freshness (Scan within 60m)
        c.execute("SELECT status, last_scan_at, error_message FROM collector_health WHERE mailbox = ?", (email_addr,))
        health = c.fetchone()
        evidence_summary["collector_health"] = dict(health) if health else None

        if action != "PAUSE":
            if not health or not health["last_scan_at"]:
                effective_camp_cap = 0
                action = "PAUSE"
                reason = "No monitoring scan record found for sender"
                scope = "mailbox"
                recovery_condition = "Two complete scans without error and qualifying diagnostic <= 72h"
            elif health["status"] == "error":
                effective_camp_cap = 0
                action = "PAUSE"
                reason = f"Monitoring collector reporting error: {health['error_message']}"
                scope = "mailbox"
                recovery_condition = "Two complete scans without error and qualifying diagnostic <= 72h"
            elif health["last_scan_at"] < one_hour_ago_iso:
                effective_camp_cap = 0
                action = "PAUSE"
                reason = f"Sender monitoring scan stale (>60m ago: {health['last_scan_at']})"
                scope = "mailbox"
                recovery_condition = "Two complete scans without error and qualifying diagnostic <= 72h"

        # Rule 6: Readiness Gate (First Send) vs Diagnostic Recency
        # Has this mailbox EVER passed a diagnostic outside Spam with passing SPF/DKIM/DMARC?
        c.execute("""
            SELECT message_id, sent_at, delivery_state, auth_spf, auth_dkim, auth_dmarc
            FROM messages
            WHERE sender_email = ? AND purpose = 'test'
              AND delivery_state IN ('inbox', 'promotions')
              AND auth_spf = 'pass' AND auth_dkim = 'pass' AND auth_dmarc = 'pass'
            ORDER BY sent_at DESC LIMIT 1
        """, (email_addr,))
        ever_clean = c.fetchone()

        if not ever_clean and action != "PAUSE":
            # Mailbox has never passed readiness!
            effective_camp_cap = 0
            action = "PAUSE"
            reason = "Awaiting first clean diagnostic in Inbox with passing SPF/DKIM/DMARC"
            scope = "mailbox"
            recovery_condition = "Observe 1 registered diagnostic outside Spam with passing SPF/DKIM/DMARC and active monitoring"
        elif ever_clean and action != "PAUSE":
            # Mailbox passed readiness historically! Check recency (<72h)
            c.execute("""
                SELECT message_id, sent_at, delivery_state, auth_spf, auth_dkim, auth_dmarc
                FROM messages
                WHERE sender_email = ? AND purpose = 'test'
                  AND delivery_state IN ('inbox', 'promotions')
                  AND auth_spf = 'pass' AND auth_dkim = 'pass' AND auth_dmarc = 'pass'
                  AND sent_at >= ?
                ORDER BY sent_at DESC LIMIT 1
            """, (email_addr, seventy_two_hours_ago_iso))
            recent_clean = c.fetchone()
            if not recent_clean:
                effective_camp_cap = 0
                action = "PAUSE"
                reason = "HOLD_DIAGNOSTIC_EXPIRED: Last qualifying diagnostic older than 72 hours"
                scope = "mailbox"
                recovery_condition = "Observe clean diagnostic outside Spam with passing SPF/DKIM/DMARC"
            else:
                evidence_ids.append(recent_clean["message_id"])
                evidence_summary["recent_clean_diag"] = dict(recent_clean)

        # Rule 7: Seed Visibility Loss Grace Period
        # If seeds unavailable, freeze increases (action=KEEP), but allow baseline if diagnostic <= 72h
        if action == "KEEP" and healthy_seeds_count == 0:
            reason = "Seed visibility temporarily unavailable; growth frozen; baseline preserved (diagnostic <= 72h)"
            evidence_summary["seed_visibility_freeze"] = True

        # Rule 8: 3 Consecutive Pre-Acceptance 4xx Failures within 24h -> DECREASE
        c.execute("""
            SELECT message_id, smtp_status, smtp_code, sent_at FROM messages
            WHERE sender_email = ? AND sent_at >= ?
            ORDER BY sent_at DESC LIMIT 3
        """, (email_addr, twenty_four_hours_ago_iso))
        recent_24h_sends = c.fetchall()
        if len(recent_24h_sends) == 3 and all(r["smtp_status"] == "temp_failure" for r in recent_24h_sends):
            # Pre-acceptance 4xx failures: reduce baseline by 1 (min 1)
            new_level = max(1, current_level - 1)
            effective_camp_cap = LEVEL_BASE_CAPS[new_level]["campaign"]
            action = "DECREASE"
            reason = "Three consecutive pre-acceptance 4xx failures in 24h: 1h backoff and baseline reduced by 1"
            scope = "mailbox"
            recovery_condition = "1 hour backoff elapsed and clean subsequent send"
            for r in recent_24h_sends:
                evidence_ids.append(r["message_id"])
            if not shadow and new_level != current_level:
                c.execute("""
                    UPDATE mailbox_levels
                    SET level = ?, level_updated_at = ?
                    WHERE mailbox = ?
                """, (new_level, now_iso, email_addr))
                current_level = new_level

        # Rule 9: Promotion Eligibility Check (INCREASE: +1, max 3)
        # Conditions: 7 days at level, 5 accepted sends >= 48h, 3 clean tests across >= 2 seeds in 7d, latest <= 72h
        if action == "KEEP" and current_level < 3 and healthy_seeds_count > 0:
            clean_lu_str = level_updated_iso.replace("Z", "+00:00")
            try:
                dt_lu = datetime.fromisoformat(clean_lu_str)
                if dt_lu.tzinfo is None:
                    dt_lu = dt_lu.replace(tzinfo=timezone.utc)
            except Exception:
                dt_lu = now

            days_at_level = (now - dt_lu).total_seconds() / 86400.0

            # 5 accepted campaign messages observed >= 48h
            c.execute("""
                SELECT message_id FROM messages
                WHERE sender_email = ? AND purpose = 'campaign'
                  AND smtp_status = 'accepted' AND sent_at <= ? AND sent_at >= ?
            """, (email_addr, forty_eight_hours_ago_iso, level_updated_iso))
            accepted_camp_rows = c.fetchall()
            accepted_camp_cnt = len(accepted_camp_rows)

            # 3 distinct clean diagnostics across >= 2 seeds in 7d with verified SPF and DKIM pass
            c.execute("""
                SELECT message_id, recipient_email FROM messages
                WHERE sender_email = ? AND purpose = 'test'
                  AND delivery_state IN ('inbox', 'promotions')
                  AND auth_spf = 'pass' AND auth_dkim = 'pass' AND auth_dmarc = 'pass'
                  AND sent_at >= ?
            """, (email_addr, seven_days_ago_iso))
            diag_rows = c.fetchall()
            distinct_seeds = len(set(r["recipient_email"] for r in diag_rows))
            diag_count = len(diag_rows)

            # Check for sibling domain spam freeze
            c.execute("""
                SELECT m.message_id FROM messages m
                JOIN delivery_events de ON m.message_id = de.message_id
                WHERE m.sender_domain = ? AND m.purpose = 'test'
                  AND de.folder = 'SPAM' AND de.detected_at >= ?
                LIMIT 1
            """, (domain, seven_days_ago_iso))
            sibling_spam = c.fetchone()

            evidence_summary["days_at_level"] = round(days_at_level, 2)
            evidence_summary["accepted_camp_48h_cnt"] = accepted_camp_cnt
            evidence_summary["clean_diag_count_7d"] = diag_count
            evidence_summary["distinct_seeds_7d"] = distinct_seeds
            evidence_summary["sibling_spam_freeze"] = bool(sibling_spam)

            if days_at_level >= 7.0 and accepted_camp_cnt >= 5 and diag_count >= 3 and distinct_seeds >= 2 and not sibling_spam:
                action = "INCREASE"
                new_level = current_level + 1
                effective_camp_cap = LEVEL_BASE_CAPS[new_level]["campaign"]
                reason = f"Promoted from Level {current_level} to Level {new_level} (7d mature, 5 sends @ 48h+, 3 clean diagnostics across {distinct_seeds} seeds)"
                for r in accepted_camp_rows[:5]:
                    evidence_ids.append(r["message_id"])
                for r in diag_rows[:3]:
                    evidence_ids.append(r["message_id"])
                if not shadow:
                    c.execute("""
                        UPDATE mailbox_levels
                        SET level = ?, level_updated_at = ?
                        WHERE mailbox = ?
                    """, (new_level, now_iso, email_addr))
                    current_level = new_level

        # Compute revision & decision_id
        c.execute("""
            SELECT revision, decision_action, effective_campaign_cap, decision_reason
            FROM mailbox_daily_decisions 
            WHERE mailbox = ? AND period_id = ?
            ORDER BY revision DESC LIMIT 1
        """, (email_addr, period_id))
        last_decision = c.fetchone()

        if last_decision:
            curr_rev = last_decision["revision"]
            # Idempotency check: has anything material changed?
            material_change = (
                last_decision["decision_action"] != action or
                last_decision["effective_campaign_cap"] != effective_camp_cap or
                last_decision["decision_reason"] != reason
            )
            next_rev = curr_rev + 1 if material_change else curr_rev
            skip_insert = not material_change
        else:
            next_rev = 1
            skip_insert = False

        decision_id = f"DEC-{period_id}-{email_addr}-r{next_rev}"

        if not shadow and not skip_insert:
            c.execute("""
                INSERT INTO mailbox_daily_decisions (
                    decision_id, period_id, decision_date_utc, mailbox, domain,
                    policy_version, baseline_cap, current_level,
                    effective_campaign_cap, effective_diagnostic_cap,
                    decision_action, decision_reason, scope, recovery_condition,
                    evidence_summary_json, evidence_ids, campaign_name, revision, created_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
            """, (
                decision_id, period_id, date_label, email_addr, domain,
                POLICY_VERSION, baseline_cap, current_level,
                effective_camp_cap, effective_diag_cap,
                action, reason, scope, recovery_condition,
                json.dumps(evidence_summary), json.dumps(evidence_ids), "all", next_rev, now_iso
            ))

        decisions.append({
            "decision_id": decision_id,
            "period_id": period_id,
            "mailbox": email_addr,
            "domain": domain,
            "level": current_level,
            "baseline_cap": baseline_cap,
            "campaign_cap": effective_camp_cap,
            "diagnostic_cap": effective_diag_cap,
            "action": action,
            "reason": reason,
            "scope": scope,
            "recovery_condition": recovery_condition,
            "revision": next_rev,
            "evidence": evidence_summary,
            "skipped_insert": skip_insert if not shadow else True
        })

    if not shadow:
        conn.commit()

        # Write reports
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_md_path = os.path.join(REPORTS_DIR, f"nightly_review_{period_id}.md")
        report_json_path = os.path.join(DATA_DIR, f"nightly_review_{period_id}.json")

        with open(report_json_path, "w", encoding="utf-8") as f:
            json.dump({
                "period_id": period_id,
                "policy_version": POLICY_VERSION,
                "generated_at": now_iso,
                "decisions": decisions
            }, f, indent=2)

        render_markdown_report(decisions, period_id, now_iso, report_md_path)
    else:
        report_md_path = None
        report_json_path = None

    return {
        "period_id": period_id,
        "mode": "shadow" if shadow else "apply",
        "total_mailboxes": len(decisions),
        "active_capacity": sum(d["campaign_cap"] for d in decisions),
        "report_md": report_md_path,
        "report_json": report_json_path,
        "decisions": decisions
    }


def render_markdown_report(decisions: List[Dict[str, Any]], period_id: str, generated_at: str, out_path: str):
    total_capacity = sum(d["campaign_cap"] for d in decisions)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Nightly Review & Mailbox Control Report: {period_id}\n\n")
        f.write(f"**Policy Version:** `{POLICY_VERSION}`  \n")
        f.write(f"**Generated:** {generated_at} (UTC)  \n")
        f.write(f"**Total Senders Evaluated:** {len(decisions)}  \n")
        f.write(f"**Total Effective Campaign Capacity:** **{total_capacity}** messages  \n\n")
        f.write("> [!NOTE]\n")
        f.write("> Telemetry reflects controlled personal Gmail seeds and explicit recipient responses only. Unused allowances do not accumulate across periods.\n\n")
        f.write("---\n\n")

        f.write("## 1. Mailbox Decision Ledger\n\n")
        f.write("| # | Mailbox | Domain | Lvl | Cap | Diag | Action | Reason | Recovery Condition |\n")
        f.write("| :-: | :--- | :--- | :-: | :-: | :-: | :--- | :--- | :--- |\n")

        for i, d in enumerate(decisions, 1):
            act_badge = f"`{d['action']}`"
            rec_text = d["recovery_condition"] or "—"
            f.write(f"| {i:02d} | `{d['mailbox']}` | `{d['domain']}` | {d['level']} | **{d['campaign_cap']}** | {d['diagnostic_cap']} | {act_badge} | {d['reason']} | {rec_text} |\n")

        f.write("\n---\n")


def main():
    parser = argparse.ArgumentParser(description="Mindmaxing Nightly Reviewer & Mailbox Control Engine")
    subparsers = parser.add_subparsers(dest="command")

    review_parser = subparsers.add_parser("review", help="Execute review")
    review_group = review_parser.add_mutually_exclusive_group(required=True)
    review_group.add_argument("--apply", action="store_true", help="Apply and persist review decisions to database")
    review_group.add_argument("--shadow", action="store_true", help="Calculate decisions in shadow mode without database mutations")
    review_parser.add_argument("--period", help="Explicit budget period identifier (e.g. 2026-09-22-IST)")
    review_parser.add_argument("--json", action="store_true", help="Output summary in JSON format")

    args = parser.parse_args()

    if not args.command:
        # Default backward-compatible execution: review --apply
        is_shadow = False
        period_arg = None
        is_json = False
    else:
        is_shadow = bool(args.shadow)
        period_arg = args.period
        is_json = bool(args.json)

    if not os.path.exists(DB_PATH):
        print(f"Error: Database file does not exist at {DB_PATH}")
        sys.exit(1)

    # Single-instance lock protection
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Error: Another nightly review instance is currently running. Exiting.")
        sys.exit(1)

    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        res = plan_day(conn, period_id=period_arg, shadow=is_shadow)
        conn.close()

        if is_json:
            print(json.dumps(res, indent=2))
        else:
            mode_str = "[SHADOW MODE]" if is_shadow else "[APPLIED]"
            print(f"Nightly review complete {mode_str} for {res['period_id']}.")
            print(f"Total mailboxes evaluated: {res['total_mailboxes']}")
            print(f"Total effective daily campaign capacity: {res['active_capacity']}")
            if res.get("report_md"):
                print(f"Markdown report: {res['report_md']}")
                print(f"JSON summary: {res['report_json']}")
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
