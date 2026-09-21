#!/usr/bin/env python3
"""
Mindmaxing Peer-to-Peer VPS Mailbox Warmup Engine v1.0
- Rotates cross-domain email threads across 25 dedicated mailboxes (4 domains).
- Domain Mesh: mindmaxing.online <-> mindmaxing.store <-> mindmaxing.org <-> mindmaxing.info
- Natural conversation generation with randomized professional subjects & bodies.
- IMAP verification: Recipient opens email, flags/stars it (high-trust signal), and sends in-thread reply.
- Zero external SaaS cost ($0.00 / mo).
"""

import os
import sys
import json
import time
import random
import imaplib
import smtplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from datetime import datetime

BASE_DIR = "/root/outbound"
CONFIG_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
LOG_FILE = os.path.join(BASE_DIR, "data", "warmup_log.json")
SMTP_HOST = "smtp.ionos.com"
SMTP_PORT = 587
IMAP_HOST = "imap.ionos.com"
CREDENTIALS_FILE = os.path.join(BASE_DIR, "config", "credentials.env")

def get_ionos_password():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE) as f:
            for line in f:
                if line.startswith("IONOS_PASSWORD="):
                    return line.strip().split("=", 1)[1].strip().strip('"\'')
    return os.environ.get("IONOS_PASSWORD", "")

IONOS_PASSWORD = get_ionos_password()

# Natural conversational templates between tech / design / growth peers
WARMUP_TEMPLATES = [
    {
        "subject": "Quick check on the Liquid snippet refactor",
        "body": "Hey,\n\nDid you finish reviewing the snippet for the sticky add-to-cart component? Want to make sure we don't introduce any layout shift before merging.\n\nLet me know when you get a chance.\n\nBest,\nAryan",
        "reply": "Hey Aryan,\n\nYes, just checked it out. The layout shift is completely gone on mobile viewports now. Looks clean and ready to go.\n\nTalk soon!"
    },
    {
        "subject": "Shopify theme benchmark comparison",
        "body": "Hi,\n\nRan the mobile performance audit on the staging environment. First Contentful Paint is down to 1.1s after removing the external script tags.\n\nShall we run the full Lighthouse pass this afternoon?\n\nAryan",
        "reply": "Hey,\n\nThat's a huge improvement. Let's definitely run the full pass today around 3 PM. Ping me when you kick it off."
    },
    {
        "subject": "Slide cart drawer event listener notes",
        "body": "Hey Aryan,\n\nLeft a couple of comments on the cart drawer merge request regarding the mutation observer. Take a look when you're at your desk.\n\nThanks!",
        "reply": "Thanks for flagging! Just updated the observer callback so it only triggers on cart subtotal changes. Pushed to main."
    },
    {
        "subject": "Checkout redirect latency test",
        "body": "Hi Aryan,\n\nWere you able to replicate that 300ms delay on the currency switch callback on Safari mobile? Checking if it's device-specific.\n\nBest,\nAryan",
        "reply": "Tested on iPhone 15 Pro and iPhone 13. Safari handles it smoothly once the debounce timeout was set to 150ms. All good now."
    },
    {
        "subject": "Notes from the client CRO sync",
        "body": "Hey,\n\nQuick summary from our earlier discussion: prioritizing the product page ATF hierarchy and moving the trust badges below the primary CTA.\n\nLet me know if you need any additional assets.\n\nAryan",
        "reply": "Got it. Agree with keeping the ATF clean. I'll stage the draft so we can review the before/after side by side."
    }
]

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [WARMUP] {msg}", flush=True)

def load_mailboxes():
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_log(entry: dict):
    history = load_log()
    history.append(entry)
    # Keep last 500 records
    if len(history) > 500:
        history = history[-500:]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def send_warmup_email(sender: dict, recipient: dict, subject: str, body: str, in_reply_to: str = None) -> str:
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender['name']} <{sender['email']}>"
    msg["To"] = f"{recipient['name']} <{recipient['email']}>"
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg_id = make_msgid(domain=sender["domain"])
    msg["Message-ID"] = msg_id
    
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    # Plain text and clean HTML parts
    part_text = MIMEText(body, "plain", "utf-8")
    html_content = "".join([f"<p style='margin:0 0 10px 0;'>{line}</p>" for line in body.split("\n\n")])
    part_html = MIMEText(f"<html><body style='font-family:-apple-system,sans-serif;font-size:14px;color:#111;'>{html_content}</body></html>", "html", "utf-8")
    
    msg.attach(part_text)
    msg.attach(part_html)

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.starttls()
    server.login(sender["email"], IONOS_PASSWORD)
    server.sendmail(sender["email"], [recipient["email"]], msg.as_string())
    server.quit()
    return msg_id

