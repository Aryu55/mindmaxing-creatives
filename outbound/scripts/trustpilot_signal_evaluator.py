#!/usr/bin/env python3
"""
Trustpilot Signal Evaluator (Task E Implementation)
Pure function:
    evaluate_trustpilot_signal(review: dict, now_utc: datetime) -> tuple[str, list[str], dict]

Decisions:
- INCIDENT_CANDIDATE: Customer reports a specific, active storefront component malfunction within 7 days.
- REVIEW_REQUIRED: Pricing discrepancies, card decline ambiguity, missing/unresolved timestamps, or manual inspection required.
- NO_MATCH: Fulfillment, shipping, general support/refund grievances, resolved incidents, stale incidents (>7d), or non-technical complaints.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Tuple, List, Dict, Any, Optional

POLICY_VERSION = "v2.3-trustpilot-evaluator"

INCIDENT_CANDIDATE = "INCIDENT_CANDIDATE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
NO_MATCH = "NO_MATCH"

# Storefront components
STOREFRONT_COMPONENTS = [
    r"\bcheckout\b",
    r"\bcheckout button\b",
    r"\bcheckout page\b",
    r"\bcart\b",
    r"\bcart drawer\b",
    r"\bshopping bag\b",
    r"\bbasket\b",
    r"\badd to cart\b",
    r"\bquantity\b",
    r"\bvariant\b",
    r"\bdiscount code\b",
    r"\bpromo code\b",
    r"\bcoupon code\b",
    r"\bpayment page\b",
    r"\bpayment gateway\b",
    r"\bproduct page\b",
    r"\bdirection to checkout\b",
]

# Explicit malfunction indicators
MALFUNCTION_PATTERNS = [
    r"\bdoes nothing\b",
    r"\bdoesn't work\b",
    r"\bdoes not work\b",
    r"\bwon'?t let me\b",
    r"\bcannot continue\b",
    r"\bcan'?t continue\b",
    r"\bcannot proceed\b",
    r"\bcan'?t proceed\b",
    r"\bcannot complete\b",
    r"\bcan'?t complete\b",
    r"\bunable to (?:order|checkout|pay|purchase|buy)\b",
    r"\b(?:resets|clears|empties)\b",
    r"\bfreez(?:es|ing|ed)\b",
    r"\bcrash(?:es|ed|ing)\b",
    r"\bstuck\b",
    r"\bglitch(?:es|ed|y|ing)?\b",
    r"\bbug(?:gy|ged)?\b",
    r"\bloop\b",
    r"\bspinner\b",
    r"\bdisappear(?:s|ed)?\b",
    r"\bunresponsive\b",
    r"\bfailed to load\b",
    r"\berror\b",
]

# Resolution patterns (issues that were fixed)
RESOLVED_PATTERNS = [
    r"\bfixed it\b",
    r"\bresolved\b",
    r"\bworking now\b",
    r"\bfixed yesterday\b",
    r"\bsupport fixed\b",
    r"\bwas able to (?:finally|eventually)\b",
]

# Pure shipping / fulfillment keywords (when no storefront malfunction is present)
FULFILLMENT_PATTERNS = [
    r"\bnever received\b",
    r"\bhasn'?t arrived\b",
    r"\bdid not arrive\b",
    r"\bdelayed delivery\b",
    r"\bslow shipping\b",
    r"\bpackage never\b",
    r"\btracking number\b",
    r"\bwhere is my order\b",
    r"\bcustoms\b",
    r"\bcourier\b",
    r"\bpost office\b",
    r"\busps\b",
    r"\bfedex\b",
    r"\bdhl\b",
    r"\bups\b",
]

# Support / Refund dispute patterns
SUPPORT_REFUND_PATTERNS = [
    r"\bgood luck trying to get a refund\b",
    r"\bno refund\b",
    r"\brefuse to refund\b",
    r"\brefusing a refund\b",
    r"\bwhere is my refund\b",
    r"\bnobody answers\b",
    r"\bno one replies\b",
    r"\bno customer service\b",
    r"\bterrible customer service\b",
    r"\bworst customer service\b",
    r"\bhorrible customer service\b",
    r"\bauto(?:matic)? shipping\b",
    r"\bauto(?:matically)? subscribe\b",
]


def split_sentences(text: str) -> List[str]:
    """Splits text into sentences while preserving sentence order."""
    if not text:
        return []
    # Normalize clean breaks
    clean = re.sub(r'[\r\n]+', '. ', text)
    raw = re.split(r'(?<=[.!?])\s+', clean)
    return [s.strip() for s in raw if s.strip()]


def parse_review_date(date_val: Any) -> Optional[datetime]:
    """Parses ISO timestamp string or datetime object to UTC datetime."""
    if isinstance(date_val, datetime):
        if date_val.tzinfo is None:
            return date_val.replace(tzinfo=timezone.utc)
        return date_val.astimezone(timezone.utc)
    if not isinstance(date_val, str) or not date_val.strip():
        return None
    cleaned = date_val.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        # Try strptime fallbacks
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d-%b-%Y"):
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def evaluate_trustpilot_signal(review: Dict[str, Any], now_utc: datetime) -> Tuple[str, List[str], Dict[str, Any]]:
    """
    Evaluates an individual Trustpilot review signal.
    Returns: (decision, reason_codes, evidence_dict)
    """
    if now_utc.tzinfo is None:
        raise ValueError("now_utc must be a timezone-aware UTC datetime")

    if not isinstance(review, dict):
        return NO_MATCH, ["INVALID_REVIEW_PAYLOAD"], {}

    title = (review.get("title") or "").strip()
    body = (review.get("text") or review.get("snippet") or review.get("body") or "").strip()
    full_text = f"{title}\n{body}".strip()

    evidence = {
        "policy_version": POLICY_VERSION,
        "review_id": review.get("id") or review.get("review_id") or "",
        "source_url": review.get("url") or review.get("source_url") or "",
        "author": review.get("author") or review.get("consumer", {}).get("displayName") or "",
        "raw_date": review.get("date") or review.get("publishedDate") or "",
        "evidence_span": "",
        "timestamp_evaluated": now_utc.isoformat(),
    }

    if not full_text:
        return NO_MATCH, ["EMPTY_REVIEW_TEXT"], evidence

    # Check for explicitly resolved issues ("support fixed it yesterday", "was resolved")
    for rpat in RESOLVED_PATTERNS:
        if re.search(rpat, full_text, re.IGNORECASE):
            match = re.search(rpat, full_text, re.IGNORECASE)
            evidence["evidence_span"] = match.group(0)
            return NO_MATCH, ["RESOLVED_INCIDENT"], evidence

    # 1. Date & Recency Verification
    raw_date = review.get("date") or review.get("publishedDate")
    rev_dt = parse_review_date(raw_date)

    # Missing date check: If there's an explicit storefront malfunction but no valid date, return REVIEW_REQUIRED
    has_component = any(re.search(cp, full_text, re.IGNORECASE) for cp in STOREFRONT_COMPONENTS)
    has_malfunction = any(re.search(mp, full_text, re.IGNORECASE) for mp in MALFUNCTION_PATTERNS)

    if not rev_dt:
        if has_component and has_malfunction:
            evidence["evidence_span"] = full_text[:200]
            return REVIEW_REQUIRED, ["MISSING_OR_INVALID_TIMESTAMP_NEEDS_MANUAL_DATE_CHECK"], evidence
        return NO_MATCH, ["MISSING_OR_INVALID_TIMESTAMP"], evidence

    # Future date sanity check
    if rev_dt > now_utc + timedelta(hours=24):
        return NO_MATCH, ["FUTURE_DATED_REVIEW"], evidence

    # Strict 7-day recency window per invariant
    age = now_utc - rev_dt
    if age > timedelta(days=7):
        evidence["evidence_span"] = f"Review date {rev_dt.isoformat()} is {age.days} days old (>7d limit)"
        return NO_MATCH, ["STALE_INCIDENT_OLDER_THAN_7_DAYS"], evidence

    evidence["review_datetime"] = rev_dt.isoformat()
    evidence["age_hours"] = round(age.total_seconds() / 3600.0, 1)

    # 2. Check for Specific Discrepancy / Ambiguous Patterns (REVIEW_REQUIRED fixtures)
    # Fixture 6: Bundle price / Currency / Cart discrepancy
    # e.g. "Bundle says $99 AUD but when added to cart it switches to $140 AUD"
    cart_price_discrepancy = re.search(
        r'(?:bundle|price|cost|says|listed|advertised).*?(?:\$|\bAUD\b|\bUSD\b|\bEUR\b|\bGBP\b|\bCAD\b|\d+).*?(?:cart|checkout).*?(?:switches|changes|becomes|charges|jumps|different|higher)',
        full_text,
        re.IGNORECASE | re.DOTALL
    ) or re.search(
        r'(?:added to cart|in cart|at checkout).*?(?:switches to|changes to|becomes).*?(?:\$|\bAUD\b|\bUSD\b|\d+)',
        full_text,
        re.IGNORECASE
    )
    if cart_price_discrepancy:
        evidence["evidence_span"] = cart_price_discrepancy.group(0)
        return REVIEW_REQUIRED, ["PRICE_CURRENCY_OR_DISCOUNT_DISCREPANCY_REQUIRES_INVESTIGATION"], evidence

    # Fixture 7: Card declined without explicit storefront malfunction
    # e.g. "My card was declined."
    card_declined = re.search(r'\b(?:my )?card (?:was )?declined\b', full_text, re.IGNORECASE)
    if card_declined:
        # Check if there is an explicit storefront crash/bug mentioned in conjunction
        if not re.search(r'\b(?:crash|bug|glitch|error|loop|broken|stuck)\b', full_text, re.IGNORECASE):
            evidence["evidence_span"] = card_declined.group(0)
            return REVIEW_REQUIRED, ["CARD_DECLINED_ISSUER_OR_GATEWAY_UNRESOLVED"], evidence

    # 3. Component + Malfunction Matching in Same or Adjacent Sentence
    sentences = split_sentences(full_text)
    candidate_spans = []

    for idx, s in enumerate(sentences):
        # Check same sentence
        c_matches = [re.search(cp, s, re.IGNORECASE) for cp in STOREFRONT_COMPONENTS]
        m_matches = [re.search(mp, s, re.IGNORECASE) for mp in MALFUNCTION_PATTERNS]

        comp_found = any(bool(m) for m in c_matches)
        malf_found = any(bool(m) for m in m_matches)

        if comp_found and malf_found:
            candidate_spans.append(s)
            continue

        # Check adjacent sentence (idx - 1 or idx + 1)
        if comp_found:
            prev_s = sentences[idx - 1] if idx > 0 else ""
            next_s = sentences[idx + 1] if idx + 1 < len(sentences) else ""
            if any(re.search(mp, prev_s, re.IGNORECASE) for mp in MALFUNCTION_PATTERNS):
                candidate_spans.append(f"{prev_s} {s}")
            elif any(re.search(mp, next_s, re.IGNORECASE) for mp in MALFUNCTION_PATTERNS):
                candidate_spans.append(f"{s} {next_s}")

    if candidate_spans:
        # Clean extracted span
        best_span = candidate_spans[0]
        evidence["evidence_span"] = best_span
        return INCIDENT_CANDIDATE, ["STOREFRONT_COMPONENT_MALFUNCTION_OBSERVED"], evidence

    # 4. Filter Common False Positives (Fulfillment / Support / Generic)
    for fpat in FULFILLMENT_PATTERNS:
        if re.search(fpat, full_text, re.IGNORECASE):
            evidence["evidence_span"] = re.search(fpat, full_text, re.IGNORECASE).group(0)
            return NO_MATCH, ["FULFILLMENT_OR_COURIER_ISSUE"], evidence

    for spat in SUPPORT_REFUND_PATTERNS:
        if re.search(spat, full_text, re.IGNORECASE):
            evidence["evidence_span"] = re.search(spat, full_text, re.IGNORECASE).group(0)
            return NO_MATCH, ["CUSTOMER_SUPPORT_OR_REFUND_GRIEVANCE"], evidence

    # Default fallback
    evidence["evidence_span"] = full_text[:140]
    return NO_MATCH, ["NO_ACTIONABLE_STOREFRONT_INCIDENT_FOUND"], evidence
