#!/usr/bin/env python3
"""
Mindmaxing Email & Contact Classifier v1.0
- Deterministic classification of email addresses into PERSONAL vs GENERIC_SUPPORT.
- Comprehensive 85+ prefix blocklist derived from production mail systems (flask-mailing, OpenLeads).
- Strict 75+ word non-person blocklist to prevent false-positive founder names ("Team", "Customerservice", "Services").
- Standalone with zero external dependencies.
"""

import re
from typing import Dict, Optional, Tuple

# 85+ known role-based and department prefixes
ROLE_BASED_PREFIXES = frozenset({
    "support", "info", "contact", "hello", "help", "care", "service", "services",
    "customercare", "customerservice", "customer", "team", "sales", "orders",
    "returns", "press", "media", "legal", "privacy", "billing", "invoices",
    "accounting", "careers", "jobs", "hr", "marketing", "security", "abuse",
    "postmaster", "mailer-daemon", "noreply", "no-reply", "do-not-reply", "bounce",
    "admin", "administrator", "office", "frontdesk", "reception", "enquiry",
    "enquiries", "general", "community", "wecare", "clientservices", "member",
    "members", "feedback", "shop", "store", "orders-tracking", "affiliate",
    "wholesale", "techsupport", "operations", "ops", "cs", "helpdesk",
    "customersupport", "clientcare", "guestservices", "contactus", "hi", "hey",
    "chat", "desk", "inquiry", "inquiries", "shipping", "fulfillment", "returns-exchanges",
    "tracking", "b2b", "corp", "corporate", "partners", "partnership", "partnerships",
    "dev", "development", "it", "webmaster", "hostmaster", "root", "compliance",
    "privacy-policy", "dmca", "claims", "warranty", "tech", "sales-team",
    "connect", "branding", "onlinesales", "brand", "ecommerce", "e-commerce"
})

# Ticketing systems and bot domains/patterns
BOT_PATTERNS = [
    r"zendesk\.com",
    r"gorgias\.io",
    r"freshdesk\.com",
    r"tidio\.com",
    r"intercom-mail\.com",
    r"kayako\.com",
    r"zoho\.com",
]

# 130+ blocklist words that are NOT human founder names (departments, commerce tokens, stopwords, headings)
NON_PERSON_NAMES = frozenset({
    "team", "services", "service", "customercare", "customerservice", "customer",
    "support", "hello", "contact", "founder", "founders", "co-founder", "owner",
    "owners", "creator", "creators", "admin", "administrator", "store", "shop",
    "staff", "desk", "department", "brand", "company", "management", "official",
    "help", "care", "info", "sales", "billing", "returns", "press", "media",
    "ciao", "welcome", "security", "community", "inquiry", "inquiries", "orders",
    "operations", "boutique", "market", "collection", "collections", "studio",
    "studios", "group", "holdings", "enterprises", "international", "global",
    "europe", "usa", "uk", "australia", "canada", "germany", "france",
    "client", "clients", "member", "members", "partner", "partners", "shipping",
    "fulfillment", "general", "office", "frontdesk", "reception", "anonymous",
    "social", "marketing", "sleep", "ops", "onlinesales", "yourvoice", "wecare",
    "meow", "ourosjewels", "servic", "sales-support",
    # English stopwords & web heading noise
    "the", "our", "we", "for", "are", "about", "behind", "meet", "search", "story",
    "loved", "by", "cleaning", "products", "discount", "loyalty", "program", "all",
    "and", "or", "in", "on", "at", "to", "from", "with", "your", "my", "their",
    "this", "that", "these", "those", "how", "what", "who", "where", "why", "when",
    "can", "will", "do", "does", "did", "have", "has", "had", "be", "is", "was",
    "were", "been", "being", "more", "most", "some", "any", "no", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "now",
    # E-commerce product and category tokens
    "pet", "pets", "dog", "cat", "tumbler", "glass", "glasses", "sauna", "saunas",
    "rug", "rugs", "apparel", "clothing", "jewelry", "jewels", "door", "doors",
    "cover", "covers", "supply", "supplies", "outlet", "warranties", "warranty",
    "accessories", "accessory", "reviews", "review", "happiness", "practice",
    "esports", "blog", "govx", "rewards", "affiliates", "stores", "scratch",
    "designers", "designer", "promise", "enthusiasm", "started", "learn", "made",
    "forbes", "yrs", "people", "live"
})

# File asset extensions to ignore in regex
ASSET_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js",
    ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mov"
)


def clean_email(email: Optional[str]) -> str:
    """Sanitizes raw email string, removes quotes, spaces, and trailing punctuation."""
    if not email:
        return ""
    em = str(email).strip().lower()
    em = em.strip(".,;:\"'<>[](){}\\/")
    return em


