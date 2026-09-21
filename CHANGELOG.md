# Changelog — Mindmaxing Creatives

All notable changes to the Mindmaxing Creatives platform, showcase portfolio, and outbound growth pipelines are documented in this file.

---

## [2.1.0] - 2026-09-21

### Added
- **Nightly Campaign Review & Mailbox Control System (Astra Spec v2.1)**:
  - Built deterministic nightly reviewer (`daily_mailbox_planner.py`) running at 00:30 Asia/Kolkata (19:00 UTC) with explicit budget periods (`YYYY-MM-DD-IST`).
  - Implemented immediate baseline sending (cap 1) upon passing 1 clean diagnostic in Inbox with passing SPF/DKIM/DMARC (eliminating arbitrary 7-day startup delays).
  - Enforced 7-day maturation on volume scaling ($1 \to 2 \to 3$) bounded by strict v1 ceiling of 3 messages/day/mailbox.
  - Implemented 72-hour seed visibility grace period (temporary seed outage freezes growth with `KEEP`, but preserves baseline sending; expiry >72h triggers `HOLD_DIAGNOSTIC_EXPIRED`).
  - Unified atomic touch reservation (`volume_controller.reserve_and_claim_job()`): health checks, recipient suppression, lead qualification, sequence immutability, daily decision checks, and job claiming execute in one atomic SQLite transaction before SMTP dispatch. Post-DATA network errors mark jobs `UNCERTAIN` without quota refund.
  - Strictly read-only status reporting (`outbound_status.py report --today` and `--date YYYY-MM-DD`).
  - Passed all 12 required Astra verification scenarios (51 / 51 tests passing green).
  - Verified 100% SHA-256 bit-for-bit file parity across all 17 scripts between macOS and Hostinger production VPS (`root@72.62.230.37`).
- **SQLite Concurrency & WAL Mode Deployment**:
  - Migrated `mindmaxing_crm.db` to Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) with a 30-second busy timeout (`PRAGMA busy_timeout=30000;`) on both local and production VPS, resolving multi-process write-lock contention.
  - Terminated duplicate background tmux monitor daemon in favor of the unified production crontab schedule.

### Audited & Fixed
- **Reddit Lead Incident Qualification Repair (Astra Spec v2.2)**:
  - Replaced keyword-only matching with pure evaluator `evaluate_reddit_signal(post, now)`: enforces component/malfunction sentence adjacency, strict 7-day source freshness, verified operator ownership, negation handling, hypothetical filtering, and explicit evidence capture.
  - Implemented 5-tier signal taxonomy: `INCIDENT_CANDIDATE`, `REVIEW_REQUIRED`, `NO_MATCH`, `STALE`, `INVALID_SOURCE`.
  - Added additive schema migration `migrate_signal_schema.py` (`signal_decision`, `signal_reasons`, `signal_evidence`, `signal_policy_version`, `evaluated_at`).
  - Added duplicate post evidence preservation (`attach_duplicate_reddit_evidence`), preventing active conversations from resetting.
  - Hardened `volume_controller.reserve_and_claim_job()` to fail-closed on unverified contacts and require `INCIDENT_CANDIDATE` for Reddit outreach.
  - Re-evaluated all 9 existing Reddit leads factually with zero budget inferences: all 9 reclassified as `NO_MATCH` (general store feedback / ads queries without storefront code malfunction).
  - Created comprehensive test suite `test_reddit_signal_evaluator.py` passing all 12 Astra fixtures and 4 architectural invariants.

---

## [1.9.0] - 2026-09-20

### Added
- **Peer-to-Peer VPS Mailbox Warmup Engine (`warmup_engine.py` & `warmup_daemon.py`)**:
  - Engineered native cross-domain warmup mesh across 25 mailboxes and 4 distinct domains (`mindmaxing.online`, `.store`, `.org`, `.info`) with zero SaaS subscriptions ($0.00/mo).
  - IMAP automated interaction: Recipient logs in via TLS IMAP, marks incoming warmup messages as `\Seen` (Read) and `\Flagged` (Starred), and sends authentic in-thread conversational replies with `In-Reply-To` and `References` headers.
  - Active background execution via `warmup_daemon` in a dedicated tmux session on Hostinger VPS (`72.62.230.37`).
