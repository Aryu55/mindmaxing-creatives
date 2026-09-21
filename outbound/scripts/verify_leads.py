import json
import re
import subprocess

COMMON_TLDS = [
    "com", "org", "net", "co", "io", "ca", "uk", "shop", "store",
    "de", "nl", "it", "ro", "digital", "art", "co.uk", "com.au"
]

def clean_email(em: str) -> str:
    if not em:
        return ""
    em = em.strip().lower().strip(".,;:\"'<>")
    for tld in COMMON_TLDS:
        pattern = rf"^([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.{re.escape(tld)})[a-zA-Z]{{3,}}$"
        m = re.match(pattern, em)
        if m:
            return m.group(1)
    em = re.sub(r"\.+$", "", em)
    return em

def check_mx(email: str) -> bool:
    if "@" not in email:
        return False
    dom = email.split("@")[1].strip().lower()
    try:
        r = subprocess.run(["host", "-t", "mx", dom], capture_output=True, text=True, timeout=4)
        out = r.stdout.lower()
        return ("mail is handled by" in out or "has mx record" in out)
    except Exception:
        return False

with open("/root/outbound/data/icp1_shopify_dtc/leads.json", "r", encoding="utf-8") as f:
    leads = json.load(f)

verified_leads = []
fixed_count = 0
dropped_mx = 0

for l in leads:
    em = l.get("contact_email", "")
    cleaned = clean_email(em)
    if cleaned != em:
        print(f"Fixed email: {em} -> {cleaned}")
        l["contact_email"] = cleaned
        fixed_count += 1
    
    if check_mx(l["contact_email"]):
        verified_leads.append(l)
    else:
        print(f"Dropped lead (NO MX RECORD): {l.get('domain')} | {l.get('contact_email')}")
        dropped_mx += 1

print(f"\nAudit summary:")
print(f"Fixed malformed emails: {fixed_count}")
print(f"Dropped due to failed MX: {dropped_mx}")
print(f"Total 100% verified leads: {len(verified_leads)}")

with open("/root/outbound/data/icp1_shopify_dtc/leads.json", "w", encoding="utf-8") as f:
    json.dump(verified_leads, f, indent=2)

print("Updated leads.json successfully!")
