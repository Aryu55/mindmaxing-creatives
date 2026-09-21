import sqlite3
import subprocess

conn = sqlite3.connect("/root/outbound/data/mindmaxing_crm.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

candidates = [
    "grilldogsapparel.com", "slumbrband.com", "tryvayora.co", "framedcars.it",
    "glorytheshop.com", "memarinedivesupply.com", "jureynco.com", "riverzshop.ro",
    "thepawsitivespace.com", "blyssofficial.com", "funnyfuzzy.com", "kittysupps.com",
    "kilgourmd.com", "smalls.com", "shapellx.com", "hexclad.com", "norseorganics.co",
    "smoothspine.com", "luminskin.com", "guers.art", "lostgenclub.com", "poponveneers.com",
    "petkit.com", "woolx.com", "fromourplace.com"
]

def check_mx(dom):
    try:
        r = subprocess.run(["host", "-t", "mx", dom], capture_output=True, text=True, timeout=4)
        out = r.stdout.lower()
        return ("mail is handled by" in out or "has mx record" in out)
    except Exception:
        return False

print(f"Auditing {len(candidates)} stores:")
valid_count = 0
for d in candidates:
    c.execute("SELECT domain, company_name, contact_email, source, pain_trigger FROM leads WHERE domain = ?", (d,))
    r = c.fetchone()
    if r:
        em = r["contact_email"].strip()
        mail_dom = em.split("@")[1] if "@" in em else ""
        has_mx = check_mx(mail_dom)
        if has_mx:
            valid_count += 1
            print(f"  OK [{r['source'].upper()}] {r['domain']} ({r['company_name']}) -> {em} (MX: VALID)")
        else:
            print(f"  FAIL MX: {r['domain']} -> {em}")

print(f"\nTotal MX-verified leads: {valid_count} / {len(candidates)}")
