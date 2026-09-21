#!/usr/bin/env python3
"""
Mindmaxing Delivery Events & Pure MIME/DSN Parser v2.0
- Pure functions for RFC-compliant delivery status, bounce, and reply analysis.
- RFC 3464 DSN parser:
  - Distinguishes Action: failed, delayed, delivered, relayed.
  - Distinguishes Status: 5.1.1 (invalid mailbox), 5.2.2 (mailbox full), 4.x.x (temporary delay), 5.7.x (policy rejection).
  - Strictly rejects empty or wildcard matching. Unmatched notices never alter unrelated records.
- Inbound Reply Classifier:
  - Detects RFC Auto-Submitted headers (auto-replied, auto-generated).
  - Recognizes human replies, out-of-office notices, ticket deflections, and explicit opt-outs.
  - INVARIANT: A human reply supersedes any prior auto-response acknowledgement.
- Trusted Authentication-Results parser (RFC 8601).
"""

import email
import email.policy
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class DSNAction:
    FAILED = "failed"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    RELAYED = "relayed"
    UNKNOWN = "unknown"


class BounceCategory:
    HARD_BOUNCE = "HARD_BOUNCE"         # 5.1.1, 5.1.2 - invalid destination
    TEMP_FAILURE = "TEMP_FAILURE"       # 4.x.x, connection timed out, greylisted
    MAILBOX_FULL = "MAILBOX_FULL"       # 5.2.2 - over quota
    POLICY_BLOCKED = "POLICY_BLOCKED"   # 5.7.x - spam block, DMARC/SPF reject
    UNMATCHED = "UNMATCHED"             # Inconclusive or no recipient found


class ReplyType:
    HUMAN_REPLY = "HUMAN_REPLY"
    AUTO_RESPONSE = "AUTO_RESPONSE"
    OUT_OF_OFFICE = "OUT_OF_OFFICE"
    OPT_OUT = "OPT_OUT"
    TICKET_DEFLECTION = "TICKET_DEFLECTION"


@dataclass
class ParsedDSN:
    action: str
    status_code: str
    diagnostic_code: str
    recipient: str
    original_message_id: Optional[str]
    category: str
    is_hard_bounce: bool
    is_ambiguous: bool


@dataclass
class ParsedReply:
    reply_type: str
    in_reply_to: Optional[str]
    references: List[str]
    from_email: str
    subject: str
    body_excerpt: str
    is_opt_out: bool
    is_human: bool
    stated_return_date: Optional[str] = None


@dataclass
class ParsedAuthResults:
    trusted_auth: bool
    spf_result: str
    dkim_result: str
    dmarc_result: str
    raw_header: str


def parse_dsn_report(raw_bytes: bytes) -> ParsedDSN:
    """
    Parses a DSN (Delivery Status Notification) according to RFC 3464.
    Extracts action, status code, diagnostic code, and failed recipient.
    Rejects wildcarding.
    """
    msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)
    action = DSNAction.UNKNOWN
    status_code = ""
    diag_code = ""
    recipient = ""
    orig_msg_id = None

    # 1. Walk multipart parts to find message/delivery-status
    for part in msg.walk():
        content_type = part.get_content_type()
        
        if content_type == "message/delivery-status":
            payload = part.get_payload()
            # Can be list of Message objects or raw string
            if isinstance(payload, list):
                for sub_msg in payload:
                    if "Action" in sub_msg:
                        action = str(sub_msg.get("Action", "")).lower().strip()
                    if "Status" in sub_msg:
                        status_code = str(sub_msg.get("Status", "")).strip()
                    if "Diagnostic-Code" in sub_msg:
                        diag_code = str(sub_msg.get("Diagnostic-Code", "")).strip()
                    if "Final-Recipient" in sub_msg:
                        raw_rcpt = str(sub_msg.get("Final-Recipient", ""))
                        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_rcpt)
                        if m:
                            recipient = m.group(0).lower().strip()
                    elif "Original-Recipient" in sub_msg and not recipient:
                        raw_rcpt = str(sub_msg.get("Original-Recipient", ""))
                        m = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_rcpt)
                        if m:
                            recipient = m.group(0).lower().strip()

        elif content_type in ("message/rfc822", "text/rfc822-headers"):
            # Original sent message headers
            sub_payload = part.get_payload()
            if isinstance(sub_payload, list) and len(sub_payload) > 0:
                orig_msg_id = sub_payload[0].get("Message-ID")
            elif hasattr(sub_payload, "get"):
                orig_msg_id = sub_payload.get("Message-ID")

    # Fallback: scan body text if recipient or action was not structured
    body_text = str(raw_bytes[:4000], errors="ignore")
    if not recipient:
        m = re.search(r"(?:for|to|recipient)[:\s]+(?:rfc822;\s*)?<?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>?", body_text, re.IGNORECASE)
        if m:
            recipient = m.group(1).lower().strip()

    if not status_code:
        m_stat = re.search(r"(?:Status|code)[:\s]+([45]\.\d+\.\d+)", body_text, re.IGNORECASE)
        if m_stat:
            status_code = m_stat.group(1)

    if not diag_code:
        m_diag = re.search(r"(?:Diagnostic-Code|Diagnostic)[:\s]+([^\r\n]+)", body_text, re.IGNORECASE)
        if m_diag:
            diag_code = m_diag.group(1).strip()

    if not action:
        if "5." in status_code:
            action = DSNAction.FAILED
        elif "4." in status_code:
            action = DSNAction.DELAYED

    # Determine bounce category
    is_hard = False
    is_ambig = False
    category = BounceCategory.UNMATCHED

    if not recipient:
        is_ambig = True
        category = BounceCategory.UNMATCHED
    elif status_code.startswith("4.") or action == DSNAction.DELAYED:
        category = BounceCategory.TEMP_FAILURE
    elif status_code in ("5.1.1", "5.1.2") or "user unknown" in diag_code.lower() or "recipient unknown" in body_text.lower():
        category = BounceCategory.HARD_BOUNCE
        is_hard = True
    elif status_code == "5.2.2" or "mailbox full" in diag_code.lower():
        category = BounceCategory.MAILBOX_FULL
    elif status_code.startswith("5.7.") or "spam" in diag_code.lower() or "blocked" in diag_code.lower():
        category = BounceCategory.POLICY_BLOCKED
    elif action == DSNAction.FAILED:
        # Generic 5xx failure
        category = BounceCategory.HARD_BOUNCE
        is_hard = True
    else:
        category = BounceCategory.UNMATCHED
        is_ambig = True

    return ParsedDSN(
        action=action,
        status_code=status_code,
        diagnostic_code=diag_code,
        recipient=recipient,
        original_message_id=str(orig_msg_id).strip() if orig_msg_id else None,
        category=category,
        is_hard_bounce=is_hard,
        is_ambiguous=is_ambig
    )


