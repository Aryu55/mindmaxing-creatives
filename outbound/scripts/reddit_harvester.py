#!/usr/bin/env python3
"""
Mindmaxing Reddit Incident Harvester v3.0 (Astra Evidence-Based Qualification Design)
- Replaces generic "review my store" queries with concrete incident-specific query families (Q1-Q8).
- Explicit target communities: r/shopify, r/ecommerce (primary); r/FacebookAds, r/PPC (scoped technical only).
- Enforces negative suffix: NOT (title:"rate my" OR title:"review my" OR title:"roast my" OR title:"feedback on my").
- Evaluates posts as untrusted text with strict soft-negative discard rules.
- Saves leads strictly into 'CANDIDATE' status (Fail-closed: requires human approval before dispatch).
- Multi-stage gatekeeping: Shopify physical DTC, custom domain only (0 bare myshopify), non-Indian/non-INR currency gate, live Linux DNS MX verification.
- Stealth biology: Poisson/Gaussian timing, modern rotating browser fingerprints, live rate-limit telemetry.
"""

import base64
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone

try:
    from email_classifier import is_valid_founder_name, is_role_account
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from email_classifier import is_valid_founder_name, is_role_account

try:
    from reddit_signal_evaluator import (
        evaluate_reddit_signal,
        INCIDENT_CANDIDATE,
        REVIEW_REQUIRED,
        NO_MATCH,
        STALE,
        INVALID_SOURCE,
        POLICY_VERSION
    )
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from reddit_signal_evaluator import (
        evaluate_reddit_signal,
        INCIDENT_CANDIDATE,
        REVIEW_REQUIRED,
        NO_MATCH,
        STALE,
        INVALID_SOURCE,
        POLICY_VERSION
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ICP1_DIR = os.path.join(DATA_DIR, "icp1_shopify_dtc")
OUTPUT_FILE = os.path.join(ICP1_DIR, "leads.json")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")
LOG_FILE = os.path.join(DATA_DIR, "reddit_harvester.log")
TARGET_COUNT = 1000

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "w0_Bj6zG0uZrxVydfqW05Q")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "gtCjNNxJiA_P8VIDMqVFiG84lrKFMg")
REDDIT_USER_AGENT = "MindmaxingHarvester/3.0 (by /u/aryupanchal)"

# Astra Primary Negative Suffix
NEGATIVE_SUFFIX = 'NOT (title:"rate my" OR title:"review my" OR title:"roast my" OR title:"feedback on my")'

# Astra Query Families Q1 - Q8
PRIMARY_INCIDENT_QUERIES = [
    # Q1: Actionable cart/button malfunction
    f'("checkout button" OR "add to cart button" OR "cart drawer") AND ("not working" OR "unresponsive" OR "does nothing" OR "stopped working" OR "won\'t open") AND {NEGATIVE_SUFFIX}',
    # Q2: Cart-state failure
    f'("cart drawer" OR "shopping cart" OR "cart page") AND ("resets" OR "empties" OR "disappears" OR "quantity resets" OR "items removed" OR "stuck loading") AND {NEGATIVE_SUFFIX}',
    # Q3: Cart-to-checkout counts (funnel breakdown)
    f'("add to cart" OR "add to carts" OR "ATC") AND ("reached checkout" OR "initiated checkout" OR "initiate checkout" OR "IC") AND ("zero" OR "0" OR "dropped" OR "drop off") AND {NEGATIVE_SUFFIX}',
    # Q4: Checkout/payment symptom
    f'("checkout" OR "Apple Pay" OR "Shop Pay" OR "payment gateway") AND ("spinning" OR "freezes" OR "frozen" OR "blank page" OR "won\'t load" OR "cannot complete") AND {NEGATIVE_SUFFIX}',
    # Q5: Temporal regression after theme or app change
    f'("theme update" OR "installed an app" OR "updated the theme" OR "changed theme") AND ("checkout" OR "cart" OR "conversion rate") AND ("stopped" OR "broken" OR "dropped" OR "error") AND {NEGATIVE_SUFFIX}',
    # Q6: Performance regression
    f'("Lighthouse" OR "PageSpeed" OR "LCP" OR "INP" OR "theme.liquid") AND ("mobile" OR "product page") AND ("regression" OR "after installing" OR "after updating" OR "seconds" OR "blocking") AND {NEGATIVE_SUFFIX}',
    # Q7: Declared demand for help with relevant fault
    f'("hire" OR "paid help" OR "pay someone" OR "budget") AND ("Shopify" OR "Liquid") AND ("cart" OR "checkout" OR "theme bug") AND {NEGATIVE_SUFFIX}',
    # Q8: Small rescue pass (NO title-exclusion suffix; catches genuine incidents in feedback-titled posts)
    '("checkout button" OR "cart drawer") AND ("unresponsive" OR "stopped working" OR "resets") AND ("orders" OR "customers" OR "sales")'
]