- **Andrej Karpathy's LLM Council System (`llm-council` & `council`)**:
  - Global and workspace agent skill enabling 5-advisor multi-perspective deliberation (Contrarian, First Principles Thinker, Expansionist, Outsider, Executor), peer-review rounds, and synthesized verdicts.
  - Auto-enrichment scanning project memory (`AGENTS.md`, `strategic-memory.md`).
- **Master Brief for Astra (`advice/astra-brief-warmup-and-routing.md`)**:
  - Comprehensive document breaking down deliverability physics, the 14-day ramp schedule, and the formal justification for why fixing mechanical recipient routing preserves the 1,000-Send Law.
- **Automated Delivery Tracking & Volume Controller Engine (Astra Spec)**:
  - Terminated synthetic P2P warmup mesh following Astra's deliverability critique (P2P between same-host mailboxes does not establish reputation at Google Workspace or Microsoft 365).
  - Integrated 8 verified personal Gmail test inboxes with 16-character App Passwords into `/root/outbound/config/test_inboxes.json` (`chmod 600`).
  - Built strict read-only IMAP collector (`delivery_monitor.py` & `delivery_monitor_daemon.py`) sweeping 25 IONOS mailboxes and 8 Gmail inboxes every 10 minutes (`readonly=True`, `BODY.PEEK[]`; never flags `\Seen`, never moves, stars, or replies).
  - Parses real RFC `Authentication-Results` for SPF, DKIM, and DMARC verification and detects Inbox vs Spam vs Promotions (`X-GM-LABELS`).
  - Built transactional safety circuit-breaker (`volume_controller.py`) enforcing Level 1 caps (1 campaign msg/mailbox/day, 1 diagnostic/day), immediate auto-pause on Spam placement, SPF/DKIM failure, 3 consecutive temp fails, or stale monitoring (>1h).
  - Integrated `volume_controller` into `dispatcher.py` and `scheduler.py`: transactional quota reservations, recipient suppression check, and delivery event logging.
  - Automated 8-point test suite (`test_delivery_system.py`) passing 100% on VPS.

### Changed
- **Lead Database Forensic Audit & Fail-Closed Enforcement**:
  - Audited CRM database: discovered 520 out of 588 leads (88.4%) were pointing at generic customer care addresses (`support@`, `info@`, `care@`).
  - Audited remaining 67 "founder" leads: discovered 64 were regex/HTML scraper false positives (capturing "Customercare", "Services", "Welcome", "Team", or contact page URLs as founder names).
  - Migrated all 586 unverified leads to status `CANDIDATE` in `mindmaxing_crm.db`.
  - Locked `dispatcher.py` and `scheduler.py` to strict fail-closed: live dispatches only accept `status = 'HUMAN_APPROVED'`. Live queue build returns 0 eligible until leads are manually reviewed and approved.
