#!/usr/bin/env python3
"""
Mindmaxing Ground-Truth Founder Contact Resolver v1.0
- Discovers authentic decision-makers (Founders, Co-Founders, CEOs, Owners) from Shopify DTC store websites.
- Extraction order: JSON-LD `@type: Person` structured data -> Targeted regex patterns -> Verified mailto links.
- ABSOLUTE INVARIANT: ZERO BLIND EMAIL GUESSING.
  - If a founder is discovered without an explicit published personal email, status is marked `NAME_ONLY`.
  - Never fabricates `{first}.{last}@{domain}` permutations.
- Preserves active sequences: If `current_sequence_step > 0`, never overwrites `contact_email`.
- Uses native `host -t mx` for DNS validation with zero third-party search engine dependencies.
"""

import argparse
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# Try local import first, fallback to script directory import
try:
    from email_classifier import (
        clean_email, is_valid_email, is_role_account,
        classify_email, is_valid_founder_name, NON_PERSON_NAMES
    )
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from email_classifier import (
        clean_email, is_valid_email, is_role_account,
        classify_email, is_valid_founder_name, NON_PERSON_NAMES
    )

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
]

TARGET_PATHS = [
    "/pages/about",
    "/pages/about-us",
    "/pages/our-story",
    "/pages/team",
    "/pages/contact",
    "/about",
    "/about-us",
    "/our-story",
    "/team",
    "/contact"
]

EXECUTIVE_ROLES = frozenset({
    "founder", "co-founder", "cofounder", "owner", "co-owner", "ceo",
    "chief executive officer", "president", "managing director", "creator"
})


def check_mx_record(domain: str) -> bool:
    """Verifies domain has valid active MX records using native host command."""
    if not domain:
        return False
    try:
        r = subprocess.run(["host", "-t", "mx", domain], capture_output=True, text=True, timeout=3)
        out = r.stdout.lower()
        return ("mail is handled by" in out or "has mx record" in out)
    except Exception:
        return False


def clean_domain_string(raw_domain: str) -> str:
    """Sanitizes domain input."""
    d = raw_domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0]
    return d.strip()