# Query Plan: subreddits mapped to queries
PRIMARY_SUBREDDITS = ["shopify", "ecommerce"]
SCOPED_SUBREDDITS = ["FacebookAds", "PPC"]

# Blocked communities yielding non-commercial / hobbyist / swap-thread noise
BLOCKED_SUBREDDITS = {
    "slime", "fragranceswap", "minibrands", "adeptuscustodes", "dnd",
    "halloweencoupons", "indianjerseyculture", "marvel_india", "freeart",
    "stickers", "tshirtdesigns", "indiebookpromo", "brandnew",
    "pakistanfragrances", "travelersnotebooks", "lads_og",
    "promoteyourclothing", "illumicrate", "walmartsellers", "u_bullykingmag",
    "coupons", "deals", "giveaways", "reps", "fashionreps", "jenova_ai", "botconsole",
    "reviewmyshopify" # Excluded per Astra strategic decision
}

# Blocked TLDs: South Asia (non-ICP) + disposable TLDs
BLOCKED_TLDS = (
    ".in", ".co.in", ".pk", ".lk", ".bd", ".np",
    ".store", ".site", ".fun", ".xyz", ".club", ".top", ".buzz", ".online"
)

IGNORED_DOMAINS = [
    "reddit.com", "redd.it", "imgur.com", "preview.redd.it", "i.redd.it", "v.redd.it",
    "youtube.com", "youtu.be", "google.com", "apple.com", "facebook.com", "instagram.com",
    "twitter.com", "x.com", "tiktok.com", "linkedin.com", "pinterest.com",
    "stripe.com", "paypal.com", "shopify.com", "wikipedia.org", "github.com",
    "medium.com", "discord.gg", "discord.com", "t.me", "telegram.org",
    "amazon.com", "aliexpress.com", "ebay.com", "etsy.com", "walmart.com",
    "bit.ly", "linktr.ee", "canva.com", "notion.so", "figma.com", "loom.com",
    "salesforce.com", "pluginhive.com", "sellerapp.com", "podbase.com"
]

DISCARDED_EMAIL_DOMAINS = {
    "example.com", "test.com", "domain.com", "email.com", "yourdomain.com",
    "shopify.com", "myshopify.com", "sentry.io", "wixpress.com", "cloudflare.com"
}

VALID_EMAIL_TLDS = [
    "com", "org", "net", "co", "io", "ca", "uk", "shop", "store",
    "de", "nl", "it", "ro", "digital", "art", "co.uk", "com.au", "eu"
]

SAAS_PATTERNS = [
    r"\bsoftware as a service\b",
    r"\bstart free trial\b",
    r"\bstart your free trial\b",
    r"\bapi documentation\b",
    r"\bpricing plans\b",
    r"\bgame boost\b",
    r"\bweb hosting\b",
    r"\bcloud server\b",
    r"\bcloud vps\b",
    r"\besim plans\b",
    r"\bcrypto trading\b",
    r"\btrading bot\b",
    r"\bforex\b"
]

BROWSER_PROFILES = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1"
    }
]

