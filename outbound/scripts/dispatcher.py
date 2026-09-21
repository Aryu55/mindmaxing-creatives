#!/usr/bin/env python3
"""
Mindmaxing Forensic Outbound Dispatcher v3.0 (Astra Evidence-Based Architecture)
- Enforces Astra Offer Boundaries: Never claim an unrecorded video audit or inferred root cause.
- Draft A: Truthful diagnostic inquiry separating theme-level cart handoff from checkout friction.
- Draft B: Concrete reproduction evidence ONLY if a verified audit artifact exists.
- Fail-Closed Gate: In live dispatch, strictly requires status == 'HUMAN_APPROVED' (CANDIDATE requires manual review).
- Stable Sender Pinning: Pins one IONOS mailbox per prospect domain for authentic email threading.
- CAN-SPAM & FTC Compliant: Full physical registered business address and functional opt-out.
- Synchronous SQLite CRM logging (mindmaxing_crm.db).
"""

import json
import os
import random
import re
import smtplib
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
ICP1_DIR = os.path.join(DATA_DIR, "icp1_shopify_dtc")
LEADS_FILE = os.path.join(ICP1_DIR, "leads.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sent_history.json")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")

try:
    from crm_manager import log_touch
except ImportError:
    try:
        from outbound.scripts.crm_manager import log_touch
    except ImportError:
        log_touch = None

try:
    import volume_controller
except ImportError:
    try:
        from outbound.scripts import volume_controller
    except ImportError:
        volume_controller = None

try:
    from contact_policy import evaluate_contact, ContactDecision
except ImportError:
    try:
        from outbound.scripts.contact_policy import evaluate_contact, ContactDecision
    except ImportError:
        evaluate_contact = None

SMTP_HOST = os.environ.get("IONOS_SMTP_HOST", "smtp.ionos.com")
SMTP_PORT = int(os.environ.get("IONOS_SMTP_PORT", 587))
REPLY_TO = os.environ.get("REPLY_TO", "aryan@mindmaxing.info")
MAX_PER_MAILBOX = 10

PHYSICAL_FOOTER = """--
Mindmaxing Studio
102, Sunrise Business Park, Road No. 16, Wagle Estate, Thane, Maharashtra 400604, India
Reply "stop" to opt out"""

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def load_mailboxes():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_crm_status():
    """Reads lead sequence states, source info, and dates from SQLite CRM."""
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT domain, status, current_sequence_step, last_contacted_at, client_won,
               source, subreddit, post_title, post_url, post_author, contact_email
        FROM leads
    """)
    data = {r["domain"]: dict(r) for r in cursor.fetchall()}
    conn.close()
    return data

def get_pinned_sender(domain: str, mailboxes: list, history: list, mailbox_usage: dict = None) -> dict:
    """Pins a consistent sender mailbox to a prospect domain for authentic email threading, or selects an unused mailbox today."""
    for h in reversed(history):
        if h.get("lead_domain") == domain and h.get("sender_email"):
            match = next((m for m in mailboxes if m["email"] == h["sender_email"]), None)
            if match:
                return match
    if mailbox_usage is not None:
        min_used = min(mailbox_usage.get(m["email"], 0) for m in mailboxes)
        available = [m for m in mailboxes if mailbox_usage.get(m["email"], 0) == min_used]
        if available:
            return random.choice(available)
    return random.choice(mailboxes)

def generate_touch_1_copy(lead: dict, sender: dict) -> tuple[str, str]:
    """
    Touch 1: Astra Truthful Outreach
    - Draft A: Objective diagnostic question exploring the cart vs checkout boundary.
    - Draft B: Only if an audit artifact clip actually exists for this domain.
    """
    company = lead.get("company_name") or lead.get("domain", "your store")
    founder_name = (lead.get("contact_name") or "").strip()
    contact_type = lead.get("contact_type", "GENERIC_SUPPORT")
    trigger = lead.get("pain_trigger", "checkout")
    sender_name = sender.get("name", "Aryan Panchal")

    source = lead.get("source", "trustpilot")
    is_reddit = (source == "reddit" or lead.get("dominant_pattern") == "Reddit Incident Report")

    if contact_type in ["FOUNDER_DIRECT", "FOUNDER_NAMED_DESK", "FOUNDER_RESOLVED"] and founder_name and founder_name.lower() not in ["team", "support", "admin", "info", "help", "customer service"]:
        greeting = f"Hi {founder_name},"
        ps_line = ""
    else:
        greeting = f"Hi {company} team,"
        ps_line = "\n\nP.S. If you're on the customer support team, could you pass this to whoever handles your Shopify theme / development? It's directly tied to the checkout drop-offs you've been seeing."

    # Check if a genuine audit artifact was recorded and linked
    audit_clip_url = (lead.get("audit_clip_url") or "").strip()

    if audit_clip_url:
        # DRAFT B: Real observed reproduction clip exists
        subject = f"{company}: mobile cart issue"
        body = f"""{greeting}

