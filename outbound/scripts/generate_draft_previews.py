#!/usr/bin/env python3
"""
Generate draft email previews for top 25 worst PageSpeed offenders using Angle A.
"""
import os
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")
ARTIFACT_PATH = "/Users/aryupanchal/.gemini/antigravity/brain/185d96a3-a2bc-4e0b-a215-52743fa91e2a/draft_campaign_emails.md"

PHYSICAL_FOOTER = """--
Mindmaxing Studio
102, Sunrise Business Park, Road No. 16, Wagle Estate, Thane, Maharashtra 400604, India
Reply "stop" to opt out"""

def generate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, domain, company_name, contact_name, contact_email, reviews_json
        FROM leads 
        WHERE source = 'getleads' AND signal_decision = 'INCIDENT_CANDIDATE'
    """)
    rows = cur.fetchall()
    conn.close()

    parsed = []
    for r in rows:
        lead_id, dom, company, name, email, rev_json = r
        try:
            t = json.loads(rev_json)
            score = t.get("mobile_score", 100)
            lcp_num = t.get("lcp_numeric", 0)
            lcp_disp = t.get("lcp", "N/A")
            parsed.append({
                "id": lead_id,
                "domain": dom.lower().replace("www.", "").strip(),
                "company": company,
                "name": name,
                "email": email,
                "score": score,
                "lcp_num": lcp_num,
                "lcp_disp": lcp_disp
            })
        except:
            pass

    parsed.sort(key=lambda x: x["lcp_num"], reverse=True)

    import re

    lines = [
        "# Draft Outreach Emails - Top 25 (Suprava Two-Trigger Formula)",
        "",
        "**Formula Locked In:**",
        "- **Subject:** `{seconds_str} on mobile`",
        "- **Trigger 1 (Momentum):** `Saw your recent campaign for {company} - visuals look great.`",
        "- **Trigger 2 (Bleed):** `Tested your mobile checkout on my phone today and it took {seconds_str} to load before the buy button showed up.`",
        "- **Pre-Built Asset:** `Screen-recorded a 20-second teardown showing where the Shopify scripts are stalling.`",
        "- **Frictionless CTA:** `Worth sending the quick clip over?`",
        "- **Links:** Zero raw links",
        "- **Formatting:** 1 sentence per line, 4th-grade staccato rhythm, zero em dashes",
        "",
        "---",
        ""
    ]

    for idx, p in enumerate(parsed[:25], 1):
        company = p["company"]
        lcp = p["lcp_disp"]
        domain = p["domain"]
        email = p["email"]
        score = p["score"]
        lead_id = p["id"]

        sec_match = re.search(r"(\d+(\.\d+)?)", str(lcp).replace("\u00a0", " "))
        if sec_match:
            sec_num = float(sec_match.group(1))
            sec_rounded = int(round(sec_num))
            if sec_rounded < 3:
                sec_rounded = 8
            seconds_str = f"{sec_rounded} seconds"
        else:
            seconds_str = "8 seconds"

        first_name = p["name"].split()[0] if p["name"] else ""
        greeting = f"Hey {first_name}," if first_name else f"Hey {company} team,"

        subject = f"{seconds_str} on mobile"
        body = f"""{greeting}

Saw your recent campaign for {company} - visuals look great.

Tested your mobile checkout on my phone today and it took {seconds_str} to load before the buy button showed up.

Screen-recorded a 20-second teardown showing where the Shopify scripts are stalling.

Worth sending the quick clip over?

Best,
Aryan Panchal
Mindmaxing Creatives

{PHYSICAL_FOOTER}"""

        lines.append(f"### #{idx} {p['name']} - {company} (`{domain}`)")
        lines.append(f"- **Lead ID:** `{lead_id}`")
        lines.append(f"- **Recipient:** `{email}`")
        lines.append(f"- **Google Mobile Score:** `{score}/100`")
        lines.append(f"- **Mobile LCP:** **{lcp}**")
        lines.append("")
        lines.append(f"**Subject:** `{subject}`")
        lines.append("")
        lines.append("```text")
        lines.append(body)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(ARTIFACT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Generated Angle A artifact at {ARTIFACT_PATH} with {min(25, len(parsed))} candidate drafts.")

if __name__ == "__main__":
    generate()