REFERRERS = [
    "https://www.google.com/search?q=",
    "https://duckduckgo.com/?q=",
    "https://www.bing.com/search?q=",
    ""
]

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [Reddit v3] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_stealth_headers(domain: str = "") -> dict:
    headers = dict(random.choice(BROWSER_PROFILES))
    ref = random.choice(REFERRERS)
    if ref:
        headers["Referer"] = f"{ref}{urllib.parse.quote(domain)}" if domain else "https://www.google.com/"
    return headers

def human_delay(mode: str = "candidate"):
    roll = random.random()
    if mode == "candidate":
        if roll < 0.72:
            d = random.uniform(3.5, 7.0)
        elif roll < 0.93:
            d = random.uniform(11.0, 22.0)
        else:
            d = random.uniform(32.0, 58.0)
    elif mode == "query":
        d = random.uniform(8.0, 16.0)
    elif mode == "cycle":
        d = random.uniform(180.0, 360.0)
    else:
        d = random.uniform(2.0, 5.0)
    time.sleep(d)

class RedditAuth:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.access_token = None
        self.expires_at = 0

    def get_token(self) -> str:
        if self.access_token and time.time() < (self.expires_at - 60):
            return self.access_token

        log("Authenticating Reddit OAuth client_credentials...")
        auth_url = "https://www.reddit.com/api/v1/access_token"
        cred = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("utf-8")
        req_headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"Basic {cred}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")
        req = urllib.request.Request(auth_url, data=data, headers=req_headers)

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                self.access_token = res_data.get("access_token")
                expires_in = res_data.get("expires_in", 3600)
                self.expires_at = time.time() + expires_in
                log(f"Reddit OAuth Token refreshed (expires in {expires_in}s)")
                return self.access_token
        except Exception as e:
            log(f"Failed to authenticate with Reddit OAuth: {e}")
            raise

def load_existing_records() -> tuple[set, set]:
    domains = set()
    emails = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                leads = json.load(f)
                for l in leads:
                    if l.get("domain"):
                        domains.add(l.get("domain").lower().replace("www.", "").strip())
                    if l.get("contact_email"):
                        emails.add(l.get("contact_email").lower().strip())
        except Exception:
            pass
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT domain, contact_email FROM leads")
            for row in cur.fetchall():
                if row[0]:
                    domains.add(row[0].lower().replace("www.", "").strip())
                if row[1]:
                    emails.add(row[1].lower().strip())
            conn.close()
        except Exception:
            pass
    return domains, emails

def sanitize_email(raw_email: str) -> str:
    if not raw_email or "@" not in raw_email:
        return ""
    em = raw_email.strip().lower().strip(".,;:\"'<>)([]{}/\\")
    for tld in VALID_EMAIL_TLDS:
        pattern = rf"^([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.{re.escape(tld)})[a-zA-Z]{{3,}}$"
        m = re.match(pattern, em)
        if m:
            em = m.group(1)
            break
    em = re.sub(r"\.+$", "", em)
    return em

def verify_dns_mx(email: str) -> bool:
    if not email or "@" not in email:
        return False
    domain = email.split("@")[1].strip().lower()
    if domain in DISCARDED_EMAIL_DOMAINS:
        return False
    try:
        res = subprocess.run(["host", "-t", "mx", domain], capture_output=True, text=True, timeout=3.5)
        out = res.stdout.lower()
        return ("mail is handled by" in out or "has mx record" in out)
    except Exception:
        return False

