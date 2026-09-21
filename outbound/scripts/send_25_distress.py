import os
import sys
import json
import time
import random
import smtplib
import ssl
import sqlite3
import argparse
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv("/root/outbound/.env")

BASE_DIR = "/root/outbound"
CONFIG_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "sent_history.json")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")

SMTP_HOST = os.environ.get("IONOS_SMTP_HOST", "smtp.ionos.com")
SMTP_PORT = int(os.environ.get("IONOS_SMTP_PORT", 587))
SMTP_PASSWORD = os.environ.get("IONOS_SMTP_PASSWORD", "")

# Curated 25 distress stores (9 Reddit founders + 16 Trustpilot technical friction)
# All 100% verified physical Shopify DTC, 100% valid MX, 100% foreign
TARGET_DOMAINS = [
    # 9 Reddit Founders
    "grilldogsapparel.com",
    "slumbrband.com",
    "tryvayora.co",
    "framedcars.it",
    "glorytheshop.com",
    "memarinedivesupply.com",
    "jureynco.com",
    "riverzshop.ro",
    "thepawsitivespace.com",
    # 16 Trustpilot Technical Checkout Friction
    "blyssofficial.com",
    "funnyfuzzy.com",
    "kittysupps.com",
    "kilgourmd.com",
    "smalls.com",
    "shapellx.com",
    "customjewelcompany.com",
    "norseorganics.co",
    "smoothspine.com",
    "luminskin.com",
    "guers.art",
    "lostgenclub.com",
    "poponveneers.com",
    "petkit.com",
    "woolx.com",
    "purebredkitties.com"
]

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def generate_astra_email(lead: dict, sender: dict) -> tuple[str, str]:
    """
    Astra Human Developer Voice:
    - No agency buzzwords, no 'native cart serialization', no 'unbundled scripts'
    - Real reason for writing (Reddit post title or customer review observation)
    - One relevant honest question
    - Plain conversational English
    """
    source = lead.get("source", "trustpilot")
    company = lead.get("company_name") or lead.get("domain", "your store")
    sender_name = sender.get("name", "Aryan Panchal")

    if source == "reddit":
        title = (lead.get("post_title") or "").strip()
        sub = lead.get("subreddit") or "reviewmyshopify"
        
        # Determine honest diagnostic question based on their exact post
        t_low = title.lower()
        if "add to cart" in t_low or "atc" in t_low or "don't buy" in t_low or "dont buy" in t_low:
            core_q = "Are they getting as far as checkout, or leaving before that?"
        elif "traffic" in t_low or "no sales" in t_low or "ads" in t_low:
            core_q = "When traffic lands, are you seeing sessions reach the checkout step at all, or bouncing before the cart opens?"
        elif "theme" in t_low or "horizon" in t_low or "redesign" in t_low:
            core_q = "Did you run into any layout or speed hitches on mobile after the theme rebuild?"
        else:
            core_q = "Are you seeing visitors drop off before the cart opens, or in the checkout step itself?"

        subject = f"{company}: where the cart drop-off happens"

        body = f"""Hey {company} team,

Saw your Reddit post in r/{sub} about {title.rstrip('.')}. {core_q}

I’m a Shopify developer. Before suggesting any theme work, I’d want to know whether something actually breaks in that step.

If you’re still dealing with it, I can take a quick look.

{sender_name}
Mindmaxing Studio
102, Sunrise Business Park, Road No. 16, Wagle Estate, Thane, Maharashtra 400604, India
Reply "stop" to opt out."""

        return subject, body

    else:
        # Trustpilot Astra standard: Plain English symptom, no unearned certainty
        trigger = lead.get("pain_trigger", "checkout")
        
        symptom_map = {
            "cart": "the cart drawer freezing or items resetting on mobile",
            "checkout": "the checkout button being unresponsive or dropping off on mobile",
            "payment": "the payment step spinning or timing out during checkout",
            "order": "duplicate charges or order lag during final checkout",
            "cancel": "cancellation or subscription errors during checkout",
            "discount": "discount codes failing to apply at checkout",
            "slow": "mobile load lag causing drop-offs before checkout",
            "stuck": "the checkout flow freezing on mobile",
            "refund": "checkout and refund processing friction"
        }
        symptom = symptom_map.get(trigger, "a hitch during the checkout flow on mobile")

        subject = f"{company} mobile checkout"

        body = f"""Hey {company} team,

Saw a couple of customer notes mentioning {symptom} on {company}.

I’m a Shopify developer. Is that something customers are still running into, or has your team already patched it?

If you're still seeing drops there, happy to test the cart-to-checkout flow on a couple of devices and tell you what happens.

{sender_name}
Mindmaxing Studio
102, Sunrise Business Park, Road No. 16, Wagle Estate, Thane, Maharashtra 400604, India
Reply "stop" to opt out.

P.S. If you're on support, feel free to pass this to whoever manages your Shopify theme."""

        return subject, body