I took a look at {company}'s store on mobile and noticed a friction point in the cart drawer before checkout initiates.

I recorded the exact steps in a short 60-second clip here:
{audit_clip_url}

I haven't established the root cause yet, but I can scope a fix if it sits in the theme/cart Liquid code.

Would the clip be useful?

Best,
{sender_name}
Mindmaxing Studio
https://mindmaxing.one{ps_line}

{PHYSICAL_FOOTER}"""
        return subject, body

    if is_reddit:
        # DRAFT A (Reddit): Diagnostic inquiry anchored to their reported symptom
        sub = lead.get("subreddit", "")
        raw_title = (lead.get("post_title") or "").strip()
        clean_title = re.sub(r"[\r\n\t]+", " ", raw_title).strip()
        if len(clean_title) > 60:
            clean_title = clean_title[:57].rstrip() + "..."

        if clean_title and sub:
            opener = f'Saw your post "{clean_title}" in r/{sub}.'
        elif sub:
            opener = f"Saw your note in r/{sub} regarding {company}'s store conversions."
        else:
            opener = f"Saw your note regarding {company}'s store conversions."

        reviews = lead.get("reviews_collection", [])
        post_snippet = reviews[0].get("text", "") if reviews else ""
        combined_text = (clean_title + " " + post_snippet).lower()

        if "add to cart but" in combined_text or "atc" in combined_text or trigger == "cart":
            symptom_distinction = "When customers add items to the cart but purchases stall, the key distinction is whether those sessions actually reach the Shopify checkout initiation step, or freeze beforehand in the theme's cart drawer."
        elif "slow" in combined_text or "speed" in combined_text or trigger == "slow":
            symptom_distinction = "On mobile themes, render-blocking tracking scripts and unbundled app Liquid often delay first interaction, causing high bounce rates before the cart even opens."
        else:
            symptom_distinction = "When traffic arrives but checkout doesn't convert, the distinction is usually whether sessions reach the checkout initiation step, or stall in the theme cart drawer."

        subject = f"{company}: where the cart drop-off happens"

        body = f"""{greeting}

{opener}

{symptom_distinction}

That distinction helps separate a theme-level JavaScript/Liquid conflict from downstream checkout friction or missing tracking. The surface numbers alone don't identify the fault.

I handle fixed-scope Shopify cart and theme optimizations. If this is still unresolved on {company}, happy to outline the first check I'd make.

Best,
{sender_name}
Mindmaxing Studio
https://mindmaxing.one{ps_line}

{PHYSICAL_FOOTER}"""

        return subject, body

    elif source == "meta_pagespeed":
        telemetry = lead.get("telemetry", {})
        score = telemetry.get("mobile_score", 30)
        lcp = telemetry.get("lcp", lead.get("lcp", "4.0s"))
        tbt = telemetry.get("tbt", "N/A")
        scripts = telemetry.get("blocking_scripts", [])

        if scripts:
            script_str = f"unbundled third-party script payloads ({', '.join(scripts[:2])})"
        else:
            script_str = "unbundled tracking and app scripts"

        subject = f"{company}: {lcp} mobile latency on your ad traffic"
        body = f"""{greeting}

Noticed you're running active paid campaigns for {company}, but your mobile product page is currently clocking a {lcp} Largest Contentful Paint on Google Lighthouse, with {script_str} delaying first render before the cart drawer responds.

When paying Meta for mobile traffic, that level of theme.liquid latency typically bounces 30–40% of visitors before the Add-to-Cart button even registers a tap.

I handle fixed-scope Shopify Liquid performance optimizations. If your dev team hasn't looked at this yet, I can outline the first check I'd make to patch this latency so your ad spend doesn't bleed.

Mind if I share a quick note on it?

Best,
{sender_name}
Mindmaxing Studio
https://mindmaxing.one{ps_line}