def save_lead(lead: dict) -> bool:
    os.makedirs(ICP1_DIR, exist_ok=True)
    existing_leads = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_leads = json.load(f)
        except Exception:
            existing_leads = []

    clean_dom = lead.get("domain", "").lower().replace("www.", "").strip()
    clean_em = lead.get("contact_email", "").lower().strip()
    if any(l.get("domain", "").lower().replace("www.", "").strip() == clean_dom for l in existing_leads):
        return False
    if any(l.get("contact_email", "").lower().strip() == clean_em for l in existing_leads):
        return False

    status = lead.get("status", "CANDIDATE")
    existing_leads.append(lead)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_leads, f, indent=2)

    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cur = conn.cursor()
        cur.execute("""
        INSERT OR IGNORE INTO leads (
            domain, company_name, contact_email, contact_type, contact_name,
            country_code, city, platform, pain_trigger, dominant_pattern,
            reviews_count, review_freshest_date, reviews_json, captured_at, status,
            source, subreddit, post_title, post_url, post_author,
            signal_decision, signal_reasons, signal_evidence, signal_policy_version, evaluated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead.get("domain"),
            lead.get("company_name"),
            lead.get("contact_email"),
            lead.get("contact_type", "GENERIC_SUPPORT"),
            lead.get("contact_name", ""),
            lead.get("country_code", "US"),
            lead.get("city", ""),
            "Shopify",
            lead.get("pain_trigger", "checkout"),
            lead.get("dominant_pattern", "Reddit Incident Report"),
            lead.get("reviews_count", 1),
            lead.get("review_freshest_date"),
            json.dumps(lead.get("reviews_collection", [])),
            lead.get("captured_at"),
            status,
            "reddit",
            lead.get("subreddit", ""),
            lead.get("post_title", ""),
            lead.get("post_url", ""),
            lead.get("post_author", ""),
            lead.get("signal_decision", INCIDENT_CANDIDATE),
            json.dumps(lead.get("signal_reasons", [])),
            json.dumps(lead.get("signal_evidence", {})),
            lead.get("signal_policy_version", POLICY_VERSION),
            lead.get("evaluated_at", datetime.now(timezone.utc).isoformat())
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"Database write warning: {e}")

    return True


def attach_duplicate_reddit_evidence(existing_lead: dict, new_evidence: dict) -> dict:
    """
    Attaches newer duplicate post evidence to an existing business without
    replacing its active recipient, status, or conversation sequence step.
    """
    lead = dict(existing_lead)
    reviews = list(lead.get("reviews_collection") or [])
    reviews.append(new_evidence)
    lead["reviews_collection"] = reviews
    lead["reviews_count"] = len(reviews)
    lead["review_freshest_date"] = new_evidence.get("date") or lead.get("review_freshest_date")
    return lead


def record_duplicate_reddit_evidence(domain: str, new_evidence: dict):
    """Updates database and file evidence for existing domain without resetting sequence step."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        c = conn.cursor()
        c.execute("SELECT id, reviews_count, reviews_json FROM leads WHERE domain = ?", (domain,))
        row = c.fetchone()
        if row:
            lead_id, count, reviews_raw = row
            reviews = []
            if reviews_raw:
                try:
                    reviews = json.loads(reviews_raw)
                except Exception:
                    reviews = []
            reviews.append(new_evidence)
            c.execute("""
                UPDATE leads
                SET reviews_count = ?,
                    reviews_json = ?,
                    review_freshest_date = ?
                WHERE id = ?
            """, (len(reviews), json.dumps(reviews), new_evidence.get("date"), lead_id))
            conn.commit()
        conn.close()
    except Exception as e:
        log(f"Database duplicate update warning for {domain}: {e}")

def verify_physical_shopify(domain: str) -> tuple[bool, str]:
    clean_domain = domain.replace("www.", "").strip()
    url = f"https://{clean_domain}"
    headers = get_stealth_headers(clean_domain)

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=7) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            html_lower = html.lower()

            # SaaS filter
            if any(re.search(p, html_lower) for p in SAAS_PATTERNS):
                return False, "SaaS/Software indicators found"

            # Strict India/INR filter
            india_indicators = [
                "₹", "\u20B9", "rs.", "inr", "india", "+91",
                '"currency":"inr"', "money_format.*₹", "cash on delivery available"
            ]
            if any(ind in html_lower for ind in india_indicators):
                return False, "Indian / South Asian brand (INR / domestic signals detected)"

            # Shopify signature
            is_shopify = ("cdn.shopify.com" in html_lower or "shopify." in html_lower or "myshopify.com" in html_lower)
            if not is_shopify:
                return False, "Not running Shopify"

            # Cart flow
            has_cart = any(k in html_lower for k in ["cart", "add to cart", "cart-drawer", "checkout", "name=\"add\""])
            if not has_cart:
                return False, "No physical cart flow detected"

            return True, "Verified Shopify DTC"
    except Exception as e:
        return False, f"Connection error: {str(e)[:40]}"

