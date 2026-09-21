import urllib.request
import urllib.parse
import json
import base64
import re
import time
import subprocess
import ssl

client_id = 'w0_Bj6zG0uZrxVydfqW05Q'
client_secret = 'gtCjNNxJiA_P8VIDMqVFiG84lrKFMg'

auth = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
req = urllib.request.Request(
    'https://www.reddit.com/api/v1/access_token',
    data=b'grant_type=client_credentials',
    headers={
        'Authorization': f'Basic {auth}',
        'User-Agent': 'Mindmaxing/3.0 (by /u/aryupanchal)'
    }
)
resp = urllib.request.urlopen(req)
token = json.loads(resp.read().decode())['access_token']

queries = [
    'subreddit:reviewmyshopify',
    'subreddit:shopify "traffic but no sales"',
    'subreddit:ecommerce "traffic but no sales"',
    'subreddit:shopify "add to cart but no"'
]

found_posts = []

for q in queries:
    url = f'https://oauth.reddit.com/search?q={urllib.parse.quote(q)}&sort=new&limit=50'
    req = urllib.request.Request(
        url,
        headers={
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Mindmaxing/3.0 (by /u/aryupanchal)'
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            for child in data.get('data', {}).get('children', []):
                p = child['data']
                title = p.get('title', '')
                selftext = p.get('selftext', '')
                sub = p.get('subreddit', '')
                combined = title + ' ' + selftext
                
                urls = re.findall(r'https?://(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,})', combined)
                for dom in urls:
                    dom = dom.lower()
                    if dom.endswith('.in') or dom in ['reddit.com', 'preview.redd.it', 'imgur.com', 'myshopify.com', 'google.com', 'youtube.com', 'shopify.com', 'tiktok.com', 'instagram.com']:
                        continue
                    found_posts.append({
                        'domain': dom,
                        'title': title,
                        'sub': sub,
                        'permalink': f"https://reddit.com{p.get('permalink')}"
                    })
    except Exception as e:
        pass
    time.sleep(0.5)

seen = set()
unique_posts = []
for p in found_posts:
    if p['domain'] not in seen:
        seen.add(p['domain'])
        unique_posts.append(p)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def check_mx(dom):
    try:
        r = subprocess.run(["host", "-t", "mx", dom], capture_output=True, text=True, timeout=3)
        out = r.stdout.lower()
        return ("mail is handled by" in out or "has mx record" in out)
    except Exception:
        return False

def extract_email_from_site(dom):
    paths = ["/", "/pages/contact", "/pages/contact-us", "/policies/privacy-policy", "/policies/terms-of-service"]
    for p in paths:
        try:
            url = f"https://{dom}{p}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, context=ctx, timeout=4) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                # check shopify
                is_shopify = bool(re.search(r'cdn\.shopify\.com|myshopify\.com|window\.Shopify', html))
                if not is_shopify and p == "/":
                    return None, False
                emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', html)
                valid_emails = [e.lower() for e in emails if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.js', '.css', 'wixpress.com', 'shopify.com', 'sentry.io'))]
                # Filter out generic privacy/legal
                good = [e for e in valid_emails if not any(x in e for x in ['privacy@', 'legal@', 'abuse@', 'dmca@'])]
                if good:
                    return good[0], True
                elif valid_emails:
                    return valid_emails[0], True
        except Exception:
            continue
    return None, False

print(f"Testing {len(unique_posts)} candidate stores from Reddit for Shopify + Contact Email + MX:")
qualified_founders = []

for post in unique_posts:
    d = post['domain']
    em, is_shopify = extract_email_from_site(d)
    if is_shopify and em:
        mail_dom = em.split('@')[1]
        if check_mx(mail_dom):
            post['contact_email'] = em
            qualified_founders.append(post)
            print(f"  FOUNDER QUALIFIED: {d} -> {em} | r/{post['sub']} | Title: {post['title'][:50]}")
            if len(qualified_founders) >= 25:
                break
    time.sleep(0.3)

print(f"\nTotal Qualified Reddit Founders: {len(qualified_founders)}")
with open("/root/outbound/data/qualified_reddit_founders.json", "w") as f:
    json.dump(qualified_founders, f, indent=2)
