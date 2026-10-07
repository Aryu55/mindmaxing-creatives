#!/usr/bin/env python3
"""
Google Alternate Email Verification Helper
Listens on specified IONOS mailbox for incoming Google verification emails,
extracts verification links and codes, and outputs them instantly.
"""
import imaplib
import email
import re
import time
import sys

IMAP_HOST = "imap.ionos.com"
DEFAULT_PWD = "Aryan@2002"

def parse_msg(raw_bytes: bytes, target_email: str):
    msg = email.message_from_bytes(raw_bytes)
    subject = msg.get("Subject", "")
    sender = msg.get("From", "")
    
    if "google" in sender.lower() or "google" in subject.lower() or "verify" in subject.lower() or "verification" in subject.lower() or "confirm" in subject.lower():
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                if ctype in ("text/plain", "text/html"):
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="ignore") + "\n"
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
        
        # Check for 6-digit code
        code_matches = re.findall(r"\b(\d{6})\b", body)
        # Check for verification URLs
        url_matches = re.findall(r'(https://accounts\.google\.com/[^\s"\'<>]+)', body)

        print("\n" + "="*60, flush=True)
        print(f"🎉 GOOGLE EMAIL DETECTED for {target_email}!", flush=True)
        print(f"From: {sender}", flush=True)
        print(f"Subject: {subject}", flush=True)
        if code_matches:
            print(f"🎯 VERIFICATION CODE: {code_matches[0]}", flush=True)
        if url_matches:
            print(f"🔗 VERIFICATION LINK:\n{url_matches[0]}", flush=True)
        print("="*60 + "\n", flush=True)
        return {"code": code_matches[0] if code_matches else None, "link": url_matches[0] if url_matches else None}
    return None

def listen_for_google(target_email: str, password: str = DEFAULT_PWD, timeout_seconds: int = 300):
    print(f"\n[IMAP] Connecting to {target_email} on {IMAP_HOST}...", flush=True)
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=15)
        mail.login(target_email, password)
        mail.select("INBOX")
    except Exception as e:
        print(f"[ERROR] Failed to login to {target_email}: {e}", flush=True)
        return None

    print(f"[IMAP] Connected successfully to {target_email}.", flush=True)
    
    # 1. First inspect the 5 most recent messages in INBOX in case it already arrived
    res, data = mail.search(None, "ALL")
    all_ids = data[0].split() if (res == "OK" and data[0]) else []
    recent_ids = all_ids[-5:] if len(all_ids) >= 5 else all_ids

    for mid in reversed(recent_ids):
        _, msg_data = mail.fetch(mid, "(RFC822)")
        if msg_data and msg_data[0]:
            found = parse_msg(msg_data[0][1], target_email)
            if found:
                mail.logout()
                return found

    seen_ids = set(all_ids)
    print(f"[IMAP] Monitoring INBOX for fresh Google verification message (timeout: {timeout_seconds}s)...", flush=True)
    print(f"👉 Go ahead and click 'Next' or 'Add' for '{target_email}' in Google now!", flush=True)
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        time.sleep(2)
        try:
            mail.select("INBOX")
            res, data = mail.search(None, "ALL")
            if res != "OK" or not data[0]:
                continue
            
            current_ids = set(data[0].split())
            new_ids = current_ids - seen_ids

            for mid in new_ids:
                seen_ids.add(mid)
                _, msg_data = mail.fetch(mid, "(RFC822)")
                if msg_data and msg_data[0]:
                    found = parse_msg(msg_data[0][1], target_email)
                    if found:
                        mail.logout()
                        return found
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error, OSError):
            # Reconnect on transient IMAP drop
            try:
                mail = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=15)
                mail.login(target_email, password)
                mail.select("INBOX")
            except Exception:
                pass

    print(f"[TIMEOUT] No Google verification email arrived within {timeout_seconds}s.", flush=True)
    try:
        mail.logout()
    except Exception:
        pass
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 google_verify_helper.py <email_address>")
        sys.exit(1)
    listen_for_google(sys.argv[1].strip())