def scrape_store_details(domain: str) -> tuple[str, str, str, str]:
    clean_domain = domain.replace("www.", "").strip()
    headers = get_stealth_headers(clean_domain)
    paths = ["/pages/about", "/pages/about-us", "/pages/contact", "/pages/contact-us", "/policies/privacy-policy", "/policies/terms-of-service"]

    found_email = ""
    founder_name = ""
    contact_type = "GENERIC_SUPPORT"
    country_code = "US"

    for p in paths:
        url = f"https://{clean_domain}{p}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                text_lower = text.lower()

                # India reject
                if any(k in text_lower for k in ["india", "₹", "inr", "+91", "delhi", "mumbai", "bengaluru", "cash on delivery"]):
                    return "", "", "", "IN"

                # Country heuristics
                if any(k in text_lower for k in ["united kingdom", "london", "england", "postcode", "gbr", "gb"]):
                    country_code = "GB"
                elif any(k in text_lower for k in ["canada", "ontario", "toronto", "vancouver", "postal code"]):
                    country_code = "CA"
                elif any(k in text_lower for k in ["australia", "sydney", "melbourne", "nsw", "vic"]):
                    country_code = "AU"

                # Founder name validation
                if not founder_name:
                    name_matches = re.findall(r"(?:founder|founded by|co-founder|owner|creator)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text)
                    if name_matches:
                        raw_n = name_matches[0].strip()
                        is_valid, clean_n = is_valid_founder_name(raw_n)
                        if is_valid:
                            founder_name = clean_n
                            contact_type = "FOUNDER_NAMED_DESK"

                # Email extraction + sanitization
                if not found_email:
                    raw_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
                    for em in raw_emails:
                        clean_em = sanitize_email(em)
                        if clean_em and not clean_em.endswith((".png", ".jpg", ".svg", ".css", ".js")):
                            em_domain = clean_em.split("@")[1]
                            if clean_domain in em_domain or "gmail.com" in em_domain or "outlook.com" in em_domain:
                                is_role = is_role_account(clean_em)
                                prefix = clean_em.split("@")[0].lower()
                                if prefix in ["hello", "contact", "support", "cs", "info"] or is_role:
                                    found_email = clean_em
                                    if not founder_name:
                                        contact_type = "GENERIC_SUPPORT"
                                else:
                                    found_email = clean_em
                                    contact_type = "PERSONAL_CANDIDATE"
                                    break
        except Exception:
            continue

    return found_email, founder_name, contact_type, country_code

def extract_store_domains_from_text(text: str) -> list[str]:
    candidates = set()
    cleaned = re.sub(r"[\[\]\(\)\*\"']", " ", text)
    tokens = cleaned.split()

    for token in tokens:
        token = token.strip(".,;:!?/")
        if token.startswith(("http://", "https://")):
            try:
                parsed = urllib.parse.urlparse(token)
                token = parsed.netloc or parsed.path
            except Exception:
                pass

        dom = token.lower().replace("www.", "").strip("/")
        if dom.endswith(".myshopify.com"):
            continue
        if "." in dom and not any(ign in dom for ign in IGNORED_DOMAINS):
            if not dom.endswith((".jpg", ".png", ".webp", ".mp4", ".pdf", ".gif", ".css", ".js")):
                candidates.add(dom)

    return list(candidates)

def classify_trigger(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["lighthouse", "pagespeed", "lcp", "inp", "speed", "slow", "theme.liquid"]):
        return "slow"
    if any(k in t for k in ["cart drawer", "add to cart", "atc", "cart resets", "cart page"]):
        return "cart"
    if any(k in t for k in ["apple pay", "shop pay", "payment gateway", "gateway", "stripe"]):
        return "payment"
    if any(k in t for k in ["discount", "coupon", "promo code"]):
        return "discount"
    return "checkout"

def post_passes_incident_evaluation(title: str, selftext: str, created_utc: float = None, author: str = "") -> tuple[bool, str]:
    """Bridge function delegating to evaluate_reddit_signal pure function."""
    post = {
        "title": title,
        "selftext": selftext,
        "created_utc": created_utc or time.time(),
        "author": author or "Founder"
    }
    decision, reasons, _ = evaluate_reddit_signal(post, datetime.now(timezone.utc))
    return (decision == INCIDENT_CANDIDATE), ", ".join(reasons)

def run_reddit_harvester(once: bool = False, dry_run: bool = False):
    os.makedirs(ICP1_DIR, exist_ok=True)
    mode_str = "DRY-RUN (zero writes/sends)" if dry_run else ("SINGLE-PASS" if once else "CONTINUOUS")
    log(f"=== Mindmaxing Reddit Incident Harvester v3.0 [Mode: {mode_str}] Starting ===")

    auth = RedditAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT)
    known_domains, known_emails = load_existing_records()
    log(f"Current CRM Lead Reservoir: {len(known_domains)} unique domains, {len(known_emails)} unique emails loaded.")

    cycle = 0
    total_new_qualified = 0
    seen_post_ids = set()

    sweep_stats = {
        "posts_examined": 0,
        "incident_candidates": [],
        "review_required": [],
        "rejected": Counter(),
        "total_new_qualified": 0
    }

    while True:
        cycle += 1
        log(f"--- Starting Astra Evidence-Based Sweep #{cycle} ---")

        # Build query tasks: (subreddit, query_string)
        query_tasks = []
        for sub in PRIMARY_SUBREDDITS:
            for q in PRIMARY_INCIDENT_QUERIES:
                query_tasks.append((sub, q))

        for sub in SCOPED_SUBREDDITS:
            for q in PRIMARY_INCIDENT_QUERIES[:5]:
                scoped_q = f'("Shopify" OR "Liquid" OR "cart drawer") AND {q}'
                query_tasks.append((sub, scoped_q))

        random.shuffle(query_tasks)
        log(f"Compiled {len(query_tasks)} scoped search tasks across target subreddits.")

        for task_idx, (subreddit, query) in enumerate(query_tasks):
            token = auth.get_token()
            headers = {
                "Authorization": f"bearer {token}",
                "User-Agent": REDDIT_USER_AGENT
            }

            log(f"Task [{task_idx+1}/{len(query_tasks)}] r/{subreddit} -> {query[:65]}...")
            params = {
                "q": query,
                "restrict_sr": "1",
                "sort": "new",
                "t": "week",
                "limit": 50,
                "raw_json": "1"
            }

            url = f"https://oauth.reddit.com/r/{subreddit}/search?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers=headers)

            posts = []
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_headers = dict(resp.headers)
                    rl_remaining = float(resp_headers.get("x-ratelimit-remaining", 100))
                    rl_reset = float(resp_headers.get("x-ratelimit-reset", 60))

                    if rl_remaining < 25:
                        pause_sec = rl_reset + random.uniform(4.0, 10.0)
                        log(f"⚠️ Low quota ({rl_remaining:.0f} remaining). Pausing {pause_sec:.1f}s until reset...")
                        time.sleep(pause_sec)

                    res_json = json.loads(resp.read().decode("utf-8"))
                    data = res_json.get("data", {})
                    posts = data.get("children", [])

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    reset_wait = float(e.headers.get("x-ratelimit-reset", 120)) + random.uniform(15.0, 30.0)
                    log(f"🛑 [429 Rate Limit] Backing off {reset_wait:.1f}s...")
                    time.sleep(reset_wait)
                    break
                else:
                    log(f"  HTTP {e.code}: {e}")
                    continue
            except Exception as e:
                log(f"  API Error: {e}")
                continue

            for post_item in posts:
                p = post_item.get("data", {})
                post_id = p.get("id", "")
                if post_id in seen_post_ids:
                    continue
                seen_post_ids.add(post_id)
                sweep_stats["posts_examined"] += 1

                title = p.get("title", "")
                selftext = p.get("selftext", "")
                url_field = p.get("url", "")
                author = p.get("author", "Founder")
                permalink = p.get("permalink", "")
                created_utc = p.get("created_utc", time.time())

                # Post-level evidence filter using pure evaluate_reddit_signal
                decision, reason_codes, evidence = evaluate_reddit_signal(p, datetime.now(timezone.utc))

                if decision == INCIDENT_CANDIDATE:
                    sweep_stats["incident_candidates"].append({
                        "post_id": post_id,
                        "title": title,
                        "author": author,
                        "subreddit": subreddit,
                        "reasons": reason_codes,
                        "evidence": evidence,
                        "url": f"https://reddit.com{permalink}"
                    })
                    log(f"  [★ INCIDENT_CANDIDATE r/{subreddit}] /u/{author}: {title[:70]}")
                elif decision == REVIEW_REQUIRED:
                    sweep_stats["review_required"].append({
                        "post_id": post_id,
                        "title": title,
                        "author": author,
                        "subreddit": subreddit,
                        "reasons": reason_codes,
                        "evidence": evidence,
                        "url": f"https://reddit.com{permalink}"
                    })
                    log(f"  [? REVIEW_REQUIRED r/{subreddit}] /u/{author}: {title[:70]}")
                else:
                    for r in reason_codes:
                        sweep_stats["rejected"][r] += 1

                if dry_run:
                    continue

                if decision in (NO_MATCH, STALE, INVALID_SOURCE):
                    continue

                status = "CANDIDATE" if decision == INCIDENT_CANDIDATE else "REVIEW_REQUIRED"

                post_blob = f"{title}\n{selftext}\n{url_field}"
                extracted_domains = extract_store_domains_from_text(post_blob)
                if not extracted_domains and evidence.get("domain"):
                    extracted_domains = [evidence["domain"]]
                if not extracted_domains:
                    continue

                for candidate_domain in extracted_domains:
                    clean_dom = candidate_domain.replace("www.", "").strip()

                    # Gate 1: Bare myshopify & blocked TLDs
                    if clean_dom.endswith(".myshopify.com") or any(clean_dom.endswith(tld) for tld in BLOCKED_TLDS):
                        continue

                    created_iso = datetime.fromtimestamp(created_utc, timezone.utc).isoformat()
                    clean_body_snippet = re.sub(r"\s+", " ", selftext).strip()[:180]

                    # Gate 2: Deduplication with conversation preservation
                    if clean_dom in known_domains:
                        record_duplicate_reddit_evidence(clean_dom, {
                            "author": author,
                            "text": f"[r/{subreddit}] {title}: {clean_body_snippet}",
                            "date": created_iso,
                            "url": f"https://reddit.com{permalink}",
                            "signal_decision": decision,
                            "signal_reasons": reason_codes
                        })
                        continue
                    known_domains.add(clean_dom)

                    log(f"  [Incident Candidate ({decision}) r/{subreddit}] Inspecting: {clean_dom} (by /u/{author})")

                    # Gate 3: Physical Shopify DTC + Non-INR
                    is_valid, reason = verify_physical_shopify(clean_dom)
                    if not is_valid:
                        log(f"    Rejected {clean_dom}: {reason}")
                        continue

                    # Gate 4: Contact details & Geo
                    email, f_name, c_type, c_code = scrape_store_details(clean_dom)
                    if c_code == "IN":
                        log(f"    Dropped {clean_dom}: Indian store detected.")
                        continue
                    if not email:
                        log(f"    Dropped {clean_dom}: No published contact email found.")
                        continue

                    clean_em = email.lower().strip()
                    if clean_em in known_emails:
                        log(f"    Dropped {clean_dom}: Email {email} already exists (cross-source dedup).")
                        continue

                    # Gate 5: Live DNS MX record
                    if not verify_dns_mx(email):
                        log(f"    Dropped {clean_dom}: Email {email} failed DNS MX lookup.")
                        continue

                    trigger = classify_trigger(title + " " + selftext)
                    company_display = clean_dom.split(".")[0].replace("-", " ").title()

                    lead_record = {
                        "domain": clean_dom,
                        "company_name": company_display,
                        "contact_email": email,
                        "contact_type": c_type,
                        "contact_name": f_name,
                        "country_code": c_code,
                        "city": "",
                        "platform": "Shopify",
                        "pain_trigger": trigger,
                        "dominant_pattern": "Reddit Incident Report",
                        "source": "reddit",
                        "subreddit": subreddit,
                        "post_title": title,
                        "post_author": author,
                        "post_url": f"https://reddit.com{permalink}",
                        "reviews_count": 1,
                        "review_freshest_date": created_iso,
                        "reviews_collection": [{
                            "author": author,
                            "text": f"[r/{subreddit}] {title}: {clean_body_snippet}",
                            "date": created_iso,
                            "trigger": trigger,
                            "url": f"https://reddit.com{permalink}"
                        }],
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "status": status,
                        "signal_decision": decision,
                        "signal_reasons": reason_codes,
                        "signal_evidence": evidence,
                        "signal_policy_version": POLICY_VERSION,
                        "evaluated_at": datetime.now(timezone.utc).isoformat()
                    }

                    if save_lead(lead_record):
                        total_new_qualified += 1
                        sweep_stats["total_new_qualified"] += 1
                        known_domains.add(clean_dom)
                        known_emails.add(clean_em)
                        log(f"    ⭐ QUALIFIED CANDIDATE #{total_new_qualified} -> {company_display} ({email}) [{c_code}]")
                        log(f"       Incident: {trigger} | r/{subreddit} | Post: \"{title[:50]}...\"")

                    human_delay("candidate")

            # Pacing delay between query tasks
            if dry_run:
                time.sleep(random.uniform(1.2, 2.0))
            else:
                time.sleep(random.uniform(3.5, 7.0))

        log("=================================================================")
        log("=== MINDMAXING REDDIT INCIDENT HARVESTER SWEEP REPORT ===")
        log("=================================================================")
        log(f"Total Posts Examined:        {sweep_stats['posts_examined']}")
        log(f"INCIDENT_CANDIDATE:          {len(sweep_stats['incident_candidates'])}")
        log(f"REVIEW_REQUIRED:             {len(sweep_stats['review_required'])}")
        rejected_total = sweep_stats['posts_examined'] - len(sweep_stats['incident_candidates']) - len(sweep_stats['review_required'])
        log(f"REJECTED / NO_MATCH / STALE: {rejected_total}")
        log("")
        log("--- Rejection Reasons Breakdown ---")
        for r, count in sweep_stats["rejected"].most_common():
            log(f"  {r}: {count}")
        log("")
        if sweep_stats["incident_candidates"]:
            log("--- INCIDENT CANDIDATES ---")
            for idx, cand in enumerate(sweep_stats["incident_candidates"], 1):
                log(f"  #{idx} [r/{cand['subreddit']}] /u/{cand['author']} | Reasons: {cand['reasons']}")
                log(f"      Title: \"{cand['title']}\"")
                log(f"      URL: {cand['url']}")
                log(f"      Evidence: {cand['evidence']}")
        else:
            log("No INCIDENT_CANDIDATE found in this sweep. (Zero qualifying leads is expected per Invariant #6).")

        if sweep_stats["review_required"]:
            log("--- REVIEW REQUIRED ---")
            for idx, rev in enumerate(sweep_stats["review_required"], 1):
                log(f"  #{idx} [r/{rev['subreddit']}] /u/{rev['author']} | Reasons: {rev['reasons']}")
                log(f"      Title: \"{rev['title']}\"")
                log(f"      URL: {rev['url']}")
                log(f"      Evidence: {rev['evidence']}")
        log("=================================================================")

        if once or dry_run:
            log("Execution mode finished. Exiting sweep.")
            return sweep_stats

        log("Cycle complete. Pacing before next cycle...")
        human_delay("cycle")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mindmaxing Reddit Incident Harvester v3.0")
    parser.add_argument("--once", action="store_true", help="Run a single pass and exit")
    parser.add_argument("--dry-run", action="store_true", help="Dry run evaluation without scraping or saving")
    args = parser.parse_args()
    run_reddit_harvester(once=args.once, dry_run=args.dry_run)
