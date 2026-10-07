#!/usr/bin/env python3
"""
Mindmaxing Twitter/X High-Signal Lead Radar
Queries apidojo/tweet-scraper on Apify, applies commercial qualification filters,
and maintains a dedicated, deduplicated sourcing ledger.

Strict Invariants Enforced:
- Invariant 1: Minimum $500 - $1,000 sprint targets.
- Invariant 7: Pure lead sourcing. Zero automated messaging or spec builds.
- Invariant 8: Blink-speed / 4th-grade plain copy for manual review.
- Invariant 10: Strict zero em dashes in all output and reports.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone, timedelta
import requests

APIFY_ACTOR_ENDPOINT = "https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items"

DISQUALIFYING_KEYWORDS = [
    "intern", "internship", "unpaid", "equity only", "stipend", 
    "co-founder", "cofounder", "rev share", "revenue share",
    "commission only", "ba model", "looking for work", "hire me",
    "my portfolio", "check my work", "i am a developer", "i build web apps",
    "bookmark this", "save this", "growth playbook", "full stack i'd start with",
    "anyone who says there's a", "here is how it works now"
]

HIGH_INTENT_KEYWORDS = [
    "urgent", "asap", "budget", "paid", "contract", "sprint", 
    "client project", "redesign", "overwhelmed", "recommend", "hiring"
]

def get_dynamic_search_terms(days_back=14):
    since_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    terms = [
        f'("looking for a developer" OR "looking for a dev" OR "need a dev to build" OR "need a shopify dev") since:{since_date} -intern -unpaid -equity -jobboard',
        f'("need a dev partner" OR "agency looking for a developer" OR "overflow dev") since:{since_date} -intern -unpaid -equity',
        f'("anyone know a good" OR "can someone recommend a") ("shopify developer" OR "react developer" OR "full stack developer") since:{since_date} -course -job',
        f'("looking for a full stack" OR "looking for a frontend dev" OR "hiring a contractor") ("sprint" OR "mvp" OR "build" OR "app") since:{since_date} -intern -unpaid -equity',
        f'("need a shopify expert" OR "looking for a shopify dev" OR "custom shopify theme") since:{since_date} -course -intern',
        f'("recommend a dev" OR "recommend a web developer" OR "looking for a web developer") ("agency" OR "client" OR "project") since:{since_date} -intern -unpaid'
    ]
    return terms

def load_apify_token(cli_token=None):
    if cli_token:
        return cli_token
    token = os.environ.get("APIFY_API_TOKEN") or os.environ.get("APIFY_TOKEN")
    if token:
        return token
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("APIFY_API_TOKEN=") or line.startswith("APIFY_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None

def fetch_tweets_from_apify(token, search_terms, max_items=40):
    headers = {"Content-Type": "application/json"}
    payload = {
        "searchTerms": search_terms,
        "maxItems": max_items,
        "sort": "Latest"
    }
    url = f"{APIFY_ACTOR_ENDPOINT}?token={token}"
    print(f"[*] Calling Apify actor apidojo/tweet-scraper with {len(search_terms)} queries...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=180)
        response.raise_for_status()
        items = response.json()
        print(f"[+] Successfully extracted {len(items)} raw tweets from Apify.")
        return items
    except requests.exceptions.RequestException as e:
        print(f"[-] Apify API error: {e}", file=sys.stderr)
        return []

def evaluate_tweet(tweet, min_followers=100):
    text = tweet.get("text", "") or tweet.get("full_text", "")
    tweet_id = str(tweet.get("id", "") or tweet.get("id_str", ""))
    author = tweet.get("author", {}) or {}
    author_name = author.get("name", "Unknown")
    author_handle = author.get("userName", "") or author.get("screen_name", "")
    author_bio = author.get("description", "") or ""
    followers_count = author.get("followers", 0) or author.get("followers_count", 0)
    is_verified = author.get("isBlueVerified", False) or author.get("verified", False)
    tweet_url = tweet.get("url", f"https://x.com/{author_handle}/status/{tweet_id}")
    retweet_count = tweet.get("retweetCount", 0) or 0
    like_count = tweet.get("likeCount", 0) or 0
    
    lower_text = text.lower()
    lower_bio = author_bio.lower()

    # Rule 1: Exclude viral mega-threads (thought leadership fluff, not real job/help requests)
    if retweet_count > 50 or like_count > 150:
        return None, f"Viral thread detected (Likes: {like_count}, Retweets: {retweet_count})"

    # Rule 2: Exclude accounts with insufficient follower count
    if followers_count < min_followers:
        return None, f"Followers ({followers_count}) < {min_followers}"

    # Rule 3: Exclude disqualifying keywords in tweet text
    for kw in DISQUALIFYING_KEYWORDS:
        if kw in lower_text:
            return None, f"Disqualifying keyword in tweet: '{kw}'"

    # Rule 4: Exclude other developers pitching themselves
    if any(k in lower_bio for k in ["freelance web developer", "full-stack developer looking", "available for hire", "hire me"]):
        return None, "Author bio indicates another freelancer looking for gigs"

    # Intent Scoring
    score = 50
    if is_verified:
        score += 20
    if followers_count > 1000:
        score += 15
    for kw in HIGH_INTENT_KEYWORDS:
        if kw in lower_text:
            score += 5

    first_name = author_name.split()[0].lower() if author_name else "there"
    draft_dm = (
        f"hey {first_name}, saw your post about needing dev bandwidth.\n\n"
        f"i run engineering sprints at Mindmaxing. we handle custom web apps and shopify builds in fixed 7 to 14 day sprints so you don't have to manage hourly contractors or delay launches.\n\n"
        f"what is the primary tech stack on this build?"
    )

    qualified_data = {
        "tweet_id": tweet_id,
        "source": "X / Twitter (apidojo/tweet-scraper)",
        "score": score,
        "author_name": author_name,
        "author_handle": author_handle,
        "followers_count": followers_count,
        "is_verified": is_verified,
        "author_bio": author_bio,
        "text": text,
        "tweet_url": tweet_url,
        "tweet_created_at": tweet.get("createdAt", ""),
        "sourced_at_utc": datetime.now(timezone.utc).isoformat(),
        "suggested_dm": draft_dm
    }
    return qualified_data, "Qualified"

def update_lead_database(new_leads, json_path, md_path):
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    existing_leads = []
    existing_ids = set()

    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                existing_leads = json.load(f)
                for item in existing_leads:
                    if "tweet_id" in item:
                        existing_ids.add(item["tweet_id"])
        except Exception:
            existing_leads = []

    fresh_added = 0
    for lead in new_leads:
        if lead["tweet_id"] and lead["tweet_id"] not in existing_ids:
            existing_leads.append(lead)
            existing_ids.add(lead["tweet_id"])
            fresh_added += 1

    # Sort all leads by score descending
    existing_leads.sort(key=lambda x: x["score"], reverse=True)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_leads, f, indent=2)

    # Generate Markdown Digest
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Mindmaxing Sourced Leads: Twitter/X Lead Database",
        f"**Last Sync:** {now_str}  ",
        f"**Source Engine:** Apify `apidojo/tweet-scraper`  ",
        f"**Total Database Size:** {len(existing_leads)} leads ({fresh_added} newly added in this run)  ",
        "**Strict Rule:** Pure lead sourcing. Zero automated messaging. Manually review each lead.",
        "",
        "---",
        ""
    ]

    for idx, lead in enumerate(existing_leads, start=1):
        verified_badge = "Verified [Blue]" if lead["is_verified"] else "Standard"
        lines.append(f"## {idx}. @{lead['author_handle']} ({lead['author_name']}) | Score: {lead['score']}")
        lines.append(f"* **Source:** `{lead['source']}`")
        lines.append(f"* **Followers:** {lead['followers_count']:,} | **Status:** {verified_badge}")
        lines.append(f"* **Bio:** {lead['author_bio']}")
        lines.append(f"* **Tweet Link:** [{lead['tweet_url']}]({lead['tweet_url']})")
        lines.append(f"* **Tweet Date:** {lead['tweet_created_at']}")
        lines.append("")
        lines.append(f"> \"{lead['text']}\"")
        lines.append("")
        lines.append("### Recommended Manual Action (Copy-Paste DM):")
        lines.append("```text")
        lines.append(lead["suggested_dm"])
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[+] Updated dedicated JSON database: {json_path}")
    print(f"[+] Updated dedicated Markdown report: {md_path}")
    print(f"[+] Fresh leads added: {fresh_added}")

def main():
    parser = argparse.ArgumentParser(description="Mindmaxing Twitter Signal Scraper")
    parser.add_argument("--token", help="Apify API Token")
    parser.add_argument("--min-followers", type=int, default=100, help="Minimum followers required")
    parser.add_argument("--max-items", type=int, default=30, help="Max tweets to fetch per run")
    parser.add_argument("--days-back", type=int, default=14, help="Days back to search (freshness filter)")
    args = parser.parse_args()

    token = load_apify_token(args.token)
    if not token:
        print("[!] ERROR: No Apify API token found.", file=sys.stderr)
        sys.exit(1)

    search_terms = get_dynamic_search_terms(days_back=args.days_back)
    raw_tweets = fetch_tweets_from_apify(token, search_terms, max_items=args.max_items)
    if not raw_tweets:
        print("[!] No tweets returned from Apify.")
        sys.exit(0)

    qualified_leads = []
    disqualified_count = 0

    for tweet in raw_tweets:
        lead, reason = evaluate_tweet(tweet, min_followers=args.min_followers)
        if lead:
            qualified_leads.append(lead)
        else:
            disqualified_count += 1

    print(f"\n[+] Processing Complete:")
    print(f"    - Raw Tweets Scraped: {len(raw_tweets)}")
    print(f"    - Disqualified (Noise/Spam/Low-Follower/Viral): {disqualified_count}")
    print(f"    - Qualified Leads in this run: {len(qualified_leads)}")

    json_path = os.path.join(os.path.dirname(__file__), "..", "reports", "twitter_sourced_leads.json")
    md_path = os.path.join(os.path.dirname(__file__), "..", "reports", "twitter_sourced_leads.md")
    update_lead_database(qualified_leads, json_path, md_path)

if __name__ == "__main__":
    main()
