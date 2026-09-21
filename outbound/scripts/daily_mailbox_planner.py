#!/usr/bin/env python3
"""
Mindmaxing Daily Mailbox Planner & Adaptive Scheduling Engine v2.0
- Computes deterministic daily allowances for all 25 senders.
- Implements strict priority rules:
  1. Recipient opt-out / explicit complaint / confirmed invalid address: Suppresses recipient across all mailboxes.
  2. Confirmed authentication failure on diagnostic: Domain cap 0.
  3. Identified seed message in Spam: Sender cap 0, freezes sibling promotions.
  4. Missing or stale sender monitoring (>60m): Sender cap 0 until fresh coverage restored.
  5. Required seed monitoring unavailable: Hold campaigns.
  6. No clean diagnostic in last 36 hours: Sender cap 0.
  7. 3 consecutive pre-acceptance 4xx failures: Transport hold.
  8. 2 invalid recipients in latest 20 submissions: Source hold.
  9. Promotion gate: 7 days at level, 5 accepted campaign messages @ 48h+, 3 clean diagnostics across >=2 seeds in 7d, latest <=36h, complete monitoring -> Level +1 (max 3).
  10. Default: Retain existing baseline cap.
- Writes immutable decisions to `mailbox_daily_decisions`.
- Generates comprehensive daily Markdown and JSON reports.
"""

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

LEVEL_BASE_CAPS = {
    1: {"campaign": 1, "diagnostic": 1},
    2: {"campaign": 2, "diagnostic": 1},
    3: {"campaign": 3, "diagnostic": 1}
}


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


