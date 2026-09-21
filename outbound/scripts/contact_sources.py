#!/usr/bin/env python3
"""
Mindmaxing Contact Sources Adapter v2.0
- External discovery and verification adapters with strict boundary controls:
  1. Hunter Found-Only Adapter:
     - Strictly uses `GET /v2/email-finder/found` (documented endpoint excluding generated addresses).
     - Never falls back to ordinary inference-capable email finder.
     - Zero-budget discipline: hard credit cap (default 20), stops on exhausted balance.
     - Redacts API credentials in all logs.
     - Respects removal requests (GDPR/CCPA removals prevent future contact attempts).
  2. Bounded DuckDuckGo Public Web Search:
     - Capped at 3 queries per business attempt.
     - Fetches and inspects original external pages (bios, interviews, press), not just snippets.
     - Enforces safe fetch limits (max 5 external pages, 1MB limit, TLS verified, private IP rejection).
     - Cross-checks candidate name/role against the specific target business.
"""

import ipaddress
import json
import logging
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("contact_sources")

# Safe desktop user agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
]


class SourceOutcome:
    FOUND = "FOUND"
    NO_RESULT = "NO_RESULT"
    AUTH_FAILURE = "AUTH_FAILURE"
    RATE_LIMITED = "RATE_LIMITED"
    UNKNOWN_VERIFICATION = "UNKNOWN_VERIFICATION"
    REMOVAL_REQUEST = "REMOVAL_REQUEST"
    CREDITS_EXHAUSTED = "CREDITS_EXHAUSTED"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


def redact_api_key(key: Optional[str]) -> str:
    """Redacts API keys for secure logging."""
    if not key:
        return "[NOT SET]"
    if len(key) <= 8:
        return "***REDACTED***"
    return f"{key[:3]}...{key[-3:]}"


