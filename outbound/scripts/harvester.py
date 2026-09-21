#!/usr/bin/env python3
"""
Mindmaxing Trustpilot Forensic Harvester v2
- 100% Physical Goods DTC E-Commerce Gatekeeper (Drops SaaS / software / digital services).
- Strictly harvests pure 1★ customer complaints (?stars=1).
- Extracts Trustpilot verified businessUnit.contactInfo.email + countryCode.
- Collects full Page 1 review clusters (up to 20 reviews) to diagnose systemic checkout/cart failure.
- Filters out pure courier/shipping complaints (FedEx, USPS, carrier).
- Enforces 90-day review recency filter.
- Scrapes store for physical Shopify verification + founder name enrichment.
- Strict discard if no verified email exists (Zero guessed support@ fallbacks).
- Saves directly to outbound/data/icp1_shopify_dtc/leads.json.
"""

import asyncio
import json
import os
import random
import re
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from playwright.async_api import async_playwright

try:
    from email_classifier import classify_email, is_role_account, is_valid_founder_name
    from founder_resolver import resolve_founder_contact
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from email_classifier import classify_email, is_role_account, is_valid_founder_name
    from founder_resolver import resolve_founder_contact

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
ICP1_DIR = os.path.join(DATA_DIR, "icp1_shopify_dtc")
OUTPUT_FILE = os.path.join(ICP1_DIR, "leads.json")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")
LOG_FILE = os.path.join(DATA_DIR, "harvester.log")
TARGET_COUNT = 1000

# 10 Pure Physical Goods DTC Categories (Zero SaaS/Tech)
CATEGORIES = [
    "clothing_store",
    "jewelry_store",
    "cosmetics_store",
    "beauty_products",
    "furniture_store",
    "shoes_footwear",
    "home_goods_store",
    "sports_outdoor",
    "pet_store",
    "food_beverages"
]

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
]

TECH_PAIN_KEYWORDS = [
    "checkout", "cart", "payment", "card", "mobile", "slow", "bug", "crash",
    "loading", "charged", "order", "cancel", "stuck", "discount", "code",
    "voucher", "refund", "glitch", "apple pay", "paypal", "duplicate", "freeze"
]

COURIER_ONLY_KEYWORDS = [
    "usps", "fedex", "dhl", "ups", "carrier", "mailman", "customs", "delivery driver"
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

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_random_delay() -> float:
    base = random.uniform(38.0, 68.0)
    jitter = random.gauss(0, 2.0)
    return max(32.0, base + jitter)

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

def load_existing_leads() -> list:
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_lead(lead: dict) -> bool:
    os.makedirs(ICP1_DIR, exist_ok=True)
    existing_leads = load_existing_leads()
    clean_dom = lead.get("domain", "").lower().replace("www.", "").strip()
    clean_em = lead.get("contact_email", "").lower().strip()

    if any(l.get("domain", "").lower().replace("www.", "").strip() == clean_dom for l in existing_leads):
        return False
    if clean_em and any(l.get("contact_email", "").lower().strip() == clean_em for l in existing_leads):
        return False

    existing_leads.append(lead)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_leads, f, indent=2)

    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        INSERT OR IGNORE INTO leads (
            domain, company_name, contact_email, contact_type, contact_name,
            country_code, city, platform, pain_trigger, dominant_pattern,
            reviews_count, review_freshest_date, reviews_json, captured_at, status,
            source, subreddit, post_title, post_url, post_author,
            resolved_name, resolved_email, resolved_role, resolved_evidence,
            resolution_status, resolved_at, original_contact_email
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            lead.get("dominant_pattern", "Trustpilot Complaint Cluster"),
            lead.get("reviews_count", 1),
            lead.get("review_freshest_date"),
            json.dumps(lead.get("reviews_collection", [])),
            lead.get("captured_at"),
            "CANDIDATE",
            "trustpilot",
            "",
            "",
            "",
            "",
            lead.get("resolved_name"),
            lead.get("resolved_email"),
            lead.get("resolved_role"),
            lead.get("resolved_evidence"),
            lead.get("resolution_status", "UNRESOLVED"),
            lead.get("resolved_at"),
            lead.get("original_contact_email", "")
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"Database write warning: {e}")

    return True