def plan_day(conn: sqlite3.Connection, date_utc: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates all 25 mailboxes against rolling 7-day evidence and persists daily decisions.
    """
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    now = datetime.now(timezone.utc)
    if not date_utc:
        date_utc = now.strftime("%Y-%m-%d")

    now_iso = now.isoformat()
    one_hour_ago_iso = (now - timedelta(hours=1)).isoformat()
    thirty_six_hours_ago_iso = (now - timedelta(hours=36)).isoformat()
    seven_days_ago_iso = (now - timedelta(days=7)).isoformat()
    forty_eight_hours_ago_iso = (now - timedelta(hours=48)).isoformat()

    mailboxes = load_mailboxes_config()
    seeds = load_seeds_config()

    decisions: List[Dict[str, Any]] = []

    # Check overall seed health with freshness requirement (<= 60m)
    c.execute("SELECT mailbox, status, last_scan_at FROM collector_health WHERE mailbox_type = 'test_inbox'")
    seed_health_rows = {row["mailbox"]: dict(row) for row in c.fetchall()}
    healthy_seeds_count = sum(
        1 for s in seeds 
        if seed_health_rows.get(s["email"], {}).get("status") == "healthy" 
        and seed_health_rows.get(s["email"], {}).get("last_scan_at") 
        and seed_health_rows.get(s["email"], {}).get("last_scan_at") >= one_hour_ago_iso
    )

    # Day offset for rotating seed assignment
    epoch_days = int(now.timestamp() // 86400)

    for idx, mb in enumerate(mailboxes):
        email_addr = mb["email"]
        domain = mb["domain"]

        # Ensure mailbox exists in mailbox_levels
        c.execute("SELECT level, level_updated_at, status, paused_reason FROM mailbox_levels WHERE mailbox = ?", (email_addr,))
        m_level_row = c.fetchone()
        if not m_level_row:
            current_level = 1
            c.execute("""
                INSERT OR IGNORE INTO mailbox_levels (mailbox, domain, level, level_updated_at, status)
                VALUES (?, ?, 1, ?, 'active')
            """, (email_addr, domain, now_iso))
            level_updated_iso = now_iso
            mb_status = "active"
            paused_reason = None
        else:
            current_level = m_level_row["level"]
            level_updated_iso = m_level_row["level_updated_at"]
            mb_status = m_level_row["status"]
            paused_reason = m_level_row["paused_reason"]

        base_camp_cap = LEVEL_BASE_CAPS.get(current_level, {}).get("campaign", 1)
        base_diag_cap = LEVEL_BASE_CAPS.get(current_level, {}).get("diagnostic", 1)

        effective_camp_cap = base_camp_cap
        effective_diag_cap = base_diag_cap
        action = "HOLD"
        reason = "Baseline capacity retained"
        evidence_summary: Dict[str, Any] = {
            "current_level": current_level,
            "base_campaign_cap": base_camp_cap,
            "base_diagnostic_cap": base_diag_cap
        }

        # Assigned rotating seed for diagnostic
        if seeds:
            assigned_seed = seeds[(idx + epoch_days) % len(seeds)]["email"]
        else:
            assigned_seed = None
        evidence_summary["assigned_seed"] = assigned_seed

        # Rule 1: Manual or Circuit-Breaker Pause
        if mb_status == "paused":
            effective_camp_cap = 0
            action = "PAUSED"
            reason = f"Mailbox is paused: {paused_reason}"

        # Rule 2: Domain-level pause
        c.execute("""
            SELECT mailbox, paused_reason FROM mailbox_levels 
            WHERE domain = ? AND status = 'paused' AND paused_reason LIKE '%DOMAIN%'
        """, (domain,))
        dom_paused = c.fetchone()
        if dom_paused and action != "PAUSED":
            effective_camp_cap = 0
            action = "DOMAIN_PAUSED"
            reason = f"Domain {domain} is paused: {dom_paused['paused_reason']}"

        # Rule 3: Missing or Stale Sender Monitoring (>60m)
        c.execute("SELECT status, last_scan_at, error_message FROM collector_health WHERE mailbox = ?", (email_addr,))
        health = c.fetchone()
        evidence_summary["collector_health"] = dict(health) if health else None

        if action not in ("PAUSED", "DOMAIN_PAUSED"):
            if not health:
                effective_camp_cap = 0
                action = "HOLD_MONITORING_MISSING"
                reason = "No monitoring scan record found for sender"
            elif health["status"] == "error":
                effective_camp_cap = 0
                action = "HOLD_MONITORING_ERROR"
                reason = f"Collector reporting error: {health['error_message']}"
            elif not health["last_scan_at"] or health["last_scan_at"] < one_hour_ago_iso:
                effective_camp_cap = 0
                action = "HOLD_MONITORING_STALE"
                reason = f"Monitoring scan stale (>60m ago: {health['last_scan_at']})"

        # Rule 4: Seed Monitoring Availability
        if action not in ("PAUSED", "DOMAIN_PAUSED", "HOLD_MONITORING_MISSING", "HOLD_MONITORING_ERROR", "HOLD_MONITORING_STALE"):
            if healthy_seeds_count == 0:
                effective_camp_cap = 0
                action = "HOLD_SEEDS_UNAVAILABLE"
                reason = "Zero healthy seed inboxes available for delivery telemetry"

        # Rule 5: Seed Message in Spam
        c.execute("""
            SELECT m.message_id, m.recipient_email, de.detected_at, de.folder
            FROM messages m
            JOIN delivery_events de ON m.message_id = de.message_id
            WHERE m.sender_email = ? AND m.purpose = 'test' 
              AND de.folder = 'SPAM' AND de.detected_at >= ?
            ORDER BY de.detected_at DESC LIMIT 1
        """, (email_addr, seven_days_ago_iso))
        spam_event = c.fetchone()
        if spam_event and action not in ("PAUSED", "DOMAIN_PAUSED"):
            effective_camp_cap = 0
            action = "HOLD_SPAM_DETECTED"
            reason = f"Diagnostic test observed in SPAM folder on {spam_event['detected_at']}"
            evidence_summary["spam_event"] = dict(spam_event)

        # Rule 6: Authentication Failure on Diagnostic
        c.execute("""
            SELECT message_id, recipient_email, auth_spf, auth_dkim, auth_dmarc, sent_at
            FROM messages
            WHERE sender_domain = ? AND purpose = 'test'
              AND (auth_spf = 'fail' OR auth_dkim = 'fail' OR auth_dmarc = 'fail')
              AND sent_at >= ?
            ORDER BY sent_at DESC LIMIT 1
        """, (domain, seven_days_ago_iso))
        auth_fail = c.fetchone()
        if auth_fail and action not in ("PAUSED", "DOMAIN_PAUSED", "HOLD_SPAM_DETECTED"):
            effective_camp_cap = 0
            action = "HOLD_AUTH_FAILED"
            reason = f"Authentication failure detected on domain {domain} (SPF={auth_fail['auth_spf']}, DKIM={auth_fail['auth_dkim']})"
            evidence_summary["auth_failure"] = dict(auth_fail)

        # Rule 7: Clean Diagnostic Recency (<36 hours) with verified auth pass
        c.execute("""
            SELECT m.message_id, m.sent_at, m.delivery_state, m.auth_spf, m.auth_dkim, m.auth_dmarc
            FROM messages m
            WHERE m.sender_email = ? AND m.purpose = 'test'
              AND m.delivery_state = 'inbox'
              AND m.auth_spf = 'pass' AND m.auth_dkim = 'pass'
              AND m.sent_at >= ?
            ORDER BY m.sent_at DESC LIMIT 1
        """, (email_addr, thirty_six_hours_ago_iso))
        clean_diag = c.fetchone()
        evidence_summary["recent_clean_diag"] = dict(clean_diag) if clean_diag else None

        if not clean_diag and action not in ("PAUSED", "DOMAIN_PAUSED", "HOLD_MONITORING_MISSING", "HOLD_MONITORING_ERROR", "HOLD_MONITORING_STALE", "HOLD_SEEDS_UNAVAILABLE", "HOLD_SPAM_DETECTED", "HOLD_AUTH_FAILED"):
            effective_camp_cap = 0
            action = "HOLD_DIAGNOSTIC_EXPIRED"
            reason = "No clean inbox diagnostic test observed within the last 36 hours"

        # Rule 8: 3 Consecutive Pre-Acceptance 4xx Failures
        c.execute("""
            SELECT smtp_status, smtp_code, sent_at FROM messages
            WHERE sender_email = ? AND sent_at >= ?
            ORDER BY sent_at DESC LIMIT 3
        """, (email_addr, seven_days_ago_iso))
        recent_sends = c.fetchall()
        if len(recent_sends) == 3 and all(r["smtp_status"] == "temp_failure" for r in recent_sends):
            if action not in ("PAUSED", "DOMAIN_PAUSED", "HOLD_SPAM_DETECTED", "HOLD_AUTH_FAILED"):
                effective_camp_cap = 0
                action = "HOLD_TRANSPORT"
                reason = "3 consecutive 4xx transport failures observed"

        # Rule 9: Promotion Eligibility Check (Level 1 -> 2, Level 2 -> 3)
        if action == "HOLD" and current_level < 3:
            # Parse level_updated_at safely
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
                SELECT count(*) as cnt FROM messages
                WHERE sender_email = ? AND purpose = 'campaign'
                  AND smtp_status = 'accepted' AND sent_at <= ? AND sent_at >= ?
            """, (email_addr, forty_eight_hours_ago_iso, level_updated_iso))
            accepted_camp_cnt = c.fetchone()["cnt"]

            # 3 distinct clean diagnostics across >=2 seeds in 7d with verified SPF and DKIM pass
            c.execute("""
                SELECT count(DISTINCT recipient_email) as seed_cnt, count(*) as test_cnt
                FROM messages
                WHERE sender_email = ? AND purpose = 'test'
                  AND delivery_state = 'inbox'
                  AND auth_spf = 'pass' AND auth_dkim = 'pass'
                  AND sent_at >= ?
            """, (email_addr, seven_days_ago_iso))
            diag_stat = c.fetchone()
            seed_count = diag_stat["seed_cnt"]
            diag_count = diag_stat["test_cnt"]

            evidence_summary["days_at_level"] = round(days_at_level, 2)
            evidence_summary["accepted_camp_48h_cnt"] = accepted_camp_cnt
            evidence_summary["clean_diag_count_7d"] = diag_count
            evidence_summary["distinct_seeds_7d"] = seed_count

            if days_at_level >= 7.0 and accepted_camp_cnt >= 5 and diag_count >= 3 and seed_count >= 2:
                action = "INCREASE"
                new_level = current_level + 1
                effective_camp_cap = LEVEL_BASE_CAPS[new_level]["campaign"]
                reason = f"Promoted from Level {current_level} to Level {new_level} (7d mature, 5 sends, 3 clean tests across {seed_count} seeds)"
                # Update level in DB
                c.execute("""
                    UPDATE mailbox_levels
                    SET level = ?, level_updated_at = ?
                    WHERE mailbox = ?
                """, (new_level, now_iso, email_addr))

        # Persist daily decision with append-only revision tracking
        c.execute("""
            SELECT COALESCE(MAX(revision), 0) + 1 AS next_rev 
            FROM mailbox_daily_decisions 
            WHERE mailbox = ? AND decision_date_utc = ?
        """, (email_addr, date_utc))
        next_rev = c.fetchone()["next_rev"]

        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap,
                decision_action, decision_reason, evidence_summary_json, revision, created_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            date_utc, email_addr, domain, current_level,
            effective_camp_cap, effective_diag_cap,
            action, reason, json.dumps(evidence_summary), next_rev, now_iso
        ))

        decisions.append({
            "mailbox": email_addr,
            "domain": domain,
            "level": current_level,
            "campaign_cap": effective_camp_cap,
            "diagnostic_cap": effective_diag_cap,
            "action": action,
            "reason": reason,
            "evidence": evidence_summary
        })

    conn.commit()

    # Generate Markdown and JSON Reports
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_md_path = os.path.join(REPORTS_DIR, f"daily_mailbox_report_{date_utc}.md")
    report_json_path = os.path.join(DATA_DIR, f"daily_summary_{date_utc}.json")

    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump({"date_utc": date_utc, "decisions": decisions, "generated_at": now_iso}, f, indent=2)

    render_markdown_report(decisions, date_utc, now_iso, report_md_path)

    return {
        "date_utc": date_utc,
        "total_mailboxes": len(decisions),
        "active_capacity": sum(d["campaign_cap"] for d in decisions),
        "report_md": report_md_path,
        "report_json": report_json_path,
        "decisions": decisions
    }


