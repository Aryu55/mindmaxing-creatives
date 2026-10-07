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
import re
import uuid
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
    c.execute("PRAGMA table_info(mailbox_levels)")
    ml_cols = [r[1] for r in c.fetchall()]
    q_paused = ", paused_reason" if "paused_reason" in ml_cols else ""
    c.execute(f"SELECT domain, level, status{q_paused} FROM mailbox_levels WHERE mailbox = ?", (mailbox,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, f"Mailbox {mailbox} not initialized in mailbox_levels"
    
    domain = row["domain"]
    paused_reason_val = row["paused_reason"] if "paused_reason" in row.keys() else None
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    has_structured_hold = False
    # 1. Check structured incident holds in mailbox_holds (Task C)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mailbox_holds'")
    if c.fetchone():
        # Domain-level contagion quarantine: if explicit DOMAIN_PAUSED or >=3 SEED_SPAM in last 48h
        if purpose == "campaign":
            c.execute("""
                SELECT count(*) as cnt FROM mailbox_holds 
                WHERE domain = ? AND (
                    (hold_type = 'DOMAIN_PAUSED' AND resolved_at IS NULL)
                    OR (hold_type = 'SEED_SPAM' AND opened_at >= datetime('now', '-48 hours') AND resolved_at IS NULL)
                )
            """, (domain,))
            sc_row = c.fetchone()
            if sc_row and sc_row["cnt"] >= 3:
                conn.close()
                return False, f"Campaign blocked: domain {domain} is quarantined ({sc_row['cnt']} active/recent spam incidents)"

        c.execute("""
            SELECT hold_id, hold_type, scope, opened_at, retry_after, remediation_ref
            FROM mailbox_holds
            WHERE (mailbox = ? OR (domain = ? AND scope = 'domain')) AND resolved_at IS NULL
            ORDER BY opened_at DESC
        """, (mailbox, domain))
        holds = c.fetchall()
        if holds:
            has_structured_hold = True
            for h in holds:
                htype = h["hold_type"]
                if purpose == "campaign":
                    if htype in ("SEED_SPAM", "AWAITING_READINESS", "HOLD_DIAGNOSTIC_EXPIRED", "MANUAL_PAUSE", "DOMAIN_PAUSED", "HOLD_AUTH_FAILED", "PROVIDER_BLOCK", "MONITORING_ERROR", "MONITORING_STALE"):
                        conn.close()
                        return False, f"Campaign blocked by active hold ({htype}): {h['hold_id']}"
                    if htype == "TEMP_FAILURE_BACKOFF":
                        if h["retry_after"] and now_iso < h["retry_after"]:
                            conn.close()
                            return False, f"Campaign blocked: temporary backoff active until {h['retry_after']}"
                elif purpose == "test":
                    if htype == "MANUAL_PAUSE":
                        conn.close()
                        return False, f"Diagnostic blocked by manual stop: {h['hold_id']}"
                    if htype == "DOMAIN_PAUSED":
                        conn.close()
                        return False, f"Diagnostic blocked by domain stop: {h['hold_id']}"
                    if htype == "PROVIDER_BLOCK":
                        conn.close()
                        return False, f"Diagnostic blocked by provider block: {h['hold_id']}"
                    if htype == "HOLD_AUTH_FAILED" and not h["remediation_ref"]:
                        conn.close()
                        return False, f"Diagnostic blocked: authentication failure requires recorded remediation reference"
                    if htype == "TEMP_FAILURE_BACKOFF":
                        if h["retry_after"] and now_iso < h["retry_after"]:
                            conn.close()
                            return False, f"Diagnostic blocked: temporary backoff active until {h['retry_after']}"
                    if htype == "SEED_SPAM":
                        try:
                            dt_op = datetime.fromisoformat(h["opened_at"].replace("Z", "+00:00"))
                            if dt_op.tzinfo is None:
                                dt_op = dt_op.replace(tzinfo=timezone.utc)
                            if now_dt < dt_op + timedelta(hours=24):
                                conn.close()
                                return False, f"Diagnostic blocked: 24h backoff active following SEED_SPAM until {(dt_op + timedelta(hours=24)).isoformat()}"
                        except Exception:
                            pass

    # Legacy mailbox_levels pause check fallback
    if not has_structured_hold and row["status"] == "paused":
        reason = paused_reason_val or "Manually paused"
        if purpose == "test":
            is_manual = ("manual" in reason.lower())
            is_auth = ("auth" in reason.lower() or "credential" in reason.lower())
            is_transport = ("transport" in reason.lower())
            if is_manual or is_auth or is_transport:
                conn.close()
                return False, f"Mailbox {mailbox} is PAUSED ({reason}): diagnostic recovery not permitted"
        else:
            conn.close()
            return False, f"Mailbox {mailbox} is PAUSED: {reason}"

    # 2. Check if entire domain is paused
    if "paused_reason" in ml_cols:
        c.execute("SELECT mailbox, paused_reason FROM mailbox_levels WHERE domain = ? AND status = 'paused' AND paused_reason LIKE '%DOMAIN%'", (domain,))
        domain_paused = c.fetchone()
        if domain_paused:
            conn.close()
            return False, f"Domain {domain} is PAUSED: {domain_paused['paused_reason']}"

    # 3. Check collector freshness
    one_hour_ago = (now_dt - timedelta(hours=1)).isoformat()
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
        if health and health["status"] == "error":
            h_dict = dict(health)
            err_str = str(h_dict.get("error_message") or "").lower()
            if "transport" in err_str or "auth" in err_str:
                conn.close()
                return False, f"Collector reporting transport ERROR on {mailbox}: {h_dict.get('error_message')}"

    # 4. Check temporary failure streak in last 24h (aligned with nightly planner)
    twenty_four_hours_ago = (now_dt - timedelta(hours=24)).isoformat()
    c.execute("PRAGMA table_info(messages)")
    msg_cols = [r[1] for r in c.fetchall()]
    if "smtp_status" in msg_cols and "sent_at" in msg_cols:
        q_code = ", smtp_code" if "smtp_code" in msg_cols else ""
        c.execute(f"""
            SELECT smtp_status, sent_at{q_code}
            FROM messages 
            WHERE sender_email = ? AND sent_at >= ?
            ORDER BY sent_at DESC LIMIT 3
        """, (mailbox, twenty_four_hours_ago))
        recent_sends = c.fetchall()
        if len(recent_sends) == 3 and all(r["smtp_status"] == "temp_failure" and ("smtp_code" not in r.keys() or r["smtp_code"] is None or 400 <= r["smtp_code"] < 500) for r in recent_sends):
            latest_fail_at = recent_sends[0]["sent_at"]
            try:
                dt_fail = datetime.fromisoformat(latest_fail_at.replace("Z", "+00:00"))
                if dt_fail.tzinfo is None:
                    dt_fail = dt_fail.replace(tzinfo=timezone.utc)
                retry_after_dt = dt_fail + timedelta(hours=1)
                if now_dt < retry_after_dt:
                    conn.close()
                    return False, f"Temporary failure backoff active until {retry_after_dt.isoformat()} (3 consecutive 4xx failures in 24h)"
            except Exception:
                pass

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
    Returns (True, 'Reserved: token=...') or (False, reason).
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
        
        # Ensure period usage tables exist in DB
        c.execute("""
            CREATE TABLE IF NOT EXISTS mailbox_period_usage (
                mailbox TEXT NOT NULL,
                period_id TEXT NOT NULL,
                campaign_used INTEGER NOT NULL DEFAULT 0 CHECK(campaign_used >= 0),
                diagnostic_used INTEGER NOT NULL DEFAULT 0 CHECK(diagnostic_used >= 0),
                PRIMARY KEY (mailbox, period_id)
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS quota_reservations (
                reservation_id TEXT PRIMARY KEY,
                mailbox TEXT NOT NULL,
                period_id TEXT NOT NULL,
                purpose TEXT NOT NULL CHECK(purpose IN ('campaign','test')),
                status TEXT NOT NULL CHECK(status IN ('RESERVED','ACCEPTED','UNCERTAIN','RELEASED')),
                message_id TEXT,
                job_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Get level and caps
        c.execute("SELECT level FROM mailbox_levels WHERE mailbox = ?", (mailbox,))
        lvl_row = c.fetchone()
        level = lvl_row["level"] if lvl_row else 1
        base_caps = LEVEL_CAPS.get(level, LEVEL_CAPS[1])

        # Exact decision lookup by period_id
        c.execute("""
            SELECT decision_id, effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason
            FROM mailbox_daily_decisions
            WHERE mailbox = ? AND period_id = ?
            ORDER BY revision DESC, id DESC LIMIT 1
        """, (mailbox, period_id))
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
                is_manual_pause = (action in ("PAUSED", "MANUAL_PAUSE") or "manually paused" in reason_str.lower())
                is_domain_pause = (action == "DOMAIN_PAUSED" or "domain is paused" in reason_str.lower())
                is_transport_or_auth = (action in ("HOLD_TRANSPORT_ERROR", "HOLD_AUTH_FAILED") or "transport" in reason_str.lower() or "authentication failure" in reason_str.lower())

                if is_manual_pause or is_domain_pause or is_transport_or_auth:
                    c.execute("COMMIT")
                    conn.close()
                    return False, f"Diagnostic blocked by hard stop ({action}): {reason_str}"

                # Exemptions: awaiting readiness, expired diagnostic, seed spam recovery, or active
                is_awaiting_readiness = ("awaiting first clean diagnostic" in reason_str.lower())
                is_diag_expired = ("hold_diagnostic_expired" in action.lower() or "older than 72 hours" in reason_str.lower() or "expired" in reason_str.lower())
                is_seed_spam_recovery = ("spam" in reason_str.lower() or "seed_spam" in action.lower())
                is_active_or_kept = (action in ("KEEP", "INCREASE", "DECREASE", "ACTIVE"))

                # For seed spam recovery: enforce 24h backoff from latest spam incident
                if is_seed_spam_recovery and not (is_awaiting_readiness or is_active_or_kept):
                    c.execute("""
                        SELECT de.detected_at FROM delivery_events de
                        JOIN messages m ON de.message_id = m.message_id
                        WHERE m.sender_email = ? AND de.folder = 'SPAM'
                        ORDER BY de.detected_at DESC LIMIT 1
                    """, (mailbox,))
                    last_spam = c.fetchone()
                    if last_spam and last_spam["detected_at"]:
                        try:
                            spam_dt = datetime.fromisoformat(last_spam["detected_at"].replace("Z", "+00:00"))
                            if datetime.now(timezone.utc) - spam_dt < timedelta(hours=24):
                                c.execute("COMMIT")
                                conn.close()
                                return False, f"Diagnostic recovery held: 24h backoff from seed spam incident required for {mailbox}"
                        except Exception:
                            pass

                if not (is_awaiting_readiness or is_diag_expired or is_seed_spam_recovery or is_active_or_kept):
                    c.execute("COMMIT")
                    conn.close()
                    return False, f"Diagnostic send not permitted under decision ({action}): {reason_str}"
            else:
                c.execute("COMMIT")
                conn.close()
                return False, f"Invalid message purpose: {purpose}"
        else:
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

        # Usage checking on mailbox_period_usage
        c.execute("""
            SELECT campaign_used, diagnostic_used
            FROM mailbox_period_usage
            WHERE mailbox = ? AND period_id = ?
        """, (mailbox, period_id))
        u_row = c.fetchone()
        camp_used = u_row["campaign_used"] if u_row else 0
        diag_used = u_row["diagnostic_used"] if u_row else 0

        if purpose == "campaign":
            if camp_used >= camp_cap:
                c.execute("COMMIT")
                conn.close()
                return False, f"Campaign daily limit reached ({camp_used}/{camp_cap} sends for {mailbox} at Level {level})"
        elif purpose == "test":
            if diag_used >= diag_cap:
                c.execute("COMMIT")
                conn.close()
                return False, f"Diagnostic daily limit reached ({diag_used}/{diag_cap} sends for {mailbox})"

        reservation_id = f"res_{uuid.uuid4().hex[:16]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        c.execute("""
            INSERT INTO mailbox_period_usage (mailbox, period_id, campaign_used, diagnostic_used)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(mailbox, period_id) DO UPDATE SET
                campaign_used = campaign_used + excluded.campaign_used,
                diagnostic_used = diagnostic_used + excluded.diagnostic_used
        """, (mailbox, period_id, 1 if purpose == "campaign" else 0, 1 if purpose == "test" else 0))

        c.execute("""
            INSERT INTO quota_reservations (reservation_id, mailbox, period_id, purpose, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'RESERVED', ?, ?)
        """, (reservation_id, mailbox, period_id, purpose, now_iso, now_iso))

        # Safe update to legacy mailbox_quotas for backward compatibility
        try:
            c.execute("""
                INSERT INTO mailbox_quotas (mailbox, date_utc, period_id, campaign_sent, diagnostic_sent)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(mailbox, date_utc) DO UPDATE SET
                    campaign_sent = campaign_sent + excluded.campaign_sent,
                    diagnostic_sent = diagnostic_sent + excluded.diagnostic_sent,
                    period_id = excluded.period_id
            """, (mailbox, utc_date, period_id, 1 if purpose == "campaign" else 0, 1 if purpose == "test" else 0))
        except Exception:
            pass

        c.execute("COMMIT")
        conn.close()
        return True, f"Quota reserved ({purpose} under Level {level} limit): {reservation_id}"

    except Exception as e:
        c.execute("ROLLBACK")
        conn.close()
        return False, f"Database error during quota reservation: {e}"

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
        for opt_col in ("contact_type", "source", "signal_decision", "signal_evidence", "review_date", "captured_at", "timezone", "country_code"):
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

        # Sequence recipient immutability
        if (lead_row.get("current_sequence_step") or 0) > 0 and lead_row.get("contact_email") != recipient:
            c.execute("ROLLBACK")
            conn.close()
            return False, f"Sequence recipient mismatch for {domain}: active recipient is {lead_row.get('contact_email')}", None

        # Strict Conjunctive Pre-SMTP Eligibility Gate (Task F & Task G)
        if purpose == "campaign":
            # 1. Human Approval Gate: HUMAN_APPROVED required for Touch 1; TOUCH_1_SENT/TOUCH_2_SENT for follow-ups
            allowed_lead_statuses = {"HUMAN_APPROVED", "TOUCH_1_SENT", "TOUCH_2_SENT"}
            if lead_st not in allowed_lead_statuses:
                c.execute("ROLLBACK")
                conn.close()
                return False, f"Campaign send blocked: Lead {domain} requires explicit human review and approval (status is not in {allowed_lead_statuses}: {lead_st})", None

            # 2. Copy Gate: subject and body must not be empty
            if not subject or not subject.strip():
                c.execute("ROLLBACK")
                conn.close()
                return False, f"Campaign send blocked: Empty subject for {domain}", None
            if not body or not body.strip():
                c.execute("ROLLBACK")
                conn.close()
                return False, f"Campaign send blocked: Empty body for {domain}", None

            # 3. Recipient Prefix Gate: no generic desk addresses (support@, info@, help@, etc.)
            recip_prefix = recipient.split("@")[0].lower().strip()
            generic_prefixes = {"support", "info", "help", "contact", "sales", "team", "hello", "orders", "care", "admin", "office", "service", "billing", "inquiry"}
            if recip_prefix in generic_prefixes:
                c.execute("ROLLBACK")
                conn.close()
                return False, f"Campaign send blocked: Recipient {recipient} is a generic desk address ({recip_prefix}@); verified founder address required", None

            # 4. Contact Qualification Gate: unverified contact cannot reach SMTP
            c_type = (lead_row.get("contact_type") or "").strip().upper()
            if c_type in ("UNVERIFIED", "INVALID", "GENERIC_SUPPORT", "LEGACY_UNKNOWN"):
                c.execute("ROLLBACK")
                conn.close()
                return False, f"Lead {domain} has unverified contact status: {c_type}", None

            # 5. Qualifying Technical Incident Signal Gate: HUMAN_APPROVED must not act as an OR bypass
            if "signal_decision" in lead_cols:
                sig_dec = (lead_row.get("signal_decision") or "").strip().upper()
                if sig_dec != "INCIDENT_CANDIDATE":
                    c.execute("ROLLBACK")
                    conn.close()
                    return False, f"Lead {domain} lacks qualifying technical incident signal (decision={sig_dec})", None

                # Freshness verification: incident evidence must be <= 7 days
                ev_date_str = None
                sig_ev = lead_row.get("signal_evidence")
                if sig_ev:
                    try:
                        ev_data = json.loads(sig_ev) if isinstance(sig_ev, str) else sig_ev
                        ev_date_str = ev_data.get("evidence_timestamp") or ev_data.get("review_date")
                    except Exception:
                        pass
                if not ev_date_str:
                    # Only use review_date (actual signal observation time).
                    # captured_at is scrape time and should NOT gate evidence freshness.
                    ev_date_str = lead_row.get("review_date")

                if ev_date_str:
                    try:
                        ev_dt = datetime.fromisoformat(ev_date_str.replace("Z", "+00:00"))
                        if ev_dt.tzinfo is None:
                            ev_dt = ev_dt.replace(tzinfo=timezone.utc)
                        if datetime.now(timezone.utc) - ev_dt > timedelta(days=7):
                            c.execute("ROLLBACK")
                            conn.close()
                            return False, f"Incident evidence for {domain} is older than 7 days ({ev_date_str})", None
                    except Exception:
                        pass

            # 6. Timezone Gate: If timezone is known, recipient local business hours window must be open
            recipient_tz = lead_row.get("timezone")
            if recipient_tz:
                try:
                    from timezone_util import local_window_open
                except ImportError:
                    try:
                        from outbound.scripts.timezone_util import local_window_open
                    except ImportError:
                        local_window_open = None
                if local_window_open and not local_window_open(datetime.now(timezone.utc), recipient_tz):
                    c.execute("ROLLBACK")
                    conn.close()
                    return False, f"Recipient local sending window closed in timezone {recipient_tz}", None

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

        # Increment quota by period_id in mailbox_period_usage and quota_reservations
        c.execute("""
            INSERT INTO mailbox_period_usage (mailbox, period_id, campaign_used, diagnostic_used)
            VALUES (?, ?, 1, 0)
            ON CONFLICT(mailbox, period_id) DO UPDATE SET
                campaign_used = campaign_used + 1
        """, (mailbox, period_id))

        reservation_id = f"res_{uuid.uuid4().hex[:16]}"
        c.execute("""
            INSERT INTO quota_reservations (reservation_id, mailbox, period_id, purpose, status, job_id, created_at, updated_at)
            VALUES (?, ?, ?, 'campaign', 'RESERVED', ?, ?, ?)
        """, (reservation_id, mailbox, period_id, job_id, now_iso, now_iso))

        # Safe update to legacy mailbox_quotas
        c.execute("SELECT 1 FROM mailbox_quotas WHERE mailbox = ? AND period_id = ?", (mailbox, period_id))
        if not c.fetchone():
            c.execute("""
                INSERT INTO mailbox_quotas (mailbox, date_utc, period_id, campaign_sent, diagnostic_sent)
                VALUES (?, ?, ?, 1, 0)
            """, (mailbox, utc_date, period_id))
        else:
            c.execute("UPDATE mailbox_quotas SET campaign_sent = campaign_sent + 1 WHERE mailbox = ? AND period_id = ?", (mailbox, period_id))

        c.execute("COMMIT")
        conn.close()

        return True, "Claimed", {
            "job_id": job_id,
            "decision_id": decision_id,
            "period_id": period_id,
            "attempt_count": attempt_count,
            "reservation_id": reservation_id
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

def rollback_quota(mailbox: str, purpose: str = "campaign", period_id: str = None, reservation_id: str = None):
    """
    Rollback quota ONLY if SMTP failed completely before DATA submission.
    INVARIANT: Never rollback quota for post-DATA exceptions (e.g. QUIT errors or timeouts).
    """
    if not period_id:
        period_id = get_current_period_id()
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        c.execute("BEGIN IMMEDIATE")
        if reservation_id:
            c.execute("""
                SELECT status FROM quota_reservations
                WHERE reservation_id = ? AND mailbox = ? AND period_id = ?
            """, (reservation_id, mailbox, period_id))
            r_row = c.fetchone()
            if not r_row or r_row["status"] != "RESERVED":
                c.execute("COMMIT")
                conn.close()
                return
            c.execute("""
                UPDATE quota_reservations
                SET status = 'RELEASED', updated_at = ?
                WHERE reservation_id = ?
            """, (now_iso, reservation_id))

        if purpose == "campaign":
            c.execute("""
                UPDATE mailbox_period_usage
                SET campaign_used = MAX(0, campaign_used - 1)
                WHERE mailbox = ? AND period_id = ?
            """, (mailbox, period_id))
            c.execute("""
                UPDATE mailbox_quotas 
                SET campaign_sent = MAX(0, campaign_sent - 1) 
                WHERE mailbox = ? AND period_id = ?
            """, (mailbox, period_id))
        elif purpose == "test":
            c.execute("""
                UPDATE mailbox_period_usage
                SET diagnostic_used = MAX(0, diagnostic_used - 1)
                WHERE mailbox = ? AND period_id = ?
            """, (mailbox, period_id))
            c.execute("""
                UPDATE mailbox_quotas 
                SET diagnostic_sent = MAX(0, diagnostic_sent - 1) 
                WHERE mailbox = ? AND period_id = ?
            """, (mailbox, period_id))
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

def open_hold(mailbox: str, hold_type: str, scope: str = 'mailbox', opening_event_id: str = None, retry_after: str = None, domain: str = None, conn = None) -> str:
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    c = conn.cursor()
    if not domain:
        domain = mailbox.split("@")[-1]
    
    # Check if this exact hold or an active hold of this type already exists
    c.execute("""
        SELECT hold_id, opened_at FROM mailbox_holds
        WHERE mailbox = ? AND hold_type = ? AND resolved_at IS NULL
    """, (mailbox, hold_type))
    existing = c.fetchone()
    now_iso = datetime.now(timezone.utc).isoformat()
    if existing:
        hold_id = existing["hold_id"]
        if retry_after:
            c.execute("UPDATE mailbox_holds SET retry_after = ? WHERE hold_id = ?", (retry_after, hold_id))
    else:
        hold_id = f"hold_{hold_type.lower()}_{mailbox}_{uuid.uuid4().hex[:6]}"
        c.execute("""
            INSERT INTO mailbox_holds (hold_id, mailbox, domain, hold_type, scope, opening_event_id, opened_at, retry_after)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (hold_id, mailbox, domain, hold_type, scope, opening_event_id, now_iso, retry_after))
        
    c.execute("""
        UPDATE mailbox_levels
        SET status = 'paused', paused_reason = COALESCE(paused_reason, ?), paused_at = COALESCE(paused_at, ?)
        WHERE mailbox = ?
    """, (f"Active hold: {hold_type}", now_iso, mailbox))
    
    if close_conn:
        conn.commit()
        conn.close()
    return hold_id


def resolve_hold(hold_id: str, resolution_evidence_ids: str = None, conn = None):
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    c.execute("""
        UPDATE mailbox_holds
        SET resolved_at = ?, resolution_evidence_ids = ?
        WHERE hold_id = ?
    """, (now_iso, resolution_evidence_ids, hold_id))
    
    c.execute("SELECT mailbox FROM mailbox_holds WHERE hold_id = ?", (hold_id,))
    row = c.fetchone()
    if row:
        mb = row["mailbox"]
        c.execute("SELECT COUNT(*) FROM mailbox_holds WHERE mailbox = ? AND resolved_at IS NULL", (mb,))
        remaining = c.fetchone()[0]
        if remaining == 0:
            c.execute("""
                UPDATE mailbox_levels
                SET status = 'active', paused_reason = NULL, paused_at = NULL
                WHERE mailbox = ?
            """, (mb,))
            
    if close_conn:
        conn.commit()
        conn.close()


def pause_mailbox(mailbox: str, reason: str):
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
    UPDATE mailbox_levels SET status = 'paused', paused_reason = ?, paused_at = ?
    WHERE mailbox = ?
    """, (reason, now_iso, mailbox))
    
    # Also record structured hold in mailbox_holds
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mailbox_holds'")
    if c.fetchone():
        r_lower = reason.lower()
        if "spam" in r_lower:
            htype = "SEED_SPAM"
        elif "transport" in r_lower:
            htype = "HOLD_TRANSPORT_ERROR"
        elif "auth" in r_lower:
            htype = "HOLD_AUTH_FAILED"
        elif "temporary" in r_lower or "4xx" in r_lower:
            htype = "TEMP_FAILURE_BACKOFF"
        else:
            htype = "MANUAL_PAUSE"
            
        m_match = re.search(r"<([^>]+)>", reason)
        op_event = m_match.group(0) if m_match else "pause_event"
        open_hold(mailbox, htype, scope="mailbox", opening_event_id=op_event, conn=conn)

    conn.commit()
    conn.close()

def pause_domain(domain: str, reason: str):
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
    UPDATE mailbox_levels SET status = 'paused', paused_reason = ? || ' [DOMAIN LEVEL]', paused_at = ?
    WHERE domain = ?
    """, (reason, now_iso, domain))
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mailbox_holds'")
    if c.fetchone():
        r_lower = reason.lower()
        htype = "HOLD_AUTH_FAILED" if "auth" in r_lower else "DOMAIN_PAUSED"
        m_match = re.search(r"<([^>]+)>", reason)
        op_event = m_match.group(0) if m_match else "domain_pause_event"
        # Open domain-scoped hold
        hold_id = f"hold_{htype.lower()}_dom_{domain}_{uuid.uuid4().hex[:6]}"
        c.execute("""
            INSERT OR IGNORE INTO mailbox_holds (hold_id, mailbox, domain, hold_type, scope, opening_event_id, opened_at)
            VALUES (?, ?, ?, ?, 'domain', ?, ?)
        """, (hold_id, f"@{domain}", domain, htype, op_event, now_iso))

    conn.commit()
    conn.close()

def resume_mailbox(mailbox: str):
    """Requires manual operator invocation with documented resolution."""
    conn = get_db_connection()
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    c.execute("""
    UPDATE mailbox_levels SET status = 'active', paused_reason = NULL, paused_at = NULL
    WHERE mailbox = ?
    """, (mailbox,))
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mailbox_holds'")
    if c.fetchone():
        c.execute("""
            UPDATE mailbox_holds SET resolved_at = ?, resolution_evidence_ids = 'manual_admin_resumption'
            WHERE mailbox = ? AND resolved_at IS NULL
        """, (now_iso, mailbox))
    conn.commit()
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
