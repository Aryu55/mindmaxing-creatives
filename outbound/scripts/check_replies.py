import imaplib
import ssl
import json
import email
import re
from datetime import datetime

import os
CONFIG_FILE = os.environ.get("MAILBOXES_FILE", "/root/outbound/config/mailboxes.json")
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "/root/outbound/config/credentials.env")

def get_password():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE) as f:
            for line in f:
                if line.startswith("IONOS_PASSWORD="):
                    return line.strip().split("=", 1)[1].strip().strip('"\'')
    return os.environ.get("IONOS_PASSWORD", "")

PASSWORD = get_password()

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE) as f:
        mailboxes = json.load(f)
else:
    mailboxes = []

ctx = ssl.create_default_context()
replies = []

for mb in mailboxes:
    em = mb["email"]
    try:
        mail = imaplib.IMAP4_SSL("imap.ionos.com", 993, ssl_context=ctx, timeout=5)
        mail.login(em, PASSWORD)
        mail.select("INBOX")
        status, data = mail.search(None, "ALL")
        msg_ids = data[0].split()
        for m_id in msg_ids:
            status, msg_data = mail.fetch(m_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            frm = msg.get("From", "")
            subj = msg.get("Subject", "")
            date = msg.get("Date", "")
            
            # Skip system ionos / gmail setup emails
            if any(s in frm.lower() for s in ["support@ionos.com", "gmail-noreply@google.com", "mailer-daemon"]):
                continue
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            replies.append({
                "mailbox": em,
                "from": frm,
                "subject": subj,
                "date": date,
                "snippet": body.strip()[:200].replace("\n", " ")
            })
        mail.logout()
    except Exception as e:
        pass

print(f"Total Prospect Replies Detected: {len(replies)}\n")
for i, r in enumerate(replies, 1):
    print(f"{i}. [To: {r['mailbox']}] From: {r['from']}")
    print(f"   Subject: {r['subject']}")
    print(f"   Date: {r['date']}")
    print(f"   Snippet: {r['snippet']}\n")
