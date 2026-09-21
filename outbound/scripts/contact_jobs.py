#!/usr/bin/env python3
"""
Mindmaxing Contact Jobs & Persistent Resolution Queue v2.0
- Transactional job leasing and lease recovery.
- Strict exponential retry backoff schedule:
  - Retry 1: +1 hour
  - Retry 2: +1 day (24h)
  - Retry 3: +7 days
  - Exceeded retries (> 3): Held for review (`HELD_FOR_REVIEW`).
  - Genuine no-results: Bounded retry after 30 days.
  - Honours provider `Retry-After` headers.
- Full auditability:
  - Records every candidate in `contact_candidates`.
  - Appends all transitions to `contact_resolution_events`.
"""

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

CODE_VERSION = "2.0.0-phase3"

# Retry Delays (in seconds)
RETRY_DELAY_1 = 3600         # 1 hour
RETRY_DELAY_2 = 86400        # 24 hours
RETRY_DELAY_3 = 604800       # 7 days
NO_RESULT_RETRY_DELAY = 2592000  # 30 days


def generate_run_id() -> str:
    """Generates unique run ID for audit tracking."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return f"run_{ts}_{uid}"


def claim_next_job(
    conn: sqlite3.Connection,
    worker_id: str,
    lease_duration_sec: int = 300
) -> Optional[sqlite3.Row]:
    """
    Transactionally claims the next eligible contact job.
    Recovers expired leases where worker crashed or timed out.
    """
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    lease_expires = (now_dt + timedelta(seconds=lease_duration_sec)).isoformat()

    c.execute("BEGIN IMMEDIATE;")
    try:
        # Find pending job or expired lease
        row = c.execute("""
            SELECT id, lead_id, domain, attempt_count, status
            FROM contact_jobs
            WHERE (status = 'PENDING' AND (next_attempt_at IS NULL OR next_attempt_at <= :now_iso))
               OR (status = 'RUNNING' AND lease_expires_at IS NOT NULL AND lease_expires_at < :now_iso)
            ORDER BY id ASC
            LIMIT 1;
        """, {"now_iso": now_iso}).fetchone()

        if not row:
            conn.commit()
            return None

        job_id = row["id"]
        prior_status = row["status"]

        # Atomically claim the lease
        c.execute("""
            UPDATE contact_jobs
            SET status = 'RUNNING',
                worker_id = :worker_id,
                lease_expires_at = :lease_expires,
                updated_at = :now_iso
            WHERE id = :job_id;
        """, {
            "worker_id": worker_id,
            "lease_expires": lease_expires,
            "now_iso": now_iso,
            "job_id": job_id
        })

        # Append lease claim event
        run_id = generate_run_id()
        c.execute("""
            INSERT INTO contact_resolution_events (
                lead_id, domain, run_id, code_version, event_type,
                inputs_json, outcome, before_state_json, after_state_json, created_at
            ) VALUES (
                :lead_id, :domain, :run_id, :code_version, 'JOB_CLAIMED',
                :inputs, 'CLAIMED', :before_state, :after_state, :now_iso
            );
        """, {
            "lead_id": row["lead_id"],
            "domain": row["domain"],
            "run_id": run_id,
            "code_version": CODE_VERSION,
            "inputs": json.dumps({"worker_id": worker_id, "lease_sec": lease_duration_sec}),
            "before_state": json.dumps({"status": prior_status}),
            "after_state": json.dumps({"status": "RUNNING", "lease_expires_at": lease_expires}),
            "now_iso": now_iso
        })

        conn.commit()

        # Re-fetch full updated row
        claimed = c.execute("SELECT * FROM contact_jobs WHERE id = :job_id", {"job_id": job_id}).fetchone()
        return claimed

    except Exception as e:
        conn.rollback()
        raise e


def complete_job(
    conn: sqlite3.Connection,
    job_id: int,
    run_id: str,
    outcome: str,
    candidates: List[Dict[str, Any]],
    lead_summary: Dict[str, Any],
    worker_id: Optional[str] = None
) -> bool:
    """
    Marks job completed, stores evaluated candidates, records resolution events,
    and updates lead summary fields with strict lease fencing and sequence protection.
    """
    c = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    c.execute("BEGIN IMMEDIATE;")
    try:
        job = c.execute("SELECT lead_id, domain, worker_id, lease_expires_at, status FROM contact_jobs WHERE id = :job_id", {"job_id": job_id}).fetchone()
        if not job:
            conn.rollback()
            return False

        # Lease fencing token validation
        if worker_id is not None:
            if job["worker_id"] != worker_id or job["status"] != "RUNNING":
                conn.rollback()
                return False
            if job["lease_expires_at"] and job["lease_expires_at"] < now_iso:
                conn.rollback()
                return False

        lead_id = job["lead_id"]
        domain = job["domain"]

        # 1. Insert candidates into contact_candidates
        for cand in candidates:
            c.execute("""
                INSERT INTO contact_candidates (
                    lead_id, domain, full_name, role, email,
                    email_origin, mailbox_status, mailbox_checked_at,
                    identity_status, identity_checked_at, evidence_json,
                    rejection_reasons, is_selected, created_at, updated_at
                ) VALUES (
                    :lead_id, :domain, :name, :role, :email,
                    :origin, :mailbox_status, :mailbox_checked_at,
                    :identity_status, :identity_checked_at, :evidence,
                    :rejection_reasons, :is_selected, :now_iso, :now_iso
                );
            """, {
                "lead_id": lead_id,
                "domain": domain,
                "name": cand.get("name") or "Unknown",
                "role": cand.get("role"),
                "email": cand.get("email"),
                "origin": cand.get("email_origin", "LEGACY_UNKNOWN"),
                "mailbox_status": cand.get("mailbox_status", "UNCHECKED"),
                "mailbox_checked_at": cand.get("mailbox_checked_at", now_iso if cand.get("email") else None),
                "identity_status": cand.get("identity_status", "UNCONFIRMED"),
                "identity_checked_at": cand.get("identity_checked_at", now_iso),
                "evidence": json.dumps(cand.get("evidence", {})),
                "rejection_reasons": json.dumps(cand.get("rejection_reasons", [])),
                "is_selected": 1 if cand.get("is_selected") else 0,
                "now_iso": now_iso
            })

        # 2. Append event
        c.execute("""
            INSERT INTO contact_resolution_events (
                lead_id, domain, run_id, code_version, event_type,
                inputs_json, outcome, before_state_json, after_state_json, created_at
            ) VALUES (
                :lead_id, :domain, :run_id, :code_version, 'JOB_COMPLETED',
                :inputs, :outcome, :before_state, :after_state, :now_iso
            );
        """, {
            "lead_id": lead_id,
            "domain": domain,
            "run_id": run_id,
            "code_version": CODE_VERSION,
            "inputs": json.dumps({"candidates_count": len(candidates)}),
            "outcome": outcome,
            "before_state": json.dumps({"status": "RUNNING"}),
            "after_state": json.dumps({"status": "COMPLETED", "summary": lead_summary}),
            "now_iso": now_iso
        })

        # 3. Update contact_jobs
        c.execute("""
            UPDATE contact_jobs
            SET status = 'COMPLETED',
                lease_expires_at = NULL,
                updated_at = :now_iso
            WHERE id = :job_id;
        """, {"job_id": job_id, "now_iso": now_iso})

        # 4. Update leads compatibility summary fields while strictly preserving active sequence recipients
        l_row = c.execute("SELECT current_sequence_step, contact_email FROM leads WHERE id = :lead_id", {"lead_id": lead_id}).fetchone()
        seq_active = l_row and (l_row["current_sequence_step"] or 0) > 0

        if not seq_active and lead_summary.get("resolution_status") == "FOUNDER_FOUND" and lead_summary.get("resolved_email"):
            c.execute("""
                UPDATE leads
                SET original_contact_email = COALESCE(original_contact_email, contact_email),
                    contact_email = :r_email,
                    contact_name = :r_name,
                    contact_type = 'FOUNDER_RESOLVED',
                    resolved_name = :r_name,
                    resolved_email = :r_email,
                    resolved_role = :r_role,
                    resolved_evidence = :r_evidence,
                    resolution_status = :r_status,
                    resolved_at = :now_iso
                WHERE id = :lead_id;
            """, {
                "r_name": lead_summary.get("resolved_name"),
                "r_email": lead_summary.get("resolved_email"),
                "r_role": lead_summary.get("resolved_role"),
                "r_evidence": json.dumps(lead_summary.get("evidence", {})),
                "r_status": lead_summary.get("resolution_status", outcome),
                "now_iso": now_iso,
                "lead_id": lead_id
            })
        else:
            c.execute("""
                UPDATE leads
                SET resolved_name = :r_name,
                    resolved_email = :r_email,
                    resolved_role = :r_role,
                    resolved_evidence = :r_evidence,
                    resolution_status = :r_status,
                    resolved_at = :now_iso
                WHERE id = :lead_id;
            """, {
                "r_name": lead_summary.get("resolved_name"),
                "r_email": lead_summary.get("resolved_email"),
                "r_role": lead_summary.get("resolved_role"),
                "r_evidence": json.dumps(lead_summary.get("evidence", {})),
                "r_status": lead_summary.get("resolution_status", outcome),
                "now_iso": now_iso,
                "lead_id": lead_id
            })

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e


def fail_job(
    conn: sqlite3.Connection,
    job_id: int,
    run_id: str,
    error_message: str,
    error_type: str = "ERROR",
    retry_after_sec: Optional[int] = None,
    worker_id: Optional[str] = None
) -> bool:
    """
    Records job failure and schedules next attempt with exponential backoff.
    Enforces lease fencing and transitions to HELD_FOR_REVIEW after 3 retries.
    """
    c = conn.cursor()
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    c.execute("BEGIN IMMEDIATE;")
    try:
        job = c.execute("SELECT lead_id, domain, attempt_count, worker_id, lease_expires_at, status FROM contact_jobs WHERE id = :job_id", {"job_id": job_id}).fetchone()
        if not job:
            conn.rollback()
            return False

        # Lease fencing token validation
        if worker_id is not None:
            if job["worker_id"] != worker_id or job["status"] != "RUNNING":
                conn.rollback()
                return False
            if job["lease_expires_at"] and job["lease_expires_at"] < now_iso:
                conn.rollback()
                return False

        lead_id = job["lead_id"]
        domain = job["domain"]
        attempts = (job["attempt_count"] or 0) + 1

        # Determine next retry schedule
        if retry_after_sec is not None:
            delay = max(10, retry_after_sec)
            next_status = "PENDING"
        elif error_type == "NO_PUBLIC_FOUNDER":
            # Genuine bounded-search no-result: retry after 30 days
            delay = NO_RESULT_RETRY_DELAY
            next_status = "PENDING"
        elif attempts == 1:
            delay = RETRY_DELAY_1  # 1 hour
            next_status = "PENDING"
        elif attempts == 2:
            delay = RETRY_DELAY_2  # 24 hours
            next_status = "PENDING"
        elif attempts == 3:
            delay = RETRY_DELAY_3  # 7 days
            next_status = "PENDING"
        else:
            # Exceeded 3 retries: Hold for manual review
            delay = None
            next_status = "HELD_FOR_REVIEW"

        next_attempt_iso = (now_dt + timedelta(seconds=delay)).isoformat() if delay else None

        # 1. Update contact_jobs
        c.execute("""
            UPDATE contact_jobs
            SET status = :next_status,
                attempt_count = :attempts,
                lease_expires_at = NULL,
                next_attempt_at = :next_attempt_iso,
                last_error = :error_msg,
                last_error_type = :error_type,
                updated_at = :now_iso
            WHERE id = :job_id;
        """, {
            "next_status": next_status,
            "attempts": attempts,
            "next_attempt_iso": next_attempt_iso,
            "error_msg": error_message,
            "error_type": error_type,
            "now_iso": now_iso,
            "job_id": job_id
        })

        # 2. Append event
        c.execute("""
            INSERT INTO contact_resolution_events (
                lead_id, domain, run_id, code_version, event_type,
                inputs_json, outcome, before_state_json, after_state_json, rejection_reasons, created_at
            ) VALUES (
                :lead_id, :domain, :run_id, :code_version, 'JOB_FAILED',
                :inputs, :outcome, :before_state, :after_state, :rejection, :now_iso
            );
        """, {
            "lead_id": lead_id,
            "domain": domain,
            "run_id": run_id,
            "code_version": CODE_VERSION,
            "inputs": json.dumps({"attempt_count": attempts}),
            "outcome": next_status,
            "before_state": json.dumps({"status": "RUNNING"}),
            "after_state": json.dumps({
                "status": next_status,
                "next_attempt_at": next_attempt_iso,
                "error_type": error_type,
                "error_message": error_message
            }),
            "rejection": json.dumps([error_message]),
            "now_iso": now_iso
        })

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        raise e
