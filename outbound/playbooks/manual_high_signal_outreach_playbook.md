# Mindmaxing High-Signal Manual Outreach Master Playbook
**Version:** 1.0 (Live Production Reference)  
**Author:** Aryan Panchal / Mindmaxing  
**Core Thesis:** Win high-ticket ($1,000) engineering sprints on Reddit, X, and Threads by being the only "Strongest Signal" peer engineer in a sea of generic copy-paste agency spam.

---

## 1. The Core Philosophy (The "Video Editor" Realization)

When you look to hire someone (like a video editor), 99% of cold pitches are spammy, generic Google Drive links:
> *"Hey bro, I can edit your videos, hire me: [link]"* ➔ **Deleted in 2 seconds.**

What actually closes a client is someone who demonstrates **forensic context before asking for anything**:
> *"Hey, saw your video on X. Your first 3 seconds drop 40% retention because of the static text hook. For a creator in your exact space, we fixed this by doing a 1.2s dynamic zoom + sound riser, boosting 30s retention by 22%. Here is the exact side-by-side clip, took 3 hours, cost $120. If you want, I drafted a storyboard for your next topic."*

### Strategic Invariants (Strict Rules):
1. **The 1-Client Focus Invariant:** Target 1 client at $1,000 (₹75k–₹85k) or 2 at $500. Never take low-ticket clients ($50–$100) that demand endless manual babysitting.
2. **Intent-Signal Over Volume:** Only engage posts where founders state **explicit requirements** or **specific technical bottlenecks**.
3. **Proof-Before-Pitch:** Walk in with a pre-analyzed solution, architecture diagram, or forensic precedent before pitching any service.
4. **No Inferred Poverty:** Qualify by whether a real business/cash flow exists (e.g. active store, agency clients, revenue), not guessing from webmail.

---

## 2. Platform Discovery Logistics (How to Find Real Operators)

### A. The Vetting Filter (15-Second Profile Inspection)
| ❌ Immediate Disqualifiers (Skip Instantly) | 🟢 High-Signal Operator (Engage Immediately) |
| :--- | :--- |
| Mentions *"equity"*, *"co-founder"*, *"rev share"* | Has an **existing business, agency, or store** (already cash-flowing) |
| "I have an idea for an app" | "My manual workflow is breaking / we need a custom portal for our clients" |
| Brand new account (created days ago) | Established account posting real operational/business challenges |
| Vague: "Need an app made cheap" | Specific: "Need a React/Node MVP with Stripe & Supabase" |

---

### B. The Google Dorks (Use with `Tools → Past 24 hours` or `Past week`)

#### 1. "Agency Quote Shock" (Highest Budget Signal 🔥)
Founders who have money, got sticker shock from a $20k agency, and want a lean developer:
```text
site:reddit.com/r/smallbusiness OR site:reddit.com/r/agency ("agency quoted" OR "quote from an agency" OR "dev agency wants") ("app" OR "software" OR "portal") -"equity"
```
```text
site:reddit.com/r/SaaS OR site:reddit.com/r/entrepreneur ("quoted" OR "estimate") ("MVP" OR "developer" OR "build an app") -"equity" -"cofounder"
```

#### 2. "Client Portals & Internal Tool Bottlenecks" (Real Cash-Flowing Businesses)
Agencies and companies outgrowing Google Sheets:
```text
site:reddit.com/r/agency OR site:reddit.com/r/smallbusiness ("need a client portal" OR "build a custom portal" OR "looking for a developer to build") -"equity"
```

#### 3. "Shopify Private & Custom App Requests" (High Ticket Ecom)
```text
site:reddit.com/r/shopify OR site:reddit.com/r/ecommerce ("custom app" OR "private app" OR "hire a developer to build") -"review my store" -"dropshipping"
```

---

### C. Direct Reddit Internal Search (Scoped by Subreddit)
*Reddit's native search engine fails on complex `OR` queries. Use scoped queries with `Sort: New` and `Time: Past Week`:*
* **In `r/shopify`:** `subreddit:shopify "custom app" OR "private app"`
* **In `r/agency`:** `subreddit:agency "client portal"`
* **In `r/SaaS`:** `subreddit:SaaS "looking for a developer"`
* **In `r/MicroSaaS`:** `subreddit:MicroSaaS "developer"`

---

### D. X (Twitter) Search Operators (Search Bar → "Latest" Tab)
* **Founders asking their network for dev recommendations:**
  ```text
  ("recommend a developer" OR "recommend a dev" OR "who can build") ("app" OR "MVP" OR "portal") -filter:replies -equity
  ```
* **Founders directly hiring for a build:**
  ```text
  ("looking for a developer" OR "need a developer") ("build an app" OR "MVP" OR "web app") -filter:replies -equity -crypto
  ```
* **Founders venting about agency quotes:**
  ```text
  ("agency quoted" OR "dev agency quote" OR "cost to build an app") -filter:replies
  ```

---

## 3. The Conversational Mechanics (The Public Reply + Companion DM)

```
[Prospect Posts Requirements]
             │
             ▼
[Step 1: Public Forensic Reply] ──► Drops 80% of technical value publicly
             │                      Establishes authority + notifies prospect
             ▼
[Step 2: Companion DM] ─────────► Delivers the 1-page architecture artifact
             │                      Triggers prospect to check "Message Requests"
             ▼
[Step 3: Inbound DM Response] ──► Prospect asks questions / books $1,000 sprint
```

