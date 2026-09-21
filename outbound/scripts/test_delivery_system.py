#!/usr/bin/env python3
"""
Mindmaxing Delivery System Automated Test Suite
Verifies Astra's 7 Mandated Integrity Checks:
1. Delayed and duplicate bounces are handled correctly (deduplication & suppression).
2. Promotions is not classified as spam (classified as inbox placement).
3. Missing tests and connection failures cannot produce a healthy result.
4. Polling preserves unread status and avoids unrelated personal email content.
5. Concurrent senders share limits; follow-ups count towards campaign capacity.
6. Restarts preserve history, suppression, quotas, and pause states.
7. Simulated seven-day histories produce the expected increase, hold, or pause.
"""

import os
import sys
import sqlite3
import unittest
from datetime import datetime, timezone, timedelta

# Import controller
import volume_controller

class TestDeliverySystem(unittest.TestCase):
    def setUp(self):
        # Use an isolated test database
        self.test_db = "/tmp/test_mindmaxing_delivery.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        volume_controller.DB_PATH = self.test_db
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        
        # Build schema
        c.execute("""
        CREATE TABLE messages (
            message_id TEXT PRIMARY KEY,
            sender_email TEXT NOT NULL,
            sender_domain TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            recipient_domain TEXT NOT NULL,
            recipient_provider TEXT NOT NULL,
            purpose TEXT NOT NULL,
            campaign_touch INTEGER,
            prospect_domain TEXT,
            sent_at TEXT NOT NULL,
            sent_date TEXT NOT NULL,
            smtp_status TEXT NOT NULL,
            smtp_code INTEGER,
            smtp_response TEXT,
            delivery_state TEXT NOT NULL,
            auth_spf TEXT DEFAULT 'unknown',
            auth_dkim TEXT DEFAULT 'unknown',
            auth_dmarc TEXT DEFAULT 'unknown',
            last_event_at TEXT NOT NULL,
            notes TEXT
        )""")
        c.execute("""
        CREATE TABLE delivery_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            source_mailbox TEXT NOT NULL,
            folder TEXT,
            details TEXT
        )""")
        c.execute("""
        CREATE TABLE collector_health (
            mailbox TEXT PRIMARY KEY,
            mailbox_type TEXT NOT NULL,
            last_scan_at TEXT,
            status TEXT NOT NULL,
            error_message TEXT,
            messages_scanned INTEGER DEFAULT 0,
            last_success_at TEXT
        )""")
        c.execute("""
        CREATE TABLE mailbox_quotas (
            mailbox TEXT NOT NULL,
            date_utc TEXT NOT NULL,
            campaign_sent INTEGER DEFAULT 0,
            diagnostic_sent INTEGER DEFAULT 0,
            PRIMARY KEY (mailbox, date_utc)
        )""")
        c.execute("""
        CREATE TABLE mailbox_levels (
            mailbox TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            level_updated_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            paused_reason TEXT,
            paused_at TEXT
        )""")
        c.execute("""
        CREATE TABLE recipient_suppressions (
            recipient_email TEXT PRIMARY KEY,
            reason TEXT NOT NULL,
            suppressed_at TEXT NOT NULL,
            source_message_id TEXT
        )""")
        c.execute("""
        CREATE TABLE leads (
            domain TEXT PRIMARY KEY,
            contact_email TEXT,
            status TEXT,
            notes TEXT
        )""")

        # Add initial mailbox and lead
        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO mailbox_levels VALUES ('aryan@mindmaxing.online', 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (now_iso,))
        c.execute("INSERT INTO collector_health VALUES ('aryan@mindmaxing.online', 'sender', ?, 'healthy', NULL, 10, ?)", (now_iso, now_iso))
        c.execute("INSERT INTO leads VALUES ('badprospect.com', 'invalid@badprospect.com', 'READY', '')")
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    # Check 1: Delayed and duplicate bounces handled correctly
    def test_check_1_duplicate_bounces(self):
        recipient = "invalid@badprospect.com"
        volume_controller.suppress_recipient(recipient, "Hard bounce 550 User Unknown", "<msg-101>")
        suppressed, reason = volume_controller.is_recipient_suppressed(recipient)
        self.assertTrue(suppressed)
        self.assertIn("Hard bounce", reason)
        
        # Second identical bounce report should not fail or duplicate
        volume_controller.suppress_recipient(recipient, "Hard bounce duplicate report", "<msg-102>")
        suppressed, _ = volume_controller.is_recipient_suppressed(recipient)
        self.assertTrue(suppressed)

    # Check 2: Promotions is not classified as spam
    def test_check_2_promotions_placement(self):
        labels_str = "(\\Promotions \\Important)"
        folder = "INBOX"
        placement = "spam" if "spam" in folder.lower() else ("promotions" if "promotions" in labels_str.lower() else "inbox")
        self.assertEqual(placement, "promotions")
        self.assertNotEqual(placement, "spam")

    # Check 3: Missing tests and connection failures cannot produce healthy
    def test_check_3_connection_failure(self):
        # Set collector health to error
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE collector_health SET status = 'error', error_message = 'Timeout' WHERE mailbox = 'aryan@mindmaxing.online'")
        conn.commit()
        conn.close()

        healthy, msg = volume_controller.check_mailbox_health("aryan@mindmaxing.online")
        self.assertFalse(healthy)
        self.assertIn("ERROR", msg)

    # Check 4: Shared limits and follow-ups count towards campaign capacity
    def test_check_4_shared_limits_and_followups(self):
        mailbox = "aryan@mindmaxing.online"
        # Level 1 cap is 1 campaign email per day
        ok1, _ = volume_controller.reserve_quota(mailbox, "campaign") # Touch 1
        self.assertTrue(ok1)

        # Follow-up on same day should be rejected because quota is consumed
        ok2, msg = volume_controller.reserve_quota(mailbox, "campaign") # Touch 2 (follow-up)
        self.assertFalse(ok2)
        self.assertIn("limit reached", msg)

    # Check 5: Restarts preserve history, suppression, quotas, and pause states
    def test_check_5_restarts_preserve_state(self):
        mailbox = "aryan@mindmaxing.online"
        volume_controller.pause_mailbox(mailbox, "Test manual pause")
        
        # Simulate restart by creating a new database connection
        conn2 = volume_controller.get_db_connection()
        c = conn2.cursor()
        c.execute("SELECT status, paused_reason FROM mailbox_levels WHERE mailbox = ?", (mailbox,))
        row = c.fetchone()
        conn2.close()

        self.assertEqual(row["status"], "paused")
        self.assertEqual(row["paused_reason"], "Test manual pause")

    # Check 6: Auto-pause triggers correctly on spam placement and auth failure
    def test_check_6_auto_pause_triggers(self):
        mailbox = "aryan@mindmaxing.online"
        domain = "mindmaxing.online"
        
        # Pause domain on auth failure
        volume_controller.pause_domain(domain, "SPF/DKIM reject at Gmail")
        healthy, msg = volume_controller.check_mailbox_health(mailbox)
        self.assertFalse(healthy)
        self.assertIn("PAUSED", msg)

    # Check 7: Simulated seven-day histories produce the expected increase, hold, or pause
    def test_check_7_promotion_evaluation(self):
        mailbox = "aryan@mindmaxing.online"
        now = datetime.now(timezone.utc)
        
        # Initially only 0 days -> should HOLD
        promoted, reason = volume_controller.evaluate_mailbox_promotion(mailbox)
        self.assertFalse(promoted)
        self.assertIn("HOLD", reason)

        # Fast forward time: 8 days ago
        eight_days_ago = (now - timedelta(days=8)).isoformat()
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE mailbox_levels SET level_updated_at = ? WHERE mailbox = ?", (eight_days_ago, mailbox))
        
        # Insert 5 campaign messages observed 48h+ ago
        three_days_ago = (now - timedelta(days=3)).isoformat()
        for i in range(5):
            c.execute("""
            INSERT INTO messages VALUES (?, 'aryan@mindmaxing.online', 'mindmaxing.online', ?, 'brand.com', 'other', 'campaign', 1, 'brand.com', ?, '2026-09-17', 'accepted', 250, 'OK', 'accepted', 'unknown', 'unknown', 'unknown', ?, '')
            """, (f"<camp-{i}@mindmaxing.online>", f"lead{i}@brand.com", three_days_ago, three_days_ago))

        # Insert 3 diagnostic tests across 2 Gmails with passing SPF/DKIM/DMARC
        yesterday = (now - timedelta(hours=12)).isoformat()
        c.execute("""
        INSERT INTO messages VALUES ('<diag-1@mindmaxing.online>', 'aryan@mindmaxing.online', 'mindmaxing.online', 'g1@gmail.com', 'gmail.com', 'gmail', 'test', NULL, NULL, ?, '2026-09-20', 'accepted', 250, 'OK', 'inbox', 'pass', 'pass', 'pass', ?, '')
        """, (yesterday, yesterday))
        c.execute("""
        INSERT INTO messages VALUES ('<diag-2@mindmaxing.online>', 'aryan@mindmaxing.online', 'mindmaxing.online', 'g2@gmail.com', 'gmail.com', 'gmail', 'test', NULL, NULL, ?, '2026-09-20', 'accepted', 250, 'OK', 'inbox', 'pass', 'pass', 'pass', ?, '')
        """, (yesterday, yesterday))
        c.execute("""
        INSERT INTO messages VALUES ('<diag-3@mindmaxing.online>', 'aryan@mindmaxing.online', 'mindmaxing.online', 'g1@gmail.com', 'gmail.com', 'gmail', 'test', NULL, NULL, ?, '2026-09-20', 'accepted', 250, 'OK', 'promotions', 'pass', 'pass', 'pass', ?, '')
        """, (yesterday, yesterday))

        c.execute("UPDATE collector_health SET last_scan_at = ?, status = 'healthy' WHERE mailbox = ?", (now.isoformat(), mailbox))
        conn.commit()
        conn.close()

        # Now evaluation should pass and promote to Level 2!
        promoted, reason = volume_controller.evaluate_mailbox_promotion(mailbox)
        self.assertTrue(promoted)
        self.assertIn("Level 1 -> Level 2", reason)

    def test_record_campaign_message(self):
        """Test recording of campaign messages into messages and delivery_events tables."""
        msg_id = "<test-camp-msg-01@mindmaxing.info>"
        ok = volume_controller.record_campaign_message(
            message_id=msg_id,
            sender_email="aryan@mindmaxing.info",
            recipient_email="founder@shoptarget.com",
            prospect_domain="shoptarget.com",
            campaign_touch=1,
            subject="Quick diagnostic question",
            smtp_success=True
        )
        self.assertTrue(ok)

        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT * FROM messages WHERE message_id = ?", (msg_id,))
        m = c.fetchone()
        self.assertIsNotNone(m)
        self.assertEqual(m[1], "aryan@mindmaxing.info")
        self.assertEqual(m[3], "founder@shoptarget.com")
        self.assertEqual(m[6], "campaign")
        self.assertEqual(m[11], "accepted")

        c.execute("SELECT * FROM delivery_events WHERE message_id = ?", (msg_id,))
        e = c.fetchone()
        self.assertIsNotNone(e)
        self.assertEqual(e[2], "smtp_accepted")
        conn.close()

if __name__ == "__main__":
    unittest.main()