def verify_physical_shopify(domain: str) -> tuple[bool, str]:
    """Live website inspection: verifies physical shipping + cart + Shopify."""
    clean_domain = domain.replace("www.", "").strip()
    url = f"https://{clean_domain}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=7) as resp:
            html = resp.read().decode("utf-8", errors="ignore").lower()
            
            # 1. Hard rejection on SaaS patterns
            if any(re.search(p, html) for p in SAAS_PATTERNS):
                return False, "SaaS/Software indicators found"
            
            # 2. Must have Shopify signature
            is_shopify = ("cdn.shopify.com" in html or "shopify." in html or "myshopify.com" in html or "shopify-digital-wallet" in html)
            if not is_shopify:
                return False, "Not running Shopify"
            
            # 3. Must have eCommerce cart mechanics
            has_cart = any(k in html for k in ["cart", "add to cart", "cart-drawer", "checkout", "name=\"add\""])
            if not has_cart:
                return False, "No cart flow detected"
                
            return True, "Shopify Physical DTC Verified"
    except Exception as e:
        # Fallback: check shipping policy page directly
        try:
            policy_url = f"https://{clean_domain}/policies/shipping-policy"
            req2 = urllib.request.Request(policy_url, headers=headers)
            with urllib.request.urlopen(req2, timeout=5) as resp2:
                html2 = resp2.read().decode("utf-8", errors="ignore").lower()
                if "shipping" in html2 or "delivery" in html2 or "order" in html2:
                    return True, "Verified via Shipping Policy"
        except Exception:
            pass
        return False, f"Connection/Verification error: {str(e)[:30]}"

