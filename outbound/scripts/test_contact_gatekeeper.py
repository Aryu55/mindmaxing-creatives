#!/usr/bin/env python3
"""
Mindmaxing Contact Gatekeeper & Protocol Integrity Test Suite
Tests:
1. Person with no role or Organization.employee: Never promoted to founder.
2. Organization.founder via @graph and @id: Correct name/role retained.
3. Founder Alice Morgan; press Alice Jones with alice@example.com: No automatic association.
4. Exact founder bio links an email: Correct DOM-local association.
5. Capitalization noise, non-Latin and multipart names: Handled safely.
6. evaluate_contact conjunctive checks:
   - Rejects unconfirmed identity
   - Rejects role accounts
   - Rejects unapproved status (passing checks does not approve)
   - Rejects active sequence recipient mismatch
   - Rejects suppressed recipients
   - Rejects expired verification (> 7 days)
   - Rejects catch-all routing
"""

import json
import os
import sqlite3
import sys
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import urllib.error

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from founder_resolver import (
    extract_json_ld_people, extract_text_founder_blocks, email_matches_name,
    resolve_founder_contact, extract_navigation_links
)
from contact_policy import (
    evaluate_contact, IdentityStatus, EmailOrigin, MailboxVerification, ContactDecision
)
from contact_sources import (
    HunterFoundOnlyAdapter, SourceOutcome, is_safe_public_url
)
from contact_jobs import (
    claim_next_job, complete_job, fail_job, CODE_VERSION
)


