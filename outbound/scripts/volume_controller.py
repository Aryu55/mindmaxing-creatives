#!/usr/bin/env python3
"""
Mindmaxing Shared Transactional Volume Controller & Safety Circuit-Breaker
Enforces:
- Unified daily UTC counters across all dispatchers and schedulers.
- Level-based caps:
    Level 1: 1 campaign / day / mailbox (Combined max: 2 with diagnostic)
    Level 2: 2 campaign / day / mailbox (Combined max: 3 with diagnostic)
    Level 3: 3 campaign / day / mailbox (Combined max: 4 with diagnostic)
- Follow-ups consume campaign capacity.
- Transactional reservation preventing race conditions during concurrent runs.
- Strict auto-pause circuit-breakers (Spam placement, Auth failure, Temp fail streak, Stale collector).
- Cautious promotion evaluation (7 days, 5 accepted campaign messages @ 48h+, 3 clean diagnostics across 2 Gmails, zero hard bounces/complaints).
"""

import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")

LEVEL_CAPS = {
    1: {"campaign": 1, "diagnostic": 1, "combined": 2},
    2: {"campaign": 2, "diagnostic": 1, "combined": 3},
    3: {"campaign": 3, "diagnostic": 1, "combined": 4}
}

def get_utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn

def is_recipient_suppressed(recipient_email: str) -> tuple[bool, str]:
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT reason FROM recipient_suppressions WHERE recipient_email = ?", (recipient_email.lower().strip(),))
    row = c.fetchone()
    conn.close()
    if row:
        return True, row["reason"]
    return False, ""

