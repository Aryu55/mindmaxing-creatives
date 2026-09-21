# 🚀 Mindmaxing Creatives — Product Studio Portfolio

> **"We notice problems and then go build the thing."**

**Mindmaxing Creatives** is an independent product studio based in India. This repository contains the flagship interactive web experience for **[mindmaxing.one](https://mindmaxing.one)** — showcasing 11 active products, custom 3D shaders, an interactive Resend-powered contact lead engine, and a dedicated founder showcase for **Aryan**.

---

## 🌐 Live URLs

- **Official Domain**: [https://mindmaxing.one](https://mindmaxing.one)
- **Cloudflare Pages Production**: [https://mindmaxing-creatives.pages.dev](https://mindmaxing-creatives.pages.dev)
- **GitHub Repository**: [https://github.com/Aryu55/mindmaxing-creatives](https://github.com/Aryu55/mindmaxing-creatives)

---

## ⚡ Key Highlights & Features

- **Interactive 3D WebGL Background Shaders**: Custom Three.js liquid FBM noise field that dynamically shifts ambient gradient palettes as you scroll through products.
- **3D Morphing Glass/Metal Orb**: Real-time vertex displacement shader reacting to cursor position and scroll depth.
- **GSAP Panel & Typography Reveals**: Fluid scroll-triggered line reveals and panel transitions matching high-end design aesthetics.
- **Resend-Powered Serverless Lead Engine**: Integrated glassmorphism contact modal that POSTs lead inquiries directly to Cloudflare Pages Serverless Function (`/functions/api/contact.js`) which proxies secure emails to `mindmaxxxing@gmail.com` via Resend API.
- **Meet the Founder Showcase**: Dedicated section spotlighting founder **Aryan**, highlighting key achievements (4 profitable AI products, Fortune 500 training, ₹20 Cr+ alumni earnings in 2025, 1:1 C-suite consulting).
- **100% Mobile Optimized**: Responsive fluid typography (`clamp()`), automatic rail index collapsing on mobile viewports, touch-friendly bottom-sheet lead modal with iOS 16px auto-zoom prevention.
- **14 Active Showcase Products**:
  1. **SafeSpot** (`trysafespot.com`): Pre-date verification & background safety checking engine.
  2. **ABX Engine** (`mindmaxing.one`): Shopify Liquid A/B testing & CRO telemetry engine.
  3. **Hisaab** (`hisaab-lilac-rho.vercel.app`): Employment FnF legal notice & Labour Commissioner pack builder.
  4. **Before Token** (`before-token.vercel.app`): Real estate brochure vs MahaRERA registry risk screener.
  5. **Bhoomiputra Foundation** (`bhoomi-roots-foundation.lovable.app`): Digital platform protecting coastal fishing & farming communities in Mumbai.
  6. **Freedoms AI** (`freedoms.ai/join`): Voice capture & nightly memory pass AI journaling assistant.
  7. **BUKL** (`bukl.co`): Ultralight friction-lock belt direct-to-consumer storefront.
  8. **Xalt Watches** (`xaltwatches.com`): Swiss luxury timepiece storefront with bilingual Gulf checkout.
  9. **Manifest** (`manifest.leblessed.com/lp01`): Direct response book funnel & conversion engine.
  10. **WESHUB** (`weshub.lovable.app`): Multi-brand collective (Societe events, IHC master franchise expansion into India, Regenerate AI).
  11. **Saffron Origins** (`saffronorigins.com`): Direct-to-consumer luxury storefront for pure Kashmiri saffron.
  12. **WhatsApp Autopilot** (`whisper-buddy-21.mindmaxing.workers.dev`): 5-stage automated webinar attendance & support bot.
  13. **Glaze** (`getglaze.in`): Anonymous peer feedback loop app.
  14. **Janus** (`janus-engine.vercel.app`): Multi-business content command centre and DM pipeline.
- **Dedicated Navigation & Pages**:
  - `About Us` (`/about.html`)
  - `Case Studies` (`/case-studies.html`)
  - `Privacy Policy` (`/privacy.html`)
  - `Terms of Service` (`/terms.html`)

---

## 🛠️ Architecture & Tech Stack

- **Core**: HTML5, Vanilla JavaScript (ESNext), Three.js (r128), GSAP (3.12.5)
- **Design & Styling**: Custom Dark Glassmorphism Design System, Fluid Typography (`clamp()`), Custom SVG Chevron Select Dropdowns, HSL Tailored Palettes
- **Serverless Edge Backend**: Cloudflare Pages Functions (`/functions/api/contact.js`)
- **Transactional Email**: Resend API (`api.resend.com/emails`)
- **Hosting & Infrastructure**: Cloudflare Pages, Cloudflare DNS (`mindmaxing.one`)

---

## 📜 Full Changelog & Evolution History

### v2.1.0 (2026-09-21)
- **Nightly Campaign Review & Mailbox Control System (v2.1)**:
  - Built rules-based nightly review engine (`daily_mailbox_planner.py`) running at 00:30 IST (19:00 UTC) with explicit budget periods (`YYYY-MM-DD-IST`).
  - Immediate baseline sending (cap 1) upon passing 1 clean diagnostic in Inbox with SPF/DKIM/DMARC pass, with 7-day maturation governing volume increases ($1 \to 2 \to 3$) up to a maximum cap of 3.
  - Unified atomic touch reservation (`volume_controller.reserve_and_claim_job()`) running health checks, recipient suppression, sequence immutability, and job claiming in one short SQLite transaction before SMTP dispatch.
  - Strictly read-only status reporting (`outbound_status.py report --today`).
  - Enabled SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and 30s busy timeout for high-concurrency dispatch.
- **Reddit Signal Qualification Engine (v2.2 Astra Specification)**:
  - Replaced keyword matching with pure evaluator `evaluate_reddit_signal()` enforcing 7-day source freshness, storefront component malfunction evidence (cart drawer, checkout button, liquid errors), operator ownership, and negation/hypothetical filtering.
  - Implemented 5-tier taxonomy: `INCIDENT_CANDIDATE`, `REVIEW_REQUIRED`, `NO_MATCH`, `STALE`, `INVALID_SOURCE` with additive database schema migration.
  - Reclassified all 9 legacy Reddit leads factually as `NO_MATCH` with zero speculative budget inferences.

### v1.8.0 (2026-09-19)
- **ABX Engine Integration**: Featured the ABX Engine (Shopify Liquid A/B testing & CRO telemetry suite) as flagship Panel 02 on the homepage and added a dedicated case study card.
- **Case Studies Page Overhaul (`/case-studies.html`)**: Fully restructured from SafeSpot-first to Shopify DTC-first. Built interactive category filter pills (All / Shopify DTC / Growth & Meta Ads / Custom Software) and replaced dense paragraphs with an ultra-lean 2-column card grid with high-contrast metric pills.
- **Outbound Harvester & CRM Infrastructure**:
  - Built autonomous Reddit OAuth Harvester (`reddit_harvester.py`) targeting founders with active funnel bottlenecks and ad spend bleed.
  - Implemented multi-stage verification: live Linux DNS MX record verification (`host -t mx`), strict TLD boundary sanitization, and automated bare `.myshopify.com` rejection.
  - Added strict geography/currency gatekeeping: automated detection and rejection of INR (`₹`, `INR`), `+91` numbers, and domestic COD signals to ensure 100% foreign DTC ICP targeting.
  - Implemented biological Poisson/Gaussian timing jitter and rotating modern browser header profiles (macOS/Win11 Chrome/Safari/Firefox).
  - Migrated SQLite CRM (`mindmaxing_crm.db`) with dedicated columns for `source`, `subreddit`, `post_title`, `post_url`, and `post_author`.
  - Built two-way cross-source runtime deduplication between Trustpilot and Reddit scrapers (guaranteeing 0 duplicate emails or domains).
  - Upgraded Outbound Dispatcher (`dispatcher.py` v2.2) to sort queue by freshest pain signals first and generate hyper-personalized Touch 1 openers quoting the founder's exact Reddit post title and specific problem.

### v1.7.0 (2026-08-19)
- **Studio Repositioning (Full-Stack Product & Growth Studio)**: Repositioned Mindmaxing Creatives to feature both **Aryan Panchal** (Software & AI Engineering Founder) and **Himanshu Agrawal** (Creative Strategy & Performance Marketing Partner).
- **Added 6 Performance Marketing & Growth Case Studies**: Added Zyron Tech (4.6X ROAS on Google Shopping), Alcohol Ecom ($238K revenue at 9X ROAS), Zupee (+117K followers in 6 months), D2C Fitness (5+ ROAS), Solar Solutions (80% CAC drop), and Healthy Meals Cafe (+40% lead growth).
- **Dedicated Client Pitch Page (`/swim.html`)**: Built custom high-converting partnership pitch for Command Studio (Rajvi Damania) to scale upcoming swimwear brands MACHHLI & MAG.
- **Created & Deployed 2 Live Concept Storefront Prototypes**:
  - **MACHHLI Swimwear**: [https://machhli.vercel.app](https://machhli.vercel.app)
  - **MAG SWIMS**: [https://mag-eta.vercel.app](https://mag-eta.vercel.app)
- **Updated `about.html` and `case-studies.html`**: Added co-founders profiles, full capability matrix, and metric-backed growth case studies.

### v1.6.0 (2026-08-01)
- Added **WESHUB** (`https://weshub.lovable.app/`) and **Saffron Origins** (`https://www.saffronorigins.com/`) as 13th and 14th showcase products.
- Integrated deep-dive case studies for both products into `/case-studies.html` detailing bottleneck, engineering solution, and key outcomes.
- Expanded scroll sentinel system to 14 steps (`1400vh` scroll track) and updated Three.js background shader palette transitions.

### v1.5.0 (2026-08-01)
- Added **Bhoomiputra Foundation** (`https://bhoomi-roots-foundation.lovable.app/`) as project #04 across portfolio and case study grid.
- Created dedicated **Case Studies Deep-Dive Page** (`/case-studies.html`) detailing problem statements, technical architecture, and key metrics for all 12 products.
- Added universal high-contrast typography system (`#ffffff` headings, `#e2e8f0` body text, glowing orange tag pills).
- Created `About Us` (`/about.html`), `Privacy Policy` (`/privacy.html`), and `Terms of Service` (`/terms.html`) pages.
- Upgraded copywriting using active voice, 5th-grade vocabulary, visual analogies, and "What We Don't Do" authority framing.

### v1.4.0 (2026-08-01)
- 🚀 **GitHub Repository Launch**: Published open-source project to `Aryu55/mindmaxing-creatives`.
- 💵 **USD Budget Selection Dropdown**: Converted budget field to a styled dark glass `<select>` dropdown ranging from `$1,000` up to `$20,000+`. Replaced en-dashes with clean hyphens.
- 🔒 **Privacy Protection Update**: Removed raw email address display from the lead submission success banner to prevent UI email harvesting.

### v1.3.0 (2026-08-01)
- 👤 **"Meet Aryan" Founder Section**: Built a dark glass profile section showcasing Aryan's photo, bio, and key achievements (4 profitable AI products, Fortune 500 advisory, ₹20 Cr+ alumni earnings in 2025).
- 🖼️ **Icon & Favicon Fix**: Updated `favicon.ico`, `favicon.png`, and `apple-touch-icon.png` with the official 500x500 1:1 red & black MindMaxing logo icon with `?v=3` cache-busting headers.

### v1.2.0 (2026-08-01)
- 📱 **Mobile Layout & Typography Optimization**: Fixed top margin alignment on mobile headers. Set fluid typography scaling (`clamp(36px, 9.5vw, 56px)`). Auto-collapsed sidebar rail index on mobile screens for 100% full-width showcase cards.
- ⚡ **Global Event Delegation Fix**: Resolved `support.js` React template mounting issue by implementing top-level event delegation (`document.addEventListener('click')`) and global `window.openContactModal(e)` trigger.
- 🔍 **DevTools Console Diagnostics**: Added `[Mindmaxing]` log prefixes across all modal triggers and API fetch payloads for instant debugging.

### v1.1.0 (2026-08-01)
- 📩 **Resend Lead Modal Integration**: Embedded glassmorphism modal with inputs for Name, Email, Phone, Budget, and Problem details.
- ⚡ **Cloudflare Pages Serverless Function**: Created `/functions/api/contact.js` proxying inquiries to `mindmaxxxing@gmail.com` via Resend API (`re_gn3FwoXw...`).
- 🗑️ **Product Lineup Cleanup**: Removed RoofHero, cleanly renumbering the showcase to 11 active live products.
- 🌐 **Custom Domain Integration**: Attached `mindmaxing.one` and `www.mindmaxing.one` via Cloudflare REST API & CNAME routing.

### v1.0.0 (2026-08-01)
- Initial release of the Mindmaxing Creatives interactive 3D WebGL product studio portfolio.

---

## 🛠️ Local Development & Deployment

### 1. Run Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 2. Deploy to Cloudflare Pages
```bash
npm run deploy
```
or via Wrangler CLI:
```bash
npx wrangler pages deploy . --project-name mindmaxing-creatives
```

---

## 📬 Contact & Enquiries

- **Lead Form**: [https://mindmaxing.one/#contact](https://mindmaxing.one/#contact)
- **Target Recipient**: `mindmaxxxing@gmail.com`
