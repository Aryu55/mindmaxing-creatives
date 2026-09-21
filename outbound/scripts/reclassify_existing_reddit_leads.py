#!/usr/bin/env python3
"""
Reclassify Existing Reddit Leads (Astra Specification)
- Evaluates the 9 existing Reddit records in mindmaxing_crm.db using evaluate_reddit_signal().
- Replaces speculative low-budget notes with factual signal rejection reasons.
- Preserves audit history in notes.
- Keeps them excluded from campaign queues.
- Missing original content -> REVIEW_REQUIRED (never invented conclusions).
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from reddit_signal_evaluator import (
    evaluate_reddit_signal,
    INCIDENT_CANDIDATE,
    REVIEW_REQUIRED,
    NO_MATCH,
    STALE,
    INVALID_SOURCE,
    POLICY_VERSION
)

DEFAULT_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mindmaxing_crm.db")


def reclassify_leads(db_path: str = DEFAULT_DB, apply: bool = False):
    print(f"=== Mindmaxing Reddit Leads Factual Reclassification ===")
    print(f"Database: {db_path}")
    print(f"Mode: {'APPLY' if apply else 'READ-ONLY AUDIT'}\n")

    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    leads = c.execute("SELECT * FROM leads WHERE source = 'reddit'").fetchall()
    print(f"Found {len(leads)} Reddit leads to evaluate.\n")

    eval_now = datetime.now(timezone.utc)
    summary_counts = {
        INCIDENT_CANDIDATE: 0,
        REVIEW_REQUIRED: 0,
        NO_MATCH: 0,
        STALE: 0,
        INVALID_SOURCE: 0
    }

    reclassifications = []

    for idx, lead in enumerate(leads, 1):
        domain = lead["domain"]
        title = lead["post_title"] or ""
        author = lead["post_author"] or ""
        url = lead["post_url"] or ""
        reviews_json = lead["reviews_json"]
        selftext = ""

        if reviews_json:
            try:
                rev_list = json.loads(reviews_json)
                if rev_list and isinstance(rev_list, list):
                    first_rev = rev_list[0]
                    raw_text = first_rev.get("text", "")
                    # Strip leading "[r/sub] title: " if present
                    if ": " in raw_text:
                        selftext = raw_text.split(": ", 1)[1]
                    else:
                        selftext = raw_text
            except Exception:
                selftext = ""

        created_raw = lead["review_freshest_date"] or lead["captured_at"]

        # If missing original content -> REVIEW_REQUIRED per Astra requirement
        if not title and not selftext:
            decision = REVIEW_REQUIRED
            reasons = ["MISSING_ORIGINAL_CONTENT"]
            evidence = {"domain": domain, "note": "Original post content missing; held for review."}
        else:
            post_payload = {
                "title": title,
                "selftext": selftext,
                "author": author,
                "url": url,
                "permalink": url.replace("https://reddit.com", ""),
                "created_utc": created_raw
            }
            decision, reasons, evidence = evaluate_reddit_signal(post_payload, eval_now)

        summary_counts[decision] = summary_counts.get(decision, 0) + 1

        # Determine target status:
        # Only INCIDENT_CANDIDATE enters normal candidate queue
        # REVIEW_REQUIRED goes to separate research view
        # Others remain outside campaign queue (DROPPED)
        if decision == INCIDENT_CANDIDATE:
            new_status = "CANDIDATE"
        elif decision == REVIEW_REQUIRED:
            new_status = "REVIEW_REQUIRED"
        else:
            new_status = "DROPPED"

        # Update notes: replace unsupported low-budget assumptions with factual reasons while preserving audit history
        old_notes = lead["notes"] or ""
        clean_notes = old_notes.replace(" | Quarantined: Micro-budget / free-mail Reddit beginner violating Invariant #1 & #6", "")
        updated_notes = f"{clean_notes} | Signal evaluated ({decision}): {', '.join(reasons)}".strip(" |")

        reclassifications.append({
            "id": lead["id"],
            "domain": domain,
            "title": title,
            "selftext": selftext,
            "decision": decision,
            "reasons": reasons,
            "new_status": new_status,
            "notes": updated_notes,
            "evidence": evidence
        })

        print(f"#{idx} [{domain}] -> {decision}")
        print(f"   Title: \"{title[:70]}\"")
        if selftext:
            print(f"   Body snippet: \"{selftext[:90]}...\"")
        print(f"   Reason codes: {reasons}")
        print(f"   Target Status: {new_status}\n")

    if apply:
        print("[*] Applying reclassification updates to database...")
        for r in reclassifications:
            c.execute("""
                UPDATE leads
                SET status = ?,
                    signal_decision = ?,
                    signal_reasons = ?,
                    signal_evidence = ?,
                    signal_policy_version = ?,
                    evaluated_at = ?,
                    notes = ?
                WHERE id = ?
            """, (
                r["new_status"],
                r["decision"],
                json.dumps(r["reasons"]),
                json.dumps(r["evidence"]),
                POLICY_VERSION,
                eval_now.isoformat(),
                r["notes"],
                r["id"]
            ))
        conn.commit()
        print(f"[✓] Successfully reclassified {len(reclassifications)} records in database.")

    conn.close()

    print("=== SUMMARY OF EXAMINED REDDIT RECORDS ===")
    print(f"Total Examined:       {len(leads)}")
    print(f"INCIDENT_CANDIDATE:   {summary_counts.get(INCIDENT_CANDIDATE, 0)}")
    print(f"REVIEW_REQUIRED:      {summary_counts.get(REVIEW_REQUIRED, 0)}")
    print(f"NO_MATCH / REJECTED:  {summary_counts.get(NO_MATCH, 0)}")
    print(f"STALE:                {summary_counts.get(STALE, 0)}")
    print(f"INVALID_SOURCE:       {summary_counts.get(INVALID_SOURCE, 0)}")
    print("==========================================\n")
    return reclassifications


if __name__ == "__main__":
    apply_mode = "--apply" in sys.argv
    db_file = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--apply" else (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "--apply" else DEFAULT_DB)
    reclassify_leads(db_file, apply=apply_mode)
