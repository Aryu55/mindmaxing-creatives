#!/usr/bin/env python3
"""
Requalify Trustpilot Leads (Task A & Task E Implementation)
Evaluates existing READY Trustpilot leads against the strict 7-day storefront incident criteria.

Modes:
  python3 requalify_trustpilot.py --dry-run
  python3 requalify_trustpilot.py --apply
"""

import sys
import os
import json
import sqlite3
import argparse
from datetime import datetime, timezone

# Ensure local imports work
sys.path.insert(0, os.path.dirname(__file__))

from trustpilot_signal_evaluator import (
    evaluate_trustpilot_signal,
    INCIDENT_CANDIDATE,
    REVIEW_REQUIRED,
    NO_MATCH,
    POLICY_VERSION
)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mindmaxing_crm.db")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def requalify_all_ready(apply_changes: bool = False) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    now_utc = datetime.now(timezone.utc)

    # Fetch all READY leads from Trustpilot
    c.execute("""
        SELECT id, domain, company_name, contact_email, contact_type, source,
               pain_trigger, reviews_json, status, current_sequence_step
        FROM leads
        WHERE status = 'READY' AND source = 'trustpilot'
        ORDER BY id ASC
    """)
    leads = c.fetchall()

    manifest = []
    counts = {
        "total_evaluated": len(leads),
        "proposed_candidate": 0,
        "proposed_review_required": 0,
        "proposed_incident_candidate": 0,
    }

    for lead in leads:
        lead_id = lead["id"]
        domain = lead["domain"]
        reviews_raw = lead["reviews_json"]
        reviews = []
        if reviews_raw:
            try:
                reviews = json.loads(reviews_raw)
            except Exception:
                pass

        # Evaluate each review for this lead
        best_decision = NO_MATCH
        best_reasons = []
        best_evidence = {}
        best_snippet = ""
        freshest_eval_date = ""

        # Order by priority: INCIDENT_CANDIDATE > REVIEW_REQUIRED > NO_MATCH
        priority_map = {INCIDENT_CANDIDATE: 3, REVIEW_REQUIRED: 2, NO_MATCH: 1}

        for rev in reviews:
            dec, reasons, ev = evaluate_trustpilot_signal(rev, now_utc)
            if priority_map.get(dec, 0) > priority_map.get(best_decision, 0):
                best_decision = dec
                best_reasons = reasons
                best_evidence = ev
                best_snippet = ev.get("evidence_span") or rev.get("snippet", "")[:120]
                freshest_eval_date = ev.get("review_datetime", "")
            elif best_decision == NO_MATCH and not best_reasons:
                best_reasons = reasons
                best_evidence = ev
                best_snippet = ev.get("evidence_span") or rev.get("snippet", "")[:120]
                freshest_eval_date = ev.get("review_datetime", "")

        # Target status mapping
        if best_decision == INCIDENT_CANDIDATE:
            # Note: Even if incident is found, if contact is generic support, it still cannot be sendable
            proposed_status = "CANDIDATE" if lead["contact_type"] == "GENERIC_SUPPORT" else "INCIDENT_CANDIDATE"
            counts["proposed_incident_candidate"] += 1
        elif best_decision == REVIEW_REQUIRED:
            proposed_status = "HELD_FOR_REVIEW"
            counts["proposed_review_required"] += 1
        else:
            proposed_status = "CANDIDATE"
            counts["proposed_candidate"] += 1

        entry = {
            "id": lead_id,
            "domain": domain,
            "old_status": lead["status"],
            "proposed_status": proposed_status,
            "signal_decision": best_decision,
            "signal_reasons": best_reasons,
            "evidence_snippet": best_snippet,
            "evidence_date": freshest_eval_date,
            "contact_type": lead["contact_type"],
            "contact_email": lead["contact_email"],
        }
        manifest.append(entry)

    # If applying changes
    if apply_changes:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = os.path.join(REPORTS_DIR, f"requalification_manifest_{now_utc.strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        for item in manifest:
            c.execute("""
                UPDATE leads
                SET status = ?,
                    signal_decision = ?,
                    signal_reasons = ?,
                    signal_evidence = ?,
                    signal_policy_version = ?,
                    evaluated_at = ?
                WHERE id = ? AND status = 'READY'
            """, (
                item["proposed_status"],
                item["signal_decision"],
                json.dumps(item["signal_reasons"]),
                json.dumps({"snippet": item["evidence_snippet"], "date": item["evidence_date"]}),
                POLICY_VERSION,
                now_utc.isoformat(),
                item["id"]
            ))
        conn.commit()
        print(f"Applied updates to {len(manifest)} leads. Manifest saved to {report_path}")

    conn.close()
    return {"counts": counts, "manifest": manifest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Requalify Trustpilot leads in CRM.")
    parser.add_argument("--apply", action="store_true", help="Apply proposed status changes to SQLite DB")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry-run inspection and output manifest")
    args = parser.parse_args()

    apply_flag = args.apply and not args.dry_run
    res = requalify_all_ready(apply_changes=apply_flag)

    counts = res["counts"]
    print("\n=== REQUALIFICATION SUMMARY ===")
    print(f"Total READY Evaluated:         {counts['total_evaluated']}")
    print(f"Proposed -> CANDIDATE (No match / Generic support): {counts['proposed_candidate']}")
    print(f"Proposed -> HELD_FOR_REVIEW:   {counts['proposed_review_required']}")
    print(f"Proposed -> INCIDENT_CANDIDATE:{counts['proposed_incident_candidate']}")

    print("\n=== SAMPLE MANIFEST ENTRIES (FIRST 5) ===")
    for m in res["manifest"][:5]:
        print(f"[{m['id']}] {m['domain']} ({m['contact_email']}) -> {m['proposed_status']} [{m['signal_decision']}]")
        print(f"     Reason: {m['signal_reasons']}")
        print(f"     Evidence: {m['evidence_snippet'][:100]}")
        print()

    # Specifically show gohaus.com (1027)
    gohaus = next((m for m in res["manifest"] if m["id"] == 1027 or "gohaus" in m["domain"]), None)
    if gohaus:
        print("=== GOHAUS.COM RECORD ===")
        print(f"[{gohaus['id']}] {gohaus['domain']} -> {gohaus['proposed_status']} [{gohaus['signal_decision']}]")
        print(f"     Reason: {gohaus['signal_reasons']}")
        print(f"     Evidence: {gohaus['evidence_snippet']}")
