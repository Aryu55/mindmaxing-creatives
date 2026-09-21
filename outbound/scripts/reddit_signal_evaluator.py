#!/usr/bin/env python3
"""
Mindmaxing Reddit Signal Evaluator (Astra Specification v2.2)
Pure function:
    evaluate_reddit_signal(post: dict, now: datetime) -> tuple[str, list[str], dict]

Taxonomy:
- INCIDENT_CANDIDATE: Store operator reports a specific, current storefront malfunction.
- REVIEW_REQUIRED: Potentially relevant, but ownership, context, or numeric funnel requires inspection.
- NO_MATCH: Generic feedback, marketing advice, hypothetical question, or non-malfunction.
- STALE: Relevant incident older than 7 days.
- INVALID_SOURCE: Missing/invalid timestamp or deleted/missing source identity.
"""

import re
import urllib.parse
from datetime import datetime, timezone

INCIDENT_CANDIDATE = "INCIDENT_CANDIDATE"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
NO_MATCH = "NO_MATCH"
STALE = "STALE"
INVALID_SOURCE = "INVALID_SOURCE"

POLICY_VERSION = "v2.2-astra-signal"

IGNORED_DOMAINS = {
    "reddit.com", "redd.it", "imgur.com", "preview.redd.it", "i.redd.it", "v.redd.it",
    "youtube.com", "youtu.be", "google.com", "apple.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "tiktok.com", "linkedin.com", "pinterest.com",
    "stripe.com", "paypal.com", "shopify.com", "wikipedia.org", "github.com",
    "medium.com", "discord.gg", "discord.com", "t.me", "telegram.org",
    "amazon.com", "aliexpress.com", "ebay.com", "etsy.com", "walmart.com",
    "bit.ly", "linktr.ee", "canva.com", "notion.so", "figma.com", "loom.com"
}


def extract_store_domain(text: str) -> str:
    """Extracts first valid non-infrastructure domain from text."""
    # Match standard URLs or explicit domains
    matches = re.findall(r'https?://(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+)', text)
    for m in matches:
        dom = m.lower().strip("/.,;:'\"")
        if dom.endswith(".myshopify.com"):
            continue
        if dom not in IGNORED_DOMAINS and not any(dom.endswith("." + ign) for ign in IGNORED_DOMAINS):
            if "." in dom and not dom.endswith((".jpg", ".png", ".webp", ".mp4", ".pdf", ".gif", ".css", ".js")):
                return dom

    # Match raw domains (e.g., example.com)
    raw_matches = re.findall(r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|co|store|org|net|it|ro|ca|uk|shop|io|de|fr|nl))\b', text)
    for dom in raw_matches:
        dom = dom.lower().strip("/.,;:'\"")
        if dom not in IGNORED_DOMAINS and not any(dom.endswith("." + ign) for ign in IGNORED_DOMAINS):
            return dom

    return ""


def split_sentences(text: str) -> list[str]:
    """Splits text into clean normalized sentences."""
    # Split on period, exclamation, question mark, or newlines
    raw = re.split(r'[.!?\n\r]+', text)
    return [s.strip() for s in raw if s.strip()]