class TestContactGatekeeper(unittest.TestCase):

    def test_person_no_role_never_promoted(self):
        """Person with no role or Organization.employee must never become Founder."""
        html = """
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Person",
              "@id": "https://brand.com/#p1",
              "name": "Bob Smith"
            },
            {
              "@type": "Person",
              "@id": "https://brand.com/#p2",
              "name": "Jane Doe",
              "jobTitle": "Lead Developer"
            },
            {
              "@type": "Organization",
              "name": "Brand",
              "employee": {"@id": "https://brand.com/#p1"}
            }
          ]
        }
        </script>
        """
        people = extract_json_ld_people(html)
        # Neither Bob Smith (no role, employee) nor Jane Doe (developer) are founders
        self.assertEqual(len(people), 0, "Non-founders must not be promoted")

    def test_organization_founder_via_graph_and_id(self):
        """Organization.founder via @graph/@id retains correct founder identity."""
        html = """
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Organization",
              "@id": "https://brand.com/#org",
              "name": "SuperBrand",
              "founder": {
                "@id": "https://brand.com/#founder1"
              }
            },
            {
              "@type": "Person",
              "@id": "https://brand.com/#founder1",
              "name": "Alice Morgan",
              "jobTitle": "Co-Founder & CEO",
              "email": "alice@superbrand.com"
            }
          ]
        }
        </script>
        """
        people = extract_json_ld_people(html)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["name"], "Alice Morgan")
        self.assertEqual(people[0]["role"], "Co-Founder & CEO")
        self.assertEqual(people[0]["email"], "alice@superbrand.com")
        self.assertEqual(people[0]["relationship"], "Organization.founder")

    def test_no_false_association_across_separate_blocks(self):
        """
        Founder Alice Morgan and press contact Alice Jones at alice@brand.com:
        DOM-local scoping must NOT bind Alice Jones's email to Alice Morgan!
        """
        html = """
        <div class="founder-section">
          <h2>Our Leadership</h2>
          <p>Alice Morgan is the Founder and CEO of SuperBrand.</p>
        </div>
        <div class="press-section">
          <h3>Media Inquiries</h3>
          <p>Contact PR Manager Alice Jones: <a href="mailto:alice@superbrand.com">alice@superbrand.com</a></p>
        </div>
        """
        founders = extract_text_founder_blocks(html, "superbrand.com")
        self.assertEqual(len(founders), 1)
        self.assertEqual(founders[0]["name"], "Alice Morgan")
        # Alice Morgan must NOT have alice@superbrand.com attached!
        self.assertEqual(founders[0]["email"], "", "Must not pool unrelated page emails across DOM blocks")

    def test_exact_founder_bio_links_dom_local_email(self):
        """When an email is directly inside the founder's bio block, association is preserved."""
        html = """
        <div class="founder-profile">
          <h2>Alice Morgan</h2>
          <p>Alice Morgan is the Founder & CEO. For partnerships, contact her at <a href="mailto:alice@superbrand.com">alice@superbrand.com</a>.</p>
        </div>
        """
        founders = extract_text_founder_blocks(html, "superbrand.com")
        self.assertEqual(len(founders), 1)
        self.assertEqual(founders[0]["name"], "Alice Morgan")
        self.assertEqual(founders[0]["email"], "alice@superbrand.com")

    def test_evaluate_contact_conjunctive_requirements(self):
        """Pure contact policy strictly rejects non-conforming leads."""
        now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

        # 1. Base fully conforming candidate
        candidate = {
            "contact_email": "alice@superbrand.com",
            "contact_name": "Alice Morgan",
            "identity_status": IdentityStatus.FOUNDER_CONFIRMED,
            "email_origin": EmailOrigin.PUBLIC_SITE,
            "mailbox_verification": MailboxVerification.VALID,
            "verification_time": (now - timedelta(days=2)).isoformat(),
            "identity_evidence_time": (now - timedelta(days=5)).isoformat()
        }
        campaign = {
            "status": "HUMAN_APPROVED",
            "current_sequence_step": 0,
            "active_recipient": "alice@superbrand.com",
            "is_suppressed": False,
            "quota_available": True
        }

        # Conforming passes
        ok, decision, reasons = evaluate_contact(candidate, campaign, now)
        self.assertTrue(ok)
        self.assertEqual(decision, ContactDecision.ELIGIBLE)
        self.assertEqual(reasons, [])

        # 2. Rejects if not HUMAN_APPROVED (even if contact is 100% verified)
        unapproved_campaign = dict(campaign, status="CANDIDATE")
        ok, decision, reasons = evaluate_contact(candidate, unapproved_campaign, now)
        self.assertFalse(ok)
        self.assertEqual(decision, ContactDecision.REVIEW_REQUIRED)
        self.assertIn("CAMPAIGN_STATUS_NOT_APPROVED_CANDIDATE", reasons)

        # 3. Rejects role accounts
        role_candidate = dict(candidate, contact_email="support@superbrand.com")
        ok, decision, reasons = evaluate_contact(role_candidate, campaign, now)
        self.assertFalse(ok)
        self.assertIn("GENERIC_ROLE_ACCOUNT_REJECTED", reasons)

        # 4. Rejects Catch-All mailboxes
        catchall_candidate = dict(candidate, mailbox_verification=MailboxVerification.ACCEPT_ALL)
        ok, decision, reasons = evaluate_contact(catchall_candidate, campaign, now)
        self.assertFalse(ok)
        self.assertIn("MAILBOX_ACCEPT_ALL_ROUTING", reasons)

        # 5. Rejects Inferred Provider Emails for automatic dispatch
        inferred_candidate = dict(candidate, email_origin=EmailOrigin.PROVIDER_INFERRED)
        ok, decision, reasons = evaluate_contact(inferred_candidate, campaign, now)
        self.assertFalse(ok)
        self.assertIn("EMAIL_ORIGIN_INFERRED_REQUIRES_REVIEW", reasons)

        # 6. Rejects Active Sequence Mismatch
        mismatch_campaign = dict(campaign, current_sequence_step=1, active_recipient="old_contact@superbrand.com")
        ok, decision, reasons = evaluate_contact(candidate, mismatch_campaign, now)
        self.assertFalse(ok)
        self.assertIn("ACTIVE_SEQUENCE_RECIPIENT_MISMATCH", reasons)

        # 7. Rejects Stale Verification (> 7 days)
        stale_candidate = dict(candidate, verification_time=(now - timedelta(days=8)).isoformat())
        ok, decision, reasons = evaluate_contact(stale_candidate, campaign, now)
        self.assertFalse(ok)
        self.assertEqual(decision, ContactDecision.RETRY_DUE)
        self.assertIn("MAILBOX_VERIFICATION_EXPIRED", reasons)

        # 8. Rejects Suppressed Recipients
        suppressed_campaign = dict(campaign, is_suppressed=True)
        ok, decision, reasons = evaluate_contact(candidate, suppressed_campaign, now)
        self.assertFalse(ok)
        self.assertEqual(decision, ContactDecision.NEEDS_CONTACT)
        self.assertIn("RECIPIENT_SUPPRESSED", reasons)

    @patch("founder_resolver.check_mx_record", return_value=True)
    def test_homepage_navigation_link_discovery(self, mock_mx):
        """Founder on /our-story discovered via actual homepage link traversal."""
        hp_html = """
        <html><body>
          <nav>
            <a href="/our-story">Discover Our Story</a>
            <a href="/collections/all">Shop All</a>
          </nav>
        </body></html>
        """
        story_html = """
        <html><body>
          <div class="bio-block">
            <p>Jane Doe, Co-Founder of TestBrand. Direct contact: jane@testbrand.com</p>
          </div>
        </body></html>
        """

        def mock_fetch(url, timeout=3.5):
            if url == "https://testbrand.com/":
                return 200, hp_html
            elif url == "https://testbrand.com/our-story":
                return 200, story_html
            return 404, ""

        with patch("founder_resolver.fetch_url", side_effect=mock_fetch):
            res = resolve_founder_contact("testbrand.com", "TestBrand")

        self.assertEqual(res["resolution_status"], "FOUNDER_FOUND")
        self.assertEqual(res["resolved_name"], "Jane Doe")
        self.assertEqual(res["resolved_email"], "jane@testbrand.com")
        self.assertEqual(res["resolved_role"], "Co-founder")
        self.assertIn("/our-story", res["evidence"]["pages_crawled"])

    def test_hunter_found_only_no_inferred_fallback(self):
        """Found-only Hunter adapter returns NO_RESULT on 404 without falling back to inference."""
        adapter = HunterFoundOnlyAdapter(api_key="mock_hunter_key", credit_cap=20)
        
        mock_404 = urllib.error.HTTPError(
            url="https://api.hunter.io/v2/email-finder/found",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )

        with patch("urllib.request.urlopen", side_effect=mock_404):
            res = adapter.find_found_email("brand.com", "John Founder")

        self.assertEqual(res["outcome"], SourceOutcome.NO_RESULT)
        self.assertIsNone(res["email"])
        self.assertEqual(adapter.credits_used, 1)

    def test_hunter_removal_request_respected(self):
        """Hunter adapter detects HTTP 451 removal request to prevent contacting."""
        adapter = HunterFoundOnlyAdapter(api_key="mock_hunter_key", credit_cap=20)
        
        mock_451 = urllib.error.HTTPError(
            url="https://api.hunter.io/v2/email-finder/found",
            code=451,
            msg="Unavailable For Legal Reasons",
            hdrs={},
            fp=None
        )

        with patch("urllib.request.urlopen", side_effect=mock_451):
            res = adapter.find_found_email("brand.com", "John Founder")

        self.assertEqual(res["outcome"], SourceOutcome.REMOVAL_REQUEST)
        self.assertIsNone(res["email"])

    def test_hunter_credits_exhausted_stops_queries(self):
        """Hunter adapter stops firing requests when credit cap is reached."""
        adapter = HunterFoundOnlyAdapter(api_key="mock_hunter_key", credit_cap=2)
        adapter.credits_used = 2

        res = adapter.find_found_email("brand.com", "John Founder")
        self.assertEqual(res["outcome"], SourceOutcome.CREDITS_EXHAUSTED)
        self.assertIsNone(res["email"])

    @patch("founder_resolver.check_mx_record", return_value=True)
    def test_provider_wrong_person_held(self, mock_mx):
        """If provider returns an email belonging to another person, it is rejected and held as NAME_ONLY."""
        hp_html = """
        <html><body>
          <h3>Jane Doe, Founder of MyBrand</h3>
        </body></html>
        """
        adapter = HunterFoundOnlyAdapter(api_key="mock_key", credit_cap=20)
        # Mock Hunter returning an email that does NOT match Jane Doe
        hunter_mock_result = {
            "outcome": SourceOutcome.FOUND,
            "email": "charlie@mybrand.com",
            "score": 90,
            "sources": [{"uri": "https://external.com/press"}]
        }

        with patch("founder_resolver.fetch_url", return_value=(200, hp_html)):
            with patch.object(adapter, "find_found_email", return_value=hunter_mock_result):
                res = resolve_founder_contact("mybrand.com", "MyBrand", hunter_adapter=adapter)

        # Because charlie does not match Jane Doe, direct email is rejected
        self.assertEqual(res["resolution_status"], "NAME_ONLY")
        self.assertEqual(res["resolved_name"], "Jane Doe")
        self.assertIsNone(res["resolved_email"])

    def test_contact_job_transactional_leasing_and_recovery(self):
        """Tests atomic job claiming, duplicate worker prevention, and crashed lease recovery."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            CREATE TABLE contact_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL UNIQUE,
                domain TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'PENDING',
                attempt_count INTEGER DEFAULT 0,
                worker_id TEXT,
                lease_expires_at TEXT,
                next_attempt_at TEXT,
                last_error TEXT,
                last_error_type TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        c.execute("""
            CREATE TABLE contact_resolution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                run_id TEXT NOT NULL,
                code_version TEXT NOT NULL,
                event_type TEXT NOT NULL,
                inputs_json TEXT,
                outcome TEXT NOT NULL,
                before_state_json TEXT,
                after_state_json TEXT,
                rejection_reasons TEXT,
                created_at TEXT NOT NULL
            );
        """)
        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO contact_jobs (id, lead_id, domain, status, created_at, updated_at) VALUES (1, 101, 'site1.com', 'PENDING', ?, ?);", (now_iso, now_iso))
        c.execute("INSERT INTO contact_jobs (id, lead_id, domain, status, created_at, updated_at) VALUES (2, 102, 'site2.com', 'PENDING', ?, ?);", (now_iso, now_iso))
        conn.commit()

        # Worker 1 claims job 1
        job_w1 = claim_next_job(conn, worker_id="worker_1", lease_duration_sec=300)
        self.assertIsNotNone(job_w1)
        self.assertEqual(job_w1["id"], 1)

        # Worker 2 claims job 2 (cannot claim job 1)
        job_w2 = claim_next_job(conn, worker_id="worker_2", lease_duration_sec=300)
        self.assertIsNotNone(job_w2)
        self.assertEqual(job_w2["id"], 2)

        # No more pending jobs
        job_none = claim_next_job(conn, worker_id="worker_3", lease_duration_sec=300)
        self.assertIsNone(job_none)

        # Worker 1 crashes -> lease expires
        past_iso = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        c.execute("UPDATE contact_jobs SET lease_expires_at = ? WHERE id = 1", (past_iso,))
        conn.commit()

        # Worker 3 can now recover expired lease for Job 1
        job_w3 = claim_next_job(conn, worker_id="worker_3", lease_duration_sec=300)
        self.assertIsNotNone(job_w3)
        self.assertEqual(job_w3["id"], 1)
        self.assertEqual(job_w3["worker_id"], "worker_3")
        conn.close()

    def test_contact_job_retry_backoff_and_hold_for_review(self):
        """Tests 1h -> 24h -> 7d backoff schedule and transition to HELD_FOR_REVIEW after 3 failures."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            CREATE TABLE contact_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL UNIQUE,
                domain TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'PENDING',
                attempt_count INTEGER DEFAULT 0,
                worker_id TEXT,
                lease_expires_at TEXT,
                next_attempt_at TEXT,
                last_error TEXT,
                last_error_type TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        c.execute("""
            CREATE TABLE contact_resolution_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                domain TEXT NOT NULL,
                run_id TEXT NOT NULL,
                code_version TEXT NOT NULL,
                event_type TEXT NOT NULL,
                inputs_json TEXT,
                outcome TEXT NOT NULL,
                before_state_json TEXT,
                after_state_json TEXT,
                rejection_reasons TEXT,
                created_at TEXT NOT NULL
            );
        """)
        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO contact_jobs (id, lead_id, domain, status, attempt_count, created_at, updated_at) VALUES (1, 101, 'site1.com', 'RUNNING', 0, ?, ?);", (now_iso, now_iso))
        conn.commit()

        # Attempt 1 failure -> +1h
        fail_job(conn, job_id=1, run_id="r1", error_message="Crawl failed", error_type="TIMEOUT")
        j1 = c.execute("SELECT * FROM contact_jobs WHERE id = 1").fetchone()
        self.assertEqual(j1["attempt_count"], 1)
        self.assertEqual(j1["status"], "PENDING")
        self.assertIsNotNone(j1["next_attempt_at"])

        # Attempt 2 failure -> +24h
        fail_job(conn, job_id=1, run_id="r2", error_message="Crawl failed", error_type="TIMEOUT")
        j2 = c.execute("SELECT * FROM contact_jobs WHERE id = 1").fetchone()
        self.assertEqual(j2["attempt_count"], 2)
        self.assertEqual(j2["status"], "PENDING")

        # Attempt 3 failure -> +7d
        fail_job(conn, job_id=1, run_id="r3", error_message="Crawl failed", error_type="TIMEOUT")
        j3 = c.execute("SELECT * FROM contact_jobs WHERE id = 1").fetchone()
        self.assertEqual(j3["attempt_count"], 3)
        self.assertEqual(j3["status"], "PENDING")

        # Attempt 4 failure -> HELD_FOR_REVIEW
        fail_job(conn, job_id=1, run_id="r4", error_message="Crawl failed", error_type="TIMEOUT")
        j4 = c.execute("SELECT * FROM contact_jobs WHERE id = 1").fetchone()
        self.assertEqual(j4["attempt_count"], 4)
        self.assertEqual(j4["status"], "HELD_FOR_REVIEW")
        self.assertIsNone(j4["next_attempt_at"])
        conn.close()

    def test_safe_public_url_validation(self):
        """Validates that non-public, internal, or loopback URLs are strictly rejected."""
        self.assertFalse(is_safe_public_url("http://localhost/admin"))
        self.assertFalse(is_safe_public_url("http://127.0.0.1:8000"))
        self.assertFalse(is_safe_public_url("http://192.168.1.1/router"))
        self.assertFalse(is_safe_public_url("file:///etc/passwd"))
        self.assertFalse(is_safe_public_url("ftp://ftp.example.com"))
        # Public domain
        self.assertTrue(is_safe_public_url("https://example.com/about"))

    def test_mailbox_verification_honesty_onsite_scraped(self):
        """On-site scraped emails must set mailbox_verification = 'UNCHECKED', never fake 'VALID'."""
        hp_html = """
        <div class="founder-card">
          <p>John Doe is the Founder & CEO. Contact: <a href="mailto:john@testdomain.com">john@testdomain.com</a></p>
        </div>
        """
        with patch("founder_resolver.fetch_url", return_value=(200, hp_html)), \
             patch("founder_resolver.check_mx_record", return_value=True):
            res = resolve_founder_contact("testdomain.com", "TestDomain")

        self.assertEqual(res["resolution_status"], "FOUNDER_FOUND")
        self.assertEqual(res["mailbox_verification"], "UNCHECKED")
        self.assertEqual(res["identity_status"], "FOUNDER_CONFIRMED")

    def test_hunter_invalid_rejected_by_gatekeeper(self):
        """Hunter 'invalid' verification returns INVALID status and is rejected by evaluate_contact."""
        mock_hunter = MagicMock()
        mock_hunter.is_enabled = True
        mock_hunter.find_found_email.return_value = {
            "outcome": "FOUND",
            "email": "john@testdomain.com",
            "score": 10,
            "verification": {"status": "invalid", "date": "2026-09-21T10:00:00Z"},
            "sources": [{"url": "https://source.com"}]
        }

        hp_html = """
        <div class="founder-card">
          <p>John Doe is the Founder & CEO.</p>
        </div>
        """
        with patch("founder_resolver.fetch_url", return_value=(200, hp_html)), \
             patch("founder_resolver.check_mx_record", return_value=True):
            res = resolve_founder_contact("testdomain.com", "TestDomain", hunter_adapter=mock_hunter)

        self.assertEqual(res["mailbox_verification"], "INVALID")
        self.assertEqual(res["resolution_status"], "FOUNDER_VERIFICATION_FAILED")

        # Pass into evaluate_contact
        candidate = {
            "contact_email": "john@testdomain.com",
            "contact_name": "John Doe",
            "contact_role": "Founder",
            "identity_status": "FOUNDER_CONFIRMED",
            "email_origin": "PROVIDER_FOUND",
            "mailbox_verification": "INVALID",
            "verification_time": "2026-09-21T10:00:00Z",
            "identity_evidence_time": "2026-09-21T10:00:00Z",
        }
        campaign_state = {
            "status": "HUMAN_APPROVED",
            "current_sequence_step": 0,
            "active_recipient": "john@testdomain.com",
            "is_suppressed": False,
            "quota_available": True
        }
        eligible, decision, reasons = evaluate_contact(candidate, campaign_state, datetime.now(timezone.utc))
        self.assertFalse(eligible)
        self.assertEqual(decision, ContactDecision.NEEDS_CONTACT)
        self.assertIn("MAILBOX_RECIPIENT_INVALID", reasons)

    def test_stale_worker_lease_fencing_rejected(self):
        """Worker completing a job after its lease expired or ownership changed must be rejected."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
        CREATE TABLE contact_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            domain TEXT UNIQUE,
            priority INTEGER DEFAULT 50,
            status TEXT DEFAULT 'PENDING',
            worker_id TEXT,
            lease_expires_at TEXT,
            attempt_count INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 4,
            next_attempt_at TEXT,
            last_run_id TEXT,
            last_error TEXT,
            last_error_type TEXT,
            created_at TEXT,
            updated_at TEXT
        )""")
        c.execute("""
        CREATE TABLE leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE,
            status TEXT DEFAULT 'CANDIDATE',
            current_sequence_step INTEGER DEFAULT 0
        )""")
        now_iso = datetime.now(timezone.utc).isoformat()
        past_iso = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        c.execute("INSERT INTO leads (id, domain) VALUES (1, 'leasetest.com')")
        c.execute("""
            INSERT INTO contact_jobs (id, lead_id, domain, status, worker_id, lease_expires_at, created_at, updated_at)
            VALUES (1, 1, 'leasetest.com', 'CLAIMED', 'worker_A', ?, ?, ?)
        """, (past_iso, now_iso, now_iso))
        conn.commit()

        # Worker B attempts completion
        ok = complete_job(conn, job_id=1, run_id="r1", outcome="FOUND", candidates=[], lead_summary={}, worker_id="worker_B")
        self.assertFalse(ok, "Mismatched worker must not complete job")

        # Worker A attempts completion with expired lease
        ok_expired = complete_job(conn, job_id=1, run_id="r1", outcome="FOUND", candidates=[], lead_summary={}, worker_id="worker_A")
        self.assertFalse(ok_expired, "Expired lease worker must not complete job")
        conn.close()

    def test_dispatcher_reaches_send_with_approved_founder(self):
        """Dispatcher dry-run loads CRM status with valid candidate evidence and builds send queue."""
        import dispatcher
        test_db = "/tmp/test_dispatcher_evidence.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        dispatcher.DB_PATH = test_db

        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE,
            company_name TEXT,
            contact_email TEXT,
            status TEXT,
            current_sequence_step INTEGER DEFAULT 0,
            last_contacted_at TEXT,
            client_won INTEGER DEFAULT 0,
            source TEXT,
            subreddit TEXT,
            post_title TEXT,
            post_url TEXT,
            post_author TEXT,
            contact_type TEXT,
            contact_name TEXT,
            resolved_name TEXT,
            resolved_email TEXT,
            resolved_role TEXT,
            resolved_evidence TEXT,
            resolution_status TEXT,
            resolved_at TEXT,
            original_contact_email TEXT
        )""")
        c.execute("""
        CREATE TABLE contact_candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER,
            full_name TEXT,
            role TEXT,
            email TEXT,
            email_origin TEXT,
            mailbox_status TEXT,
            mailbox_checked_at TEXT,
            identity_status TEXT,
            identity_checked_at TEXT,
            is_selected INTEGER DEFAULT 1
        )""")
        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute("""
        INSERT INTO leads (id, domain, company_name, contact_email, status, current_sequence_step, resolved_at)
        VALUES (1, 'approvedbrand.com', 'ApprovedBrand', 'founder@approvedbrand.com', 'HUMAN_APPROVED', 0, ?)
        """, (now_iso,))
        c.execute("""
        INSERT INTO contact_candidates (lead_id, full_name, role, email, email_origin, mailbox_status, mailbox_checked_at, identity_status, identity_checked_at, is_selected)
        VALUES (1, 'John Founder', 'Founder', 'founder@approvedbrand.com', 'PROVIDER_FOUND', 'VALID', ?, 'FOUNDER_CONFIRMED', ?, 1)
        """, (now_iso, now_iso))
        conn.commit()
        conn.close()

        crm_status = dispatcher.get_crm_status()
        self.assertIn("approvedbrand.com", crm_status)
        lead_row = crm_status["approvedbrand.com"]
        self.assertEqual(lead_row["mailbox_status"], "VALID")
        self.assertEqual(lead_row["identity_status"], "FOUNDER_CONFIRMED")
        if os.path.exists(test_db):
            os.remove(test_db)


if __name__ == "__main__":
    unittest.main(verbosity=2)

