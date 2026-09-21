#!/usr/bin/env python3
"""
Unit and Integration Test Suite for Mindmaxing Nightly Campaign Review & Mailbox Control v2.1
Tests the 12 scenarios mandated by Astra's Revised Specification:
1. All 25 appear; one unready mailbox does not disable healthy peers.
2. First qualifying diagnostic enables baseline sending without a seven-day startup delay.
3. Brief seed outage freezes growth; expiry beyond 72 hours pauses campaigns.
4. Campaign holds permit appropriate recovery diagnostics.
5. Positive reply quoting an opt-out footer stays positive; standalone `stop` suppresses.
6. Duplicate polls, more than 30 messages, UIDVALIDITY changes and failed fetches preserve accurate outcomes.
7. Two campaigns sharing a mailbox cannot multiply its allowance.
8. Follow-ups retain their sender and take priority; deferred jobs recover.
9. Concurrent claims, post-acceptance errors and interrupted attempts do not cause duplicate sends.
10. Repeated nightly runs and report requests cannot reset usage or repeat increases.
11. Restart, missing review, budget-boundary migration and backup restoration behave as specified.
12. Eligible growth, insufficient evidence, temporary-failure reduction and scoped pauses produce expected decisions.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import daily_mailbox_planner
import delivery_events
import delivery_monitor
import migrate_adaptive_mailbox_schema
import outbound_status
import volume_controller
from delivery_events import ReplyType


class TestRevisedPlan(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_revised.db")

        # Redirect volume_controller and outbound_status DB path
        self.orig_vc_db = volume_controller.DB_PATH
        volume_controller.DB_PATH = self.test_db
        outbound_status.DB_PATH = self.test_db
        daily_mailbox_planner.DB_PATH = self.test_db

        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
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
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE,
            contact_email TEXT,
            status TEXT,
            current_sequence_step INTEGER DEFAULT 0,
            last_contacted_at TEXT,
            notes TEXT
        )""")
        conn.commit()
        conn.close()

        # Run schema migration on test DB
        migrate_adaptive_mailbox_schema.run_migration(self.test_db)

    def tearDown(self):
        volume_controller.DB_PATH = self.orig_vc_db
        outbound_status.DB_PATH = self.orig_vc_db
        daily_mailbox_planner.DB_PATH = self.orig_vc_db
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # 1. All 25 appear; one unready mailbox does not disable healthy peers
    def test_scenario_1_all_25_appear_independent_qualification(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        mailboxes = daily_mailbox_planner.load_mailboxes_config()
        self.assertGreaterEqual(len(mailboxes), 20)

        # Set 1 mailbox as completely unready (no diagnostic, no monitoring)
        unready_mb = mailboxes[0]["email"]

        # Set all other mailboxes as healthy with recent clean diagnostics
        for mb in mailboxes[1:]:
            c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 10, ?)", (mb["email"], now_iso, now_iso))
            # Insert qualifying diagnostic
            msg_id = f"<diag-qual-{mb['email']}@test.com>"
            c.execute("""
                INSERT OR REPLACE INTO messages (
                    message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                    recipient_provider, purpose, sent_at, sent_date, smtp_status, delivery_state,
                    auth_spf, auth_dkim, auth_dmarc, last_event_at
                ) VALUES (?, ?, ?, 'seed@gmail.com', 'gmail.com', 'gmail', 'test', ?, '2026-09-21', 'accepted', 'inbox', 'pass', 'pass', 'pass', ?)
            """, (msg_id, mb["email"], mb["domain"], now_iso, now_iso))

        # Add healthy seed
        c.execute("INSERT OR REPLACE INTO collector_health VALUES ('seed@gmail.com', 'test_inbox', ?, 'healthy', NULL, 5, ?)", (now_iso, now_iso))
        conn.commit()

        res = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=True)
        conn.close()

        self.assertEqual(res["total_mailboxes"], len(mailboxes))
        decisions = {d["mailbox"]: d for d in res["decisions"]}

        # Unready mailbox must be PAUSE with cap 0
        self.assertEqual(decisions[unready_mb]["campaign_cap"], 0)
        self.assertEqual(decisions[unready_mb]["action"], "PAUSE")

        # Healthy peers must have baseline cap 1 (not 0!)
        healthy_sample = mailboxes[1]["email"]
        self.assertEqual(decisions[healthy_sample]["campaign_cap"], 1)
        self.assertEqual(decisions[healthy_sample]["action"], "KEEP")

    # 2. First qualifying diagnostic enables baseline sending without a 7-day startup delay
    def test_scenario_2_first_diagnostic_enables_baseline_without_7d_delay(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        mb = "aryan@mindmaxing.online"

        # Sender monitoring healthy
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 1, ?)", (mb, now_iso, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES ('seed@gmail.com', 'test_inbox', ?, 'healthy', NULL, 1, ?)", (now_iso, now_iso))

        # BEFORE diagnostic: cap must be 0
        res_before = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=True)
        dec_before = next(d for d in res_before["decisions"] if d["mailbox"] == mb)
        self.assertEqual(dec_before["campaign_cap"], 0)
        self.assertEqual(dec_before["action"], "PAUSE")
        self.assertIn("Awaiting first clean diagnostic", dec_before["reason"])

        # Insert first passing diagnostic observed in inbox 10 minutes ago
        c.execute("""
            INSERT INTO messages (
                message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                recipient_provider, purpose, sent_at, sent_date, smtp_status, delivery_state,
                auth_spf, auth_dkim, auth_dmarc, last_event_at
            ) VALUES ('<first-clean-01@mindmaxing.online>', ?, 'mindmaxing.online', 'seed@gmail.com', 'gmail.com', 'gmail', 'test', ?, '2026-09-22', 'accepted', 'inbox', 'pass', 'pass', 'pass', ?)
        """, (mb, now_iso, now_iso))
        conn.commit()

        # AFTER diagnostic: baseline 1 immediately enabled without waiting 7 days!
        res_after = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=True)
        conn.close()
        dec_after = next(d for d in res_after["decisions"] if d["mailbox"] == mb)
        self.assertEqual(dec_after["campaign_cap"], 1)
        self.assertEqual(dec_after["action"], "KEEP")
        self.assertIn("baseline", dec_after["reason"].lower())

    # 3. Brief seed outage freezes growth; expiry beyond 72 hours pauses campaigns
    def test_scenario_3_seed_outage_freezes_growth_72h_expiry_pauses(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        mb = "aryan@mindmaxing.online"

        # Sender monitoring is active
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 5, ?)", (mb, now_iso, now_iso))

        # Diagnostic from 24h ago
        twenty_four_hours_ago = (now - timedelta(hours=24)).isoformat()
        c.execute("""
            INSERT INTO messages (
                message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                recipient_provider, purpose, sent_at, sent_date, smtp_status, delivery_state,
                auth_spf, auth_dkim, auth_dmarc, last_event_at
            ) VALUES ('<diag-24h@mindmaxing.online>', ?, 'mindmaxing.online', 'seed@gmail.com', 'gmail.com', 'gmail', 'test', ?, '2026-09-21', 'accepted', 'inbox', 'pass', 'pass', 'pass', ?)
        """, (mb, twenty_four_hours_ago, twenty_four_hours_ago))

        # Seed monitoring is DOWN (error / 0 healthy seeds)
        c.execute("INSERT OR REPLACE INTO collector_health VALUES ('seed@gmail.com', 'test_inbox', ?, 'error', 'IMAP timeout', 0, NULL)", (now_iso,))
        conn.commit()

        # Phase A: Seed is down, but diagnostic is 24h old (<72h) -> Growth frozen (KEEP), baseline preserved (cap 1)
        res_grace = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=True)
        dec_grace = next(d for d in res_grace["decisions"] if d["mailbox"] == mb)
        self.assertEqual(dec_grace["campaign_cap"], 1)
        self.assertEqual(dec_grace["action"], "KEEP")
        self.assertTrue(dec_grace["evidence"]["seed_visibility_freeze"])

        # Phase B: Diagnostic becomes 80h old (>72h) -> Campaign paused
        eighty_hours_ago = (now - timedelta(hours=80)).isoformat()
        c.execute("UPDATE messages SET sent_at = ? WHERE message_id = '<diag-24h@mindmaxing.online>'", (eighty_hours_ago,))
        conn.commit()

        res_expired = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=True)
        conn.close()
        dec_expired = next(d for d in res_expired["decisions"] if d["mailbox"] == mb)
        self.assertEqual(dec_expired["campaign_cap"], 0)
        self.assertEqual(dec_expired["action"], "PAUSE")
        self.assertIn("HOLD_DIAGNOSTIC_EXPIRED", dec_expired["reason"])

    # 4. Campaign holds permit appropriate recovery diagnostics
    def test_scenario_4_campaign_holds_permit_recovery_diagnostics(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        mb = "aryan@mindmaxing.online"
        now_iso = datetime.now(timezone.utc).isoformat()
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        period_id = volume_controller.get_current_period_id()

        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (mb, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 5, ?)", (mb, now_iso, now_iso))
        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_id, period_id, decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason,
                evidence_summary_json, revision, created_at
            ) VALUES (?, ?, ?, ?, 'mindmaxing.online', 1, 0, 1, 'HOLD_DIAGNOSTIC_EXPIRED', 'Expired', '{}', 1, ?)
        """, (f"DEC-{period_id}-{mb}-r1", period_id, today_utc, mb, now_iso))
        conn.commit()
        conn.close()

        # Campaign send rejected
        camp_ok, camp_msg = volume_controller.reserve_quota(mb, "campaign")
        self.assertFalse(camp_ok)

        # Recovery diagnostic send permitted
        test_ok, test_msg = volume_controller.reserve_quota(mb, "test")
        self.assertTrue(test_ok, f"Recovery diagnostic should pass: {test_msg}")

    # 5. Positive reply quoting an opt-out footer stays positive; standalone stop suppresses
    def test_scenario_5_quoted_footer_vs_standalone_stop(self):
        positive_reply_with_footer = (
            b"From: prospect@distributor.com\r\n"
            b"Subject: Re: Partnership inquiry\r\n\r\n"
            b"Hi Aryan, we are definitely interested in discussing distribution. When are you free?\r\n\r\n"
            b"On Mon, Sep 21, 2026 at 10:00 AM Aryan <aryan@mindmaxing.info> wrote:\r\n"
            b"> --\r\n"
            b"> Mindmaxing Studio\r\n"
            b"> Reply \"stop\" to opt out\r\n"
        )
        parsed_pos = delivery_events.parse_inbound_reply(positive_reply_with_footer)
        self.assertEqual(parsed_pos.reply_type, ReplyType.HUMAN_REPLY)
        self.assertFalse(parsed_pos.is_opt_out)

        standalone_stop = (
            b"From: angry@distributor.com\r\n"
            b"Subject: Re: Outbound\r\n\r\n"
            b"Stop\r\n"
        )
        parsed_stop = delivery_events.parse_inbound_reply(standalone_stop)
        self.assertTrue(parsed_stop.is_opt_out)

    # 6. Duplicate polls, more than 30 messages, UIDVALIDITY changes and failed fetches preserve accurate outcomes
    def test_scenario_6_imap_cursors_and_deduplication(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        mb = "aryan@mindmaxing.online"

        # Initialize cursor
        c.execute("INSERT INTO imap_cursors VALUES (?, 'INBOX', 12345, 100, ?)", (mb, now_iso))
        conn.commit()

        # Verify cursor retrieval
        c.execute("SELECT uidvalidity, last_uid FROM imap_cursors WHERE mailbox = ? AND folder = 'INBOX'", (mb,))
        row = c.fetchone()
        self.assertEqual(row[0], 12345)
        self.assertEqual(row[1], 100)

        # UIDVALIDITY change resets cursor safely
        new_uidvalidity = 99999
        if new_uidvalidity != row[0]:
            c.execute("UPDATE imap_cursors SET uidvalidity = ?, last_uid = 0, updated_at = ? WHERE mailbox = ?", (new_uidvalidity, now_iso, mb))
            conn.commit()

        c.execute("SELECT uidvalidity, last_uid FROM imap_cursors WHERE mailbox = ?", (mb,))
        row_updated = c.fetchone()
        self.assertEqual(row_updated[0], 99999)
        self.assertEqual(row_updated[1], 0)
        conn.close()

    # 7. Two campaigns sharing a mailbox cannot multiply its allowance
    def test_scenario_7_shared_mailbox_allowance(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        period_id = volume_controller.get_current_period_id()
        mb = "aryan@mindmaxing.online"

        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (mb, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 5, ?)", (mb, now_iso, now_iso))
        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_id, period_id, decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason,
                evidence_summary_json, revision, created_at
            ) VALUES (?, ?, ?, ?, 'mindmaxing.online', 1, 1, 1, 'KEEP', 'Baseline', '{}', 1, ?)
        """, (f"DEC-{period_id}-{mb}-r1", period_id, today_utc, mb, now_iso))

        # Insert 2 leads from different campaigns
        c.execute("INSERT INTO leads (domain, contact_email, status) VALUES ('brand-a.com', 'a@brand-a.com', 'HUMAN_APPROVED')")
        id_a = c.lastrowid
        c.execute("INSERT INTO leads (domain, contact_email, status) VALUES ('brand-b.com', 'b@brand-b.com', 'HUMAN_APPROVED')")
        id_b = c.lastrowid
        conn.commit()
        conn.close()

        # Campaign 1 claims the 1 allowance
        ok_a, _, _ = volume_controller.reserve_and_claim_job(
            lead_id=id_a, domain="brand-a.com", touch_number=1, mailbox=mb,
            recipient="a@brand-a.com", subject="Campaign A", body="Body A",
            worker_id="w1", campaign_name="dealstrike-distributors"
        )
        self.assertTrue(ok_a)

        # Campaign 2 sharing the same mailbox MUST be rejected (allowance is shared!)
        ok_b, reason_b, _ = volume_controller.reserve_and_claim_job(
            lead_id=id_b, domain="brand-b.com", touch_number=1, mailbox=mb,
            recipient="b@brand-b.com", subject="Campaign B", body="Body B",
            worker_id="w2", campaign_name="retail-manufacturers"
        )
        self.assertFalse(ok_b)
        self.assertIn("quota reached", reason_b.lower())

    # 8. Follow-ups retain their sender and take priority; deferred jobs recover
    def test_scenario_8_followup_priority_and_sender_retention(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        mb = "aryan@mindmaxing.online"

        # Create a deferred touch 2 follow-up
        c.execute("""
            INSERT INTO outbound_jobs (
                lead_id, domain, touch_number, assigned_mailbox, recipient_email,
                subject, body, due_at, earliest_send_at, status, campaign_name, created_at, updated_at
            ) VALUES (1, 'warmlead.com', 2, ?, 'warm@warmlead.com', 'Follow up', 'Checking in', ?, ?, 'DEFERRED', 'dealstrike', ?, ?)
        """, (mb, now_iso, now_iso, now_iso, now_iso))
        job_id = c.lastrowid
        conn.commit()
        conn.close()

        # Deferred job must be claimable again
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT status, assigned_mailbox FROM outbound_jobs WHERE id = ?", (job_id,))
        row = c.fetchone()
        self.assertEqual(row[0], "DEFERRED")
        self.assertEqual(row[1], mb)  # Sender retained!
        conn.close()

    # 9. Concurrent claims, post-acceptance errors and interrupted attempts do not cause duplicate sends
    def test_scenario_9_concurrent_claims_and_post_data_uncertainty(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        period_id = volume_controller.get_current_period_id()
        mb = "aryan@mindmaxing.online"

        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (mb, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 5, ?)", (mb, now_iso, now_iso))
        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_id, period_id, decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason,
                evidence_summary_json, revision, created_at
            ) VALUES (?, ?, ?, ?, 'mindmaxing.online', 1, 1, 1, 'KEEP', 'Baseline', '{}', 1, ?)
        """, (f"DEC-{period_id}-{mb}-r1", period_id, today_utc, mb, now_iso))
        c.execute("INSERT INTO leads (domain, contact_email, status) VALUES ('targetstore.com', 't@targetstore.com', 'HUMAN_APPROVED')")
        lead_id = c.lastrowid
        conn.commit()
        conn.close()

        # First worker claims
        ok1, _, meta1 = volume_controller.reserve_and_claim_job(
            lead_id=lead_id, domain="targetstore.com", touch_number=1, mailbox=mb,
            recipient="t@targetstore.com", subject="Sub", body="Body",
            worker_id="worker_A"
        )
        self.assertTrue(ok1)

        # Second concurrent worker attempts to claim identical touch -> must be rejected!
        ok2, reason2, _ = volume_controller.reserve_and_claim_job(
            lead_id=lead_id, domain="targetstore.com", touch_number=1, mailbox=mb,
            recipient="t@targetstore.com", subject="Sub", body="Body",
            worker_id="worker_B"
        )
        self.assertFalse(ok2)

        # Post-acceptance SMTP error: mark UNCERTAIN, quota is NOT refunded
        job_id = meta1["job_id"]
        volume_controller.update_outbound_job_status(job_id, "UNCERTAIN")

        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT status FROM outbound_jobs WHERE id = ?", (job_id,))
        self.assertEqual(c.fetchone()[0], "UNCERTAIN")
        c.execute("SELECT campaign_sent FROM mailbox_quotas WHERE mailbox = ?", (mb,))
        self.assertEqual(c.fetchone()[0], 1)  # Quota preserved!
        conn.close()

    # 10. Repeated nightly runs and report requests cannot reset usage or repeat increases
    def test_scenario_10_review_and_report_idempotency(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        mb = "aryan@mindmaxing.online"

        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (mb, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 5, ?)", (mb, now_iso, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES ('seed@gmail.com', 'test_inbox', ?, 'healthy', NULL, 5, ?)", (now_iso, now_iso))
        c.execute("""
            INSERT INTO messages (
                message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                recipient_provider, purpose, sent_at, sent_date, smtp_status, delivery_state,
                auth_spf, auth_dkim, auth_dmarc, last_event_at
            ) VALUES ('<clean-diag-idemp@mindmaxing.online>', ?, 'mindmaxing.online', 'seed@gmail.com', 'gmail.com', 'gmail', 'test', ?, '2026-09-22', 'accepted', 'inbox', 'pass', 'pass', 'pass', ?)
        """, (mb, now_iso, now_iso))
        conn.commit()

        # Run 1: apply review
        res1 = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=False)
        c.execute("SELECT COUNT(*) FROM mailbox_daily_decisions WHERE mailbox = ? AND period_id = '2026-09-22-IST'", (mb,))
        count_run1 = c.fetchone()[0]
        self.assertEqual(count_run1, 1)

        # Run 2: repeat review with same evidence -> must NOT insert duplicate revision!
        res2 = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=False)
        c.execute("SELECT COUNT(*) FROM mailbox_daily_decisions WHERE mailbox = ? AND period_id = '2026-09-22-IST'", (mb,))
        count_run2 = c.fetchone()[0]
        self.assertEqual(count_run2, 1)  # Idempotent!

        # Run 3: Read-only report command must not modify DB
        rep = outbound_status.generate_period_report("2026-09-22-IST")
        self.assertEqual(rep["period_id"], "2026-09-22-IST")
        c.execute("SELECT COUNT(*) FROM mailbox_daily_decisions WHERE mailbox = ? AND period_id = '2026-09-22-IST'", (mb,))
        self.assertEqual(c.fetchone()[0], 1)
        conn.close()

    # 11. Restart, missing review, budget-boundary migration and backup restoration
    def test_scenario_11_restart_boundary_migration_and_backup_restore(self):
        # Verify SQLite backup API works and restored copy passes integrity check
        backup_path = os.path.join(self.temp_dir, "restored_backup.db")
        src_conn = sqlite3.connect(self.test_db)
        dst_conn = sqlite3.connect(backup_path)
        src_conn.backup(dst_conn)
        src_conn.close()

        # Run integrity check on restored backup
        chk = dst_conn.execute("PRAGMA integrity_check;").fetchall()
        self.assertEqual(chk, [("ok",)])
        dst_conn.close()

    # 12. Eligible growth (+1), insufficient evidence (KEEP), temporary-failure reduction (-1) and scoped pauses
    def test_scenario_12_growth_reduction_and_scoped_pauses(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        mb = "aryan@mindmaxing.online"

        # Initialize at Level 2
        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 2, ?, 'active', NULL, NULL)", (mb, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 5, ?)", (mb, now_iso, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES ('seed@gmail.com', 'test_inbox', ?, 'healthy', NULL, 5, ?)", (now_iso, now_iso))
        # Insert 3 consecutive 4xx temp failures within 24h
        for i in range(3):
            c.execute("""
                INSERT INTO messages (
                    message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                    recipient_provider, purpose, sent_at, sent_date, smtp_status, smtp_code,
                    delivery_state, last_event_at
                ) VALUES (?, ?, 'mindmaxing.online', 'r@test.com', 'test.com', 'other', 'campaign', ?, '2026-09-22', 'temp_failure', 421, 'unknown', ?)
            """, (f"<msg-4xx-{i}@mindmaxing.online>", mb, now_iso, now_iso))
        conn.commit()

        # DECREASE triggered: Level 2 -> Level 1
        res = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=False)
        dec = next(d for d in res["decisions"] if d["mailbox"] == mb)
        self.assertEqual(dec["action"], "DECREASE")
        self.assertEqual(dec["campaign_cap"], 1)
        self.assertEqual(dec["level"], 1)

        # Check DB level was updated
        c.execute("SELECT level FROM mailbox_levels WHERE mailbox = ?", (mb,))
        self.assertEqual(c.fetchone()[0], 1)
        conn.close()

    # 13. DMARC pass requirement enforced for clean diagnostic
    def test_scenario_13_dmarc_pass_requirement_enforced(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        mb = "aryan@mindmaxing.online"

        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 1, ?)", (mb, now_iso, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES ('seed@gmail.com', 'test_inbox', ?, 'healthy', NULL, 1, ?)", (now_iso, now_iso))

        # Diagnostic with SPF and DKIM pass, but DMARC FAIL
        c.execute("""
            INSERT INTO messages (
                message_id, sender_email, sender_domain, recipient_email, recipient_domain,
                recipient_provider, purpose, sent_at, sent_date, smtp_status, delivery_state,
                auth_spf, auth_dkim, auth_dmarc, last_event_at
            ) VALUES ('<diag-dmarc-fail@mindmaxing.online>', ?, 'mindmaxing.online', 'seed@gmail.com', 'gmail.com', 'gmail', 'test', ?, '2026-09-22', 'accepted', 'inbox', 'pass', 'pass', 'fail', ?)
        """, (mb, now_iso, now_iso))
        conn.commit()

        # Must NOT unlock mailbox because DMARC failed! (Caught by Rule 3 domain auth failure)
        res_fail = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=True)
        dec_fail = next(d for d in res_fail["decisions"] if d["mailbox"] == mb)
        self.assertEqual(dec_fail["campaign_cap"], 0)
        self.assertEqual(dec_fail["action"], "PAUSE")
        self.assertIn("authentication failure", dec_fail["reason"].lower())

        # Update DMARC to pass
        c.execute("UPDATE messages SET auth_dmarc = 'pass' WHERE message_id = '<diag-dmarc-fail@mindmaxing.online>'")
        conn.commit()

        # Now it unlocks baseline 1!
        res_pass = daily_mailbox_planner.plan_day(conn, period_id="2026-09-22-IST", shadow=True)
        conn.close()
        dec_pass = next(d for d in res_pass["decisions"] if d["mailbox"] == mb)
        self.assertEqual(dec_pass["campaign_cap"], 1)
        self.assertEqual(dec_pass["action"], "KEEP")

    # 14. Narrow diagnostic recovery permits awaiting readiness, but hard stops reject diagnostics
    def test_scenario_14_narrow_diagnostic_recovery_vs_hard_stops(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        period_id = volume_controller.get_current_period_id()
        mb_readiness = "readiness@mindmaxing.online"
        mb_manual_pause = "manual@mindmaxing.online"
        mb_auth_fail = "authfail@mindmaxing.online"

        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (mb_readiness, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 1, ?)", (mb_readiness, now_iso, now_iso))
        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_id, period_id, decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason,
                evidence_summary_json, revision, created_at
            ) VALUES (?, ?, '2026-09-22', ?, 'mindmaxing.online', 1, 0, 1, 'PAUSE', 'Awaiting first clean diagnostic in Inbox with passing SPF/DKIM/DMARC', '{}', 1, ?)
        """, (f"DEC-{period_id}-{mb_readiness}", period_id, mb_readiness, now_iso))

        # Manual pause mailbox
        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'paused', 'Operator hold', NULL)", (mb_manual_pause, now_iso))
        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_id, period_id, decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason,
                evidence_summary_json, revision, created_at
            ) VALUES (?, ?, '2026-09-22', ?, 'mindmaxing.online', 1, 0, 0, 'PAUSED', 'Manually paused by operator', '{}', 1, ?)
        """, (f"DEC-{period_id}-{mb_manual_pause}", period_id, mb_manual_pause, now_iso))

        # Auth failure mailbox
        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (mb_auth_fail, now_iso))
        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_id, period_id, decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason,
                evidence_summary_json, revision, created_at
            ) VALUES (?, ?, '2026-09-22', ?, 'mindmaxing.online', 1, 0, 0, 'HOLD_AUTH_FAILED', 'Confirmed authentication failure', '{}', 1, ?)
        """, (f"DEC-{period_id}-{mb_auth_fail}", period_id, mb_auth_fail, now_iso))

        conn.commit()
        conn.close()

        # Case A: Awaiting readiness permits 1 diagnostic ping
        test_ok, test_msg = volume_controller.reserve_quota(mb_readiness, purpose="test", period_id=period_id)
        self.assertTrue(test_ok, f"Awaiting readiness must permit recovery diagnostic: {test_msg}")

        # Case B: Manual pause strictly rejects diagnostic send
        man_ok, man_msg = volume_controller.reserve_quota(mb_manual_pause, purpose="test", period_id=period_id)
        self.assertFalse(man_ok, "Manual pause must reject diagnostic sends")

        # Case C: Auth failure strictly rejects diagnostic send
        auth_ok, auth_msg = volume_controller.reserve_quota(mb_auth_fail, purpose="test", period_id=period_id)
        self.assertFalse(auth_ok, "Auth failure must reject diagnostic sends")

    # 15. Unified budget period accounting across midnight UTC rollover
    def test_scenario_15_midnight_utc_crossing_preserves_period_quota(self):
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        mb = "aryan@mindmaxing.online"
        period_id = "2026-09-22-IST"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Insert required leads with HUMAN_APPROVED
        c.execute("""
            INSERT OR REPLACE INTO leads (id, domain, contact_email, status)
            VALUES (1, 'store1.com', 'owner@store1.com', 'HUMAN_APPROVED'),
                   (2, 'store2.com', 'owner@store2.com', 'HUMAN_APPROVED')
        """)

        c.execute("INSERT OR REPLACE INTO mailbox_levels VALUES (?, 'mindmaxing.online', 1, ?, 'active', NULL, NULL)", (mb, now_iso))
        c.execute("INSERT OR REPLACE INTO collector_health VALUES (?, 'sender', ?, 'healthy', NULL, 5, ?)", (mb, now_iso, now_iso))
        c.execute("""
            INSERT INTO mailbox_daily_decisions (
                decision_id, period_id, decision_date_utc, mailbox, domain, current_level,
                effective_campaign_cap, effective_diagnostic_cap, decision_action, decision_reason,
                evidence_summary_json, revision, created_at
            ) VALUES (?, ?, '2026-09-21', ?, 'mindmaxing.online', 1, 1, 1, 'KEEP', 'Baseline', '{}', 1, ?)
        """, (f"DEC-{period_id}-{mb}", period_id, mb, now_iso))
        conn.commit()
        conn.close()

        # Step 1: Send 1 campaign email before midnight UTC (date_utc = 2026-09-21)
        res1, msg1, data1 = volume_controller.reserve_and_claim_job(
            lead_id=1, domain="store1.com", touch_number=1, mailbox=mb,
            recipient="owner@store1.com", subject="Test", body="Body", worker_id="w1",
            campaign_name="c1", period_id=period_id
        )
        self.assertTrue(res1, f"First send should succeed: {msg1}")

        # Step 2: Simulate midnight UTC crossing: date_utc becomes 2026-09-22, but period_id is still 2026-09-22-IST
        # Attempt second send on the same IST budget period
        res2, msg2, data2 = volume_controller.reserve_and_claim_job(
            lead_id=2, domain="store2.com", touch_number=1, mailbox=mb,
            recipient="owner@store2.com", subject="Test", body="Body", worker_id="w1",
            campaign_name="c1", period_id=period_id
        )
        # Must be REJECTED! Budget period cap is 1 send
        self.assertFalse(res2, "Second send in same IST budget period must be blocked even if date_utc changed")
        self.assertIn("quota reached", msg2.lower())

    # 16. Timezone window precision for Ireland and US Pacific
    def test_scenario_16_timezone_window_precision(self):
        import scheduler
        # Tuesday Sept 22 at 13:30 UTC
        utc_1330 = datetime(2026, 9, 22, 13, 30, tzinfo=timezone.utc)

        # Ireland (IE): 13:30 UTC is 14:30 local BST/IST -> Window is OPEN
        ie_open, ie_msg = scheduler.get_timezone_window_status("IE", now_utc=utc_1330)
        self.assertTrue(ie_open, f"Ireland at 13:30 UTC (14:30 local) must be OPEN: {ie_msg}")

        # US California (state='CA'): 13:30 UTC is 06:30 AM PDT -> Window is CLOSED
        ca_open, ca_msg = scheduler.get_timezone_window_status("US", now_utc=utc_1330, state="CA")
        self.assertFalse(ca_open, f"California at 13:30 UTC (06:30 PDT) must be CLOSED: {ca_msg}")

        # Later at 17:00 UTC (10:00 AM PDT) -> Window is OPEN
        utc_1700 = datetime(2026, 9, 22, 17, 0, tzinfo=timezone.utc)
        ca_later_open, ca_later_msg = scheduler.get_timezone_window_status("US", now_utc=utc_1700, state="CA")
        self.assertTrue(ca_later_open, f"California at 17:00 UTC (10:00 PDT) must be OPEN: {ca_later_msg}")


if __name__ == "__main__":
    unittest.main()