def evaluate_reddit_signal(post: dict, now: datetime) -> tuple[str, list[str], dict]:
    """
    Evaluates Reddit post signal per Astra v2.2 specification.
    Returns: (decision, reason_codes, evidence_dict)
    """
    if not isinstance(post, dict):
        return INVALID_SOURCE, ["INVALID_POST_PAYLOAD"], {}

    # 1. Source Identity & Deletion Check
    author = (post.get("author") or "").strip()
    title = (post.get("title") or "").strip()
    selftext = (post.get("selftext") or "").strip()
    permalink = (post.get("permalink") or "").strip()
    url = (post.get("url") or "").strip()
    combined_text = f"{title}\n{selftext}"

    if not title and not selftext:
        return INVALID_SOURCE, ["DELETED_OR_MISSING_SOURCE"], {}

    if author in ("[deleted]", "[removed]") and selftext in ("[deleted]", "[removed]"):
        return INVALID_SOURCE, ["DELETED_OR_MISSING_SOURCE"], {}

    # 2. Strict Timestamp & Freshness Check
    created_raw = post.get("created_utc")
    if created_raw is None:
        return INVALID_SOURCE, ["MISSING_OR_INVALID_TIMESTAMP"], {}

    post_dt = None
    try:
        if isinstance(created_raw, (int, float)):
            if created_raw <= 0:
                return INVALID_SOURCE, ["MISSING_OR_INVALID_TIMESTAMP"], {}
            post_dt = datetime.fromtimestamp(created_raw, tz=timezone.utc)
        elif isinstance(created_raw, str):
            # Parse ISO or float string
            try:
                val = float(created_raw)
                if val <= 0:
                    return INVALID_SOURCE, ["MISSING_OR_INVALID_TIMESTAMP"], {}
                post_dt = datetime.fromtimestamp(val, tz=timezone.utc)
            except ValueError:
                clean_iso = created_raw.replace("Z", "+00:00")
                post_dt = datetime.fromisoformat(clean_iso)
                if post_dt.tzinfo is None:
                    post_dt = post_dt.replace(tzinfo=timezone.utc)
    except Exception:
        return INVALID_SOURCE, ["MISSING_OR_INVALID_TIMESTAMP"], {}

    if not post_dt:
        return INVALID_SOURCE, ["MISSING_OR_INVALID_TIMESTAMP"], {}

    # Ensure `now` is timezone-aware
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    age_days = (now - post_dt).total_seconds() / 86400.0
    is_stale = age_days > 7.0

    domain = extract_store_domain(combined_text)

    evidence = {
        "domain": domain,
        "author": author,
        "post_url": f"https://reddit.com{permalink}" if permalink.startswith("/") else (url or f"https://reddit.com{permalink}"),
        "post_timestamp": post_dt.isoformat(),
        "eval_timestamp": now.isoformat(),
        "policy_version": POLICY_VERSION,
        "supporting_text": "",
        "component": "",
        "malfunction": ""
    }

    # 3. Negation Check (e.g. "Our checkout is not broken", "everything works")
    # If the only problem mention is explicitly negated, it is not a malfunction.
    negation_patterns = [
        r"\b(?:not|isn't|is not|never)\s+(?:broken|down|unresponsive|failing|crashing)\b",
        r"\bcheckout\s+(?:is not|isn't|not)\s+broken\b",
        r"\bcart\s+(?:is not|isn't|not)\s+broken\b",
        r"\beverything\s+works\b",
        r"\bworks\s+fine\b",
        r"\btested\s+it\s+thoroughly\b",
        r"\bno\s+issues\b"
    ]
    has_negation = any(re.search(pat, combined_text, re.IGNORECASE) for pat in negation_patterns)

    # 4. Hypothetical Question Check
    hypothetical_patterns = [
        r"\bwhat\s+(?:should|would|can)\s+(?:i|we)\s+do\s+if\b",
        r"\bwhat\s+if\b",
        r"\bif\s+.*(?:ever|happens to)\s+(?:breaks?|crashes?|fails?)\b",
        r"\bin\s+case\s+.*(?:breaks?|crashes?|fails?)\b",
        r"\bhypothetically\b"
    ]
    is_hypothetical = any(re.search(pat, combined_text, re.IGNORECASE) for pat in hypothetical_patterns)
    if is_hypothetical:
        evidence["supporting_text"] = title
        return NO_MATCH, ["HYPOTHETICAL_QUESTION"], evidence

    # 5. Ad / Marketing Only Query Check (e.g., "My ads are not working. Should I change creatives?")
    ad_only_patterns = [
        r"\b(?:my\s+)?ads\s+are\s+not\s+working\b",
        r"\bshould\s+i\s+change\s+creatives\b",
        r"\brunning\s+meta\s+ads\b.*\bno\s+(?:sales|luck|conversions)\b",
        r"\bad\s+spend\b.*\bno\s+(?:sales|luck)\b"
    ]
    # Check if there is NO component/technical failure mentioned anywhere
    has_tech_keyword = any(k in combined_text.lower() for k in [
        "cart drawer", "checkout button", "add to cart", "atc", "quantity", "liquid", "theme update", "theme bug"
    ])
    if any(re.search(pat, combined_text, re.IGNORECASE) for pat in ad_only_patterns) and not has_tech_keyword:
        evidence["supporting_text"] = title
        return NO_MATCH, ["MARKETING_OR_AD_QUERY_ONLY"], evidence

    # 6. Aesthetic / Appearance Feedback Check (e.g. "Does the checkout button look good?", "Thoughts on colours?")
    appearance_patterns = [
        r"\blook\s+good\b",
        r"\bthoughts\s+on\s+colou?rs?\b",
        r"\bfeedback\s+on\s+palette\b",
        r"\bhow\s+does\s+.*look\b"
    ]
    if any(re.search(pat, combined_text, re.IGNORECASE) for pat in appearance_patterns):
        # If it also explicitly asserts "everything works" or doesn't claim a failure
        if has_negation or not any(w in combined_text.lower() for w in ["broken", "stopped", "resets", "empties", "unresponsive"]):
            evidence["supporting_text"] = title or selftext
            return NO_MATCH, ["NO_MALFUNCTION_ASSERTED", "NON_MALFUNCTION_THEME_FEEDBACK"], evidence

    # 7. Numeric Funnel Drop-off Case (e.g., "400 clicks, 45 add-to-carts, zero checkout starts")
    funnel_click_pat = re.search(r'(\d+)\s*(?:clicks|visitors|sessions)', combined_text, re.IGNORECASE)
    funnel_atc_pat = re.search(r'(\d+)\s*(?:add[- ]to[- ]carts?|atc)', combined_text, re.IGNORECASE)
    funnel_co_pat = re.search(r'(?:zero|0|\bno\b)\s*(?:checkout|checkouts|purchases|orders|sales)', combined_text, re.IGNORECASE)

    if funnel_click_pat and funnel_atc_pat and funnel_co_pat:
        # If there is no specific code/button malfunction explicitly reported
        has_specific_bug = any(b in combined_text.lower() for b in [
            "button stopped", "cart empties", "cart resets", "unresponsive", "fails to open", "blank page", "spinning"
        ])
        if not has_specific_bug:
            evidence["supporting_text"] = selftext[:200]
            evidence["stated_metrics"] = {
                "clicks": funnel_click_pat.group(0),
                "atc": funnel_atc_pat.group(0),
                "checkouts": funnel_co_pat.group(0)
            }
            return REVIEW_REQUIRED, ["NUMERIC_FUNNEL_DROPOFF_WITHOUT_REPORTED_MALFUNCTION"], evidence

    # 8. Payment Failure with Unknown Cause (e.g. "payment gateway failed", "Stripe payment failure")
    payment_failure_patterns = [
        r"\b(?:payment\s+gateway|stripe|paypal|apple\s+pay|shop\s+pay)\s+(?:failed|error|failing|declined)\b",
        r"\bcustomers\s+getting\s+error\s+at\s+payment\b"
    ]
    if any(re.search(pat, combined_text, re.IGNORECASE) for pat in payment_failure_patterns):
        has_theme_cause = any(k in combined_text.lower() for k in ["theme.liquid", "button stopped", "cart drawer", "js error"])
        if not has_theme_cause:
            evidence["supporting_text"] = selftext[:200] or title
            return REVIEW_REQUIRED, ["PAYMENT_FAILURE_UNKNOWN_CAUSE"], evidence

    # 9. Performance Score Alone (e.g., "Lighthouse score is 32", "PageSpeed score dropped")
    pagespeed_score_patterns = [
        r"\b(?:lighthouse|pagespeed)\s+(?:score|is)\b",
        r"\bscore\s+dropped\b"
    ]
    if any(re.search(pat, combined_text, re.IGNORECASE) for pat in pagespeed_score_patterns):
        if not any(k in combined_text.lower() for k in ["stopped responding", "broken", "cart empties", "losing sales"]):
            evidence["supporting_text"] = selftext[:200] or title
            return REVIEW_REQUIRED, ["PERFORMANCE_SCORE_WITHOUT_MALFUNCTION"], evidence

    # 10. Storefront Component & Malfunction Analysis (Adjacency Check)
    sentences = split_sentences(combined_text)

    # Component indicators
    component_defs = [
        ("mobile checkout button", r"\bmobile\s+checkout\s+button\b"),
        ("checkout button", r"\bcheckout\s+button\b"),
        ("checkout", r"\bcheckout\b"),
        ("cart drawer", r"\bcart\s+drawer\b"),
        ("cart", r"\bcart\b"),
        ("quantity update", r"\b(?:change|update|updating)\s+quantity\b|\bquantity\b"),
        ("add to cart button", r"\badd\s+to\s+cart\s+button\b|\batc\s+button\b"),
        ("add to cart", r"\badd\s+to\s+cart\b|\batc\b")
    ]

    # Malfunction indicators
    malfunction_defs = [
        ("stopped responding", r"\bstopped\s+responding\b"),
        ("not responding", r"\bnot\s+responding\b"),
        ("unresponsive", r"\bunresponsive\b"),
        ("does nothing", r"\bdoes\s+nothing\b"),
        ("not working", r"\bnot\s+working\b"),
        ("stopped working", r"\bstopped\s+working\b"),
        ("won't open", r"\bwon't\s+open\b|\bwill\s+not\s+open\b"),
        ("fails to open", r"\bfails\s+to\s+open\b"),
        ("empties", r"\bempties\b|\bempty\b"),
        ("resets", r"\bresets\b"),
        ("disappears", r"\bdisappears\b"),
        ("stuck loading", r"\bstuck\s+loading\b|\bspinning\b"),
        ("blank page", r"\bblank\s+page\b"),
        ("cannot complete", r"\bcannot\s+complete\b|\bcan't\s+complete\b"),
        ("broken", r"\bbroken\b|\bbreaks\b")
    ]

    found_incident = False
    incident_component = ""
    incident_malfunction = ""
    incident_sentence = ""

    # Evaluate each sentence individually first, then adjacent sentence pairs
    for i, s in enumerate(sentences):
        s_lower = s.lower()
        # Skip if sentence is negated ("checkout is not broken")
        if any(re.search(pat, s, re.IGNORECASE) for pat in negation_patterns):
            continue

        matched_comp = None
        for c_label, c_regex in component_defs:
            if re.search(c_regex, s, re.IGNORECASE):
                matched_comp = c_label
                break

        matched_malf = None
        for m_label, m_regex in malfunction_defs:
            if re.search(m_regex, s, re.IGNORECASE):
                # Ensure it's not "traffic but no sales" or "ads not working"
                if m_label == "not working" and ("ads" in s_lower or "creatives" in s_lower):
                    continue
                matched_malf = m_label
                break

        if matched_comp and matched_malf:
            found_incident = True
            incident_component = matched_comp
            incident_malfunction = matched_malf
            incident_sentence = s
            break

        # Check adjacent sentence connection
        if i + 1 < len(sentences):
            pair = f"{s}. {sentences[i+1]}"
            pair_lower = pair.lower()
            if not any(re.search(pat, pair, re.IGNORECASE) for pat in negation_patterns):
                matched_comp_pair = None
                for c_label, c_regex in component_defs:
                    if re.search(c_regex, pair, re.IGNORECASE):
                        matched_comp_pair = c_label
                        break
                matched_malf_pair = None
                for m_label, m_regex in malfunction_defs:
                    if re.search(m_regex, pair, re.IGNORECASE):
                        if m_label == "not working" and ("ads" in pair_lower or "creatives" in pair_lower):
                            continue
                        matched_malf_pair = m_label
                        break
                if matched_comp_pair and matched_malf_pair:
                    found_incident = True
                    incident_component = matched_comp_pair
                    incident_malfunction = matched_malf_pair
                    incident_sentence = pair
                    break

    # If negation was present and no clear positive incident was found
    if has_negation and not found_incident:
        evidence["supporting_text"] = title or selftext
        return NO_MATCH, ["NEGATION_DETECTED"], evidence

    # If no malfunction found, verify if it's generic feedback
    if not found_incident:
        # Check generic phrases: "Traffic but no sales", "people add to cart but don't buy"
        generic_phrases = [
            "traffic but no sales", "people add to cart but", "review my store", "rate my store",
            "just launched", "roast my store", "roast my website"
        ]
        evidence["supporting_text"] = title or selftext
        if any(gp in combined_text.lower() for gp in generic_phrases):
            return NO_MATCH, ["GENERIC_FEEDBACK_ONLY"], evidence
        return NO_MATCH, ["NO_MALFUNCTION_ASSERTED"], evidence

    # Incident was asserted! Populate evidence fields.
    evidence["supporting_text"] = incident_sentence
    evidence["component"] = incident_component
    evidence["malfunction"] = incident_malfunction

    # 11. Stale Check
    if is_stale:
        return STALE, ["STALE_SOURCE_EXCEEDS_7_DAYS"], evidence

    # 12. Ownership Context Check
    # Must describe operating the store: "my store", "our store", "my website", "our cart", etc.
    ownership_indicators = [
        r"\bmy\s+store\b", r"\bour\s+store\b", r"\bmy\s+website\b", r"\bour\s+website\b",
        r"\bmy\s+site\b", r"\bour\s+site\b", r"\bmy\s+shopify\b", r"\bour\s+shopify\b",
        r"\bmy\s+cart\b", r"\bour\s+cart\b", r"\bmy\s+checkout\b", r"\bour\s+checkout\b",
        r"\bi\s+run\b", r"\bwe\s+run\b", r"\bi\s+own\b", r"\bwe\s+own\b",
        r"\bmy\s+brand\b", r"\bour\s+brand\b", r"\bmy\s+store's\b", r"\bour\s+store's\b"
    ]
    has_operator_claim = any(re.search(pat, combined_text, re.IGNORECASE) for pat in ownership_indicators)

    # Check for third-party / competitor / client indicators
    third_party_indicators = [
        r"\bcompetitor(?:'s)?\b", r"\brival\b", r"\bclient(?:'s)?\b",
        r"\bsaw\s+(?:a|this)\s+(?:site|store)\b", r"\bsomeone\s+else(?:'s)?\b",
        r"\banother\s+store\b"
    ]
    is_third_party = any(re.search(pat, combined_text, re.IGNORECASE) for pat in third_party_indicators)

    if is_third_party or not has_operator_claim:
        return REVIEW_REQUIRED, ["UNCLEAR_AUTHOR_STORE_RELATIONSHIP"], evidence

    # 13. Missing Store URL Check
    if not domain:
        return REVIEW_REQUIRED, ["MISSING_STORE_URL"], evidence

    # All 5 criteria satisfied!
    return INCIDENT_CANDIDATE, ["STOREFRONT_MALFUNCTION_REPORTED"], evidence