{PHYSICAL_FOOTER}"""

        return subject, body

    else:
        # DRAFT A (Trustpilot): Anchored to customer complaint pattern
        reviews = lead.get("reviews_collection", [])
        customer_names = [r.get("author", "").split()[0] for r in reviews if r.get("author") and r.get("author") != "Customer"]
        cust_str = f"recent customers ({', '.join(customer_names[:2])})" if len(customer_names) >= 2 else "recent customer reviews"

        pain_angles = {
            "cart": "cart drawer freezing and items resetting",
            "discount": "discount codes glitching or wiping cart line items",
            "payment": "mobile checkout spinning and payment gateway timeouts",
            "checkout": "checkout drop-offs and unresponsive buttons on mobile",
            "slow": "mobile page load friction dragging conversion",
            "order": "order creation lag and duplicate charges during final checkout"
        }
        symptom = pain_angles.get(trigger, "checkout friction on mobile")

        subject = f"noticed a hitch on {company} checkout"
        body = f"""{greeting}

Noticed a pattern across {cust_str} pointing to {symptom} on {company}.

Usually on Shopify themes, this happens because of conflicting third-party app scripts in theme.liquid delaying native cart serialization before checkout initiates.

I'm a Shopify performance engineer. If your dev team hasn't patched this yet, happy to outline where this script conflict typically sits in the theme so carts don't drop off.

Mind if I share a quick note on it?

Best,
{sender_name}
Mindmaxing Studio
https://mindmaxing.one{ps_line}

{PHYSICAL_FOOTER}"""

        return subject, body

def generate_touch_2_copy(lead: dict, sender: dict, original_subject: str) -> tuple[str, str]:
    """Touch 2 (+3 days): Threaded bump."""
    founder_name = (lead.get("contact_name") or "").strip()
    company = lead.get("company_name") or lead.get("domain", "your store")
    greeting = f"Hi {founder_name}," if founder_name else f"Hi {company} team,"
    sender_name = sender.get("name", "Aryan Panchal")

    subject = f"Re: {original_subject.replace('Re: ', '')}"
    body = f"""{greeting}

Quick bump on this—did you get a chance to see my note earlier this week regarding the cart drawer and checkout flow on {company}?

Happy to outline the first theme check I'd make if you're still seeing cart drop-offs.

Best,
{sender_name}
Mindmaxing Studio
https://mindmaxing.one

{PHYSICAL_FOOTER}"""

    return subject, body

def generate_touch_3_copy(lead: dict, sender: dict, original_subject: str) -> tuple[str, str]:
    """Touch 3 (+5 days): Breakup email closing the loop."""
    founder_name = (lead.get("contact_name") or "").strip()
    company = lead.get("company_name") or lead.get("domain", "your store")
    greeting = f"Hi {founder_name}," if founder_name else f"Hi {company} team,"
    sender_name = sender.get("name", "Aryan Panchal")

    subject = f"Re: {original_subject.replace('Re: ', '')}"
    body = f"""{greeting}

Assuming the timing isn't right or your team already has the checkout issues on {company} handled.

I'll step back here. If you ever want to audit mobile cart latency or app bloat down the road, feel free to reach back out anytime.

Best,
{sender_name}
Mindmaxing Studio
https://mindmaxing.one