- **Batch #1 Telemetry Audit**:
  - Detected 3 live replies via direct TLS IMAP sweep on `imap.ionos.com:993`: KilgourMD (human support decline), Shapellx (Zendesk ticket #444636), Norse Organics (Mimir AI deflection bot). 0 hard bounces.

---

## [1.8.0] - 2026-09-19

### Added
- **ABX Engine Product Showcase**: Featured the ABX Engine (Shopify Liquid A/B testing & CRO telemetry suite) as flagship Panel 02 on `index.html` and added a dedicated case study card in `case-studies.html`.
- **Category Filter System**: Interactive client-side category pills on `/case-studies.html` (`All`, `Shopify DTC`, `Growth & Meta Ads`, `Custom Software`) with zero page reloads.
- **Autonomous Reddit OAuth Harvester (`reddit_harvester.py`)**: Built with grandfathered OAuth client credentials, biological Poisson/Gaussian delays, rotating desktop browser header profiles, and live Reddit rate-limit telemetry tracking.
- **Multi-Stage Verification Gatekeeper**:
  - Live Linux DNS MX record verification (`host -t mx`) guaranteeing 0% hard bounce rate.
  - TLD word-boundary sanitization preventing regex greedy-matching of HTML adjacent text.
  - Automatic bare `.myshopify.com` domain rejection.
  - Strict Indian / South Asian currency filter (`₹`, `INR`, `+91`, domestic COD) ensuring 100% foreign DTC ICP targeting.
- **Cross-Source Deduplication Guard**: Two-way runtime deduplication across `leads.json` and `mindmaxing_crm.db` between Trustpilot and Reddit scrapers.
- **CRM Database Schema Migration**: Added dedicated columns `source`, `subreddit`, `post_title`, `post_url`, and `post_author` to `mindmaxing_crm.db`.
- **Hyper-Personalized Dispatcher v2.2**: Generates Touch 1 openers quoting the founder's exact Reddit post title and specific pain trigger (ad spend bleed, traffic without sales, mobile speed), sorted with freshest pain signals first.

### Changed
- **Case Studies Re-Architecture**: Reordered case studies from SafeSpot-first to flagship Shopify DTC-first. Completely removed dense paragraph boilerplate ("The Bottleneck", "Engineering Solution", "Key Outcome") in favor of an ultra-lean 2-column responsive card grid with high-contrast metric pills (`⚡ Sub-1.2s Mobile`, `📈 462% ROAS`).
- **Sync & Deployment**: Synced all root HTML files to `public/` and verified Cloudflare Pages builds.

### Removed
- Purged 114 junk leads from Reddit reservoir (moderator restock lists from `r/Slime`, swap threads from `r/fragranceswap`, bare `.myshopify.com` stores, and domestic Indian stores).
- Removed `Pause` panel from the active homepage carousel to accommodate ABX Engine.

---

## [1.7.0] - 2026-08-19

### Added
- **Studio Repositioning**: Highlighted Aryan Panchal (Software & AI Engineering Founder) alongside Himanshu Agrawal (Creative Strategy & Performance Marketing Partner).
- **6 Performance Growth Case Studies**: Zyron Tech (4.6X ROAS), Alcohol Ecom ($238K at 9X ROAS), Zupee (+117K followers), D2C Fitness (5+ ROAS), Solar Solutions (80% CAC drop), and Healthy Meals Cafe (+40% lead growth).
- **Client Pitch Page (`/swim.html`)**: Bespoke high-converting partnership pitch for Command Studio (Rajvi Damania) to scale upcoming swimwear brands MACHHLI & MAG.
- **Concept Storefront Prototypes**: Deployed live prototypes for MACHHLI Swimwear (`machhli.vercel.app`) and MAG SWIMS (`mag-eta.vercel.app`).

---

## [1.6.0] - 2026-08-01

### Added
- Added **WESHUB** (`weshub.lovable.app`) and **Saffron Origins** (`saffronorigins.com`) as products #13 and #14.
- Integrated deep-dive case studies into `/case-studies.html`.
- Expanded scroll sentinel system to 14 steps (`1400vh` scroll track) with updated Three.js background shader palette transitions.

---

## [1.5.0] - 2026-08-01

### Added
- Added **Bhoomiputra Foundation** (`bhoomi-roots-foundation.lovable.app`) as project #04.
- Created dedicated Case Studies Deep-Dive Page (`/case-studies.html`).
- Added universal high-contrast typography system and glowing orange tag pills.
- Created `About Us` (`/about.html`), `Privacy Policy` (`/privacy.html`), and `Terms of Service` (`/terms.html`).

---

## [1.0.0 - 1.4.0] - 2026-08-01

- Initial release of Mindmaxing Creatives interactive 3D WebGL product studio portfolio.
- Resend-powered serverless lead engine (`/functions/api/contact.js`).
- "Meet Aryan" founder showcase section.
- Dark glassmorphism design system, mobile fluid typography, and custom domain setup (`mindmaxing.one`).
