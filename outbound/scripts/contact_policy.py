#!/usr/bin/env python3
"""
Mindmaxing Contact Policy & Gatekeeper Engine v1.0
- Pure, deterministic evaluation of prospect contact candidates.
- Enforces conjunctive gates before any message can be approved or dispatched:
  1. Verified business/person relationship (Identity)
  2. Explicit email association (Email Origin)
  3. Authoritative mailbox verification (Fresh within 7 days)
  4. Non-generic personal mailbox (Blocks role accounts)
  5. Zero active suppression (Bounces, opt-outs, unsubscribes)
  6. Campaign approval state & immutable active sequence recipient binding
- Passing contact checks does NOT automatically create HUMAN_APPROVED status.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
import re
import os
import sys

try:
    from email_classifier import is_role_account, is_valid_email
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from email_classifier import is_role_account, is_valid_email

# --- Canonical Dimension Constants ---

class IdentityStatus:
    UNCONFIRMED = "UNCONFIRMED"
    FOUNDER_CONFIRMED = "FOUNDER_CONFIRMED"
    CONFLICT = "CONFLICT"

class EmailOrigin:
    PUBLIC_SITE = "PUBLIC_SITE"
    PUBLIC_EXTERNAL = "PUBLIC_EXTERNAL"
    PROVIDER_FOUND = "PROVIDER_FOUND"
    PROVIDER_INFERRED = "PROVIDER_INFERRED"
    LEGACY_UNKNOWN = "LEGACY_UNKNOWN"

class MailboxVerification:
    UNCHECKED = "UNCHECKED"
    VALID = "VALID"
    INVALID = "INVALID"
    ACCEPT_ALL = "ACCEPT_ALL"
    UNKNOWN = "UNKNOWN"
    TEMPFAIL = "TEMPFAIL"
    BLOCKED = "BLOCKED"

class ContactDecision:
    ELIGIBLE = "ELIGIBLE"
    NEEDS_CONTACT = "NEEDS_CONTACT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    RETRY_DUE = "RETRY_DUE"

# Policy Lifetimes
MAX_VERIFICATION_AGE = timedelta(days=7)
MAX_IDENTITY_EVIDENCE_AGE = timedelta(days=30)


def _parse_iso(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def evaluate_contact(
    candidate: Dict[str, Any],
    campaign_state: Dict[str, Any],
    now: Optional[datetime] = None
) -> Tuple[bool, str, List[str]]:
    """
    Pure evaluation function for contact eligibility.
    Returns: (is_eligible: bool, decision: str, reason_codes: List[str])

    Conjunctive requirements for is_eligible == True:
    1. Identity: FOUNDER_CONFIRMED (refreshed within 30 days)
    2. Origin: PUBLIC_SITE, PUBLIC_EXTERNAL, or PROVIDER_FOUND (no inference)
    3. Mailbox: VALID (fresh within 7 days, no catch-all)
    4. Mailbox: Non-generic (is_role_account == False)
    5. Suppression: Not suppressed, bounced, or opted-out
    6. Campaign: status == HUMAN_APPROVED and immutable sequence recipient respected
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    reasons: List[str] = []

    email = (candidate.get("contact_email") or "").strip().lower()
    identity_status = candidate.get("identity_status", IdentityStatus.UNCONFIRMED)
    email_origin = candidate.get("email_origin", EmailOrigin.LEGACY_UNKNOWN)
    mailbox_verif = candidate.get("mailbox_verification", MailboxVerification.UNCHECKED)
    verif_time = _parse_iso(candidate.get("verification_time"))
    id_evidence_time = _parse_iso(candidate.get("identity_evidence_time"))

    # 1. Email Syntax Gate
    if not is_valid_email(email):
        reasons.append("INVALID_EMAIL_SYNTAX")

    # 2. Identity Check
    if identity_status == IdentityStatus.CONFLICT:
        reasons.append("IDENTITY_CONFLICT")
    elif identity_status != IdentityStatus.FOUNDER_CONFIRMED:
        reasons.append("IDENTITY_NOT_CONFIRMED")
    else:
        # Check evidence expiration (30 days) - timestamp required
        if not id_evidence_time:
            reasons.append("IDENTITY_EVIDENCE_TIME_MISSING")
        elif (now - id_evidence_time) > MAX_IDENTITY_EVIDENCE_AGE:
            reasons.append("IDENTITY_EVIDENCE_EXPIRED")

    # 3. Email Origin Check (No blind inference permitted for automated dispatch)
    if email_origin == EmailOrigin.PROVIDER_INFERRED:
        reasons.append("EMAIL_ORIGIN_INFERRED_REQUIRES_REVIEW")
    elif email_origin not in (EmailOrigin.PUBLIC_SITE, EmailOrigin.PUBLIC_EXTERNAL, EmailOrigin.PROVIDER_FOUND):
        reasons.append(f"UNSUPPORTED_EMAIL_ORIGIN_{email_origin}")

    # 4. Mailbox Verification Check - timestamp required
    if mailbox_verif == MailboxVerification.VALID:
        if not verif_time:
            reasons.append("MAILBOX_VERIFICATION_TIME_MISSING")
        elif (now - verif_time) > MAX_VERIFICATION_AGE:
            reasons.append("MAILBOX_VERIFICATION_EXPIRED")
    elif mailbox_verif == MailboxVerification.ACCEPT_ALL:
        reasons.append("MAILBOX_ACCEPT_ALL_ROUTING")
    elif mailbox_verif == MailboxVerification.TEMPFAIL:
        reasons.append("MAILBOX_TEMPFAIL")
    elif mailbox_verif == MailboxVerification.BLOCKED:
        reasons.append("MAILBOX_POLICY_BLOCKED")
    elif mailbox_verif == MailboxVerification.INVALID:
        reasons.append("MAILBOX_RECIPIENT_INVALID")
    else:
        reasons.append(f"MAILBOX_NOT_VALID_{mailbox_verif}")

    # 5. Non-Generic Role Account Gate
    if is_role_account(email):
        reasons.append("GENERIC_ROLE_ACCOUNT_REJECTED")

    # 6. Suppression Gate
    if campaign_state.get("is_suppressed", False):
        reasons.append("RECIPIENT_SUPPRESSED")

    # 7. Campaign State Gate
    camp_status = campaign_state.get("status", "CANDIDATE")
    if camp_status != "HUMAN_APPROVED":
        reasons.append(f"CAMPAIGN_STATUS_NOT_APPROVED_{camp_status}")

    # 8. Active Sequence Recipient Immutability
    seq_step = campaign_state.get("current_sequence_step", 0)
    active_recipient = (campaign_state.get("active_recipient") or "").strip().lower()
    if seq_step > 0:
        if not active_recipient:
            reasons.append("ACTIVE_SEQUENCE_RECIPIENT_MISSING")
        elif active_recipient != email:
            reasons.append("ACTIVE_SEQUENCE_RECIPIENT_MISMATCH")

    # 9. Quota Check
    if not campaign_state.get("quota_available", True):
        reasons.append("SEND_QUOTA_EXHAUSTED")

    # Decision Categorization
    if not reasons:
        return True, ContactDecision.ELIGIBLE, []

    # Map failure reasons to pure Decision
    if any(r in ("MAILBOX_TEMPFAIL", "MAILBOX_VERIFICATION_EXPIRED", "IDENTITY_EVIDENCE_EXPIRED") for r in reasons):
        decision = ContactDecision.RETRY_DUE
    elif any(r in ("INVALID_EMAIL_SYNTAX", "MAILBOX_RECIPIENT_INVALID", "RECIPIENT_SUPPRESSED") for r in reasons):
        decision = ContactDecision.NEEDS_CONTACT
    else:
        decision = ContactDecision.REVIEW_REQUIRED

    return False, decision, reasons