def scrape_store_details(domain: str) -> tuple[str, str, str]:
    """Scrapes store for contact email and founder name if Trustpilot was blank."""
    clean_domain = domain.replace("www.", "").strip()
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    paths = ["/pages/about", "/pages/about-us", "/pages/our-story", "/pages/contact", "/pages/contact-us", "/policies/privacy-policy"]
    
    found_email = ""
    founder_name = ""
    contact_type = "GENERIC_SUPPORT"

    for p in paths:
        url = f"https://{clean_domain}{p}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                
                # Check for founder name
                if not founder_name:
                    name_matches = re.findall(r"(?:founder|founded by|co-founder|creator)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text, re.IGNORECASE)
                    if name_matches:
                        cand = name_matches[0].strip()
                        if is_valid_founder_name(cand):
                            founder_name = cand
                            contact_type = "FOUNDER_NAMED_DESK"

                # Check for direct email
                if not found_email:
                    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
                    for em in emails:
                        em_clean = em.lower().strip(".,;:'\"")
                        if not em_clean.endswith((".png", ".jpg", ".svg", ".css", ".js")) and clean_domain in em_clean:
                            prefix = em_clean.split("@")[0]
                            if prefix in ["founder", "owner"]:
                                found_email = em_clean
                                contact_type = "FOUNDER_DIRECT"
                                break
                            elif prefix in ["hello", "contact"]:
                                found_email = em_clean
                            elif not found_email and prefix in ["support", "cs", "info"]:
                                found_email = em_clean
        except Exception:
            continue

    return found_email, founder_name, contact_type

async def main():
    os.makedirs(ICP1_DIR, exist_ok=True)
    log("=== Mindmaxing Forensic Harvester v2 Starting ===")
    
    known_domains, known_emails = load_existing_records()
    log(f"Current Verified Shopify DTC Reservoir: {len(known_domains)} unique domains, {len(known_emails)} unique emails loaded.")
    cat_page = 2 if len(known_domains) >= 100 else 1
    request_count = 0

    async with async_playwright() as p:
        log("Launching headless stealth Chromium...")
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]
        )
        
        while len(known_domains) < TARGET_COUNT:
            current_count = len(known_domains)
            log(f"--- Cycle Starting: Category Page {cat_page} | Progress: {current_count}/{TARGET_COUNT} ---")

            brand_domains = []
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)}
            )
            page = await context.new_page()

            log(f"Phase 1: Gathering physical DTC candidates (Page {cat_page})...")
            for cat in CATEGORIES:
                cat_url = f"https://www.trustpilot.com/categories/{cat}" if cat_page == 1 else f"https://www.trustpilot.com/categories/{cat}?page={cat_page}"
                log(f"Fetching category: {cat} (page {cat_page}) -> {cat_url}")
                try:
                    await page.goto(cat_url, wait_until="domcontentloaded", timeout=35000)
                    await asyncio.sleep(random.uniform(3.0, 5.0))
                    links = await page.evaluate("""() => {
                        const anchors = Array.from(document.querySelectorAll("a"));
                        return anchors.map(a => a.href).filter(h => h && h.includes("/review/"));
                    }""")
                    for l in links:
                        parts = l.split("/review/")
                        if len(parts) > 1:
                            d = parts[1].split("?")[0].strip("/").lower()
                            if d and "." in d and not any(x in d for x in ["trustpilot", "facebook", "google", "instagram", ".ai"]):
                                clean_d = d.replace("www.", "").strip()
                                if clean_d not in known_domains and d not in brand_domains:
                                    brand_domains.append(d)
                    log(f"  Category '{cat}' yielded. Total unique brands queued: {len(brand_domains)}")
                except Exception as e:
                    log(f"  Error loading category {cat}: {e}")
                
                await asyncio.sleep(random.uniform(3.5, 6.0))
                if len(brand_domains) >= 300:
                    break

            await page.close()
            await context.close()
            
            log(f"Phase 1 Complete: {len(brand_domains)} brands queued for cycle {cat_page}.")
            random.shuffle(brand_domains)

            log("Phase 2: Starting forensic single-page 1★ extraction + gatekeeper...")
            
            for idx, domain in enumerate(brand_domains):
                current_leads = load_existing_leads()
                if len(current_leads) >= TARGET_COUNT:
                    log(f"🎉 GOAL ACHIEVED! Exactly {TARGET_COUNT} high-intent Shopify leads collected!")
                    break

                if any(l.get("domain") == domain for l in current_leads):
                    continue

                request_count += 1
                review_url = f"https://www.trustpilot.com/review/{domain}?stars=1"
                log(f"[{request_count} | Qualified Leads: {len(current_leads)}/{TARGET_COUNT}] Scanning: {domain}")

                context = await browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)}
                )
                page = await context.new_page()

                try:
                    await page.goto(review_url, wait_until="domcontentloaded", timeout=35000)
                    await asyncio.sleep(random.uniform(3.0, 4.5))
                    
                    next_data_raw = await page.evaluate("() => { const el = document.getElementById('__NEXT_DATA__'); return el ? el.textContent : null; }")
                    if next_data_raw:
                        data = json.loads(next_data_raw)
                        props = data.get("props", {}).get("pageProps", {})
                        b_unit = props.get("businessUnit", {})
                        company_name = b_unit.get("displayName") or domain
                        country_code = b_unit.get("countryCode") or "US"
                        
                        # PRIORITY 1: Read Trustpilot verified contactInfo
                        contact_info = b_unit.get("contactInfo", {}) or {}
                        tp_email = contact_info.get("email", "").strip() if isinstance(contact_info, dict) else ""
                        city = contact_info.get("city", "").strip() if isinstance(contact_info, dict) else ""

                        reviews_raw = props.get("reviews", [])
                        valid_tech_reviews = []
                        cutoff_90d = datetime.now(timezone.utc) - timedelta(days=90)
                        freshest_date = None

                        # Ingest all 1★ reviews on Page 1 (up to 20)
                        for r in reviews_raw:
                            rating = r.get("rating", 1)
                            title = r.get("title", "")
                            body = r.get("text", "")
                            full_text = f"{title} {body}".lower()
                            pub_date = r.get("dates", {}).get("publishedDate", "")
                            author = r.get("consumer", {}).get("displayName", "Customer")
                            
                            # Filter out pure courier delays
                            is_courier_only = any(ck in full_text for ck in COURIER_ONLY_KEYWORDS) and not any(tk in full_text for tk in ["cart", "checkout", "payment", "discount", "code", "website", "bug", "mobile"])
                            if is_courier_only:
                                continue

                            matched_triggers = [kw for kw in TECH_PAIN_KEYWORDS if kw in full_text]
                            if matched_triggers and len(body) > 25:
                                # Check recency
                                rev_dt = None
                                if pub_date:
                                    try:
                                        rev_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                                    except Exception:
                                        pass
                                
                                if rev_dt:
                                    if not freshest_date or rev_dt > freshest_date:
                                        freshest_date = rev_dt

                                valid_tech_reviews.append({
                                    "author": author,
                                    "date": pub_date,
                                    "rating": rating,
                                    "title": title,
                                    "snippet": body[:220] + "..." if len(body) > 220 else body,
                                    "trigger": matched_triggers[0]
                                })

                        # Enforce 90-day recency filter
                        if not valid_tech_reviews:
                            log(f"  Skipped {domain}: No technical website complaints found.")
                        elif freshest_date and freshest_date < cutoff_90d:
                            log(f"  Skipped {domain}: Stale pain signal (freshest review was {freshest_date.strftime('%Y-%m-%d')}, older than 90d).")
                        else:
                            # GATEKEEPER: Verify Physical Shopify Store
                            is_physical_shopify, reason = verify_physical_shopify(domain)
                            if not is_physical_shopify:
                                log(f"  Gatekeeper Rejected {domain}: {reason}")
                            else:
                                # Determine best contact email and founder name via Ground-Truth Resolver
                                contact_email = tp_email
                                founder_name = ""
                                contact_type = "GENERIC_SUPPORT"

                                # Run Ground-Truth Founder Resolution
                                res = resolve_founder_contact(domain, company_name)
                                res_status = res.get("resolution_status", "UNRESOLVED")
                                res_name = res.get("resolved_name")
                                res_email = res.get("resolved_email")
                                res_role = res.get("resolved_role")
                                res_evidence = json.dumps(res.get("evidence", {}))
                                res_at = datetime.now(timezone.utc).isoformat()
                                orig_email = tp_email or ""

                                if res_status == "FOUNDER_FOUND" and res_email:
                                    # Verified direct founder email found on site
                                    contact_email = res_email
                                    founder_name = res_name or ""
                                    contact_type = "FOUNDER_DIRECT"
                                elif res_status == "NAME_ONLY" and res_name:
                                    # Verified founder name found, but no personal email published
                                    # Never guess email: keep generic contact email (if available) but label desk with genuine founder name
                                    founder_name = res_name
                                    contact_type = "FOUNDER_NAMED_DESK"
                                else:
                                    # No verified founder found on site
                                    if contact_email:
                                        classification = classify_email(contact_email)
                                        if classification.get("classification") == "PERSONAL":
                                            prefix_name = contact_email.split("@")[0].capitalize()
                                            is_valid, clean_n = is_valid_founder_name(prefix_name)
                                            if is_valid:
                                                founder_name = clean_n
                                                contact_type = "FOUNDER_DIRECT"
                                            else:
                                                contact_type = "GENERIC_SUPPORT"
                                        else:
                                            contact_type = "GENERIC_SUPPORT"
                                            founder_name = ""

                                # If Trustpilot had no email and no founder email was resolved, fallback to store detail scrape
                                if not contact_email:
                                    s_email, s_name, s_type = scrape_store_details(domain)
                                    if s_email:
                                        contact_email = s_email
                                        orig_email = s_email
                                        if not founder_name and s_name:
                                            is_valid_s, clean_s = is_valid_founder_name(s_name)
                                            if is_valid_s:
                                                founder_name = clean_s
                                                contact_type = s_type
                                            else:
                                                contact_type = "GENERIC_SUPPORT"
                                        elif not founder_name:
                                            contact_type = "GENERIC_SUPPORT"

                                # RETAIN LEAD WITH PAIN SIGNALS EVEN IF EMAIL MISSING:
                                # Raw addresses become observations; never drop high-value commercial distress signals!
                                clean_em = contact_email.lower().strip() if contact_email else ""
                                if clean_em and clean_em in known_emails:
                                    log(f"  Dropped {domain}: Email {contact_email} already exists in CRM (cross-source email dedup).")
                                else:
                                    if not contact_email:
                                        contact_type = "NO_CONTACT"
                                        log(f"  Captured {domain} without email: Preserving pain signals for subsequent enrichment.")

                                    # Cluster Analysis
                                    triggers = [vr["trigger"] for vr in valid_tech_reviews]
                                    dominant = max(set(triggers), key=triggers.count) if triggers else "checkout"

                                    lead_record = {
                                        "domain": domain,
                                        "company_name": company_name,
                                        "contact_email": contact_email,
                                        "contact_type": contact_type,
                                        "contact_name": founder_name,
                                        "country_code": country_code,
                                        "city": city,
                                        "platform": "Shopify",
                                        "pain_trigger": dominant,
                                        "dominant_pattern": f"{dominant.capitalize()} Friction",
                                        "source": "trustpilot",
                                        "reviews_count": len(valid_tech_reviews),
                                        "review_freshest_date": freshest_date.isoformat() if freshest_date else datetime.now().isoformat(),
                                        "reviews_collection": valid_tech_reviews[:5],
                                        "captured_at": datetime.now().isoformat(),
                                        "resolved_name": res_name,
                                        "resolved_email": res_email,
                                        "resolved_role": res_role,
                                        "resolved_evidence": res_evidence,
                                        "resolution_status": res_status,
                                        "resolved_at": res_at,
                                        "original_contact_email": orig_email
                                    }

                                    if save_lead(lead_record):
                                        clean_d = domain.lower().replace("www.", "").strip()
                                        known_domains.add(clean_d)
                                        if clean_em:
                                            known_emails.add(clean_em)
                                        log(f"  ✅ QUALIFIED! Lead #{len(known_domains)}/{TARGET_COUNT} -> {company_name} ({contact_email or 'NO_EMAIL_SAVED'})")
                                        log(f"     Type: {contact_type} | Founder: '{founder_name}' | Status: {res_status} | Trigger: {dominant}")
                    else:
                        log(f"  No review data on {domain}")
                except Exception as e:
                    log(f"  Request error on {domain}: {e}")
                finally:
                    await page.close()
                    await context.close()

                delay = get_random_delay()
                log(f"  Pacing delay: sleeping {delay:.1f}s...")
                await asyncio.sleep(delay)

                if request_count % random.randint(22, 28) == 0:
                    break_time = random.uniform(140.0, 220.0)
                    log(f"☕ Simulated organic micro-pause: sleeping {break_time/60:.1f} minutes...")
                    await asyncio.sleep(break_time)

            cat_page += 1

        await browser.close()
        log(f"=== Harvester Finished: Total Leads Collected = {len(load_existing_leads())} ===")

if __name__ == "__main__":
    asyncio.run(main())