def send_email_smtp(sender: dict, password: str, to_email: str, subject: str, body: str) -> tuple[bool, str]:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender['name']} <{sender['email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = sender["email"]
    
    msg_id = f"<{datetime.now(timezone.utc).timestamp()}-{random.randint(1000, 9999)}@{sender['domain']}>"
    msg["Message-ID"] = msg_id
    msg["X-Mailer"] = "Mindmaxing Engine 3.0"
    
    part = MIMEText(body, "plain", "utf-8")
    msg.attach(part)
    
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(sender["email"], password)
            server.sendmail(sender["email"], [to_email], msg.as_string())
        return True, msg_id
    except Exception as e:
        log(f"  SMTP Error [{sender['email']} -> {to_email}]: {e}")
        return False, str(e)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Execute live sends")
    args = parser.parse_args()

    with open(CONFIG_FILE) as f:
        mailboxes = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    leads = []
    for d in TARGET_DOMAINS:
        c.execute("SELECT * FROM leads WHERE domain = ?", (d,))
        r = c.fetchone()
        if r:
            leads.append(dict(r))
        else:
            log(f"WARNING: Domain not found in CRM: {d}")

    log(f"Loaded {len(mailboxes)} mailboxes.")
    log(f"Loaded {len(leads)} verified distress leads (9 Reddit founders + 16 Trustpilot checkout friction).")

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            history = json.load(open(HISTORY_FILE))
        except Exception:
            pass

    today_str = datetime.now().strftime("%Y-%m-%d")
    sent_count = 0

    log(f"\n{'='*75}")
    log(f"DISPATCH BATCH: 25 TOTAL (1 EMAIL PER MAILBOX) - ASTRA HUMAN DEVELOPER VOICE")
    log(f"MODE: {'*** LIVE SEND ***' if args.live else '--- DRY RUN ---'}")
    log(f"{'='*75}\n")

    for i, (lead, sender) in enumerate(zip(leads, mailboxes), 1):
        to_email = lead["contact_email"].strip(".,;:'\"")
        subj, body = generate_astra_email(lead, sender)
        src = lead.get("source", "trustpilot").upper()
        store = lead.get("domain")

        log(f"[{i}/25] [{src}] {sender['name']} <{sender['email']}> -> {to_email} ({store})")
        log(f"      Subject: {subj}")

        if args.live:
            log(f"      Sending via {sender['email']}...")
            ok, msg_id = send_email_smtp(sender, SMTP_PASSWORD, to_email, subj, body)
            if ok:
                log(f"      -> SUCCESS: Message-ID {msg_id}")
                record = {
                    "sender_email": sender["email"],
                    "lead_email": to_email,
                    "lead_domain": store,
                    "touch_number": 1,
                    "subject": subj,
                    "message_id": msg_id,
                    "sent_date": today_str,
                    "timestamp": datetime.now().isoformat()
                }
                history.append(record)
                with open(HISTORY_FILE, "w") as f:
                    json.dump(history, f, indent=2)

                c.execute("""
                    UPDATE leads 
                    SET current_sequence_step = 1,
                        last_contacted_at = ?,
                        status = 'READY'
                    WHERE domain = ?
                """, (datetime.now(timezone.utc).isoformat(), store))
                conn.commit()

                sent_count += 1
                delay = random.uniform(25.0, 45.0)
                log(f"      Sleeping {delay:.1f}s before next mailbox send...\n")
                time.sleep(delay)
            else:
                log(f"      -> FAILED: {msg_id}\n")
        else:
            first_two = "\n      ".join(body.splitlines()[2:5])
            log(f"      Body Preview:\n      {first_two}\n")
            sent_count += 1

    conn.close()
    log(f"{'='*75}")
    log(f"Dispatch cycle complete. Total processed: {sent_count} / 25.")

if __name__ == "__main__":
    main()
