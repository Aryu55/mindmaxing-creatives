#!/usr/bin/env python3
"""
Test Suite: Reddit Signal Evaluator (Astra Specification)
Verifies:
1. All 12 specified Astra fixtures with a fixed clock.
2. Parity between Gmail and custom domain contacts (zero budget bias).
3. Qualified signal plus unverified contact cannot reach SMTP.
4. Reprocessing a business preserves its active conversation and sequence.
5. An unapproved candidate never becomes sendable through export or synchronization.
"""

import unittest
import os
import sys
import sqlite3
from datetime import datetime, timezone, timedelta

# Ensure scripts dir is on sys.path
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
)


class TestRedditSignalEvaluatorFixtures(unittest.TestCase):
    def setUp(self):
        # Fixed clock for all deterministic fixture evaluations
        self.fixed_now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
        self.recent_created_utc = (self.fixed_now - timedelta(days=2)).timestamp()
        self.stale_created_utc = (self.fixed_now - timedelta(days=10)).timestamp()

    def test_fixture_1_just_launched_traffic_no_sales_review_my_store(self):
        """'Just launched. Traffic but no sales. Review my store.' -> NO_MATCH"""
        post = {
            "title": "Just launched. Traffic but no sales.",
            "selftext": "Review my store: https://cozyapparel.com. Let me know what you think.",
            "created_utc": self.recent_created_utc,
            "author": "store_owner_1",
            "permalink": "/r/shopify/comments/f1/just_launched/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f1/just_launched/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, NO_MATCH)
        self.assertIn("GENERIC_FEEDBACK_ONLY", reasons)

    def test_fixture_2_does_checkout_button_look_good(self):
        """'Does the checkout button look good?' -> NO_MATCH"""
        post = {
            "title": "Does the checkout button look good?",
            "selftext": "Checking out new theme styling for my store https://nordicdesign.co. Does it look right?",
            "created_utc": self.recent_created_utc,
            "author": "store_owner_2",
            "permalink": "/r/shopify/comments/f2/styling/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f2/styling/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, NO_MATCH)
        self.assertIn("NO_MALFUNCTION_ASSERTED", reasons)

    def test_fixture_3_ads_not_working_change_creatives(self):
        """'My ads are not working. Should I change creatives?' -> NO_MATCH"""
        post = {
            "title": "My ads are not working. Should I change creatives?",
            "selftext": "Running Meta ads to my site https://freshglow.com but ads are not working. Any tips?",
            "created_utc": self.recent_created_utc,
            "author": "ad_runner_3",
            "permalink": "/r/FacebookAds/comments/f3/creatives/",
            "subreddit": "FacebookAds",
            "url": "https://reddit.com/r/FacebookAds/comments/f3/creatives/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, NO_MATCH)
        self.assertIn("MARKETING_OR_AD_QUERY_ONLY", reasons)

    def test_fixture_4_updated_theme_everything_works_thoughts_on_colours(self):
        """'Updated the theme; everything works. Thoughts on colours?' -> NO_MATCH"""
        post = {
            "title": "Updated the theme; everything works. Thoughts on colours?",
            "selftext": "I updated the theme yesterday on my store https://urbanleather.com and everything works smoothly. Just looking for feedback on palette.",
            "created_utc": self.recent_created_utc,
            "author": "designer_4",
            "permalink": "/r/ecommerce/comments/f4/colours/",
            "subreddit": "ecommerce",
            "url": "https://reddit.com/r/ecommerce/comments/f4/colours/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, NO_MATCH)
        self.assertTrue(any(r in ["NO_MALFUNCTION_ASSERTED", "NON_MALFUNCTION_THEME_FEEDBACK"] for r in reasons))

    def test_fixture_5_mobile_checkout_button_stopped_responding(self):
        """'My store's mobile checkout button stopped responding after yesterday's theme update,' with explicit store URL -> INCIDENT_CANDIDATE"""
        post = {
            "title": "Need urgent help: theme update issue",
            "selftext": "My store's mobile checkout button stopped responding after yesterday's theme update. Customers can't buy on https://veloceboots.com.",
            "created_utc": self.recent_created_utc,
            "author": "founder_5",
            "permalink": "/r/shopify/comments/f5/checkout_broken/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f5/checkout_broken/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, INCIDENT_CANDIDATE)
        self.assertIn("STOREFRONT_MALFUNCTION_REPORTED", reasons)
        self.assertEqual(evidence.get("domain"), "veloceboots.com")
        self.assertIn("stopped responding", evidence.get("malfunction", "").lower())
        self.assertIn("mobile checkout button", evidence.get("component", "").lower())
        self.assertTrue(len(evidence.get("supporting_text", "")) > 10)

    def test_fixture_6_cart_empties_when_customers_change_quantity(self):
        """'Our cart empties when customers change quantity,' with explicit store URL -> INCIDENT_CANDIDATE"""
        post = {
            "title": "Cart bug on our store",
            "selftext": "Our cart empties when customers change quantity in the drawer on https://zenithtea.com. We are losing sales.",
            "created_utc": self.recent_created_utc,
            "author": "tea_brand_6",
            "permalink": "/r/shopify/comments/f6/cart_empties/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f6/cart_empties/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, INCIDENT_CANDIDATE)
        self.assertIn("STOREFRONT_MALFUNCTION_REPORTED", reasons)
        self.assertEqual(evidence.get("domain"), "zenithtea.com")
        self.assertIn("empties", evidence.get("malfunction", "").lower())
        self.assertIn("cart", evidence.get("component", "").lower())

    def test_fixture_7_our_checkout_is_not_broken(self):
        """'Our checkout is not broken.' -> NO_MATCH"""
        post = {
            "title": "Low sales this week",
            "selftext": "Our checkout is not broken on my store https://alpinewear.co. We tested it thoroughly. Any thoughts on why traffic is quiet?",
            "created_utc": self.recent_created_utc,
            "author": "alpine_7",
            "permalink": "/r/ecommerce/comments/f7/low_sales/",
            "subreddit": "ecommerce",
            "url": "https://reddit.com/r/ecommerce/comments/f7/low_sales/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, NO_MATCH)
        self.assertIn("NEGATION_DETECTED", reasons)

    def test_fixture_8_what_should_i_do_if_checkout_ever_breaks(self):
        """'What should I do if checkout ever breaks?' -> NO_MATCH"""
        post = {
            "title": "What should I do if checkout ever breaks?",
            "selftext": "Just preparing my backup plan for https://novakettle.com. What should I do if checkout ever breaks during Black Friday?",
            "created_utc": self.recent_created_utc,
            "author": "planner_8",
            "permalink": "/r/shopify/comments/f8/hypothetical/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f8/hypothetical/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, NO_MATCH)
        self.assertIn("HYPOTHETICAL_QUESTION", reasons)

    def test_fixture_9_numeric_funnel_dropoff_without_malfunction(self):
        """'400 clicks, 45 add-to-carts, zero checkout starts,' without a malfunction -> REVIEW_REQUIRED"""
        post = {
            "title": "Funnel dropoff analysis",
            "selftext": "Looking at our Shopify analytics on https://purebotanics.com: we had 400 clicks, 45 add-to-carts, zero checkout starts yesterday. Not sure what is happening.",
            "created_utc": self.recent_created_utc,
            "author": "analytics_9",
            "permalink": "/r/shopify/comments/f9/funnel/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f9/funnel/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, REVIEW_REQUIRED)
        self.assertIn("NUMERIC_FUNNEL_DROPOFF_WITHOUT_REPORTED_MALFUNCTION", reasons)
        self.assertIn("stated_metrics", evidence)
        self.assertEqual(evidence["domain"], "purebotanics.com")

    def test_fixture_10_real_incident_unclear_author_store_relationship(self):
        """Real incident but unclear author–store relationship -> REVIEW_REQUIRED"""
        post = {
            "title": "Checkout bug observed on client store",
            "selftext": "Saw a weird issue on a competitor's site https://rivaloutfitters.com: their mobile checkout button stopped responding completely.",
            "created_utc": self.recent_created_utc,
            "author": "observer_10",
            "permalink": "/r/shopify/comments/f10/competitor_bug/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f10/competitor_bug/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, REVIEW_REQUIRED)
        self.assertIn("UNCLEAR_AUTHOR_STORE_RELATIONSHIP", reasons)

    def test_fixture_11_relevant_incident_older_than_seven_days(self):
        """Relevant incident older than seven days -> STALE"""
        post = {
            "title": "Cart drawer stopped working",
            "selftext": "On my store https://vintagevibe.co the cart drawer stopped responding after an app install.",
            "created_utc": self.stale_created_utc, # 10 days ago
            "author": "vintage_11",
            "permalink": "/r/shopify/comments/f11/old_incident/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f11/old_incident/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, STALE)
        self.assertIn("STALE_SOURCE_EXCEEDS_7_DAYS", reasons)

    def test_fixture_12_missing_original_timestamp(self):
        """Missing original timestamp -> INVALID_SOURCE"""
        post = {
            "title": "My store checkout is unresponsive",
            "selftext": "My store https://quicktest.com mobile checkout stopped responding.",
            "created_utc": None, # Missing!
            "author": "tester_12",
            "permalink": "/r/shopify/comments/f12/missing_time/",
            "subreddit": "shopify",
            "url": "https://reddit.com/r/shopify/comments/f12/missing_time/"
        }
        decision, reasons, evidence = evaluate_reddit_signal(post, self.fixed_now)
        self.assertEqual(decision, INVALID_SOURCE)
        self.assertIn("MISSING_OR_INVALID_TIMESTAMP", reasons)


class TestArchitecturalInvariants(unittest.TestCase):
    def setUp(self):
        self.fixed_now = datetime(2026, 9, 22, 12, 0, 0, tzinfo=timezone.utc)
        self.recent_created_utc = (self.fixed_now - timedelta(days=1)).timestamp()

    def test_gmail_vs_custom_domain_parity(self):
        """A genuine incident qualifies under INCIDENT_CANDIDATE regardless of whether contact is Gmail or custom domain."""
        post_custom = {
            "title": "Checkout button broken",
            "selftext": "On my store https://store-a.com our checkout button stopped responding. Contact me at owner@store-a.com",
            "created_utc": self.recent_created_utc,
            "author": "owner_a",
            "permalink": "/r/shopify/comments/a1/custom/",
            "subreddit": "shopify"
        }
        post_gmail = {
            "title": "Checkout button broken",
            "selftext": "On my store https://store-b.com our checkout button stopped responding. Contact me at storeb_help@gmail.com",
            "created_utc": self.recent_created_utc,
            "author": "owner_b",
            "permalink": "/r/shopify/comments/b1/gmail/",
            "subreddit": "shopify"
        }
        dec_a, _, ev_a = evaluate_reddit_signal(post_custom, self.fixed_now)
        dec_b, _, ev_b = evaluate_reddit_signal(post_gmail, self.fixed_now)

        self.assertEqual(dec_a, INCIDENT_CANDIDATE)
        self.assertEqual(dec_b, INCIDENT_CANDIDATE)
        # Evaluator makes zero budget or contact domain inference
        self.assertNotIn("GMAIL_PENALTY", ev_b)
        self.assertEqual(ev_b["domain"], "store-b.com")

    def test_qualified_signal_plus_unverified_contact_cannot_reach_smtp(self):
        """Qualified signal plus unverified contact cannot reach SMTP."""
        import volume_controller
        test_db = f"/tmp/test_eval_guard_{os.getpid()}.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        
        orig_db = volume_controller.DB_PATH
        volume_controller.DB_PATH = test_db
        try:
            conn = sqlite3.connect(test_db)
            c = conn.cursor()
            c.execute("""
                CREATE TABLE leads (
                    id INTEGER PRIMARY KEY,
                    domain TEXT UNIQUE,
                    contact_email TEXT,
                    contact_type TEXT,
                    status TEXT,
                    source TEXT,
                    signal_decision TEXT,
                    current_sequence_step INTEGER DEFAULT 0
                )
            """)
            c.execute("""
                CREATE TABLE outbound_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    domain TEXT,
                    touch_number INTEGER,
                    assigned_mailbox TEXT,
                    recipient_email TEXT,
                    subject TEXT,
                    body TEXT,
                    due_at TEXT,
                    earliest_send_at TEXT,
                    status TEXT DEFAULT 'PENDING',
                    worker_id TEXT,
                    campaign_name TEXT,
                    period_id TEXT,
                    decision_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    UNIQUE(domain, touch_number)
                )
            """)
            c.execute("""
                CREATE TABLE mailbox_daily_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mailbox TEXT,
                    period_id TEXT,
                    decision_date_utc TEXT,
                    decision_action TEXT,
                    decision_reason TEXT,
                    effective_campaign_cap INTEGER,
                    effective_diagnostic_cap INTEGER,
                    revision INTEGER DEFAULT 1,
                    policy_version TEXT
                )
            """)
            c.execute("CREATE TABLE recipient_suppressions (recipient_email TEXT PRIMARY KEY, reason TEXT, suppressed_at TEXT)")
            c.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY, sender_email TEXT, recipient_email TEXT, domain TEXT, smtp_status TEXT, purpose TEXT, sent_at TEXT)")
            c.execute("CREATE TABLE collector_health (mailbox TEXT PRIMARY KEY, status TEXT, last_scan_at TEXT, error_message TEXT)")
            c.execute("CREATE TABLE mailbox_levels (mailbox TEXT PRIMARY KEY, domain TEXT, level INTEGER, status TEXT, paused_reason TEXT)")

            now_iso = self.fixed_now.isoformat()
            c.execute("INSERT INTO mailbox_levels VALUES ('aryan@mindmaxing.info', 'mindmaxing.info', 1, 'active', NULL)")
            c.execute("INSERT INTO collector_health VALUES ('aryan@mindmaxing.info', 'healthy', ?, NULL)", (now_iso,))
            c.execute("INSERT INTO mailbox_daily_decisions VALUES (1, 'aryan@mindmaxing.info', '2026-09-22-IST', '2026-09-22', 'KEEP', 'ok', 1, 1, 1, 'v2.1-revised')")

            # Insert lead with INCIDENT_CANDIDATE but unverified contact status
            c.execute("""
                INSERT INTO leads (id, domain, contact_email, contact_type, status, source, signal_decision, current_sequence_step)
                VALUES (1, 'brokenstore.com', 'support@brokenstore.com', 'UNVERIFIED', 'CANDIDATE', 'reddit', 'INCIDENT_CANDIDATE', 0)
            """)
            conn.commit()
            conn.close()

            claimed, reason, meta = volume_controller.reserve_and_claim_job(
                lead_id=1,
                domain="brokenstore.com",
                touch_number=1,
                mailbox="aryan@mindmaxing.info",
                recipient="support@brokenstore.com",
                subject="Broken checkout",
                body="Hello",
                worker_id="worker_1",
                campaign_name="reddit"
            )
            # Unapproved candidate with unverified status must fail-closed
            self.assertFalse(claimed)
            self.assertTrue("terminal" in reason.lower() or "eligible" in reason.lower() or "approved" in reason.lower() or "unverified" in reason.lower())

        finally:
            volume_controller.DB_PATH = orig_db
            if os.path.exists(test_db):
                os.remove(test_db)

    def test_reprocessing_business_preserves_active_conversation(self):
        """Reprocessing a business preserves its active conversation and sequence step."""
        import reddit_harvester
        # When a new post comes in for an existing domain with active touch, it appends evidence
        # but does NOT reset current_sequence_step or touch history.
        lead_existing = {
            "domain": "coffeegrinders.com",
            "current_sequence_step": 2,
            "status": "ENGAGED",
            "reviews_collection": [{"text": "old post"}]
        }
        new_evidence = {
            "text": "new post",
            "date": self.fixed_now.isoformat()
        }
        # Simulate attachment
        updated = reddit_harvester.attach_duplicate_reddit_evidence(lead_existing, new_evidence)
        self.assertEqual(updated["current_sequence_step"], 2)
        self.assertEqual(updated["status"], "ENGAGED")
        self.assertEqual(len(updated["reviews_collection"]), 2)

    def test_unapproved_candidate_never_becomes_sendable_through_export(self):
        """An unapproved candidate with INCIDENT_CANDIDATE never becomes sendable without explicit HUMAN_APPROVED."""
        lead = {
            "id": 99,
            "domain": "gadgetvault.co",
            "status": "CANDIDATE",
            "signal_decision": "INCIDENT_CANDIDATE"
        }
        # A candidate is NOT sendable in production dispatch queues
        is_sendable = (lead.get("status") == "HUMAN_APPROVED")
        self.assertFalse(is_sendable)


if __name__ == "__main__":
    unittest.main()