### The 4-Part Anatomy of the Forensic Reply:
1. **The Context Anchor:** Prove you actually read and understood their specific business context.
2. **The Forensic Precedent:** Mention an identical build you wrapped recently.
3. **The Concrete Specs:** State the exact time (e.g. 10–12 days), stack, and budget tier ($1,000) to remove agency price fear.
4. **The Critical Pitfall:** Point out the #1 mistake they are about to make before writing code.
5. **The Soft Artifact Offer:** Offer a 1-page architecture schema or doc in DMs.

---

## 4. Field-Tested Templates & Live Case Studies

### Live Example 1: Shopify Multi-Location B2B Inventory Gating
* **Target Thread:** [Separate stock B2B vs B2C](https://www.reddit.com/r/shopify/comments/1wl1bjj/separate_stock_b2b_vs_b2c/) (`u/Dobey`)
* **Context:** Founder cannot afford Shopify Plus ($2,000/mo) and third-party apps are $150/mo ($1,800/yr) and bloated. Wants custom code to separate B2B vs DTC warehouse inventory.
* **The Forensic Comment:**
```markdown
You're 100% right to avoid paying $150/mo ($1,800/yr) for an app that just does inventory routing. And Shopify Plus is absurd overkill for this stage.

The clean way to architect this without Plus or bloated monthly apps is through location-based inventory scoping via a lightweight private app / theme hook:

1. Customer Authentication: When a customer logs in, check their customer tag (e.g., tag: b2b_approved).
2. Location-Specific Scoping: In your Shopify backend, you already have separate Location IDs for B2B Warehouse and DTC Warehouse. Instead of letting the theme read global available inventory, you fetch stock specifically mapped to that user's Location ID via the Storefront API / InventoryLevel endpoint.
3. Cart Gating: You bind the PDP quantity selector and cart validation to that location’s available quantity. If DTC has 5 units and B2B has 0 units, the B2B customer sees "Out of stock for wholesale" even though the DTC store is active.

The biggest mistake to avoid here is trying to do this purely in client-side Theme Liquid without checkout validation—if a B2B user knows the direct variant ID, they can bypass the frontend theme. You need a simple backend function or webhook validating location stock before order creation.

We literally built a custom location-gating script for a wholesale brand last month to kill their $120/mo app subscription—took 3 days to deploy and saved them $1,400+/year permanently.

I actually sketched the API flow and theme logic for how we handled the checkout validation. Happy to send the spec over in DMs if you want to see how to structure it yourself.
```

---

### Template 2: Custom Client Portal / Agency Workflow
* **For:** Agency owners asking how to build a custom client portal or automate Google Sheets.
```markdown
Saw your post about wanting to build the client portal for your [agency / consulting service].

A lot of traditional dev shops will try to quote you $15k–$20k and 3 months for this, but if your core requirement is client dashboard + file deliverables, that’s complete overkill.

We just wrapped an almost identical custom portal for a [similar niche operator]:
- The Bottleneck: Clients were emailing constantly for asset updates, wasting 12+ hours/week.
- The Build: Lightweight Next.js + Supabase portal with magic-link auth (no passwords) and Stripe billing.
- The Numbers: Shipped in 11 days, total sprint was $1,000, and monthly infrastructure cost is $0 on Vercel/Supabase free tiers.

The #1 trap to avoid is building custom messaging or chat into v1—embed a Crisp or Slack webhook integration instead; that alone cuts 2 weeks of development time.

Mapped out the schema and architecture doc for that build. Shot it over to your DMs so you have the visual.
```

---

### Template 3: Companion DM (Send After Public Reply)
```markdown
Hey [Name], saw your post about wanting to build [App Name / Concept].

Left a quick technical breakdown on your thread, but wanted to drop the actual architecture diagram here so you have it handy:

[Attach screenshot of schema / tech flow]

Notice how we routed [specific component]—that’s how we kept the sprint under 2 weeks and avoided expensive third-party subscription bloat.

Zero pitch, just wanted to pass along what we learned building this so you don't overpay an agency. If you ever want a 2nd pair of eyes on the tech spec when you're ready to build, happy to bounce ideas.
```

---

## 5. Active Campaign & Infrastructure State (Reference Snapshot)

### A. The Automated Outbound Campaign
* **Campaign Name:** `getleads_dtc_top25` (*Angle A: "Meta Ghost Clicks"*)
* **Audited Leads:** 99 GetLeads DTC Shopify founders audited via Google Lighthouse mobile PageSpeed. Top 25 worst mobile LCPs (14.3s to 47.2s) approved (`HUMAN_APPROVED`).
* **Dispatch Schedule on VPS (`72.62.230.37`):**
  * **Wave 1 (East/Central):** 13:30 UTC = 7:00 PM IST (12 leads)
  * **Wave 2 (West/Pacific):** 16:30 UTC = 10:00 PM IST (13 leads)

### B. Mailbox Health Ledger
* **16 Active Mailboxes (`KEEP` status):** Baseline 1/day, 100% clean Google seed placement, 100% passing SPF/DKIM/DMARC.
  * Primary sender `aryan@mindmaxing.info` (PFP active with Mindmaxing logo GIF).
  * `engineering@mindmaxing.info` (Verified).
  * `aryan@mindmaxing.online` (Recovered & active).
* **9 Paused Mailboxes (`HOLD_SEED_SPAM`):**
  * Auto-paused by safety circuit-breaker after diagnostic pings landed in seed spam folders.
  * Self-healing automatically via nightly crons (requires 2 clean inbox pings across separate dates and seeds).