def fetch_url(url: str, timeout: float = 3.5) -> Tuple[int, str]:
    """Fetches web page content with timeout and desktop user-agent."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
            content = resp.read().decode("utf-8", errors="ignore")
            return status, content
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def extract_json_ld_people(html: str) -> List[Dict[str, Any]]:
    """
    Extracts Schema.org Person objects with explicit founder relationships.
    - Traverses JSON-LD arrays and @graph structures.
    - Resolves @id references between Organization and Person nodes.
    - Strictly requires either Organization.founder link or explicit executive jobTitle.
    - Rejects arbitrary Person nodes with missing roles (employees, authors, customers).
    """
    results: List[Dict[str, Any]] = []
    script_blocks = re.findall(r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    
    for block in script_blocks:
        block_clean = block.strip()
        if not block_clean:
            continue
        try:
            data = json.loads(block_clean)
        except Exception:
            continue

        # Flatten tree into a list of items and an @id lookup map
        flat_items: List[Dict[str, Any]] = []
        id_map: Dict[str, Dict[str, Any]] = {}

        def collect_nodes(node: Any):
            if isinstance(node, dict):
                if "@graph" in node and isinstance(node["@graph"], list):
                    for sub in node["@graph"]:
                        collect_nodes(sub)
                else:
                    flat_items.append(node)
                    if "@id" in node and isinstance(node["@id"], str):
                        id_map[node["@id"]] = node
                    for k, v in node.items():
                        if k in ("founder", "founders") and isinstance(v, (dict, list)):
                            collect_nodes(v)
            elif isinstance(node, list):
                for sub in node:
                    collect_nodes(sub)

        collect_nodes(data)

        # 1. Identify Organization nodes and their explicit founder links
        org_founder_ids: Set[str] = set()
        org_founder_inline: List[Dict[str, Any]] = []

        for item in flat_items:
            t = item.get("@type", "")
            if isinstance(t, list):
                t = " ".join(t)
            if "organization" in str(t).lower():
                for k in ("founder", "founders"):
                    f_val = item.get(k)
                    if not f_val:
                        continue
                    f_list = f_val if isinstance(f_val, list) else [f_val]
                    for f in f_list:
                        if isinstance(f, dict):
                            if "@id" in f:
                                org_founder_ids.add(f["@id"])
                            elif f.get("@type", "").lower() == "person" or f.get("name"):
                                org_founder_inline.append(f)

        # 2. Inspect all Person nodes
        for item in flat_items:
            t = item.get("@type", "")
            if isinstance(t, list):
                t = " ".join(t)
            t_lower = str(t).lower()

            is_person = "person" in t_lower
            item_id = item.get("@id", "")
            is_org_founder = item_id in org_founder_ids or item in org_founder_inline

            if not is_person and not is_org_founder:
                continue

            name = item.get("name", "")
            role = item.get("jobTitle") or item.get("roleName") or item.get("description") or ""
            email = item.get("email", "")

            role_lower = str(role).lower().strip()
            has_exec_role = any(r in role_lower for r in EXECUTIVE_ROLES)

            # Strict Invariant: Only admit if explicitly linked as founder OR has executive role
            # NEVER promote a Person with missing or unrelated role to Founder!
            if is_org_founder or has_exec_role:
                is_valid, clean_name = is_valid_founder_name(name)
                if is_valid:
                    assigned_role = str(role).strip() if role else "Founder"
                    results.append({
                        "name": clean_name,
                        "role": assigned_role,
                        "email": clean_email(email),
                        "method": "json_ld",
                        "structured_path": f"@id:{item_id}" if item_id else "@type:Person",
                        "relationship": "Organization.founder" if is_org_founder else "Explicit_Role_Person"
                    })

    return results


def extract_text_founder_blocks(html: str, target_domain: str) -> List[Dict[str, Any]]:
    """
    Extracts founder candidates from HTML text blocks with DOM-local email scoping.
    Prevents pooling page emails and falsely attributing unrelated contacts (e.g. PR/Press) to founders.
    """
    results: List[Dict[str, Any]] = []
    clean_target = target_domain.replace("www.", "").strip()

    # Strip script/style blocks
    cleaned_html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)

    # Split into structural HTML blocks
    blocks = re.split(r'</?(?:div|section|article|li|p|table|tbody|tr)[^>]*>', cleaned_html, flags=re.IGNORECASE)

    patterns = [
        # "founded by Kyle Hoff" / "co-founded by Bob Chen and..."
        r"(?:co-founded|founded|started|created)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        # "our founder, Kyle Hoff" / "meet the founder, Jane Doe"
        r"(?:our\s+founder|meet\s+the\s+founder|meet\s+our\s+founder),?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        # "Kyle Hoff, Founder and CEO" / "Jane Smith, Co-Founder"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}),?\s+(?:is\s+the\s+)?(?:founder|co-founder|owner|ceo|creator)",
        # "Founder: Kyle Hoff" / "CEO: Bob Chen"
        r"(?:Founder|Co-Founder|Owner|CEO)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})"
    ]

    for block in blocks:
        if not block.strip() or len(block) < 15:
            continue

        block_text = re.sub(r"<[^>]+>", " ", block)
        block_text = re.sub(r"\s+", " ", block_text).strip()

        for pat in patterns:
            matches = re.finditer(pat, block_text, re.IGNORECASE)
            for m in matches:
                candidate_name = m.group(1).strip()
                is_valid, clean_name = is_valid_founder_name(candidate_name)
                if not is_valid:
                    continue

                # Search for DOM-LOCAL email within this EXACT same block only
                block_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', block)
                associated_email = ""
                for em in block_emails:
                    clean_em = clean_email(em)
                    if not is_valid_email(clean_em) or is_role_account(clean_em):
                        continue
                    em_domain = clean_em.split("@")[1]
                    if em_domain == clean_target or clean_target.endswith("." + em_domain) or em_domain.endswith("." + clean_target):
                        # Verify email matches founder name
                        if email_matches_name(clean_em, clean_name):
                            associated_email = clean_em
                            break

                results.append({
                    "name": clean_name,
                    "role": "Founder",
                    "email": associated_email,
                    "method": "dom_local_text",
                    "snippet": block_text[max(0, m.start()-40):min(len(block_text), m.end()+40)].strip(),
                    "relationship": "Text_Explicit_Founder_Bio"
                })

    return results


def extract_text_founder_regex(html: str) -> List[Dict[str, Any]]:
    """Backward-compatible alias for text founder extraction."""
    return extract_text_founder_blocks(html, "")


def email_matches_name(email: str, name: str) -> bool:
    """
    Checks if an email local-part plausibly matches the person's name.
    e.g. 'kyle@floydhome.com' or 'kyle.hoff@...' matches 'Kyle Hoff'.
    """
    if not email or not name:
        return False
    local = email.split("@")[0].lower()
    parts = [p.lower() for p in name.split() if p]
    if not parts:
        return False

    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    # Exact first name (kyle@)
    if local == first:
        return True
    # first.last / firstlast
    if last and (local == f"{first}.{last}" or local == f"{first}{last}"):
        return True
    # f.last / flast
    if last and (local == f"{first[0]}.{last}" or local == f"{first[0]}{last}"):
        return True
    # last.first
    if last and (local == f"{last}.{first}" or local == f"{last}{first}"):
        return True

    return False


def extract_navigation_links(homepage_html: str, clean_domain: str) -> List[str]:
    """
    Discovers relevant company story/team/contact navigation links from homepage HTML.
    Matches paths and anchor texts for 'about', 'story', 'team', 'founder', 'contact', etc.
    """
    if not homepage_html:
        return []

    discovered = []
    a_tag_pattern = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
    relevant_keywords = ("about", "story", "team", "founder", "contact", "mission", "who-we-are", "meet")

    for match in a_tag_pattern.finditer(homepage_html):
        href = match.group(1).strip()
        anchor_text = re.sub(r'<[^>]+>', ' ', match.group(2)).strip().lower()
        href_lower = href.lower()

        is_relevant = any(kw in href_lower or kw in anchor_text for kw in relevant_keywords)
        if not is_relevant:
            continue

        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        parsed = urllib.parse.urlparse(href)
        if parsed.netloc:
            netloc = parsed.netloc.lower()
            if netloc != clean_domain and not netloc.endswith("." + clean_domain):
                continue
            path = parsed.path
        else:
            path = parsed.path

        if not path or not path.startswith("/"):
            path = "/" + path

        if any(path.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".svg", ".css", ".js", ".json", ".webp", ".gif")):
            continue

        if path not in discovered and path != "/":
            discovered.append(path)

    return discovered


def resolve_founder_contact(
    domain: str,
    company_name: str = "",
    hunter_adapter: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Main resolution engine for a single domain.
    Crawls on-site pages starting with homepage and actual navigation links,
    falling back to standard target paths, and extracts verified founder info without blind guessing.
    Enforces DOM-local email association and JSON-LD @graph traversal.
    """
    clean_domain = clean_domain_string(domain)
    pages_crawled = []
    pages_failed = []
    
    discovered_people: List[Dict[str, Any]] = []

    # Step 1: Fetch homepage first to discover actual navigation links
    homepage_url = f"https://{clean_domain}/"
    hp_status, hp_html = fetch_url(homepage_url)

    paths_to_crawl: List[str] = []
    if hp_status == 200 and hp_html:
        pages_crawled.append("/")
        # Extract structured data and DOM blocks from homepage
        for p in extract_json_ld_people(hp_html):
            p["url"] = homepage_url
            discovered_people.append(p)
        for p in extract_text_founder_blocks(hp_html, clean_domain):
            p["url"] = homepage_url
            discovered_people.append(p)

        # Traverse actual navigation links found in homepage
        nav_links = extract_navigation_links(hp_html, clean_domain)
        for pth in nav_links:
            if pth not in paths_to_crawl and pth != "/":
                paths_to_crawl.append(pth)
    else:
        pages_failed.append("/")

    # Step 2: Append fallback target paths
    for pth in TARGET_PATHS:
        if pth not in paths_to_crawl and pth not in pages_crawled:
            paths_to_crawl.append(pth)

    # Bound on-site crawl: at most 10 pages total (homepage + up to 9 subpages)
    max_subpages = max(0, 10 - len(pages_crawled))
    paths_to_crawl = paths_to_crawl[:max_subpages]

    for path in paths_to_crawl:
        url = f"https://{clean_domain}{path}"
        status, html = fetch_url(url)
        
        if status == 200 and html:
            pages_crawled.append(path)
            # Step A: Structured JSON-LD with @graph traversal
            json_people = extract_json_ld_people(html)
            for p in json_people:
                p["url"] = url
                discovered_people.append(p)

            # Step B: Text Blocks with DOM-Local Email Scoping
            text_people = extract_text_founder_blocks(html, clean_domain)
            for p in text_people:
                p["url"] = url
                discovered_people.append(p)
        else:
            pages_failed.append(path)

        time.sleep(0.35)

    # Deduplicate discovered people by name
    unique_people: Dict[str, Dict[str, Any]] = {}
    for p in discovered_people:
        name_key = p["name"].lower()
        if name_key not in unique_people:
            unique_people[name_key] = p
        elif p.get("email"):
            unique_people[name_key] = p
        elif p.get("method") == "json_ld":
            unique_people[name_key] = p

    evidence = {
        "domain": clean_domain,
        "company_name": company_name,
        "pages_crawled": pages_crawled,
        "pages_failed": pages_failed,
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "total_people_found": len(unique_people),
        "candidates": list(unique_people.values())
    }

    if not unique_people:
        if not pages_crawled:
            return {
                "resolution_status": "CRAWL_FAILED",
                "identity_status": "UNCONFIRMED",
                "email_origin": "LEGACY_UNKNOWN",
                "mailbox_verification": "UNCHECKED",
                "resolved_name": None,
                "resolved_email": None,
                "resolved_role": None,
                "evidence": evidence
            }
        return {
            "resolution_status": "NO_PUBLIC_FOUNDER",
            "identity_status": "UNCONFIRMED",
            "email_origin": "LEGACY_UNKNOWN",
            "mailbox_verification": "UNCHECKED",
            "resolved_name": None,
            "resolved_email": None,
            "resolved_role": None,
            "evidence": evidence
        }

    # Select candidate with direct email attached if available, else first founder
    candidates = list(unique_people.values())
    with_email = [c for c in candidates if c.get("email")]
    best_person = with_email[0] if with_email else candidates[0]

    founder_name = best_person["name"]
    founder_role = best_person.get("role", "Founder")
    direct_email = best_person.get("email", "")

    evidence["selected_candidate"] = best_person

    # If direct on-site email is present and valid
    if direct_email and is_valid_email(direct_email) and not is_role_account(direct_email):
        mx_ok = check_mx_record(direct_email.split("@")[1])
        evidence["mx_verified"] = mx_ok
        if mx_ok:
            return {
                "resolution_status": "FOUNDER_FOUND",
                "identity_status": "FOUNDER_CONFIRMED",
                "email_origin": "PUBLIC_SITE",
                "mailbox_verification": "VALID",
                "resolved_name": founder_name,
                "resolved_email": direct_email,
                "resolved_role": founder_role,
                "evidence": evidence
            }

    # If founder identified but no on-site email found: check Hunter found-only adapter if enabled
    if hunter_adapter and hasattr(hunter_adapter, "find_found_email") and hunter_adapter.is_enabled:
        h_res = hunter_adapter.find_found_email(clean_domain, founder_name)
        evidence["hunter_attempted"] = True
        evidence["hunter_outcome"] = h_res.get("outcome")
        if h_res.get("outcome") == "FOUND" and h_res.get("email"):
            h_email = clean_email(h_res["email"])
            if is_valid_email(h_email) and not is_role_account(h_email):
                if email_matches_name(h_email, founder_name):
                    mx_ok = check_mx_record(h_email.split("@")[1])
                    evidence["mx_verified"] = mx_ok
                    evidence["hunter_verification"] = h_res.get("verification")
                    evidence["hunter_sources"] = h_res.get("sources")
                    if mx_ok:
                        return {
                            "resolution_status": "FOUNDER_FOUND",
                            "identity_status": "FOUNDER_CONFIRMED",
                            "email_origin": "PROVIDER_FOUND",
                            "mailbox_verification": "VALID",
                            "resolved_name": founder_name,
                            "resolved_email": h_email,
                            "resolved_role": founder_role,
                            "evidence": evidence
                        }

    # ZERO BLIND GUESSING INVARIANT:
    # Founder identified, but NO direct personal email published in DOM or verified provider found-only index.
    # Never pool page emails or guess!
    return {
        "resolution_status": "NAME_ONLY",
        "identity_status": "FOUNDER_CONFIRMED",
        "email_origin": "LEGACY_UNKNOWN",
        "mailbox_verification": "UNCHECKED",
        "resolved_name": founder_name,
        "resolved_email": None,
        "resolved_role": founder_role,
        "evidence": evidence
    }


