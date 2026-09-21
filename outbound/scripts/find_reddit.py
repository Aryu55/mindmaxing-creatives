import urllib.request
import urllib.parse
import json
import base64
import re
import time

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
                    if dom not in ['reddit.com', 'preview.redd.it', 'imgur.com', 'myshopify.com', 'google.com', 'youtube.com', 'shopify.com', 'tiktok.com', 'instagram.com']:
                        found_posts.append({
                            'domain': dom,
                            'title': title,
                            'sub': sub,
                            'permalink': f"https://reddit.com{p.get('permalink')}"
                        })
    except Exception as e:
        print('Error:', e)
    time.sleep(1)

seen = set()
unique = []
for p in found_posts:
    if p['domain'] not in seen:
        seen.add(p['domain'])
        unique.append(p)

print(f"Total candidate stores found in Reddit: {len(unique)}")
for u in unique[:25]:
    print(f"- {u['domain']} in r/{u['sub']}: {u['title'][:70]}")
