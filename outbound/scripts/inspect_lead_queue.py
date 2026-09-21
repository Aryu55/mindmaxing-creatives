import sqlite3, json, re, os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")

def check_queue():
    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute('''
        SELECT * FROM leads 
        WHERE contact_email IS NOT NULL AND contact_email != ''
        ORDER BY COALESCE(review_freshest_date, review_date, captured_at) DESC
    ''')
    leads = [dict(r) for r in c.fetchall()]

valid_queue = []
for l in leads:
    email = l.get('contact_email', '').strip('.,;:\'"')
    if not email or '@' not in email or email.startswith('u003e') or len(email.split('@')[0]) < 2:
        continue
    prefix = email.split('@')[0].lower()
    if prefix in ['legal', 'privacy', 'abuse', 'dmca', 'press', 'media', 'investor', 'careers', 'jobs', 'compliance', 'sms'] or prefix.endswith('-sms'):
        continue
    tel = {}
    if l.get('reviews_json'):
        try:
            tel = json.loads(l['reviews_json'])
        except Exception:
            pass
    lcp = tel.get('lcp') if isinstance(tel, dict) else None
    if not lcp and l.get('dominant_pattern'):
        m = re.search(r'LCP\s*([\d\.]+\s*s)', l['dominant_pattern'])
        if m:
            lcp = m.group(1)
    
    date_val = l.get('review_freshest_date') or l.get('review_date') or l.get('captured_at') or ''
    valid_queue.append({
        'domain': l['domain'],
        'company': l['company_name'],
        'email': email,
        'source': l['source'],
        'date': str(date_val)[:10],
        'lcp': lcp,
        'pattern': l.get('dominant_pattern')
    })

if __name__ == '__main__':
    check_queue()
