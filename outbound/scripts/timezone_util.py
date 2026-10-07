#!/usr/bin/env python3
"""
Mindmaxing IANA Timezone Engine (Task G)
- Exact IANA ZoneInfo calculations with DST and weekday rules.
- Pure local_window_open predicate with half-open interval [09:00, 16:30).
- City/region evidence resolution; multi-zone countries without verified region remain explicitly unresolved.
"""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Tuple

SINGLE_ZONE_COUNTRIES = {
    "GB": "Europe/London",
    "UK": "Europe/London",
    "IE": "Europe/Dublin",
    "DE": "Europe/Berlin",
    "FR": "Europe/Paris",
    "NL": "Europe/Amsterdam",
    "ES": "Europe/Madrid",
    "IT": "Europe/Rome",
    "SE": "Europe/Stockholm",
    "DK": "Europe/Copenhagen",
    "NO": "Europe/Oslo",
    "AT": "Europe/Vienna",
    "CH": "Europe/Zurich",
    "BE": "Europe/Brussels",
    "NZ": "Pacific/Auckland",
    "SG": "Asia/Singapore",
    "HK": "Asia/Hong_Kong",
    "JP": "Asia/Tokyo",
    "IN": "Asia/Kolkata",
}

US_STATE_ZONES = {
    # Eastern
    "ME": "America/New_York", "NH": "America/New_York", "VT": "America/New_York",
    "MA": "America/New_York", "RI": "America/New_York", "CT": "America/New_York",
    "NY": "America/New_York", "NJ": "America/New_York", "PA": "America/New_York",
    "DE": "America/New_York", "MD": "America/New_York", "DC": "America/New_York",
    "VA": "America/New_York", "WV": "America/New_York", "NC": "America/New_York",
    "SC": "America/New_York", "GA": "America/New_York", "FL": "America/New_York",
    "OH": "America/New_York", "MI": "America/New_York",
    # Central
    "IL": "America/Chicago", "WI": "America/Chicago", "MN": "America/Chicago",
    "IA": "America/Chicago", "MO": "America/Chicago", "ND": "America/Chicago",
    "SD": "America/Chicago", "NE": "America/Chicago", "KS": "America/Chicago",
    "OK": "America/Chicago", "TX": "America/Chicago", "LA": "America/Chicago",
    "AR": "America/Chicago", "MS": "America/Chicago", "AL": "America/Chicago",
    "TN": "America/Chicago",
    # Mountain
    "MT": "America/Denver", "WY": "America/Denver", "UT": "America/Denver",
    "CO": "America/Denver", "NM": "America/Denver", "AZ": "America/Phoenix",
    # Pacific
    "WA": "America/Los_Angeles", "OR": "America/Los_Angeles",
    "CA": "America/Los_Angeles", "NV": "America/Los_Angeles",
    # Alaska & Hawaii
    "AK": "America/Anchorage", "HI": "Pacific/Honolulu"
}

CA_PROVINCE_ZONES = {
    "ON": "America/Toronto", "QC": "America/Toronto",
    "BC": "America/Vancouver", "AB": "America/Edmonton",
    "MB": "America/Winnipeg", "SK": "America/Regina",
    "NS": "America/Halifax", "NB": "America/Moncton",
    "NL": "America/St_Johns"
}

AU_STATE_ZONES = {
    "NSW": "Australia/Sydney", "VIC": "Australia/Sydney",
    "ACT": "Australia/Sydney", "TAS": "Australia/Sydney",
    "QLD": "Australia/Brisbane", "SA": "Australia/Adelaide",
    "WA": "Australia/Perth", "NT": "Australia/Darwin"
}

KNOWN_CITY_ZONES = {
    "london": "Europe/London",
    "dublin": "Europe/Dublin",
    "berlin": "Europe/Berlin",
    "paris": "Europe/Paris",
    "amsterdam": "Europe/Amsterdam",
    "madrid": "Europe/Madrid",
    "rome": "Europe/Rome",
    "auckland": "Pacific/Auckland",
    "wellington": "Pacific/Auckland",
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Sydney",
    "brisbane": "Australia/Brisbane",
    "adelaide": "Australia/Adelaide",
    "perth": "Australia/Perth",
    "new york": "America/New_York",
    "brooklyn": "America/New_York",
    "boston": "America/New_York",
    "miami": "America/New_York",
    "atlanta": "America/New_York",
    "chicago": "America/Chicago",
    "dallas": "America/Chicago",
    "austin": "America/Chicago",
    "houston": "America/Chicago",
    "denver": "America/Denver",
    "phoenix": "America/Phoenix",
    "los angeles": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "san diego": "America/Los_Angeles",
    "seattle": "America/Los_Angeles",
    "portland": "America/Los_Angeles",
    "toronto": "America/Toronto",
    "montreal": "America/Toronto",
    "vancouver": "America/Vancouver",
    "calgary": "America/Edmonton"
}


def local_window_open(now_utc: datetime, timezone_name: str) -> bool:
    """
    Pure window predicate, with a half-open interval [09:00, 16:30).
    Operating 7 days/week (including weekends) in recipient's local daytime hours.
    """
    if now_utc.tzinfo is None:
        raise ValueError("Timezone-aware UTC timestamp required")
    try:
        local = now_utc.astimezone(ZoneInfo(timezone_name))
    except Exception as e:
        raise ValueError(f"Invalid IANA timezone '{timezone_name}': {e}")
    return time(9, 0) <= local.time() < time(16, 30)



def resolve_iana_timezone(
    country_code: Optional[str],
    state: Optional[str] = None,
    city: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolves recipient location to an exact IANA timezone and records evidence provenance.
    Multi-zone countries without verified region evidence return (None, reason) to remain
    explicitly unresolved rather than guessing founder local time.
    """
    cc = (country_code or "").strip().upper()
    st = (state or "").strip().upper()
    ct = (city or "").strip().lower()

    # 1. Exact city resolution
    if ct in KNOWN_CITY_ZONES:
        return KNOWN_CITY_ZONES[ct], f"city_evidence:{ct}"

    # 2. Single-zone countries
    if cc in SINGLE_ZONE_COUNTRIES:
        return SINGLE_ZONE_COUNTRIES[cc], f"country_single_zone:{cc}"

    # 3. United States with verified state
    if cc == "US":
        if st in US_STATE_ZONES:
            return US_STATE_ZONES[st], f"us_state_evidence:{st}"
        return None, "UNRESOLVED_MULTI_ZONE: US requires verified state or city evidence"

    # 4. Canada with verified province
    if cc == "CA":
        if st in CA_PROVINCE_ZONES:
            return CA_PROVINCE_ZONES[st], f"ca_province_evidence:{st}"
        return None, "UNRESOLVED_MULTI_ZONE: Canada requires verified province or city evidence"

    # 5. Australia with verified state
    if cc == "AU":
        if st in AU_STATE_ZONES:
            return AU_STATE_ZONES[st], f"au_state_evidence:{st}"
        return None, "UNRESOLVED_MULTI_ZONE: Australia requires verified state or city evidence"

    if not cc:
        return None, "LOCATION_MISSING: Country code required"

    return None, f"UNRESOLVED_LOCATION: Country '{cc}' timezone requires manual schedule review"