def is_safe_public_url(url: str) -> bool:
    """
    Validates that a URL points to a public, safe HTTP/HTTPS destination.
    Rejects localhost, loopback, private RFC1918, link-local, and non-HTTP schemes.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
            return False

        # Check IP address resolution
        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
        return True
    except Exception:
        return False


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Ensures that all redirect targets strictly pass is_safe_public_url.
    Prevents open redirect SSRF attacks to internal/private IP addresses or loopback.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_safe_public_url(newurl):
            raise urllib.error.HTTPError(newurl, 403, f"Blocked unsafe redirect to non-public URL: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HunterFoundOnlyAdapter:
    """
    Adapter for Hunter.io's found-only endpoint.
    Strict Invariant: Strictly queries `GET /v2/email-finder/found` which only returns
    email addresses explicitly found on the public web, excluding synthetically inferred addresses.
    """

    def __init__(self, api_key: Optional[str] = None, credit_cap: int = 20):
        self.api_key = api_key or os.environ.get("HUNTER_API_KEY", "").strip()
        self.credit_cap = max(0, credit_cap)
        self.credits_used = 0
        self.base_url = "https://api.hunter.io/v2/email-finder/found"

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key)

    def find_found_email(self, domain: str, full_name: str) -> Dict[str, Any]:
        """
        Executes a found-only lookup for a domain and full name.
        Never falls back to standard email-finder.
        """
        clean_domain = domain.strip().lower()
        clean_name = full_name.strip()

        if not self.is_enabled:
            return {
                "outcome": SourceOutcome.DISABLED,
                "email": None,
                "error": "Hunter API key not configured",
                "sources": [],
                "credits_used": 0
            }

        if self.credits_used >= self.credit_cap:
            return {
                "outcome": SourceOutcome.CREDITS_EXHAUSTED,
                "email": None,
                "error": f"Credit cap reached ({self.credit_cap} credits)",
                "sources": [],
                "credits_used": self.credits_used
            }

        # Build query strictly targeting /v2/email-finder/found
        params = urllib.parse.urlencode({
            "domain": clean_domain,
            "full_name": clean_name
        })
        url = f"{self.base_url}?{params}"

        headers = {
            "X-API-KEY": self.api_key,
            "Accept": "application/json",
            "User-Agent": "MindmaxingOutbound/2.0 (Contact Gatekeeper)"
        }

        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                status_code = resp.getcode()
                raw_body = resp.read().decode("utf-8")
                data_json = json.loads(raw_body).get("data", {})

            # Documented successful query consumes 1 search credit
            self.credits_used += 1

            email = data_json.get("email")
            sources = data_json.get("sources", [])
            verification = data_json.get("verification", {})
            score = data_json.get("score")

            if email:
                return {
                    "outcome": SourceOutcome.FOUND,
                    "email": email,
                    "score": score,
                    "verification": verification,
                    "sources": sources,
                    "error": None,
                    "credits_used": self.credits_used
                }
            else:
                return {
                    "outcome": SourceOutcome.NO_RESULT,
                    "email": None,
                    "sources": [],
                    "error": "No publicly sourced email found",
                    "credits_used": self.credits_used
                }

        except urllib.error.HTTPError as e:
            # Check for specific HTTP error conditions
            if e.code == 404:
                # 404 on found endpoint indicates no publicly sourced address exists
                self.credits_used += 1
                return {
                    "outcome": SourceOutcome.NO_RESULT,
                    "email": None,
                    "sources": [],
                    "error": "HTTP 404: Not found in public index",
                    "credits_used": self.credits_used
                }
            elif e.code in (401, 403):
                return {
                    "outcome": SourceOutcome.AUTH_FAILURE,
                    "email": None,
                    "sources": [],
                    "error": f"Authentication failed (HTTP {e.code})",
                    "credits_used": self.credits_used
                }
            elif e.code == 429:
                return {
                    "outcome": SourceOutcome.RATE_LIMITED,
                    "email": None,
                    "sources": [],
                    "error": "Rate limit exceeded (HTTP 429)",
                    "credits_used": self.credits_used
                }
            elif e.code == 451:
                # Legal removal request / GDPR / CCPA deletion
                err_body = ""
                try:
                    err_body = e.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass

                try:
                    import volume_controller
                    if volume_controller:
                        found_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', err_body)
                        for em in found_emails:
                            volume_controller.suppress_recipient(em, f"Hunter removal request HTTP 451 for {clean_domain}")
                except Exception:
                    pass

                return {
                    "outcome": SourceOutcome.REMOVAL_REQUEST,
                    "email": None,
                    "sources": [],
                    "error": f"Recipient submitted removal request (HTTP 451): {err_body[:200]}",
                    "credits_used": self.credits_used
                }
            else:
                return {
                    "outcome": SourceOutcome.UNKNOWN_VERIFICATION,
                    "email": None,
                    "sources": [],
                    "error": f"HTTP error {e.code}",
                    "credits_used": self.credits_used
                }
        except Exception as e:
            return {
                "outcome": SourceOutcome.ERROR,
                "email": None,
                "sources": [],
                "error": str(e),
                "credits_used": self.credits_used
            }


class DDGSPublicSearchAdapter:
    """
    Adapter for bounded public-web search via DuckDuckGo HTML endpoint.
    - Strictly caps queries at 3 per attempt.
    - Inspects original target web pages (not just search snippets).
    - Enforces max 5 external pages, 1MB payload ceiling, verified TLS, and private IP rejection.
    - Cross-checks candidate role against the specific target business name/domain.
    """

    def __init__(self, timeout: float = 4.0, max_external_pages: int = 5):
        self.timeout = timeout
        self.max_external_pages = max_external_pages
        self.base_search_url = "https://html.duckduckgo.com/html/"

    def search_and_inspect(
        self,
        company_name: str,
        domain: str,
        founder_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes up to 3 bounded search queries, fetches up to 5 external result pages,
        and extracts candidate founder evidence matching the target company.
        """
        clean_company = company_name.strip()
        clean_domain = domain.strip().lower()
        queries = []

        # Query 1: company + domain + founder
        queries.append(f'"{clean_company}" "{clean_domain}" founder')

        # Query 2: founder + company + contact OR domain + founder/ceo
        if founder_name:
            queries.append(f'"{founder_name}" "{clean_company}" contact')
            queries.append(f'"{founder_name}" "@{clean_domain}"')
        else:
            queries.append(f'"{clean_domain}" founder OR ceo OR owner')
            queries.append(f'"{clean_company}" founder email')

        queries = queries[:3]
        external_urls: List[str] = []

        for q in queries:
            urls = self._execute_search_query(q)
            for u in urls:
                # Exclude target store's own domain (on-site crawler handles that)
                # Exclude search engines and common scrapers
                if clean_domain in u or "duckduckgo.com" in u or "google.com" in u:
                    continue
                if u not in external_urls and is_safe_public_url(u):
                    external_urls.append(u)
            if len(external_urls) >= self.max_external_pages:
                break

        external_urls = external_urls[:self.max_external_pages]
        candidates: List[Dict[str, Any]] = []

        # Inspect external pages
        for page_url in external_urls:
            page_candidates = self._inspect_page(page_url, clean_company, clean_domain)
            candidates.extend(page_candidates)

        return candidates

    def _execute_search_query(self, query: str) -> List[str]:
        """Queries DuckDuckGo HTML endpoint and parses result URLs."""
        try:
            data = urllib.parse.urlencode({"q": query}).encode("utf-8")
            headers = {
                "User-Agent": USER_AGENTS[0],
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html,application/xhtml+xml"
            }
            req = urllib.request.Request(self.base_search_url, data=data, headers=headers)
            opener = urllib.request.build_opener(SafeRedirectHandler())
            with opener.open(req, timeout=self.timeout) as resp:
                if resp.getcode() != 200:
                    return []
                html = resp.read().decode("utf-8", errors="ignore")

            # Extract result links from DuckDuckGo HTML
            # Results appear in: <a class="result__url" href="..."> or uddg= encoded links
            raw_links = re.findall(r'href="(https?://[^"]+)"', html)
            resolved_links = []
            for link in raw_links:
                # Unpack DuckDuckGo redirect wrapper if present
                if "duckduckgo.com/l/?uddg=" in link:
                    m = re.search(r'uddg=([^&]+)', link)
                    if m:
                        link = urllib.parse.unquote(m.group(1))
                if is_safe_public_url(link):
                    resolved_links.append(link)
            return resolved_links
        except Exception:
            return []

    def _inspect_page(self, url: str, target_company: str, target_domain: str) -> List[Dict[str, Any]]:
        """Fetches an external page and extracts candidate evidence with cross-checks."""
        try:
            headers = {
                "User-Agent": USER_AGENTS[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            req = urllib.request.Request(url, headers=headers)
            opener = urllib.request.build_opener(SafeRedirectHandler())
            with opener.open(req, timeout=self.timeout) as resp:
                if resp.getcode() != 200:
                    return []
                # Max 1MB response size to prevent memory bloat
                content = resp.read(1048576).decode("utf-8", errors="ignore")

            # Cross-check: The page MUST mention the target company or target domain
            page_lower = content.lower()
            if target_company.lower() not in page_lower and target_domain.lower() not in page_lower:
                return []

            # Search for founder patterns in the text
            # e.g. "Founder of {company}", "{Name}, Co-Founder of {company}"
            pattern = re.compile(
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*,\s*(founder|co-founder|ceo|owner)\s*(?:of|at)\s*' +
                re.escape(target_company),
                re.IGNORECASE
            )

            discovered = []
            for match in pattern.finditer(content):
                name = match.group(1).strip()
                role = match.group(2).strip().title()
                discovered.append({
                    "name": name,
                    "role": role,
                    "email": None,
                    "email_origin": "PUBLIC_EXTERNAL",
                    "source_url": url,
                    "method": "ddgs_external_inspection",
                    "relationship": f"{role} of {target_company}"
                })
            return discovered
        except Exception:
            return []