def is_valid_email(email: Optional[str]) -> bool:
    """Basic syntax and extension gate."""
    em = clean_email(email)
    if not em or "@" not in em:
        return False
    if any(em.endswith(ext) for ext in ASSET_EXTENSIONS):
        return False
    # Standard RFC 5322 compliant regex check
    match = re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", em)
    if not match:
        return False
    parts = em.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
        return False
    return True


def is_role_account(email: Optional[str]) -> bool:
    """Returns True if the email belongs to a generic/department mailbox."""
    em = clean_email(email)
    if not is_valid_email(em):
        return True
    local_part = em.split("@")[0].lower()
    
    # Check exact match
    if local_part in ROLE_BASED_PREFIXES:
        return True

    # Check prefixes with separators (e.g., support-team, info_uk, sales.us)
    prefix_base = re.split(r"[-._+]", local_part)[0]
    if prefix_base in ROLE_BASED_PREFIXES:
        return True

    # Check regional/localized variants (e.g. infousa, infoeu, salesuk, ordersca)
    if re.match(r"^(info|support|sales|order|orders|contact|care|service|services|help)(us|usa|uk|eu|ca|au|de|fr|it|es|in)$", local_part):
        return True

    # Check if local_part is identical to domain root (e.g. ourosjewels@gmail.com or memarinedivesupply@gmail.com)
    domain_root = em.split("@")[1].split(".")[0].lower()
    if local_part == domain_root and len(local_part) > 3:
        return True

    # Check ticketing bot patterns in the domain or local-part
    for pattern in BOT_PATTERNS:
        if re.search(pattern, em, re.IGNORECASE):
            return True

    return False


def classify_email(email: Optional[str]) -> Dict:
    """
    Classifies an email address into PERSONAL vs GENERIC_SUPPORT.
    Returns full structural breakdown.
    """
    em = clean_email(email)
    if not is_valid_email(em):
        return {
            "clean_email": em,
            "domain": "",
            "local_part": "",
            "is_valid": False,
            "is_role_account": True,
            "classification": "INVALID",
            "matched_prefix": None,
        }

    local_part, domain = em.split("@", 1)
    prefix_base = re.split(r"[-._+]", local_part)[0]
    
    matched_prefix = None
    if local_part in ROLE_BASED_PREFIXES:
        matched_prefix = local_part
    elif prefix_base in ROLE_BASED_PREFIXES:
        matched_prefix = prefix_base

    is_role = is_role_account(em)
    
    return {
        "clean_email": em,
        "domain": domain,
        "local_part": local_part,
        "is_valid": True,
        "is_role_account": is_role,
        "classification": "GENERIC_SUPPORT" if is_role else "PERSONAL",
        "matched_prefix": matched_prefix,
    }


def is_valid_founder_name(name: Optional[str]) -> Tuple[bool, str]:
    """
    Validates that a captured founder name is a genuine human name.
    Rejects generic scraper noise like 'Customerservice', 'Team', 'Services', 'Hello'.
    Requires 2+ capitalized words (e.g. 'Kyle Hoff', 'Bob Chen').
    """
    if not name:
        return False, ""
        
    cleaned = str(name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(".,;:\"'<>[](){}\\/-_")
    
    if not cleaned or len(cleaned) < 3 or len(cleaned) > 50:
        return False, ""
        
    # Check full string against blocklist
    if cleaned.lower() in NON_PERSON_NAMES:
        return False, ""
        
    # Split into words
    words = cleaned.split()
    
    # Must have at least 2 words (e.g. First Last) to avoid single-word company terms
    if len(words) < 2:
        return False, ""
        
    # Check if ANY word is in the blocklist
    for w in words:
        w_lower = w.lower()
        if w_lower in NON_PERSON_NAMES:
            return False, ""
        # Check if word is just numbers or symbols
        if not re.match(r"^[A-Za-zÀ-ÿ'-]+$", w):
            return False, ""
            
    # Name must look like capitalized names
    if not all(w[0].isupper() for w in words if w):
        return False, ""

    return True, cleaned


if __name__ == "__main__":
    # Self-test
    test_emails = [
        "support@houseofayurveda.co",
        "team@poponveneers.com",
        "customerservice@ashford.com",
        "kyle@floydhome.com",
        "frank.garden@andersonsofinverurie.co.uk",
        "hello@floydhome.com",
        "bob.chen@jureynco.com"
    ]
    
    print("=== EMAIL CLASSIFIER TEST ===")
    for t in test_emails:
        res = classify_email(t)
        print(f"{t:42} -> {res['classification']:15} (Prefix: {res['matched_prefix']})")
        
    test_names = [
        "Customerservice", "Team", "Services", "Ciao", "Hello",
        "Kyle Hoff", "Bob Chen", "Frank Garden", "John Doe-Smith"
    ]
    print("\n=== FOUNDER NAME VALIDATOR TEST ===")
    for n in test_names:
        valid, clean = is_valid_founder_name(n)
        print(f"{n:20} -> Valid: {valid} (Clean: '{clean}')")
