import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TextContent(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


class StudioSiteAcceptanceTests(unittest.TestCase):
    def test_homepage_presents_the_studio_and_primary_paths(self):
        page = (ROOT / "index.html").read_text()
        parser = TextContent()
        parser.feed(page)
        self.assertIn("Creative engineering. With a point of view.", " ".join(parser.parts))
        for landmark in ("studio-vault", "manifesto", "capabilities", "contact"):
            self.assertIn(f'id="{landmark}"', page)
        self.assertIn('id="contact-form"', page)
        self.assertIn('fetch("/api/contact"', (ROOT / "studio.js").read_text())
        self.assertNotIn("Sub-1.2s mobile page loads", page)

    def test_vault_keeps_all_24_unique_projects_and_original_categories(self):
        data = (ROOT / "case-studies-data.js").read_text()
        slugs = re.findall(r'\bslug:\s*["\']([^"\']+)["\']', data)
        self.assertEqual(len(slugs), 24)
        self.assertEqual(len(set(slugs)), 24)
        self.assertIn("saffron-origins", slugs)
        self.assertIn("knittire-3d", slugs)
        self.assertIn("abx-engine", slugs)
        self.assertIn("whatsapp-autopilot", slugs)
        self.assertIn("safespot", slugs)

    def test_vault_discloses_unverified_project_outcome_notes(self):
        page = (ROOT / "case-studies.html").read_text()
        self.assertRegex(page, r"(?i)(source|evidence).{0,80}(date|method|permission)")
        self.assertNotIn("Verified Commercial Outcomes", page)

    def test_cloudflare_public_mirrors_stay_in_sync(self):
        for filename in ("index.html", "case-studies.html", "about.html", "studio.css", "studio.js", "vault.js", "case-studies-data.js"):
            self.assertEqual(
                (ROOT / filename).read_bytes(),
                (ROOT / "public" / filename).read_bytes(),
                filename,
            )


if __name__ == "__main__":
    unittest.main()