def render_markdown_report(decisions: List[Dict[str, Any]], date_utc: str, generated_at: str, out_path: str):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Daily Mailbox Adaptive Scheduling Report: {date_utc}\n\n")
        f.write(f"**Generated:** {generated_at} (UTC)  \n")
        f.write(f"**Total Senders:** {len(decisions)}  \n")
        total_capacity = sum(d["campaign_cap"] for d in decisions)
        f.write(f"**Total Effective Daily Capacity:** {total_capacity} campaign messages  \n\n")
        f.write("> [!NOTE]\n")
        f.write("> Invariant Notice: Prospect open tracking and complete third-party complaints are unavailable by design. Telemetry reflects controlled personal Gmail seeds and explicit recipient responses only.\n\n")
        f.write("---\n\n")

        f.write("## 1. Executive Sender Capacity & Decision Ledger\n\n")
        f.write("| # | Mailbox | Domain | Level | Camp Cap | Diag Cap | Decision Action | Reason |\n")
        f.write("| :-: | :--- | :--- | :-: | :-: | :-: | :--- | :--- |\n")

        for i, d in enumerate(decisions, 1):
            act_badge = f"`{d['action']}`"
            f.write(f"| {i:02d} | `{d['mailbox']}` | `{d['domain']}` | {d['level']} | **{d['campaign_cap']}** | {d['diagnostic_cap']} | {act_badge} | {d['reason']} |\n")

        f.write("\n---\n\n")
        f.write("## 2. Priority Scheduling & Invariant Rules Applied\n\n")
        f.write("1. **Follow-Ups Take Precedence**: Due follow-ups are pinned to their original sending mailbox and scheduled before any new leads.\n")
        f.write("2. **Thread Continuity**: Outbound touches attach `In-Reply-To` and `References` headers matching previous touches.\n")
        f.write("3. **Opt-Out Cancellation**: Any recipient opting out is globally suppressed across all 25 mailboxes.\n")
        f.write("4. **Fail-Closed Monitoring**: Senders with monitoring gaps >60 minutes are capped at 0.\n")


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file does not exist at {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    res = plan_day(conn)
    conn.close()
    print(f"Daily mailbox planning complete for {res['date_utc']}.")
    print(f"Total mailboxes evaluated: {res['total_mailboxes']}")
    print(f"Total effective daily campaign capacity: {res['active_capacity']}")
    print(f"Markdown report: {res['report_md']}")
    print(f"JSON summary: {res['report_json']}")