def strip_quoted_text(body: str) -> str:
    """
    Strips quoted email history and footers to isolate newly authored text.
    Prevents false-positive opt-out matches on quoted outbound footers.
    """
    if not body:
        return ""
    lines = body.splitlines()
    clean_lines = []
    
    quote_headers = [
        re.compile(r"^\s*on\s+.+wrote\s*:\s*$", re.IGNORECASE),
        re.compile(r"^\s*-----original message-----\s*$", re.IGNORECASE),
        re.compile(r"^\s*from\s*:\s*.+@.+", re.IGNORECASE),
        re.compile(r"^\s*sent\s*:\s*.+", re.IGNORECASE),
        re.compile(r"^\s*--\s*$", re.IGNORECASE),
        re.compile(r"^\s*mindmaxing studio\s*$", re.IGNORECASE),
        re.compile(r"^\s*reply\s+[\"']?stop[\"']?\s+to\s+opt\s+out", re.IGNORECASE),
    ]
    
    for line in lines:
        stripped = line.strip()
        if line.startswith(">"):
            continue
        if any(pat.search(stripped) for pat in quote_headers):
            break
        clean_lines.append(line)
        
    return "\n".join(clean_lines).strip()


def parse_inbound_reply(raw_bytes: bytes) -> ParsedReply:
    """
    Classifies an incoming prospect reply.
    - Accurately distinguishes human replies from automated bot confirmations.
    - Recognizes opt-outs and out-of-office notices on clean, unquoted text only.
    """
    msg = email.message_from_bytes(raw_bytes, policy=email.policy.default)
    from_hdr = str(msg.get("From", "")).lower()
    subj_hdr = str(msg.get("Subject", ""))
    in_reply_to = str(msg.get("In-Reply-To", "")).strip() or None
    raw_refs = str(msg.get("References", "")).split()
    references = [r.strip() for r in raw_refs if r.strip()]

    # Extract clean from address
    m_from = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", from_hdr)
    from_email = m_from.group(0).lower() if m_from else from_hdr

    # Get body text
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
                    break
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="ignore")
    if not body:
        body = str(raw_bytes[:3000], errors="ignore")

    # Isolate newly authored text by stripping quotes & footers
    clean_text = strip_quoted_text(body)
    clean_lower = clean_text.lower()
    auto_submitted = str(msg.get("Auto-Submitted", "")).lower()
    precedence = str(msg.get("Precedence", "")).lower()

    # 1. Check Explicit Opt-Out phrases on clean authored text only
    first_word = clean_lower.split()[0].strip(".,!?:\"'") if clean_lower.split() else ""
    opt_out_triggers = [
        "unsubscribe", "remove me", "stop emailing", "opt out", "opt-out",
        "do not contact", "please remove", "take me off", "not interested",
        "stop contacting", "please stop"
    ]
    is_opt_out = (
        first_word in ("stop", "unsubscribe", "halt", "cancel") or
        any(phrase in clean_lower for phrase in opt_out_triggers) or
        any(phrase in subj_hdr.lower() for phrase in ["unsubscribe", "opt out", "opt-out"])
    )
    if is_opt_out:
        return ParsedReply(
            reply_type=ReplyType.OPT_OUT,
            in_reply_to=in_reply_to,
            references=references,
            from_email=from_email,
            subject=subj_hdr,
            body_excerpt=(clean_text or body)[:200].strip(),
            is_opt_out=True,
            is_human=True
        )

    # 2. Check Out-of-Office triggers
    ooo_triggers = [
        "out of office", "away from my desk", "on leave", "maternity leave",
        "vacation until", "annual leave", "auto-reply: away", "autoreply: away"
    ]
    is_ooo = any(phrase in clean_lower or phrase in subj_hdr.lower() for phrase in ooo_triggers)
    if is_ooo:
        return ParsedReply(
            reply_type=ReplyType.OUT_OF_OFFICE,
            in_reply_to=in_reply_to,
            references=references,
            from_email=from_email,
            subject=subj_hdr,
            body_excerpt=(clean_text or body)[:200].strip(),
            is_opt_out=False,
            is_human=False
        )

    # 3. Check Automated System headers
    if auto_submitted in ("auto-replied", "auto-generated") or precedence in ("bulk", "junk", "auto_reply"):
        return ParsedReply(
            reply_type=ReplyType.AUTO_RESPONSE,
            in_reply_to=in_reply_to,
            references=references,
            from_email=from_email,
            subject=subj_hdr,
            body_excerpt=(clean_text or body)[:200].strip(),
            is_opt_out=False,
            is_human=False
        )

    # 4. Check Support Ticket Deflection
    ticket_triggers = [
        "ticket created", "request received", "support request #",
        "ticket #", "zendesk", "gorgias", "freshdesk", "helpdesk"
    ]
    if any(phrase in clean_lower or phrase in subj_hdr.lower() for phrase in ticket_triggers):
        if any(w in clean_lower for w in ["automated response", "we have received your request", "a representative will"]):
            return ParsedReply(
                reply_type=ReplyType.TICKET_DEFLECTION,
                in_reply_to=in_reply_to,
                references=references,
                from_email=from_email,
                subject=subj_hdr,
                body_excerpt=(clean_text or body)[:200].strip(),
                is_opt_out=False,
                is_human=False
            )

    # 5. Default: Genuine Human Reply
    return ParsedReply(
        reply_type=ReplyType.HUMAN_REPLY,
        in_reply_to=in_reply_to,
        references=references,
        from_email=from_email,
        subject=subj_hdr,
        body_excerpt=(clean_text or body)[:200].strip(),
        is_opt_out=False,
        is_human=True
    )


