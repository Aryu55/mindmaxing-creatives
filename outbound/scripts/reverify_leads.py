#!/usr/bin/env python3
"""
Mindmaxing Lead Re-Verification Script
Checks MX + SMTP RCPT TO deliverability on aging leads and refreshes
their last_verified_at timestamp to prevent the 7-day verification cliff.

Run every 3 days via cron/launchd. No actual emails are sent.
Only performs SMTP handshake up to RCPT TO, then disconnects.

Usage:
    python3 reverify_leads.py [--dry-run] [--age-days 5]
"""

import argparse
import dns.resolver
import os
import smtplib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")

# Leads older than this many days get re-verified (2-day buffer before the 7-day cliff)
DEFAULT_AGE_DAYS = 5
SMTP_TIMEOUT = 10
HELO_DOMAIN = "mindmaxing.info"


def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")


def get_mx_host(domain):
    """Get the primary MX host for a domain."""
    try:
        answers = dns.resolver.resolve(domain, "MX")
        mx_records = sorted(answers, key=lambda r: r.preference)
        if mx_records:
            return str(mx_records[0].exchange).rstrip(".")
    except Exception:
        pass
    return None


def verify_rcpt(email, mx_host):
    """
    Perform SMTP handshake up to RCPT TO to check deliverability.
    Returns (is_valid, status_code, response).
    Does NOT send any email.
    """
    try:
        with smtplib.SMTP(mx_host, 25, timeout=SMTP_TIMEOUT) as smtp:
            smtp.ehlo(HELO_DOMAIN)
            try:
                smtp.starttls()
                smtp.ehlo(HELO_DOMAIN)
            except smtplib.SMTPNotSupportedError:
                pass  # TLS not required for verification

            code, msg = smtp.mail(f"verify@{HELO_DOMAIN}")
            if code != 250:
                return False, code, msg.decode("utf-8", errors="replace")

            code, msg = smtp.rcpt(email)
            response = msg.decode("utf-8", errors="replace")

            # Reset the transaction (clean disconnect)
            smtp.rset()

            if code == 250:
                return True, code, response
            else:
                return False, code, response

    except smtplib.SMTPConnectError as e:
        return False, 0, f"Connection failed: {e}"
    except smtplib.SMTPServerDisconnected as e:
        return False, 0, f"Server disconnected: {e}"
    except TimeoutError:
        return False, 0, "Connection timed out"
    except Exception as e:
        return False, 0, f"Error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Re-verify aging lead mailboxes")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be verified without doing it")
    parser.add_argument("--age-days", type=int, default=DEFAULT_AGE_DAYS,
                        help=f"Re-verify leads older than N days (default: {DEFAULT_AGE_DAYS})")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        log(f"Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.age_days)).isoformat()

    # Find HUMAN_APPROVED leads with aging captured_at and no recent re-verification
    c.execute("""
        SELECT id, domain, contact_email, captured_at, last_verified_at
        FROM leads
        WHERE status IN ('HUMAN_APPROVED', 'TOUCH_1_SENT', 'TOUCH_2_SENT')
          AND source = 'getleads'
          AND contact_email IS NOT NULL
          AND contact_email != ''
          AND (
              (last_verified_at IS NULL AND captured_at < ?)
              OR (last_verified_at IS NOT NULL AND last_verified_at < ?)
          )
    """, (cutoff, cutoff))

    leads = c.fetchall()
    log(f"Found {len(leads)} leads needing re-verification (older than {args.age_days} days)")

    if args.dry_run:
        for l in leads[:10]:
            log(f"  [DRY RUN] Would verify: {l['contact_email']} ({l['domain']}) - captured {l['captured_at']}")
        if len(leads) > 10:
            log(f"  ... and {len(leads) - 10} more")
        conn.close()
        return

    verified = 0
    failed = 0
    skipped = 0

    # Group by email domain for MX efficiency
    domain_mx_cache = {}

    for l in leads:
        email = l["contact_email"].strip().lower()
        email_domain = email.split("@")[-1] if "@" in email else None

        if not email_domain:
            skipped += 1
            continue

        # Cache MX lookups
        if email_domain not in domain_mx_cache:
            mx = get_mx_host(email_domain)
            domain_mx_cache[email_domain] = mx

        mx_host = domain_mx_cache[email_domain]
        if not mx_host:
            log(f"  SKIP: No MX record for {email_domain} ({l['domain']})")
            skipped += 1
            continue

        is_valid, code, response = verify_rcpt(email, mx_host)
        now_iso = datetime.now(timezone.utc).isoformat()

        if is_valid:
            c.execute("UPDATE leads SET last_verified_at = ? WHERE id = ?", (now_iso, l["id"]))
            conn.commit()
            verified += 1
            log(f"  OK: {email} ({l['domain']}) - refreshed")
        else:
            failed += 1
            log(f"  FAIL: {email} ({l['domain']}) - {code} {response}")

    conn.close()
    log(f"Re-verification complete: {verified} refreshed, {failed} failed, {skipped} skipped")


if __name__ == "__main__":
    main()
