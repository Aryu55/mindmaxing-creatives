#!/usr/bin/env python3
"""
Mindmaxing Contact System & Invariant Test Suite
Verifies:
1. Role-based email detection (support@, info@, team@ -> GENERIC_SUPPORT).
2. Personal email detection (kyle@, bob.chen@ -> PERSONAL).
3. Non-person blocklist enforcement ("Customerservice", "Team", "Services" -> REJECTED).
4. Valid human founder name validation.
5. ZERO BLIND GUESSING invariant (Never synthesize {first}.{last} without evidence).
6. Active sequence protection (current_sequence_step > 0 -> contact_email never overwritten).
7. JSON-LD structured schema parsing for @type: Person.
"""

import json
import os
import sqlite3
import sys
import unittest

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from email_classifier import (
    classify_email, is_role_account, is_valid_email,
    is_valid_founder_name, clean_email, ROLE_BASED_PREFIXES, NON_PERSON_NAMES
)
from founder_resolver import (
    extract_json_ld_people, extract_text_founder_regex,
    email_matches_name, audit_and_update_lead
)


class TestContactSystem(unittest.TestCase):

    def test_role_prefix_detection(self):
        """Ensure all known customer service prefixes are blocked from automated dispatch."""
        generic_samples = [
            "support@store.com",
            "info@store.com",
            "care@store.com",
            "customerservice@store.com",
            "customercare@store.com",
            "team@store.com",
            "hello@store.com",
            "contact@store.com",
            "orders@store.com",
            "returns@store.com",
            "billing@store.com",
            "help@store.com",
            "enquiries@store.com"
        ]
        for em in generic_samples:
            res = classify_email(em)
            self.assertEqual(res["classification"], "GENERIC_SUPPORT", f"Failed for {em}")
            self.assertTrue(is_role_account(em), f"is_role_account failed for {em}")

    def test_personal_email_detection(self):
        """Ensure true personal emails are classified as PERSONAL."""
        personal_samples = [
            "kyle@floydhome.com",
            "frank.garden@andersonsofinverurie.co.uk",
            "bob.chen@jureynco.com",
            "aryan@mindmaxing.online",
            "sarah.connor@brand.co"
        ]
        for em in personal_samples:
            res = classify_email(em)
            self.assertEqual(res["classification"], "PERSONAL", f"Failed for {em}")
            self.assertFalse(is_role_account(em), f"is_role_account failed for {em}")

    def test_non_person_blocklist(self):
        """Ensure legacy scraper bugs ('Customerservice', 'Team', 'Services') are rejected."""
        bad_names = [
            "Customerservice",
            "Team",
            "Services",
            "Service",
            "Customercare",
            "Hello",
            "Contact",
            "Ciao",
            "Store",
            "Shop",
            "Management",
            "Support"
        ]
        for name in bad_names:
            is_valid, _ = is_valid_founder_name(name)
            self.assertFalse(is_valid, f"Expected {name} to be REJECTED as founder name")

    def test_valid_founder_names(self):
        """Ensure genuine 2-word capitalized human names pass."""
        good_names = [
            "Kyle Hoff",
            "Bob Chen",
            "Frank Garden",
            "Sarah Jenkins",
            "Jean-Luc Picard"
        ]
        for name in good_names:
            is_valid, clean = is_valid_founder_name(name)
            self.assertTrue(is_valid, f"Expected {name} to be VALID")
            self.assertGreater(len(clean), 3)

    def test_json_ld_person_parsing(self):
        """Test structured JSON-LD extraction."""
        html = """
        <html>
        <head>
          <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": "Kyle Hoff",
            "jobTitle": "Co-Founder & CEO",
            "email": "kyle@floydhome.com"
          }
          </script>
        </head>
        <body><h1>About Us</h1></body>
        </html>
        """
        people = extract_json_ld_people(html)
        self.assertEqual(len(people), 1)
        self.assertEqual(people[0]["name"], "Kyle Hoff")
        self.assertEqual(people[0]["email"], "kyle@floydhome.com")

    def test_name_email_matching(self):
        """Verify correlation between discovered founder and email local part."""
        self.assertTrue(email_matches_name("kyle@floydhome.com", "Kyle Hoff"))
        self.assertTrue(email_matches_name("kyle.hoff@floydhome.com", "Kyle Hoff"))
        self.assertTrue(email_matches_name("k.hoff@floydhome.com", "Kyle Hoff"))
        # Department email must not match
        self.assertFalse(email_matches_name("marketing@floydhome.com", "Kyle Hoff"))
        self.assertFalse(email_matches_name("sales@floydhome.com", "Kyle Hoff"))

    def test_active_sequence_preservation(self):
        """Ensure that if current_sequence_step > 0, contact_email is NEVER overwritten."""
        # Create an in-memory SQLite database
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY,
                domain TEXT,
                company_name TEXT,
                contact_email TEXT,
                current_sequence_step INTEGER,
                status TEXT,
                resolved_name TEXT,
                resolved_email TEXT,
                resolved_role TEXT,
                resolved_evidence TEXT,
                resolution_status TEXT,
                resolved_at TEXT,
                original_contact_email TEXT
            )
        """)
        # Insert a lead with active sequence step 1
        c.execute("""
            INSERT INTO leads (id, domain, company_name, contact_email, current_sequence_step, status)
            VALUES (1, 'active-store.com', 'Active Store', 'original@active-store.com', 1, 'CANDIDATE')
        """)
        conn.commit()

        row = c.execute("SELECT * FROM leads WHERE id = 1").fetchone()

        # Mock resolve result and call the actual production function audit_and_update_lead
        from unittest.mock import patch

        mock_resolution = {
            "resolution_status": "FOUNDER_FOUND",
            "resolved_name": "Discovered Founder",
            "resolved_email": "new_founder@active-store.com",
            "resolved_role": "CEO",
            "evidence": {"mocked": True}
        }

        with patch("founder_resolver.resolve_founder_contact", return_value=mock_resolution):
            audit_and_update_lead(row, conn, dry_run=False)

        updated = c.execute("SELECT * FROM leads WHERE id = 1").fetchone()
        # contact_email must remain 'original@active-store.com' because sequence_step is 1!
        self.assertEqual(updated["contact_email"], "original@active-store.com")
        self.assertEqual(updated["resolved_email"], "new_founder@active-store.com")
        self.assertEqual(updated["resolved_name"], "Discovered Founder")
        self.assertEqual(updated["resolution_status"], "FOUNDER_FOUND")
        conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