def parse_auth_results(msg: Any, trusted_domain: str = "google.com") -> ParsedAuthResults:
    """
    Parses Authentication-Results from trusted receiver header only.
    Prevents forged internal headers from passing validation (RFC 8601).
    """
    auth_headers = msg.get_all("Authentication-Results", [])
    trusted_hdr = ""
    for hdr in auth_headers:
        hdr_str = str(hdr).strip()
        # Must match receiving authentication boundary, e.g. mx.google.com or google.com
        if re.match(r"^(?:mx\.)?" + re.escape(trusted_domain) + r"\b", hdr_str, re.IGNORECASE):
            trusted_hdr = hdr_str
            break

    if not trusted_hdr:
        return ParsedAuthResults(
            trusted_auth=False,
            spf_result="unknown",
            dkim_result="unknown",
            dmarc_result="unknown",
            raw_header=""
        )

    spf = "unknown"
    dkim = "unknown"
    dmarc = "unknown"

    m_spf = re.search(r"\bspf=([a-zA-Z0-9_-]+)", trusted_hdr, re.IGNORECASE)
    if m_spf:
        spf = m_spf.group(1).lower()

    m_dkim = re.search(r"\bdkim=([a-zA-Z0-9_-]+)", trusted_hdr, re.IGNORECASE)
    if m_dkim:
        dkim = m_dkim.group(1).lower()

    m_dmarc = re.search(r"\bdmarc=([a-zA-Z0-9_-]+)", trusted_hdr, re.IGNORECASE)
    if m_dmarc:
        dmarc = m_dmarc.group(1).lower()

    return ParsedAuthResults(
        trusted_auth=True,
        spf_result=spf,
        dkim_result=dkim,
        dmarc_result=dmarc,
        raw_header=trusted_hdr
    )