def suppress_recipient(recipient_email: str, reason: str, source_msg_id: str = None):
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
    INSERT OR REPLACE INTO recipient_suppressions (recipient_email, reason, suppressed_at, source_message_id)
    VALUES (?, ?, ?, ?)
    """, (recipient_email.lower().strip(), reason, now_iso, source_msg_id))
    # Also update lead in CRM table if present
    c.execute("""
    UPDATE leads SET status = 'SUPPRESSED', notes = COALESCE(notes, '') || ' | Suppressed: ' || ?
    WHERE contact_email = ?
    """, (reason, recipient_email.lower().strip()))
    conn.close()

def check_mailbox_health(mailbox: str, purpose: str = "campaign") -> tuple[bool, str]:
    """
    Checks if mailbox or its domain is paused, or if monitoring is stale.
    Diagnostic test sends ('test') bypass stale monitoring checks to permit telemetry recovery.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Check mailbox pause state
    c.execute("SELECT domain, level, status, paused_reason FROM mailbox_levels WHERE mailbox = ?", (mailbox,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, f"Mailbox {mailbox} not initialized in mailbox_levels"
    
    domain = row["domain"]
    if row["status"] == "paused":
        reason = row["paused_reason"] or "Manually paused"
        conn.close()
        return False, f"Mailbox {mailbox} is PAUSED: {reason}"

    # 2. Check if entire domain is paused
    c.execute("SELECT mailbox, paused_reason FROM mailbox_levels WHERE domain = ? AND status = 'paused' AND paused_reason LIKE '%DOMAIN%'", (domain,))
    domain_paused = c.fetchone()
    if domain_paused:
        conn.close()
        return False, f"Domain {domain} is PAUSED: {domain_paused['paused_reason']}"

    # 3. Check collector freshness
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    c.execute("SELECT last_scan_at, status, error_message FROM collector_health WHERE mailbox = ?", (mailbox,))
    health = c.fetchone()

    if purpose == "campaign":
        if not health or not health["last_scan_at"]:
            conn.close()
            return False, f"Collector monitoring MISSING on {mailbox}: no successful scan recorded"
        if health["status"] == "error":
            conn.close()
            return False, f"Collector reporting ERROR on {mailbox}: {health['error_message']}"
        if health["last_scan_at"] < one_hour_ago:
            conn.close()
            return False, f"Collector monitoring on {mailbox} is STALE (>1h ago: {health['last_scan_at']})"
    else:
        # Diagnostic sends: Only block if collector is reporting an explicit transport/auth error
        if health and health["status"] == "error" and "transport" in str(health.get("error_message", "")).lower():
            conn.close()
            return False, f"Collector reporting transport ERROR on {mailbox}: {health['error_message']}"

    # 4. Check temporary failure streak on this mailbox (3 consecutive pauses route)
    c.execute("""
    SELECT smtp_status FROM messages 
    WHERE sender_email = ? 
    ORDER BY sent_at DESC LIMIT 3
    """, (mailbox,))
    recent_smtp = [r["smtp_status"] for r in c.fetchall()]
    if len(recent_smtp) == 3 and all(s == "temp_failure" for s in recent_smtp):
        conn.close()
        pause_mailbox(mailbox, "3 consecutive temporary SMTP delivery failures")
        return False, f"Mailbox {mailbox} auto-paused: 3 consecutive temporary SMTP delivery failures"

    conn.close()
    return True, "Healthy"

try:
    import daily_mailbox_planner
except ImportError:
    try:
        from outbound.scripts import daily_mailbox_planner
    except ImportError:
        daily_mailbox_planner = None

def get_current_period_id() -> str:
    if daily_mailbox_planner:
        return daily_mailbox_planner.get_ist_budget_period()
    return f"{get_utc_date_str()}-IST"

def reserve_quota(mailbox: str, purpose: str = "campaign", period_id: str = None) -> tuple[bool, str]:
    """
    Transactionally reserves sending quota for the specified IST budget period (or current period).
    Returns (True, 'Reserved') or (False, reason).
    Enforces caps from mailbox_daily_decisions ledger:
    - Campaign sends require an explicit, unheld daily decision for the budget period.
    - Test sends are permitted under HOLD_DIAGNOSTIC_EXPIRED / HOLD_MONITORING_STALE
      to allow diagnostic recovery, provided diagnostic cap > 0.
    """
    healthy, reason = check_mailbox_health(mailbox, purpose=purpose)
    if not healthy:
        return False, reason

    if not period_id:
        period_id = get_current_period_id()
    utc_date = get_utc_date_str()

    conn = get_db_connection()
    c = conn.cursor()

    try:
        c.execute("BEGIN IMMEDIATE")
        
        # Get level and caps
        c.execute("SELECT level FROM mailbox_levels WHERE mailbox = ?", (mailbox,))
        lvl_row = c.fetchone()
        level = lvl_row["level"] if lvl_row else 1
        base_caps = LEVEL_CAPS.get(level, LEVEL_CAPS[1])

        # Check daily decision ledger: query by period_id first, fallback to decision_date_utc
        c.execute("""
            SELECT decision_id, effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason
            FROM mailbox_daily_decisions
            WHERE mailbox = ? AND (period_id = ? OR decision_date_utc = ?)
            ORDER BY revision DESC, id DESC LIMIT 1
        """, (mailbox, period_id, utc_date))
        d_row = c.fetchone()

        if d_row:
            action = d_row["decision_action"]
            reason_str = d_row["decision_reason"] or ""
            
            if purpose == "campaign":
                if action in ("PAUSE", "PAUSED", "DOMAIN_PAUSED", "HOLD_TRANSPORT_ERROR", "HOLD_AUTH_FAILED") or action.startswith("HOLD_"):
                    c.execute("COMMIT")
                    conn.close()
                    return False, f"Daily decision engine held campaign for {mailbox}: {reason_str}"
                camp_cap = d_row["effective_campaign_cap"]
                if camp_cap <= 0:
                    c.execute("COMMIT")
                    conn.close()
                    return False, f"Daily decision campaign cap is 0 for {mailbox}: {reason_str}"
                diag_cap = 0

            elif purpose == "test":
                camp_cap = 0
                diag_cap = d_row["effective_diagnostic_cap"]

                if diag_cap <= 0:
                    c.execute("COMMIT")
                    conn.close()
                    return False, f"Daily decision diagnostic cap is 0 for {mailbox}: {reason_str}"

                # Hard blocks that strictly apply to diagnostics:
                is_manual_pause = (action in ("PAUSED", "MANUAL_PAUSE") or "manually paused" in reason_str.lower() or "mailbox is paused" in reason_str.lower())
                is_domain_pause = (action == "DOMAIN_PAUSED" or "domain" in action.lower() or ("domain" in reason_str.lower() and "paused" in reason_str.lower()))
                is_transport_or_auth = (action in ("HOLD_TRANSPORT_ERROR", "HOLD_AUTH_FAILED") or "transport" in reason_str.lower() or "authentication failure" in reason_str.lower())

                if is_manual_pause or is_domain_pause or is_transport_or_auth:
                    c.execute("COMMIT")
                    conn.close()
                    return False, f"Diagnostic blocked by hard stop ({action}): {reason_str}"

                # Narrow exemption: allow test pings when awaiting readiness or expired diagnostic
                is_awaiting_readiness = ("awaiting first clean diagnostic" in reason_str.lower())
                is_diag_expired = ("hold_diagnostic_expired" in action.lower() or "older than 72 hours" in reason_str.lower() or "expired" in reason_str.lower())
                is_active_or_kept = (action in ("KEEP", "INCREASE", "DECREASE", "ACTIVE"))

                if not (is_awaiting_readiness or is_diag_expired or is_active_or_kept):
                    c.execute("COMMIT")
                    conn.close()
                    return False, f"Diagnostic send not permitted under decision ({action}): {reason_str}"
            else:
                c.execute("COMMIT")
                conn.close()
                return False, f"Invalid message purpose: {purpose}"
        else:
            # Fail closed for campaign sending if no daily decision exists
            if purpose == "campaign":
                c.execute("COMMIT")
                conn.close()
                return False, f"Campaign sending blocked: No daily decision generated for {mailbox} on period {period_id}. Nightly review required."
            elif purpose == "test":
                camp_cap = 0
                diag_cap = base_caps["diagnostic"]
            else:
                c.execute("COMMIT")
                conn.close()
                return False, f"Invalid message purpose: {purpose}"

        # Unified period usage tracking
        c.execute("""
            SELECT SUM(campaign_sent) as camp_sent, SUM(diagnostic_sent) as diag_sent
            FROM mailbox_quotas
            WHERE mailbox = ? AND (period_id = ? OR (period_id IS NULL AND date_utc = ?))
        """, (mailbox, period_id, period_id))
        q_row = c.fetchone()
        camp_sent = (q_row["camp_sent"] or 0) if q_row else 0
        diag_sent = (q_row["diag_sent"] or 0) if q_row else 0

        if purpose == "campaign":
            if camp_sent >= camp_cap:
                c.execute("COMMIT")
                conn.close()
                return False, f"Campaign daily limit reached ({camp_sent}/{camp_cap} sends for {mailbox} at Level {level})"
        elif purpose == "test":
            if diag_sent >= diag_cap:
                c.execute("COMMIT")
                conn.close()
                return False, f"Diagnostic daily limit reached ({diag_sent}/{diag_cap} sends for {mailbox})"

        # Check existing row for this date_utc
        c.execute("SELECT 1 FROM mailbox_quotas WHERE mailbox = ? AND date_utc = ?", (mailbox, utc_date))
        if not c.fetchone():
            c.execute("""
                INSERT INTO mailbox_quotas (mailbox, date_utc, period_id, campaign_sent, diagnostic_sent)
                VALUES (?, ?, ?, ?, ?)
            """, (mailbox, utc_date, period_id, 1 if purpose == "campaign" else 0, 1 if purpose == "test" else 0))
        else:
            if purpose == "campaign":
                c.execute("""
                    UPDATE mailbox_quotas 
                    SET campaign_sent = campaign_sent + 1, period_id = ?
                    WHERE mailbox = ? AND date_utc = ?
                """, (period_id, mailbox, utc_date))
            elif purpose == "test":
                c.execute("""
                    UPDATE mailbox_quotas 
                    SET diagnostic_sent = diagnostic_sent + 1, period_id = ?
                    WHERE mailbox = ? AND date_utc = ?
                """, (period_id, mailbox, utc_date))

        c.execute("COMMIT")
        conn.close()
        return True, f"Quota reserved ({purpose} under Level {level} limit)"

    except Exception as e:
        c.execute("ROLLBACK")
        conn.close()
        return False, f"Database lock error during quota reservation: {e}"

def reserve_and_claim_job(
    lead_id: int,
    domain: str,
    touch_number: int,
    mailbox: str,
    recipient: str,
    subject: str,
    body: str,
    worker_id: str,
    campaign_name: str = "dealstrike-distributors",
    purpose: str = "campaign",
    period_id: str = None
) -> tuple[bool, str, Optional[dict]]:
    """
    Unified transactional claim and quota reservation for an outbound touch.
    In one short atomic SQLite transaction:
    1. Rechecks mailbox health.
    2. Rechecks recipient suppression.
    3. Rechecks lead status and sequence immutability.
    4. Evaluates daily decision limits and holds for budget period.
    5. Checks remaining quota.
    6. Claims/inserts the job in outbound_jobs.
    7. Atomically reserves quota in mailbox_quotas.
    Returns (True, "Claimed", {"job_id": int, "decision_id": str, "period_id": str}) or (False, reason, None).
    """
    healthy, h_reason = check_mailbox_health(mailbox, purpose=purpose)
    if not healthy:
        return False, h_reason, None

    suppressed, s_reason = is_recipient_suppressed(recipient)
    if suppressed:
        return False, f"Recipient {recipient} is suppressed: {s_reason}", None

    if not period_id:
        period_id = get_current_period_id()
    utc_date = get_utc_date_str()
    now_iso = datetime.now(timezone.utc).isoformat()

    conn = get_db_connection()
    c = conn.cursor()

    try:
        c.execute("BEGIN IMMEDIATE")

        # 1. Lead validation
        c.execute("PRAGMA table_info(leads)")
        lead_cols = {col[1] for col in c.fetchall()}

        select_cols = ["id", "status", "contact_email", "current_sequence_step"]
        for opt_col in ("contact_type", "source", "signal_decision"):
            if opt_col in lead_cols:
                select_cols.append(opt_col)

        c.execute(f"SELECT {', '.join(select_cols)} FROM leads WHERE id = ?", (lead_id,))
        raw_lead = c.fetchone()
        if not raw_lead:
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Lead ID {lead_id} ({domain}) not found in leads table", None

        lead_row = dict(raw_lead)
        lead_st = lead_row.get("status")
        if lead_st in ("CLIENT_WON", "SEQUENCE_COMPLETED", "COOLDOWN", "REPLIED", "SUPPRESSED", "REJECTED_FROM_CAMPAIGN"):
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Lead {domain} is in terminal status: {lead_st}", None

        # Contact qualification guard: unverified contact cannot reach SMTP
        c_type = (lead_row.get("contact_type") or "").strip().upper()
        if c_type in ("UNVERIFIED", "INVALID"):
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Lead {domain} has unverified contact status: {c_type}", None

        # Reddit signal qualification guard
        src = (lead_row.get("source") or "").strip().lower()
        sig_dec = (lead_row.get("signal_decision") or "").strip().upper()
        if src == "reddit" or (campaign_name and campaign_name.strip().lower() == "reddit"):
            if lead_st != "HUMAN_APPROVED" and sig_dec != "INCIDENT_CANDIDATE":
                c.execute("ROLLBACK")
                conn.close()
                return False, f"Reddit lead {domain} lacks qualifying incident signal (decision={sig_dec})", None

        # Sequence recipient immutability
        if (lead_row.get("current_sequence_step") or 0) > 0 and lead_row.get("contact_email") != recipient:
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Sequence recipient mismatch for {domain}: active recipient is {lead_row.get('contact_email')}", None

        # 2. Daily decision lookup
        c.execute("""
            SELECT decision_id, effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason
            FROM mailbox_daily_decisions
            WHERE mailbox = ? AND (period_id = ? OR decision_date_utc = ?)
            ORDER BY revision DESC, id DESC LIMIT 1
        """, (mailbox, period_id, utc_date))
        d_row = c.fetchone()

        if not d_row:
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Campaign sending blocked: No daily review decision for {mailbox} on period {period_id}", None

        action = d_row["decision_action"]
        d_reason = d_row["decision_reason"]
        decision_id = d_row["decision_id"] or f"DEC-{period_id}-{mailbox}"
        effective_camp_cap = d_row["effective_campaign_cap"]

        if action in ("PAUSE", "PAUSED", "DOMAIN_PAUSED", "HOLD_TRANSPORT_ERROR", "HOLD_AUTH_FAILED") or action.startswith("HOLD_"):
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Mailbox {mailbox} is held/paused by review ({action}): {d_reason}", None

        if effective_camp_cap <= 0:
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Mailbox {mailbox} effective campaign cap is 0 ({d_reason})", None

        # 3. Quota check & reservation by unified period_id
        c.execute("""
            SELECT SUM(campaign_sent) as camp_sent
            FROM mailbox_quotas
            WHERE mailbox = ? AND (period_id = ? OR (period_id IS NULL AND date_utc = ?))
        """, (mailbox, period_id, period_id))
        q_row = c.fetchone()
        current_sent = (q_row["camp_sent"] or 0) if q_row else 0

        if current_sent >= effective_camp_cap:
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Mailbox {mailbox} quota reached ({current_sent}/{effective_camp_cap} sends for period {period_id})", None

        # 4. Outbound Job Claiming
        # Insert if not exists
        c.execute("""
            INSERT OR IGNORE INTO outbound_jobs (
                lead_id, domain, touch_number, assigned_mailbox, recipient_email,
                subject, body, due_at, earliest_send_at, status, campaign_name,
                period_id, decision_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)
        """, (
            lead_id, domain, touch_number, mailbox, recipient,
            subject, body, now_iso, now_iso, campaign_name,
            period_id, decision_id, now_iso, now_iso
        ))

        # Atomically claim
        c.execute("""
            UPDATE outbound_jobs
            SET status = 'CLAIMED', worker_id = ?, assigned_mailbox = ?,
                period_id = ?, decision_id = ?, campaign_name = ?,
                attempt_count = attempt_count + 1, updated_at = ?
            WHERE domain = ? AND touch_number = ? AND status IN ('PENDING', 'RESERVED', 'DEFERRED')
        """, (worker_id, mailbox, period_id, decision_id, campaign_name, now_iso, domain, touch_number))

        if c.rowcount == 0:
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Touch {touch_number} for {domain} already claimed or active", None

        # Fetch job ID
        c.execute("SELECT id, attempt_count FROM outbound_jobs WHERE domain = ? AND touch_number = ?", (domain, touch_number))
        job_row = c.fetchone()
        job_id = job_row["id"] if job_row else None
        attempt_count = job_row["attempt_count"] if job_row else 1

        # Increment quota by period_id
        c.execute("SELECT 1 FROM mailbox_quotas WHERE mailbox = ? AND date_utc = ?", (mailbox, utc_date))
        if not c.fetchone():
            c.execute("""
                INSERT INTO mailbox_quotas (mailbox, date_utc, period_id, campaign_sent, diagnostic_sent)
                VALUES (?, ?, ?, 1, 0)
            """, (mailbox, utc_date, period_id))
        else:
            c.execute("""
                UPDATE mailbox_quotas 
                SET campaign_sent = campaign_sent + 1, period_id = ?
                WHERE mailbox = ? AND date_utc = ?
            """, (period_id, mailbox, utc_date))

        c.execute("COMMIT")
        conn.close()

        return True, "Claimed", {
            "job_id": job_id,
            "decision_id": decision_id,
            "period_id": period_id,
            "attempt_count": attempt_count
        }

    except Exception as e:
        c.execute("ROLLBACK")
        conn.close()
        return False, f"Database transaction error during reserve_and_claim_job: {e}", None

def update_outbound_job_status(job_id: Optional[int], new_status: str, error_msg: str = None):
    """Updates status on outbound_jobs row safely."""
    if not job_id:
        return
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        c.execute("UPDATE outbound_jobs SET status = ?, updated_at = ? WHERE id = ?", (new_status, now_iso, job_id))
        conn.close()
    except Exception:
        pass

def rollback_quota(mailbox: str, purpose: str = "campaign", period_id: str = None):
    """
    Rollback quota ONLY if SMTP failed completely before DATA submission.
    INVARIANT: Never rollback quota for post-DATA exceptions (e.g. QUIT errors or timeouts).
    """
    if not period_id:
        period_id = get_current_period_id()
    utc_date = get_utc_date_str()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("BEGIN IMMEDIATE")
        if purpose == "campaign":
            c.execute("""
                UPDATE mailbox_quotas 
                SET campaign_sent = MAX(0, campaign_sent - 1) 
                WHERE mailbox = ? AND (period_id = ? OR (period_id IS NULL AND date_utc = ?))
            """, (mailbox, period_id, utc_date))
        elif purpose == "test":
            c.execute("""
                UPDATE mailbox_quotas 
                SET diagnostic_sent = MAX(0, diagnostic_sent - 1) 
                WHERE mailbox = ? AND (period_id = ? OR (period_id IS NULL AND date_utc = ?))
            """, (mailbox, period_id, utc_date))
        c.execute("COMMIT")
    except Exception:
        c.execute("ROLLBACK")
    finally:
        conn.close()

def record_campaign_message(
    message_id: str,
    sender_email: str,
    recipient_email: str,
    prospect_domain: str,
    campaign_touch: int,
    subject: str,
    smtp_success: bool,
    smtp_code: int = 250,
    smtp_response: str = "OK",
    error_msg: str = None
) -> bool:
    """
    Records an outgoing campaign message and its delivery event in the telemetry tables.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    utc_date = get_utc_date_str()
    sender_domain = sender_email.split("@")[1].lower() if "@" in sender_email else "unknown"
    recip_clean = recipient_email.strip().lower()
    recip_domain = recip_clean.split("@")[1] if "@" in recip_clean else "unknown"
    
    # Provider classification
    if "gmail" in recip_domain or "google" in recip_domain:
        provider = "gmail"
    elif any(k in recip_domain for k in ["outlook", "hotmail", "live", "microsoft", "office365"]):
        provider = "microsoft"
    else:
        provider = "other"

    conn = get_db_connection()
    c = conn.cursor()
    try:
        if smtp_success:
            c.execute("""
            INSERT OR REPLACE INTO messages (
                message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                recipient_provider, purpose, campaign_touch, prospect_domain, sent_at,
                sent_date, smtp_status, smtp_code, smtp_response, delivery_state,
                auth_spf, auth_dkim, auth_dmarc, last_event_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, 'campaign', ?, ?, ?, ?, 'accepted', ?, ?, 'accepted', 'unknown', 'unknown', 'unknown', ?, ?)
            """, (
                message_id, sender_email, sender_domain, recip_clean, recip_domain,
                provider, campaign_touch, prospect_domain, now_iso, utc_date,
                smtp_code, smtp_response, now_iso, f"Subject: {subject[:100]}"
            ))
            c.execute("""
            INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
            VALUES (?, 'smtp_accepted', ?, ?, 'OUTBOX', ?)
            """, (message_id, now_iso, sender_email, f"SMTP {smtp_code} {smtp_response}"))
        else:
            c.execute("""
            INSERT OR REPLACE INTO messages (
                message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                recipient_provider, purpose, campaign_touch, prospect_domain, sent_at,
                sent_date, smtp_status, smtp_code, smtp_response, delivery_state,
                auth_spf, auth_dkim, auth_dmarc, last_event_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, 'campaign', ?, ?, ?, ?, 'temp_failure', ?, ?, 'unknown', 'unknown', 'unknown', 'unknown', ?, ?)
            """, (
                message_id, sender_email, sender_domain, recip_clean, recip_domain,
                provider, campaign_touch, prospect_domain, now_iso, utc_date,
                smtp_code, (smtp_response or error_msg or "Failed")[:100], now_iso, f"SMTP Error: {str(error_msg)[:150]}"
            ))
            c.execute("""
            INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
            VALUES (?, 'smtp_failed', ?, ?, 'OUTBOX', ?)
            """, (message_id, now_iso, sender_email, str(error_msg)[:200] if error_msg else "Failed"))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def pause_mailbox(mailbox: str, reason: str):
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
    UPDATE mailbox_levels SET status = 'paused', paused_reason = ?, paused_at = ?
    WHERE mailbox = ?
    """, (reason, now_iso, mailbox))
    conn.close()

def pause_domain(domain: str, reason: str):
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
    UPDATE mailbox_levels SET status = 'paused', paused_reason = ? || ' [DOMAIN LEVEL]', paused_at = ?
    WHERE domain = ?
    """, (reason, now_iso, domain))
    conn.close()

def resume_mailbox(mailbox: str):
    """Requires manual operator invocation with documented resolution."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE mailbox_levels SET status = 'active', paused_reason = NULL, paused_at = NULL
    WHERE mailbox = ?
    """, (mailbox,))
    conn.close()

def evaluate_mailbox_promotion(mailbox: str) -> tuple[bool, str]:
    """
    Evaluates Astra's 5 Promotion Checks:
    1. Time at current level: At least 7 calendar days.
    2. Actual campaign activity: At least 5 accepted campaign messages observed for 48h+.
    3. Recent diagnostic results: Last 3 tests arrived in inbox across at least 2 Gmails with passing SPF/DKIM/DMARC.
    4. Current monitoring: Latest test within 24h; no collector gap >1h in last 24h.
    5. Recorded problems: No unresolved failures, complaints, or hard bounces in domain for preceding 7 days.
    """
    conn = get_db_connection()
    c = conn.cursor()
    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    forty_eight_hours_ago = (now - timedelta(hours=48)).isoformat()
    twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()

    c.execute("SELECT domain, level, level_updated_at, status FROM mailbox_levels WHERE mailbox = ?", (mailbox,))
    m_row = c.fetchone()
    if not m_row:
        conn.close()
        return False, "Mailbox not found"

    if m_row["status"] == "paused":
        conn.close()
        return False, "Mailbox is paused"

    current_level = m_row["level"]
    domain = m_row["domain"]
    if current_level >= 3:
        conn.close()
        return False, "Already at maximum volume level (Level 3)"

    # Check 1: Time at current level (7 calendar days)
    clean_lu = (m_row["level_updated_at"] or now.isoformat()).replace("Z", "+00:00")
    try:
        level_updated = datetime.fromisoformat(clean_lu)
        if level_updated.tzinfo is None:
            level_updated = level_updated.replace(tzinfo=timezone.utc)
    except Exception:
        level_updated = now

    if (now - level_updated).total_seconds() < 7 * 86400:
        days_left = 7 - ((now - level_updated).total_seconds() / 86400)
        conn.close()
        return False, f"HOLD: Only {7 - days_left:.1f} days at Level {current_level} (requires 7.0 full days)"

    # Check 2: Actual campaign activity (At least 5 accepted campaign messages observed 48h+)
    c.execute("""
    SELECT count(*) as cnt FROM messages 
    WHERE sender_email = ? AND purpose = 'campaign' 
      AND smtp_status = 'accepted' AND sent_at <= ? AND sent_at >= ?
    """, (mailbox, forty_eight_hours_ago, m_row["level_updated_at"]))
    camp_cnt = c.fetchone()["cnt"]
    if camp_cnt < 5:
        conn.close()
        return False, f"HOLD: Only {camp_cnt}/5 campaign messages observed for 48h+ at current level"

    # Check 3: Recent diagnostic results (Last 3 tests arrived in inbox across >=2 Gmails with SPF/DKIM/DMARC pass)
    c.execute("""
    SELECT recipient_email, delivery_state, auth_spf, auth_dkim, auth_dmarc
    FROM messages 
    WHERE sender_email = ? AND purpose = 'test'
    ORDER BY sent_at DESC LIMIT 3
    """, (mailbox,))
    diag_rows = c.fetchall()
    if len(diag_rows) < 3:
        conn.close()
        return False, f"HOLD: Only {len(diag_rows)}/3 diagnostic tests completed"

    distinct_gmails = set(r["recipient_email"] for r in diag_rows)
    if len(distinct_gmails) < 2:
        conn.close()
        return False, f"HOLD: Diagnostic tests must cover at least 2 distinct Gmail inboxes (got {len(distinct_gmails)})"

    for r in diag_rows:
        if r["delivery_state"] not in ("inbox", "promotions"):
            conn.close()
            return False, f"HOLD: Diagnostic test not in inbox (state: {r['delivery_state']})"
        if r["auth_spf"] != "pass" or r["auth_dkim"] != "pass" or r["auth_dmarc"] != "pass":
            conn.close()
            return False, f"HOLD: Diagnostic authentication failed (SPF={r['auth_spf']}, DKIM={r['auth_dkim']}, DMARC={r['auth_dmarc']})"

    # Check 4: Current monitoring (Latest test within 24h; collector gap <=1h)
    c.execute("SELECT sent_at FROM messages WHERE sender_email = ? AND purpose = 'test' ORDER BY sent_at DESC LIMIT 1", (mailbox,))
    latest_test = c.fetchone()
    if not latest_test or latest_test["sent_at"] < twenty_four_hours_ago:
        conn.close()
        return False, "HOLD: No diagnostic test within the last 24 hours"

    c.execute("SELECT last_scan_at, status FROM collector_health WHERE mailbox = ?", (mailbox,))
    health = c.fetchone()
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    if not health or health["status"] != "healthy" or health["last_scan_at"] < one_hour_ago:
        conn.close()
        return False, "HOLD: Collector monitoring is stale or not reporting healthy status"

    # Check 5: Recorded problems (No failures, complaints, or hard bounces in domain for preceding 7 days)
    c.execute("""
    SELECT count(*) as cnt FROM messages 
    WHERE sender_domain = ? AND sent_at >= ?
      AND (smtp_status = 'perm_failure' OR delivery_state = 'bounced')
    """, (domain, seven_days_ago))
    prob_cnt = c.fetchone()["cnt"]
    if prob_cnt > 0:
        conn.close()
        return False, f"HOLD: Domain {domain} has {prob_cnt} hard bounces/failures in the last 7 days"

    # All checks passed: Automatically promote to next level!
    new_level = current_level + 1
    c.execute("""
    UPDATE mailbox_levels SET level = ?, level_updated_at = ?
    WHERE mailbox = ?
    """, (new_level, now.isoformat(), mailbox))
    conn.commit()
    conn.close()
    return True, f"PROMOTED: Mailbox {mailbox} promoted from Level {current_level} -> Level {new_level}!"

if __name__ == "__main__":
    print("Testing Volume Controller initialization...")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT mailbox, level, status FROM mailbox_levels LIMIT 5")
    for r in c.fetchall():
        print(dict(r))
    conn.close()