def process_recipient_imap(recipient: dict, sender_email: str, expected_msg_id: str, reply_body: str, original_subject: str):
    """Logs into recipient IMAP, finds the warmup message, marks it read, stars/flags it, and replies."""
    time.sleep(random.uniform(5, 10))  # Wait for delivery
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(recipient["email"], IONOS_PASSWORD)
        mail.select("INBOX")

        status, messages = mail.search(None, f'(FROM "{sender_email}")')
        if status != "OK" or not messages[0]:
            log(f"    IMAP: No messages found from {sender_email} yet on {recipient['email']}")
            mail.logout()
            return False

        msg_ids = messages[0].split()
        latest_id = msg_ids[-1]

        # Fetch headers & Mark as Read + Flagged (Starring is a major positive reputation signal)
        mail.store(latest_id, "+FLAGS", "(\\Seen \\Flagged)")
        log(f"    IMAP: {recipient['email']} marked warmup message as Read & Flagged (Star)")

        # Send in-thread reply back to sender
        reply_subject = f"Re: {original_subject}" if not original_subject.lower().startswith("re:") else original_subject
        reply_msg_id = send_warmup_email(
            sender=recipient,
            recipient={"name": "Aryan", "email": sender_email, "domain": sender_email.split("@")[1]},
            subject=reply_subject,
            body=reply_body,
            in_reply_to=expected_msg_id
        )
        log(f"    IMAP Reply: {recipient['email']} -> {sender_email} successfully replied!")
        
        mail.close()
        mail.logout()
        return True
    except Exception as e:
        log(f"    IMAP Error on {recipient['email']}: {e}")
        return False

def run_warmup_cycle(num_pairs: int = 4):
    mailboxes = load_mailboxes()
    if len(mailboxes) < 2:
        log("Not enough mailboxes configured.")
        return

    # Group by domain
    domains = list(set(m["domain"] for m in mailboxes))
    if len(domains) < 2:
        log("Need at least 2 distinct domains for cross-domain warmup.")
        return

    log(f"Starting warmup cycle. Total mailboxes: {len(mailboxes)} across {len(domains)} domains.")
    successful = 0

    for i in range(num_pairs):
        # Pick 2 distinct domains for authentic cross-domain delivery
        d1, d2 = random.sample(domains, 2)
        sender = random.choice([m for m in mailboxes if m["domain"] == d1])
        recipient = random.choice([m for m in mailboxes if m["domain"] == d2])

        template = random.choice(WARMUP_TEMPLATES)
        log(f"Pair {i+1}/{num_pairs}: [{sender['email']}] -> [{recipient['email']}] (Topic: {template['subject']})")

        try:
            msg_id = send_warmup_email(sender, recipient, template["subject"], template["body"])
            log(f"    Sent OK ({msg_id})")

            # IMAP open, star, and reply
            replied = process_recipient_imap(recipient, sender["email"], msg_id, template["reply"], template["subject"])
            
            save_log({
                "timestamp": datetime.now().isoformat(),
                "sender": sender["email"],
                "recipient": recipient["email"],
                "subject": template["subject"],
                "msg_id": msg_id,
                "replied": replied
            })
            successful += 1

            if i < num_pairs - 1:
                pause = random.uniform(15, 30)
                log(f"    Sleeping {pause:.1f}s before next warmup pair...")
                time.sleep(pause)

        except Exception as e:
            log(f"    Warmup error on pair {sender['email']} -> {recipient['email']}: {e}")

    log(f"Warmup cycle complete. {successful}/{num_pairs} pairs exchanged.")

if __name__ == "__main__":
    pairs = 4
    if len(sys.argv) > 1:
        try:
            pairs = int(sys.argv[1])
        except ValueError:
            pass
    run_warmup_cycle(pairs)