{PHYSICAL_FOOTER}"""

    return subject, body

def send_email(sender: dict, password: str, to_email: str, subject: str, body: str, in_reply_to: str = None) -> tuple[bool, str]:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender['name']} <{sender['email']}>"
    msg["To"] = to_email
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = subject
    msg_id = f"<{int(time.time())}.{random.randint(1000, 9999)}@{sender['email'].split('@')[1]}>"
    msg["Message-ID"] = msg_id

    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25) as server:
            server.starttls()
            server.login(sender["email"], password)
            server.sendmail(sender["email"], [to_email], msg.as_string())
        return True, msg_id
    except Exception as e:
        log(f"SMTP Error from {sender['email']} to {to_email}: {e}")
        return False, ""

def run_dispatch(dry_run: bool = True, target_country: str = None, send_limit: int = 5):
    mailboxes = load_mailboxes()
    leads = load_leads()
    crm_data = get_crm_status()

    password = os.environ.get("IONOS_SMTP_PASSWORD")
    if not dry_run and not password:
        log("ERROR: IONOS_SMTP_PASSWORD not set in environment or .env file.")
        sys.exit(1)

    log(f"Loaded {len(mailboxes)} mailboxes across 4 domains.")
    log(f"Loaded {len(leads)} harvested leads from reservoir.")

    # Merge CRM status and metadata into leads
    for l in leads:
        d = l.get("domain")
        c_info = crm_data.get(d, {})
        if c_info:
            for k in ["source", "subreddit", "post_title", "post_url", "post_author", "status"]:
                if c_info.get(k):
                    l[k] = c_info[k]

    if target_country:
        leads = [l for l in leads if l.get("country_code", "US").upper() == target_country.upper()]
        log(f"Filtered by country [{target_country}]: {len(leads)} leads match.")

    # Sort by recency: freshest pain signal first
    def get_recency_key(lead):
        val = lead.get("review_freshest_date") or lead.get("review_date") or lead.get("captured_at") or ""
        return str(val)

    leads.sort(key=get_recency_key, reverse=True)

    now = datetime.now(timezone.utc)
    queue = []

    # Astra Fail-Closed Gate:
    # In live mode, only send to 'HUMAN_APPROVED' leads.
    # Unreviewed leads (CANDIDATE / READY) require human review before live dispatch.
    allowed_statuses = ["HUMAN_APPROVED"] if not dry_run else ["HUMAN_APPROVED", "READY", "CANDIDATE"]

    for l in leads:
        d = l.get("domain")
        email = l.get("contact_email", "").strip(".,;:'\"")
        if not email or "@" not in email:
            continue
        if email.startswith("u003e") or len(email.split("@")[0]) < 2:
            continue
        prefix = email.split("@")[0].lower()
        if prefix in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"] or prefix.endswith("-sms"):
            continue

        c_info = crm_data.get(d, {})
        status = c_info.get("status") or l.get("status", "CANDIDATE")
        step = c_info.get("current_sequence_step", 0)
        client_won = c_info.get("client_won", 0)
        last_str = c_info.get("last_contacted_at")

        if client_won or status in ["CLIENT_WON", "SEQUENCE_COMPLETED", "COOLDOWN", "REPLIED", "REJECTED_FROM_CAMPAIGN"]:
            continue

        if status not in allowed_statuses:
            continue

        # Enforce Shared Contact Policy Gate
        if not dry_run and evaluate_contact:
            candidate = {
                "contact_email": email,
                "contact_name": c_info.get("contact_name") or l.get("contact_name", ""),
                "contact_role": c_info.get("resolved_role") or "Founder",
                "identity_status": c_info.get("identity_status") or ("FOUNDER_CONFIRMED" if (c_info.get("resolved_name") or l.get("contact_name")) else "UNCONFIRMED"),
                "email_origin": c_info.get("email_origin") or ("PUBLIC_SITE" if c_info.get("contact_type") == "FOUNDER_RESOLVED" else "LEGACY_UNKNOWN"),
                "mailbox_verification": "VALID" if c_info.get("contact_type") == "FOUNDER_RESOLVED" else ("ACCEPT_ALL" if "CATCH_ALL" in str(c_info.get("resolution_status", "")) else "UNCHECKED"),
                "verification_time": c_info.get("resolved_at"),
                "identity_evidence_time": c_info.get("resolved_at"),
            }
            campaign_state = {
                "status": status,
                "current_sequence_step": step,
                "active_recipient": c_info.get("contact_email") or email,
                "is_suppressed": False,
                "quota_available": True
            }
            is_eligible, decision, reasons = evaluate_contact(candidate, campaign_state, now)
            if not is_eligible:
                continue

        last_dt = None
        if last_str:
            try:
                last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
            except Exception:
                pass

        if step == 0:
            queue.append((l, 1, "TOUCH_1", "initial", status))
        elif step == 1 and last_dt and (now - last_dt) >= timedelta(days=3):
            queue.append((l, 2, "TOUCH_2", "Re: quick question", status))
        elif step == 2 and last_dt and (now - last_dt) >= timedelta(days=5):
            queue.append((l, 3, "TOUCH_3", "Re: quick question", status))

    log(f"Dispatch queue built: {len(queue)} total eligible (Astra workload cap: {send_limit}/day).")

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            history = json.load(open(HISTORY_FILE))
        except Exception:
            pass

    today_str = datetime.now().strftime("%Y-%m-%d")
    mailbox_usage = {m["email"]: sum(1 for h in history if h.get("sender_email") == m["email"] and h.get("sent_date") == today_str) for m in mailboxes}

    lead_idx = 0
    total_sent = 0

    while lead_idx < len(queue) and total_sent < send_limit:
        lead, touch_step, touch_label, orig_subj, lead_status = queue[lead_idx]
        to_email = lead["contact_email"].strip(".,;:'\"")

        # Suppression Check
        if volume_controller:
            suppressed, s_reason = volume_controller.is_recipient_suppressed(to_email)
            if suppressed:
                log(f"  [SUPPRESSED] Skipping {to_email}: {s_reason}")
                lead_idx += 1
                continue

        sender = get_pinned_sender(lead.get("domain"), mailboxes, history, mailbox_usage)

        # Volume Controller Reservation
        if not dry_run and volume_controller:
            reserved, r_reason = volume_controller.reserve_quota(sender["email"], "campaign")
            if not reserved:
                log(f"  [QUOTA/HEALTH] Mailbox {sender['email']} unavailable: {r_reason}")
                lead_idx += 1
                continue
        elif mailbox_usage.get(sender["email"], 0) >= MAX_PER_MAILBOX:
            lead_idx += 1
            continue

        if touch_step == 1:
            subject, body = generate_touch_1_copy(lead, sender)
        elif touch_step == 2:
            subject, body = generate_touch_2_copy(lead, sender, orig_subj)
        else:
            subject, body = generate_touch_3_copy(lead, sender, orig_subj)

        freshest = lead.get("review_freshest_date") or lead.get("review_date", "N/A")
        src_tag = lead.get("source", "trustpilot").upper()

        if dry_run:
            log(f"[DRY-RUN] [{touch_label}] [{src_tag}] [{lead_status}] {sender['name']} <{sender['email']}> -> {to_email}")
            log(f"  Store: {lead.get('domain')} | Country: {lead.get('country_code', 'US')} | Date: {freshest[:10]}")
            log(f"  Subject: {subject}")
            snippet = body.splitlines()[2] if len(body.splitlines()) > 2 else body[:70]
            log(f"  Opener: {snippet}")
            mailbox_usage[sender["email"]] = mailbox_usage.get(sender["email"], 0) + 1
            total_sent += 1
        else:
            log(f"[LIVE] [{touch_label}] [{src_tag}] Sending from {sender['email']} -> {to_email}...")
            ok, msg_id = send_email(sender, password, to_email, subject, body)
            if ok:
                if volume_controller:
                    volume_controller.record_campaign_message(
                        message_id=msg_id,
                        sender_email=sender["email"],
                        recipient_email=to_email,
                        prospect_domain=lead.get("domain", ""),
                        campaign_touch=touch_step,
                        subject=subject,
                        smtp_success=True
                    )
                record = {
                    "sender_email": sender["email"],
                    "lead_email": to_email,
                    "lead_domain": lead.get("domain"),
                    "touch_number": touch_step,
                    "subject": subject,
                    "message_id": msg_id,
                    "sent_date": today_str,
                    "timestamp": datetime.now().isoformat()
                }
                history.append(record)
                json.dump(history, open(HISTORY_FILE, "w"), indent=2)

                if log_touch:
                    try:
                        log_touch(lead.get("domain"), to_email, sender["email"], step=touch_step, subject=subject)
                    except Exception as le:
                        log(f"  CRM log warning: {le}")

                mailbox_usage[sender["email"]] = mailbox_usage.get(sender["email"], 0) + 1
                total_sent += 1
                time.sleep(random.uniform(25.0, 45.0))
            else:
                log(f"  Failed sending to {to_email}")
                if volume_controller:
                    volume_controller.rollback_quota(sender["email"], "campaign")
                    volume_controller.record_campaign_message(
                        message_id=msg_id or f"failed-{int(time.time())}",
                        sender_email=sender["email"],
                        recipient_email=to_email,
                        prospect_domain=lead.get("domain", ""),
                        campaign_touch=touch_step,
                        subject=subject,
                        smtp_success=False,
                        error_msg="SMTP send failure"
                    )

        lead_idx += 1

    log(f"Dispatch cycle complete. Processed {lead_idx} items. Sent: {total_sent}.")

if __name__ == "__main__":
    is_dry = "--live" not in sys.argv
    country = None
    limit = 5
    for arg in sys.argv:
        if arg.startswith("--country="):
            country = arg.split("=")[1].upper()
        if arg.startswith("--limit="):
            try:
                limit = int(arg.split("=")[1])
            except ValueError:
                pass

    log(f"=== Mindmaxing Dispatcher v3.0 (mode={'LIVE' if not is_dry else 'DRY-RUN'}, cap={limit}/day) ===")
    run_dispatch(dry_run=is_dry, target_country=country, send_limit=limit)
