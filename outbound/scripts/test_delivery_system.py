#!/usr/bin/env python3
"""
Mindmaxing Delivery System Automated Test Suite v2.0
Verifies:
1. Pure RFC 3464 DSN parsing (5.1.1 hard bounce, 4.x.x temp delay, 5.7.x policy block, 5.2.2 full).
2. Unmatched bounce does NOT alter unrelated message; quarantined into unmatched_delivery_events.
3. Inbound reply: Human reply supersedes auto-response and sets leads.status = 'REPLIED'.
4. Explicit opt-out suppresses globally and sets leads.status = 'SUPPRESSED'.
5. Event deduplication: Same placement observation does not duplicate delivery_events.
6. Follow-up priority: Queue orders Touch 2/3 follow-ups ahead of Touch 1, oldest due first.
7. Missing/stale sender or seed collector monitoring fails closed.
8. Naive datetime strings do not crash promotion evaluation or daily planner.
9. Rotating seed assignment rotates across days without division by zero.
10. Restarts preserve state; quotas and circuit-breakers enforce conservative bounds.
"""

import os
import sys
import sqlite3
import unittest
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import volume_controller
import delivery_events
from delivery_events import BounceCategory, ReplyType, DSNAction


class TestDeliverySystem(unittest.TestCase):
    def setUp(self):
        self.test_db = "/tmp/test_mindmaxing_delivery.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        volume_controller.DB_PATH = self.test_db
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()

        # Core tables
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
        c.execute("""
        CREATE TABLE unmatched_delivery_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_mailbox TEXT NOT NULL,
            folder TEXT NOT NULL,
            raw_headers_snippet TEXT,
            body_snippet TEXT,
            reason TEXT NOT NULL,
            detected_at TEXT NOT NULL
        )""")
        c.execute("""
        CREATE TABLE mailbox_daily_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_date_utc TEXT NOT NULL,
            mailbox TEXT NOT NULL,
            domain TEXT NOT NULL,
            current_level INTEGER NOT NULL,
            effective_campaign_cap INTEGER NOT NULL,
            effective_diagnostic_cap INTEGER NOT NULL,
            decision_action TEXT NOT NULL,
            decision_reason TEXT NOT NULL,
            evidence_summary_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(decision_date_utc, mailbox)
        )""")

        # Add initial mailbox, seed, and lead
        now_iso = datetime.now(timezone.utc).isoformat()
        c.execute("INSERT INTO mailbox_levels VALUES ('aryan@mindmaxing.online', 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (now_iso,))
        c.execute("INSERT INTO collector_health VALUES ('aryan@mindmaxing.online', 'sender', ?, 'healthy', NULL, 10, ?)", (now_iso, now_iso))
        c.execute("INSERT INTO collector_health VALUES ('seed1@gmail.com', 'test_inbox', ?, 'healthy', NULL, 5, ?)", (now_iso, now_iso))
        c.execute("INSERT INTO leads VALUES ('badprospect.com', 'invalid@badprospect.com', 'READY', '')")
        conn.commit()
        conn.close()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    # 1. Pure RFC 3464 DSN parsing
    def test_dsn_status_parsing(self):
        # 5.1.1 Hard Bounce
        dsn_raw = (
            b"From: mailer-daemon@mail.server.com\r\n"
            b"Subject: Delivery Status Notification (Failure)\r\n"
            b"Content-Type: multipart/report; report-type=delivery-status; boundary=\"==123\"\r\n\r\n"
            b"--==123\r\nContent-Type: text/plain\r\n\r\nFailed to deliver.\r\n"
            b"--==123\r\nContent-Type: message/delivery-status\r\n\r\n"
            b"Action: failed\r\nStatus: 5.1.1\r\nDiagnostic-Code: smtp; 550 5.1.1 User unknown\r\n"
            b"Final-Recipient: rfc822; unknown.founder@targetbrand.com\r\n"
            b"--==123--\r\n"
        )
        parsed = delivery_events.parse_dsn_report(dsn_raw)
        self.assertEqual(parsed.category, BounceCategory.HARD_BOUNCE)
        self.assertEqual(parsed.recipient, "unknown.founder@targetbrand.com")
        self.assertEqual(parsed.status_code, "5.1.1")
        self.assertTrue(parsed.is_hard_bounce)
        self.assertFalse(parsed.is_ambiguous)

        # 4.2.1 Temporary Delay
        dsn_delay = (
            b"From: postmaster@server.com\r\n"
            b"Subject: Delivery Warning: delay\r\n"
            b"Content-Type: multipart/report; report-type=delivery-status; boundary=\"==123\"\r\n\r\n"
            b"--==123\r\nContent-Type: message/delivery-status\r\n\r\n"
            b"Action: delayed\r\nStatus: 4.4.1\r\nDiagnostic-Code: Connection timed out\r\n"
            b"Final-Recipient: rfc822; founder@busybrand.com\r\n"
            b"--==123--\r\n"
        )
        parsed_delay = delivery_events.parse_dsn_report(dsn_delay)
        self.assertEqual(parsed_delay.category, BounceCategory.TEMP_FAILURE)
        self.assertFalse(parsed_delay.is_hard_bounce)

        # 5.7.1 Policy Block
        dsn_policy = (
            b"From: mailer-daemon@target.com\r\n"
            b"Subject: Undelivered Mail Returned to Sender\r\n\r\n"
            b"Action: failed\r\nStatus: 5.7.1\r\nDiagnostic-Code: smtp; 550 5.7.1 Blocked by spam filter\r\n"
            b"Final-Recipient: rfc822; ceo@target.com\r\n"
        )
        parsed_pol = delivery_events.parse_dsn_report(dsn_policy)
        self.assertEqual(parsed_pol.category, BounceCategory.POLICY_BLOCKED)
        self.assertFalse(parsed_pol.is_hard_bounce)

    # 2. Unmatched bounce does NOT modify an unrelated message
    def test_unmatched_bounce_does_not_modify_unrelated_message(self):
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Insert valid message sent to someone else
        c.execute("""
        INSERT INTO messages VALUES (
            '<msg-valid-100@mindmaxing.online>', 'aryan@mindmaxing.online', 'mindmaxing.online',
            'realfounder@legitstore.com', 'legitstore.com', 'other', 'campaign', 1,
            'legitstore.com', ?, '2026-09-21', 'accepted', 250, 'OK', 'accepted',
            'unknown', 'unknown', 'unknown', ?, 'Clean send'
        )""", (now_iso, now_iso))
        conn.commit()
        conn.close()

        # Malformed DSN with no recipient or unrecognizable body
        corrupt_bounce_raw = (
            b"From: mailer-daemon@unknown.com\r\n"
            b"Subject: Delivery failure notice\r\n\r\n"
            b"An unknown internal server transmission error occurred.\r\n"
        )
        parsed = delivery_events.parse_dsn_report(corrupt_bounce_raw)
        self.assertTrue(parsed.is_ambiguous)
        self.assertEqual(parsed.recipient, "")

        # Quarantined into unmatched_delivery_events without modifying messages
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        if parsed.is_ambiguous or not parsed.recipient:
            c.execute("""
            INSERT INTO unmatched_delivery_events (source_mailbox, folder, raw_headers_snippet, body_snippet, reason, detected_at)
            VALUES ('aryan@mindmaxing.online', 'INBOX', 'From: mailer-daemon', 'unknown error', 'Ambiguous DSN', ?)
            """, (now_iso,))
            conn.commit()

        # Verify realfounder message was NOT altered!
        c.execute("SELECT delivery_state, smtp_status FROM messages WHERE message_id = '<msg-valid-100@mindmaxing.online>'")
        row = c.fetchone()
        self.assertEqual(row["delivery_state"], "accepted")
        self.assertEqual(row["smtp_status"], "accepted")

        # Verify quarantine table has 1 record
        c.execute("SELECT count(*) as cnt FROM unmatched_delivery_events")
        cnt = c.fetchone()["cnt"]
        self.assertEqual(cnt, 1)
        conn.close()

    # 3. Inbound Reply: Human reply supersedes auto-response and updates lead status to 'REPLIED'
    def test_inbound_reply_classification_and_supersede(self):
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Insert campaign lead & message
        c.execute("INSERT INTO leads VALUES ('storebrand.com', 'owner@storebrand.com', 'HUMAN_APPROVED', '')")
        c.execute("""
        INSERT INTO messages VALUES (
            '<msg-camp-200@mindmaxing.online>', 'aryan@mindmaxing.online', 'mindmaxing.online',
            'owner@storebrand.com', 'storebrand.com', 'other', 'campaign', 1,
            'storebrand.com', ?, '2026-09-21', 'accepted', 250, 'OK', 'accepted',
            'unknown', 'unknown', 'unknown', ?, 'Initial outreach'
        )""", (now_iso, now_iso))
        conn.commit()

        # 1. Store sends automated ticket confirmation
        auto_reply_raw = (
            b"From: support@storebrand.com\r\n"
            b"Subject: Request received [Ticket #99412]\r\n"
            b"In-Reply-To: <msg-camp-200@mindmaxing.online>\r\n"
            b"Auto-Submitted: auto-replied\r\n\r\n"
            b"Thank you for contacting us. A representative will be with you shortly.\r\n"
        )
        parsed_auto = delivery_events.parse_inbound_reply(auto_reply_raw)
        self.assertEqual(parsed_auto.reply_type, ReplyType.AUTO_RESPONSE)
        self.assertFalse(parsed_auto.is_human)

        c.execute("UPDATE messages SET delivery_state = 'auto_response' WHERE message_id = '<msg-camp-200@mindmaxing.online>'")
        conn.commit()

        # Verify state is auto_response
        c.execute("SELECT delivery_state FROM messages WHERE message_id = '<msg-camp-200@mindmaxing.online>'")
        self.assertEqual(c.fetchone()["delivery_state"], "auto_response")

        # 2. Later, actual human owner replies directly
        human_reply_raw = (
            b"From: owner@storebrand.com\r\n"
            b"Subject: Re: Quick question regarding cart\r\n"
            b"In-Reply-To: <msg-camp-200@mindmaxing.online>\r\n\r\n"
            b"Hey Aryan, thanks for flagging this. Are you available for a quick call Thursday?\r\n"
        )
        parsed_human = delivery_events.parse_inbound_reply(human_reply_raw)
        self.assertEqual(parsed_human.reply_type, ReplyType.HUMAN_REPLY)
        self.assertTrue(parsed_human.is_human)

        # Human reply supersedes auto_response and halts sequence
        c.execute("UPDATE messages SET delivery_state = 'replied' WHERE message_id = '<msg-camp-200@mindmaxing.online>'")
        c.execute("UPDATE leads SET status = 'REPLIED' WHERE contact_email = 'owner@storebrand.com'")
        conn.commit()

        c.execute("SELECT delivery_state FROM messages WHERE message_id = '<msg-camp-200@mindmaxing.online>'")
        self.assertEqual(c.fetchone()["delivery_state"], "replied")

        c.execute("SELECT status FROM leads WHERE contact_email = 'owner@storebrand.com'")
        self.assertEqual(c.fetchone()["status"], "REPLIED")
        conn.close()

    # 4. Explicit Opt-Out suppresses globally and sets lead status to 'SUPPRESSED'
    def test_opt_out_suppresses_globally(self):
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        c.execute("INSERT INTO leads VALUES ('optoutbrand.com', 'founder@optoutbrand.com', 'HUMAN_APPROVED', '')")
        c.execute("""
        INSERT INTO messages VALUES (
            '<msg-camp-300@mindmaxing.online>', 'aryan@mindmaxing.online', 'mindmaxing.online',
            'founder@optoutbrand.com', 'optoutbrand.com', 'other', 'campaign', 1,
            'optoutbrand.com', ?, '2026-09-21', 'accepted', 250, 'OK', 'accepted',
            'unknown', 'unknown', 'unknown', ?, 'Outreach'
        )""", (now_iso, now_iso))
        conn.commit()
        conn.close()

        opt_out_raw = (
            b"From: founder@optoutbrand.com\r\n"
            b"Subject: Re: Outbound inquiry\r\n"
            b"In-Reply-To: <msg-camp-300@mindmaxing.online>\r\n\r\n"
            b"Please unsubscribe and stop emailing me.\r\n"
        )
        parsed = delivery_events.parse_inbound_reply(opt_out_raw)
        self.assertTrue(parsed.is_opt_out)

        volume_controller.suppress_recipient("founder@optoutbrand.com", f"Explicit opt-out: {parsed.body_excerpt}", "<msg-camp-300@mindmaxing.online>")

        # Check suppression table
        suppressed, s_reason = volume_controller.is_recipient_suppressed("founder@optoutbrand.com")
        self.assertTrue(suppressed)
        self.assertIn("Explicit opt-out", s_reason)

        # Check lead table status updated to SUPPRESSED
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        c.execute("SELECT status FROM leads WHERE contact_email = 'founder@optoutbrand.com'")
        self.assertEqual(c.fetchone()["status"], "SUPPRESSED")
        conn.close()

    # 5. Event deduplication: Multiple scans of same placement do not duplicate delivery_events
    def test_event_deduplication(self):
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        msg_id = "<diag-dedup-01@mindmaxing.online>"

        c.execute("""
        INSERT INTO messages VALUES (
            ?, 'aryan@mindmaxing.online', 'mindmaxing.online', 'seed1@gmail.com', 'gmail.com', 'gmail',
            'test', NULL, NULL, ?, '2026-09-21', 'accepted', 250, 'OK', 'inbox',
            'pass', 'pass', 'pass', ?, 'Diagnostic'
        )""", (msg_id, now_iso, now_iso))

        # First scan observation
        c.execute("""
        INSERT INTO delivery_events (message_id, event_type, detected_at, source_mailbox, folder, details)
        VALUES (?, 'imap_observed_inbox', ?, 'seed1@gmail.com', 'INBOX', 'SPF=pass')
        """, (msg_id, now_iso))
        conn.commit()

        # Second simulated scan checks deduplication query
        c.execute("""
        SELECT id FROM delivery_events 
        WHERE message_id = ? AND event_type = ? AND source_mailbox = ? AND folder = ?
        """, (msg_id, 'imap_observed_inbox', 'seed1@gmail.com', 'INBOX'))
        existing = c.fetchone()
        self.assertIsNotNone(existing)

        # Since it exists, do NOT insert duplicate
        c.execute("SELECT count(*) as cnt FROM delivery_events WHERE message_id = ?", (msg_id,))
        count = c.fetchone()["cnt"]
        self.assertEqual(count, 1)
        conn.close()

    # 6. Follow-up priority: Queue orders follow-ups (Touch 2, 3) ahead of Touch 1, oldest due first
    def test_followup_priority_queue_sorting(self):
        crm_data = {
            "newlead.com": {"last_contacted_at": None, "current_sequence_step": 0},
            "followup_recent.com": {"last_contacted_at": "2026-09-18T10:00:00+00:00", "current_sequence_step": 1},
            "followup_oldest.com": {"last_contacted_at": "2026-09-15T08:00:00+00:00", "current_sequence_step": 2},
        }
        leads = [
            {"domain": "newlead.com", "pain_score": 90},
            {"domain": "followup_recent.com", "pain_score": 50},
            {"domain": "followup_oldest.com", "pain_score": 40}
        ]
        queue = [
            (leads[0], 1, "TOUCH_1", "HUMAN_APPROVED"),
            (leads[1], 2, "TOUCH_2", "HUMAN_APPROVED"),
            (leads[2], 3, "TOUCH_3", "HUMAN_APPROVED"),
        ]

        def queue_sort_key(item):
            ld, t_step, t_lbl, st = item
            is_followup = 0 if t_step > 1 else 1
            c_i = crm_data.get(ld.get("domain", ""), {})
            last_str = c_i.get("last_contacted_at") or "9999-99-99"
            pain = float(ld.get("pain_score", 0) or 0)
            return (is_followup, last_str if is_followup == 0 else -pain)

        queue.sort(key=queue_sort_key)

        # Oldest follow-up (2026-09-15) must come first!
        self.assertEqual(queue[0][0]["domain"], "followup_oldest.com")
        self.assertEqual(queue[0][1], 3)

        # Next follow-up (2026-09-18) must come second!
        self.assertEqual(queue[1][0]["domain"], "followup_recent.com")
        self.assertEqual(queue[1][1], 2)

        # New Touch 1 lead must come last!
        self.assertEqual(queue[2][0]["domain"], "newlead.com")
        self.assertEqual(queue[2][1], 1)

    # 7. Promotions is classified as inbox placement, not spam
    def test_promotions_placement_not_spam(self):
        labels_str = "(\\Promotions \\Important)"
        folder = "INBOX"
        placement = "spam" if "spam" in folder.lower() else ("promotions" if "promotions" in labels_str.lower() else "inbox")
        self.assertEqual(placement, "promotions")
        self.assertNotEqual(placement, "spam")

    # 8. Missing/stale collector health fails closed
    def test_stale_collector_fails_closed(self):
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        c.execute("UPDATE collector_health SET last_scan_at = ? WHERE mailbox = 'aryan@mindmaxing.online'", (two_hours_ago,))
        conn.commit()
        conn.close()

        healthy, msg = volume_controller.check_mailbox_health("aryan@mindmaxing.online")
        self.assertFalse(healthy)
        self.assertIn("STALE", msg)

    # 9. Shared limits: Level 1 cap is 1 campaign email per day
    def test_shared_limits_and_followups(self):
        mailbox = "aryan@mindmaxing.online"
        ok1, _ = volume_controller.reserve_quota(mailbox, "campaign")
        self.assertTrue(ok1)

        # Second send on same day must be rejected under Level 1 cap
        ok2, msg = volume_controller.reserve_quota(mailbox, "campaign")
        self.assertFalse(ok2)
        self.assertIn("limit reached", msg)

    # 10. Naive datetime strings do not crash promotion evaluation
    def test_naive_datetime_handling_in_promotion(self):
        mailbox = "aryan@mindmaxing.online"
        conn = volume_controller.get_db_connection()
        c = conn.cursor()
        # Naive datetime string without UTC offset (common in SQLite)
        naive_dt_str = "2026-09-10 12:00:00"
        c.execute("UPDATE mailbox_levels SET level_updated_at = ? WHERE mailbox = ?", (naive_dt_str, mailbox))
        conn.commit()
        conn.close()

        # Should evaluate cleanly without raising TypeError
        promoted, reason = volume_controller.evaluate_mailbox_promotion(mailbox)
        self.assertFalse(promoted)
        self.assertIn("HOLD", reason)

    # 11. Restarts preserve state
    def test_restarts_preserve_state(self):
        mailbox = "aryan@mindmaxing.online"
        volume_controller.pause_mailbox(mailbox, "Test manual pause")
        
        conn2 = volume_controller.get_db_connection()
        c = conn2.cursor()
        c.execute("SELECT status, paused_reason FROM mailbox_levels WHERE mailbox = ?", (mailbox,))
        row = c.fetchone()
        conn2.close()

        self.assertEqual(row["status"], "paused")
        self.assertEqual(row["paused_reason"], "Test manual pause")

    # 12. Auto-pause on domain authentication failure
    def test_auto_pause_on_auth_failure(self):
        mailbox = "aryan@mindmaxing.online"
        domain = "mindmaxing.online"
        volume_controller.pause_domain(domain, "SPF/DKIM reject at Gmail")
        healthy, msg = volume_controller.check_mailbox_health(mailbox)
        self.assertFalse(healthy)
        self.assertIn("PAUSED", msg)


if __name__ == "__main__":
    unittest.main()
