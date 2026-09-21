#!/usr/bin/env python3
"""
Mindmaxing MailScout SMTP Protocol Prober v1.0
- Connects directly to domain's primary MX on port 25.
- Tests catch-all status with random hash.
- Tests common founder email permutations (first@, first.last@, flast@, etc.).
- When mailserver returns 250 OK on a non-catch-all domain, replaces generic email with verified founder personal inbox.
"""

import json
import os
import random
import smtplib
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")
HELO_HOST = "srv1371866.hstgr.cloud"
MAIL_FROM = "verify@srv1371866.hstgr.cloud"


def get_primary_mx(domain: str) -> str:
    clean_domain = domain.replace("www.", "").strip()
    try:
        out = subprocess.check_output(["host", "-t", "mx", clean_domain], timeout=5).decode()
        mx_hosts = []
        for line in out.strip().split("\n"):
            if "handled by" in line:
                parts = line.split()
                try:
                    prio = int(parts[-2])
                    host = parts[-1].rstrip(".")
                    mx_hosts.append((prio, host))
                except (ValueError, IndexError):
                    pass
        mx_hosts.sort()
        if mx_hosts:
            return mx_hosts[0][1]
    except Exception:
        pass
    return ""


def probe_founder_email(domain: str, full_name: str) -> tuple[str, str]:
    """
    Returns (verdict, email):
      verdict in ('VERIFIED', 'CATCH_ALL', 'NO_MATCH', 'NO_MX', 'ERROR')
    """
    clean_domain = domain.replace("www.", "").strip()
    parts = [p.strip() for p in full_name.split() if p.strip()]
    if not parts:
        return "NO_NAME", ""

    first = parts[0].lower()
    last = parts[-1].lower() if len(parts) > 1 else ""

    mx = get_primary_mx(clean_domain)
    if not mx:
        return "NO_MX", ""

    try:
        s = smtplib.SMTP(mx, 25, timeout=4)
        s.helo(HELO_HOST)
        s.mail(MAIL_FROM)

        # 1. Catch-all test
        random_hash = f"chk_{int(time.time())}_{random.randint(1000, 9999)}"
        code_fake, msg_fake = s.rcpt(f"{random_hash}@{clean_domain}")
        msg_fake_str = str(msg_fake).lower()
        if code_fake == 250:
            s.quit()
            return "CATCH_ALL", "Server accepted random honeypot address"
        elif code_fake in (421, 450, 451, 452):
            s.quit()
            return "TEMPFAIL", f"Honeypot returned temporary failure: {code_fake} {msg_fake_str}"
        elif code_fake == 550 and ("5.7." in msg_fake_str or "policy" in msg_fake_str or "blocked" in msg_fake_str or "spam" in msg_fake_str):
            s.quit()
            return "BLOCKED", f"Honeypot returned policy block: {code_fake} {msg_fake_str}"
        elif code_fake != 550 and "5.1.1" not in msg_fake_str and "unknown" not in msg_fake_str:
            s.quit()
            return "INCONCLUSIVE", f"Honeypot returned unexpected code: {code_fake} {msg_fake_str}"

        # 2. Test permutations (Diagnostic Observation Only - Not Identity Proof)
        candidates = [f"{first}@{clean_domain}"]
        if last:
            candidates.extend([
                f"{first}.{last}@{clean_domain}",
                f"{first}{last}@{clean_domain}",
                f"{first[0]}{last}@{clean_domain}",
                f"{first}_{last}@{clean_domain}"
            ])

        for cand in candidates:
            code, msg = s.rcpt(cand)
            if code == 250:
                s.quit()
                return "OBSERVED_ACCEPTANCE", cand

        s.quit()
        return "NO_MATCH", "All tested permutations rejected"
    except Exception as e:
        return "ERROR", str(e)


def run_batch_prober(limit: int = 60, dry_run: bool = True):
    """
    Diagnostic protocol prober.
    READ-ONLY: Does NOT update contact_email, contact_type, or campaign status.
    All protocol observations are logged for diagnostic review only.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    leads = c.execute("""
        SELECT id, domain, contact_email, resolved_name, current_sequence_step 
        FROM leads 
        WHERE resolved_name IS NOT NULL AND resolved_name != ''
        LIMIT ?
    """, (limit,)).fetchall()

    print(f"[*] Starting MailScout Diagnostic Protocol Prober across {len(leads)} leads...")
    print(f"[*] READ-ONLY DIAGNOSTIC MODE: Zero database mutations to contact_email or contact_type.\n", flush=True)

    verified_count = 0
    catchall_count = 0
    nomatch_count = 0
    blocked_count = 0

    for lead in leads:
        lead_id = lead["id"]
        domain = lead["domain"]
        old_email = lead["contact_email"]
        name = lead["resolved_name"]

        verdict, detail = probe_founder_email(domain, name)

        if verdict == "OBSERVED_ACCEPTANCE":
            verified_count += 1
            print(f"  [OBSERVED] {domain:30} | {name:20} -> {detail} (Observation only, no CRM swap)", flush=True)
        elif verdict == "CATCH_ALL":
            catchall_count += 1
            print(f"  [CATCHALL] {domain:30} | {name:20} -> Domain accepts all (unverifiable)", flush=True)
        elif verdict in ("BLOCKED", "TEMPFAIL", "INCONCLUSIVE"):
            blocked_count += 1
            print(f"  [{verdict:8}] {domain:30} | {name:20} -> {detail}", flush=True)
        else:
            nomatch_count += 1
            print(f"  [- NO-MATCH] {domain:30} | {name:20} -> {detail}", flush=True)

        time.sleep(0.5)

    conn.close()

    print("\n" + "=" * 60)
    print("MAIL SCOUT DIAGNOSTIC PROBER SUMMARY (READ-ONLY)")
    print("=" * 60)
    print(f"Total Probed:          {len(leads)}")
    print(f"Observed Acceptances:  {verified_count}")
    print(f"Catch-All Stores:      {catchall_count}")
    print(f"Blocked / Inconclusive:{blocked_count}")
    print(f"No Match Found:        {nomatch_count}")
    print("=" * 60)


if __name__ == "__main__":
    lim = 60
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        lim = int(sys.argv[1])
    run_batch_prober(limit=lim, dry_run=False)
