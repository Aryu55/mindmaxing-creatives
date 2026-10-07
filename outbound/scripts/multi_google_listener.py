#!/usr/bin/env python3
"""
Multi-Mailbox Google Verification Snatcher
Listens concurrently across all healthy mailboxes.
The moment Google sends a verification email to ANY of them, it snatches and prints the code immediately.
"""
import imaplib
import email
import re
import time
import sys
import threading

IMAP_HOST = "imap.ionos.com"
DEFAULT_PWD = "Aryan@2002"

HEALTHY_MAILBOXES = [
    "founder@mindmaxing.info",
    "aryan.panchal@mindmaxing.info",
    "aryan@mindmaxing.org",
    "founder@mindmaxing.org",
    "aryan.panchal@mindmaxing.org",
    "studio@mindmaxing.org",
    "founder@mindmaxing.online",
    "aryan.panchal@mindmaxing.online",
    "studio@mindmaxing.online",
    "aryan@mindmaxing.store",
    "founder@mindmaxing.store",
    "aryan.panchal@mindmaxing.store",
    "aryan.dev@mindmaxing.store"
]

PREV_CODES = {"343796", "123173", "798697", "000000", "111111"}

found_event = threading.Event()
found_result = {}

def parse_msg(raw_bytes: bytes, target_email: str):
    msg = email.message_from_bytes(raw_bytes)
    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    
    # Must be from Google
    if "google" not in sender_lower and "google" not in subject_lower:
        return None
        
    # Ignore routine sign-in security alerts
    if "security alert" in subject_lower:
        return None

    # Must be fresh (within 10 minutes)
    date_hdr = msg.get("Date")
    if date_hdr:
        parsed_dt = email.utils.parsedate_tz(date_hdr)
        if parsed_dt:
            msg_ts = email.utils.mktime_tz(parsed_dt)
            if time.time() - msg_ts > 600:
                return None
    
    if any(k in subject_lower for k in ["verify", "verification", "confirm", "code"]):
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() in ("text/plain", "text/html"):
                    p = part.get_payload(decode=True)
                    if p:
                        body += p.decode("utf-8", errors="ignore") + "\n"
        else:
            p = msg.get_payload(decode=True)
            if p:
                body = p.decode("utf-8", errors="ignore")
        
        codes = [c for c in re.findall(r"\b(\d{6})\b", body) if c not in PREV_CODES]
        urls = re.findall(r'(https://accounts\.google\.com/[^\s"\'<>]+)', body)

        if codes or urls:
            return {
                "mailbox": target_email,
                "subject": subject,
                "sender": sender,
                "code": codes[0] if codes else None,
                "link": urls[0] if urls else None
            }
    return None

def monitor_mailbox(email_addr: str, timeout_sec: int = 300):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=12)
        mail.login(email_addr, DEFAULT_PWD)
        mail.select("INBOX")
    except Exception:
        return

    # Check the latest message
    try:
        res, data = mail.search(None, "ALL")
        all_ids = data[0].split() if (res == "OK" and data[0]) else []
        if all_ids:
            for mid in reversed(all_ids[-3:]):
                _, msg_data = mail.fetch(mid, "(RFC822)")
                if msg_data and msg_data[0]:
                    res = parse_msg(msg_data[0][1], email_addr)
                    if res and res.get("code"):
                        found_result.update(res)
                        found_event.set()
                        mail.logout()
                        return
    except Exception:
        pass

    seen_ids = set(all_ids)
    start = time.time()
    while not found_event.is_set() and (time.time() - start < timeout_sec):
        time.sleep(2)
        try:
            mail.select("INBOX")
            res, data = mail.search(None, "ALL")
            if res != "OK" or not data[0]:
                continue
            cur_ids = set(data[0].split())
            new_ids = cur_ids - seen_ids
            for mid in new_ids:
                seen_ids.add(mid)
                _, msg_data = mail.fetch(mid, "(RFC822)")
                if msg_data and msg_data[0]:
                    res = parse_msg(msg_data[0][1], email_addr)
                    if res:
                        found_result.update(res)
                        found_event.set()
                        mail.logout()
                        return
        except Exception:
            try:
                mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=12)
                mail.login(email_addr, DEFAULT_PWD)
                mail.select("INBOX")
            except Exception:
                pass

    try:
        mail.logout()
    except Exception:
        pass

def main():
    target = sys.argv[1].strip() if len(sys.argv) > 1 else None
    targets = [target] if target else HEALTHY_MAILBOXES
    
    print(f"📡 Multi-listener active for {len(targets)} mailboxes: {', '.join(targets)}", flush=True)
    threads = []
    for mb in targets:
        t = threading.Thread(target=monitor_mailbox, args=(mb, 300), daemon=True)
        threads.append(t)
        t.start()

    found_event.wait(timeout=300)
    if found_result:
        print("\n" + "="*60, flush=True)
        print(f"🎉 GOOGLE CODE INTERCEPTED FOR: {found_result['mailbox']}", flush=True)
        print(f"Subject: {found_result['subject']}", flush=True)
        if found_result.get("code"):
            print(f"🎯 VERIFICATION CODE: {found_result['code']}", flush=True)
        if found_result.get("link"):
            print(f"🔗 LINK: {found_result['link']}", flush=True)
        print("="*60 + "\n", flush=True)
    else:
        print("[TIMEOUT] No verification message received within 5 minutes.", flush=True)

if __name__ == "__main__":
    main()
