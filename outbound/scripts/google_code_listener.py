#!/usr/bin/env python3
"""
Real-time Google Verification Code Snatcher for aryan@mindmaxing.info
Listens via IMAP for incoming Google verification emails and prints the 6-digit code instantly.
"""
import imaplib
import email
import re
import time
import sys

IMAP_HOST = "imap.ionos.com"
EMAIL_ADDR = "aryan@mindmaxing.info"
EMAIL_PWD = "Aryan@2002"

def listen_for_code(timeout_seconds: int = 180):
    print(f"Connecting to IMAP for {EMAIL_ADDR}...")
    mail = imaplib.IMAP4_SSL(IMAP_HOST, 993)
    mail.login(EMAIL_ADDR, EMAIL_PWD)
    mail.select("INBOX")
    
    # Only look for new messages arriving now (mid > 4)
    status, data = mail.search(None, "ALL")
    all_ids = set(data[0].split())
    known_mids = {b"1", b"2", b"3", b"4"}
    new_unprocessed = all_ids - known_mids

    for mid in new_unprocessed:
        status, msg_data = mail.fetch(mid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        if "google" in sender.lower() or "verify" in subject.lower():
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
            matches = re.findall(r"\b(\d{6})\b", body)
            if matches:
                code = matches[0]
                print(f"\n[FOUND VERIFICATION CODE] From: {sender} | Subject: {subject}")
                print("\n" + "="*50)
                print(f"🎯 GOOGLE VERIFICATION CODE: {code}")
                print("="*50 + "\n")
                mail.logout()
                return code

    initial_ids = set(all_ids)
    print(f"Listening for incoming Google verification code (timeout: {timeout_seconds}s)...")
    print("Go ahead and click 'Next' on the Google signup page!")
    
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        time.sleep(2)
        mail.select("INBOX")
        status, data = mail.search(None, "ALL")
        current_ids = set(data[0].split())
        new_ids = current_ids - initial_ids
        
        if new_ids:
            for mid in new_ids:
                status, msg_data = mail.fetch(mid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)
                subject = msg.get("Subject", "")
                sender = msg.get("From", "")
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                    
                print(f"\n[NEW EMAIL RECEIVED] From: {sender} | Subject: {subject}")
                
                # Check for 6-digit code
                matches = re.findall(r"\b(\d{6})\b", body)
                if matches:
                    code = matches[0]
                    print("\n" + "="*50)
                    print(f"🎯 GOOGLE VERIFICATION CODE: {code}")
                    print("="*50 + "\n")
                    mail.logout()
                    return code
                    
    print("\nTimed out waiting for verification code.")
    mail.logout()
    return None

if __name__ == "__main__":
    timeout = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    listen_for_code(timeout)