def audit_and_update_lead(
    lead_row: sqlite3.Row,
    conn: sqlite3.Connection,
    dry_run: bool = False,
    hunter_adapter: Optional[Any] = None
) -> Dict[str, Any]:
    """Resolves a lead and transactionally updates CRM while preserving active sequences."""
    lead_id = lead_row["id"]
    domain = lead_row["domain"]
    company_name = lead_row["company_name"] or ""
    current_email = lead_row["contact_email"] or ""
    sequence_step = lead_row["current_sequence_step"] or 0

    res = resolve_founder_contact(domain, company_name, hunter_adapter=hunter_adapter)
    status = res["resolution_status"]
    resolved_name = res["resolved_name"]
    resolved_email = res["resolved_email"]
    resolved_role = res["resolved_role"]
    evidence_json = json.dumps(res["evidence"])
    now_iso = datetime.now(timezone.utc).isoformat()

    print(f"[{status:18}] {domain:32} -> Founder: {resolved_name or 'None':20} Email: {resolved_email or 'None'}", flush=True)

    if not dry_run:
        c = conn.cursor()
        
        # Invariant: If sequence is active (> 0), never overwrite contact_email!
        if sequence_step > 0:
            c.execute("""
                UPDATE leads
                SET resolved_name = ?,
                    resolved_email = ?,
                    resolved_role = ?,
                    resolved_evidence = ?,
                    resolution_status = ?,
                    resolved_at = ?
                WHERE id = ?
            """, (resolved_name, resolved_email, resolved_role, evidence_json, status, now_iso, lead_id))
        else:
            # For uncontacted leads, update contact_email ONLY if FOUNDER_FOUND
            if status == "FOUNDER_FOUND" and resolved_email:
                c.execute("""
                    UPDATE leads
                    SET original_contact_email = COALESCE(original_contact_email, contact_email),
                        contact_email = ?,
                        contact_name = ?,
                        contact_type = 'FOUNDER_RESOLVED',
                        resolved_name = ?,
                        resolved_email = ?,
                        resolved_role = ?,
                        resolved_evidence = ?,
                        resolution_status = ?,
                        resolved_at = ?
                    WHERE id = ?
                """, (resolved_email, resolved_name, resolved_name, resolved_email, resolved_role, evidence_json, status, now_iso, lead_id))
            else:
                c.execute("""
                    UPDATE leads
                    SET resolved_name = ?,
                        resolved_email = ?,
                        resolved_role = ?,
                        resolved_evidence = ?,
                        resolution_status = ?,
                        resolved_at = ?
                    WHERE id = ?
                """, (resolved_name, resolved_email, resolved_role, evidence_json, status, now_iso, lead_id))
        conn.commit()

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mindmaxing Founder Contact Resolver")
    parser.add_argument("--domain", type=str, help="Resolve a single domain directly")
    parser.add_argument("--limit", type=int, default=10, help="Number of database leads to audit")
    parser.add_argument("--dry-run", action="store_true", help="Audit without saving to database")
    parser.add_argument("--db", type=str, default=DB_PATH, help="Path to mindmaxing_crm.db")
    args = parser.parse_args()

    if args.domain:
        print(f"[*] Auditing domain: {args.domain}")
        res = resolve_founder_contact(args.domain)
        print("\n=== RESOLUTION RESULT ===")
        print(json.dumps(res, indent=2))
        sys.exit(0)

    print(f"[*] Running database batch audit on: {args.db}")
    print(f"[*] Limit: {args.limit} | Dry-run: {args.dry_run}\n")

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    leads = cursor.execute("""
        SELECT * FROM leads 
        WHERE resolution_status IS NULL OR resolution_status = 'UNRESOLVED'
        ORDER BY id ASC
        LIMIT ?
    """, (args.limit,)).fetchall()

    print(f"[*] Found {len(leads)} leads ready for founder audit.\n")

    stats = {"FOUNDER_FOUND": 0, "NAME_ONLY": 0, "NO_PUBLIC_FOUNDER": 0, "CRAWL_FAILED": 0}
    for lead in leads:
        r = audit_and_update_lead(lead, conn, dry_run=args.dry_run)
        st = r["resolution_status"]
        stats[st] = stats.get(st, 0) + 1

    print("\n=== BATCH AUDIT SUMMARY ===")
    for k, v in stats.items():
        print(f"  {k:22}: {v}")
    print("===========================\n")
    conn.close()
