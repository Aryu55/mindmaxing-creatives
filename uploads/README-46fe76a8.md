# Janus AI — Autonomous Instagram Content & DM Lead Engine

Welcome to the official technical manual and system documentation for **Janus AI**, an enterprise-grade, autonomous Instagram content intelligence, DM automation, and organic lead capture SaaS platform designed for software founders, creators, app developers, and marketing teams.

---

## 🏛️ Why "Janus AI"?

Named after **Janus**, the ancient Roman god of dual doorways, transitions, and time — portrayed with two faces looking in opposite directions:

- **Face 1 (Retrospective / Data Analyst)**: Looks backward at historical performance metrics, competitor reels, viral video structures, and engagement signals to discover winning hooks, formats, and high-retention storytelling patterns.
- **Face 2 (Forward-Facing / Content Creator & Automator)**: Looks forward to generate 4-agent video scripts, automate short-form content pipelines, and capture inbound lead DMs 24/7 on Instagram without manual effort.

Janus AI bridges the gap between **organic content creation** and **direct-response conversion**, turning Instagram feeds into automated sales pipelines for software applications and digital products.

---

## 🎯 Platform Capabilities: What Janus AI CAN & CANNOT Do for Software/App Marketing

### ✅ What Janus AI CAN Do

1. **Automate Organic Lead Capture (Comment-to-DM Engine)**
   - Automatically detect comments on your posts/reels containing trigger keywords (e.g. `"BUILD"`, `"DEMO"`, `"LINK"`, `"CODE"`).
   - Instantly deliver personalized Direct Messages containing download links, documentation, or discount codes.
   - Deploy `SMARTAI` listeners powered by GPT-4o to answer user questions contextually in natural Hinglish or English before sending the call-to-action link.
   - Automatically log lead profile details (Instagram Username, User ID, Timestamp) into a searchable directory (`/contacts`) with CSV export for CRM sync.

2. **Run Autonomous 4-Agent Content Pipelines (`/content-engine`)**
   - **Agent 01 (Scraper)**: Mimes competitor reels, trending short-form content, and viral transcripts in software, SaaS, or productivity niches.
   - **Agent 02 (Validator)**: Applies rule-based and engagement heuristics to filter out low-performing noise and group viral signals into semantic topic clusters.
   - **Agent 03 (Writer)**: Drafts short-form video screenplays tailored to customizable creator voice profiles (Hinglish/English vocabulary mix, sentence length economy, high-energy tone).
   - **Agent 04 (Hook Generator)**: Generates 5 scroll-stopping hooks with predicted virality confidence ratings.

3. **Reverse-Engineer Viral Video Formats (`/analyzer`)**
   - Paste any Instagram Reel or YouTube Short link to automatically extract spoken transcripts and reverse-engineer the exact **Hook**, **Body Structure**, and **CTA Trigger** that drove its viral reach.

4. **Multi-Tenant Master Organization Management (`/discover`, `/settings`)**
   - Support multiple brand workspaces (e.g. `Course Business`, `Dev Tool SaaS`, `Growth Agency`) under one account.
   - Manage Discord-style public organization discovery (`/discover`) allowing team members to submit join requests and assign role-based access control (`OWNER`, `ADMIN`, `MEMBER`).

5. **Hardened Production Security & Serial Queue Rendering**
   - Cryptographically signed HMAC-SHA256 session cookies (`lib/auth.ts`) preventing session forgery.
   - `bcrypt` password hashing (12 salt rounds) with automatic legacy SHA-256 hash upgrade.
   - Strict organization-level database query scoping (`orgId` filtering) preventing cross-tenant data leakage.
   - BullMQ + Redis serial job queue on host rendering VPS preventing CPU/RAM OOM collapses during overnight 10+ video batches.

---

### ❌ What Janus AI CANNOT Do (Meta Restrictions & Boundaries)

1. **CANNOT Send Cold or Unsolicited Direct Messages**
   - Meta's Instagram Platform Policy strictly prohibits initiating DMs to followers who have not messaged or commented on your profile first.
   - **Compliant Growth Strategy**: Software creators publish organic reels asking viewers to comment a specific keyword (e.g. *"Comment 'APP' for early access"*), triggering Janus AI's compliant webhook response.

2. **CANNOT Message Past Meta's 24-Hour Window**
   - Meta restricts automated API responses to within 24 hours of a follower's last comment or DM. Janus AI cannot send arbitrary re-engagement broadcasts weeks later unless the user interacts again.

3. **CANNOT Auto-Publish Videos Without Direct Meta App Review**
   - Automated video posting directly to an Instagram feed requires approved Meta Content Publishing API permissions. Janus AI builds video assets, renders scripts/audio, and queues them in a Review Queue (`/content-engine`) with interactive 9:16 mockups for one-click creator approval.

4. **CANNOT Replace Full CRM or Email Automation**
   - Janus AI is optimized for top-of-funnel organic engagement, viral short-form scripting, and initial Instagram lead capture. It is not an email newsletter provider (like ConvertKit) or a complex CRM (like HubSpot), though leads export cleanly via CSV.

---

## 📋 Table of Contents

1. [System Overview & Architecture](#1-system-overview--architecture)
2. [Data Model & Schema Deep-Dive](#2-data-model--schema-deep-dive)
3. [Folder Structure & Core Modules](#3-folder-structure--core-modules)
4. [Functional Logic & Webhook Flows](#4-functional-logic--webhook-flows)
   - [OAuth 2.0 Integration](#oauth-20-integration)
   - [Inbound Webhook Processing Loop](#inbound-webhook-processing-loop)
   - [AI Content Pipeline (4-Agent System)](#ai-content-pipeline-4-agent-system)
   - [Stripe Checkout & Billing Lifecycle](#stripe-checkout--billing-lifecycle)
5. [Theme Architecture (Neo-Glassmorphic Tech Sanctuary)](#5-theme-architecture-neo-glassmorphic-tech-sanctuary)
6. [Detailed Changelog & Styling Revision History](#6-detailed-changelog--styling-revision-history)
7. [Installation & Local Setup](#7-installation--local-setup)

---

## 1. System Overview & Architecture

Janus AI bridges user traffic on Instagram with automated backends through secure API integrations. Below is the high-level operational flowchart showing how events are routed through the system:

```mermaid
flowchart TD
    subgraph Instagram Platform
        A[Follower leaves comment or sends DM] -->|Webhook Event| B[Facebook/Instagram Graph API]
    end

    subgraph Janus AI Backend (Next.js Edge Runtime)
        B -->|POST request| C[app/api/webhook/instagram/route.ts]
        C --> D{Verify Webhook Signature}
        D -->|Valid| E[Extract Message/Comment & Sender ID]
        D -->|Invalid| F[401 Unauthorized]
        
        E --> G{Query Prisma DB: Find Integration & Active Automation}
        G --> H[Automation Found]
        
        H --> I{Determine Listener Type}
        I -->|SMARTAI| J[Query OpenAI GPT-4o-mini API with System Prompt]
        I -->|MESSAGE| K[Select Static Message Text]
        
        J --> L[Format Response Payload]
        K --> L
        
        L --> M[Send POST to Graph Send API]
        M --> N[Increment Automation Metrics in DB]
    end

    subgraph Hostinger VPS Render Box (KVM 2)
        P[BullMQ Serial Queue / Redis] --> Q[Chatterbox TTS / Whisper Devanagari]
        Q --> R[FFmpeg 9:16 Normalizer + ASS Captions]
        R --> S[Cloudflare R2 Storage]
    end
    
    subgraph Follower Device
        N -->|Direct Message Delivered| O[Follower receives DM response]
    end
```

---

## 2. Data Model & Schema Deep-Dive

Janus AI utilizes **Prisma** to model relations on a PostgreSQL database hosted via **Neon serverless**. Below is the entity relationship detail:

### Schema Overview

- **User**: Represents the primary platform subscriber, authenticated using **Clerk**.
  - Has a one-to-one relationship with `Subscription`.
  - Has a one-to-many relationship with `Integrations`, `Automation`, and `Contact`.
- **Subscription**: Details the active tier (`FREE` or `PRO`), customer IDs, and sync states linked to **Stripe**.
- **Integrations**: Stores OAuth tokens, scopes, and expiration details for the connected Instagram account.
- **Automation**: The primary container for workflows.
  - Contains one-to-many `Trigger` elements (e.g., matching keywords, comments, or story mentions).
  - Contains one-to-many `Keyword` entries used to match inbound messages.
  - Has a one-to-one relation with `Listener` which dictates whether the automation triggers a static template message or redirects to a `SMARTAI` listener.
- **Dms**: Maintains the communication log for audit trials.
- **Post**: Represents the list of specific user reels or images associated with the automation.
- **Contact**: Stores lead details (Instagram ID, Username) captured automatically when a follower interacts with any active automation.

- **Organization & Multi-Tenancy**:
  - `Organization`: Workspace entity with custom `slug`, posts per day target, brand tagline, and content settings.
  - `OrgMember`: Maps users to organizations with `OWNER`, `ADMIN`, or `MEMBER` roles.
  - `OrgJoinRequest` & `OrgInvite`: Manages Discord-style public access requests and email invitations.
- **Content Factory Engine**:
  - `ContentIdea`: Stores LLM-generated topic ideas, content pillars, and usage status.
  - `ContentJob`: Tracks video production status (`IDEA` → `SCRIPTED` → `RENDERING` → `REVIEW` → `PUBLISHED`).
  - `DocumentaryLog`: Event ledger capturing onboarding milestones, renders, publishes, and weekly metrics analysis.

---

## 3. Folder Structure & Core Modules

The codebase is organized as follows:

```
├── actions/                  # Server Actions for Database Mutations
│   ├── automation/          # Creating, updating, and triggering automations
│   ├── contacts/            # Scoped contact querying and lead exports
│   ├── factory/             # Content pipeline controllers & documentary log generators
│   ├── integration/         # Connecting & removing Instagram OAuth tokens
│   ├── team/                # Organization management, discovery, and join requests
│   └── user/                # Profile management, sessions, and dashboard overview
├── app/                      # Next.js App Router (14.2.7)
│   ├── (auth)/              # Authentication Layouts (Sign In / Sign Up)
│   ├── (protected)/         # Dashboard routes guarded by middleware auth check
│   │   └── dashboard/
│   │       └── [slug]/
│   │           ├── activity/        # Real-time event activity feed
│   │           ├── analytics/       # Performance charts and AI strategic blueprints
│   │           ├── automation/      # Specific step-builder checklists & live previews
│   │           ├── contacts/        # Collected leads directory
│   │           ├── content-engine/  # 7-Tab Content Factory & review queue
│   │           ├── discover/        # Public organization discovery & join requests
│   │           ├── inbox/           # Unified DM inbox interface
│   │           ├── integrations/    # API integrations dashboard
│   │           ├── intelligence/    # Structural viral post analyzer (/analyzer)
│   │           ├── research/        # Content research & competitor tracking
│   │           ├── settings/        # Organization settings & member management
│   │           ├── skills/          # AI Skills library with specimen caching
│   │           ├── studio/          # Video studio & pipeline editor
│   │           └── virality/        # Voice analyzer & script score checker
│   ├── api/                 # API Routes (Webhooks, predictions, content pipeline, factory crons)
│   ├── callback/            # OAuth Callback redirect targets
│   └── layout.tsx           # Main application wrapper with providers
├── components/               # Reusable React components
│   ├── global/              # Navigation, sidebars, theme toggles, search, alerts
│   └── ui/                  # Raw Shadcn components
├── hooks/                    # Reusable React hooks (automations, queries, navigation)
├── lib/                      # Base configurations (auth HMAC signing, prisma, stripe, AI helper functions)
├── marketing-machine/        # GPU Render Box & Cloudflare Workers Broker
│   ├── cloudflare-worker/   # Cloudflare Worker orchestrator & API gateway
│   └── gpu-render-box/      # Node.js + Python + FFmpeg VPS render agent
│       ├── assets/fonts/    # Bundled TTF fonts (Montserrat, Inter, Komika)
│       ├── broll_verifier.js# Pexels stock video search with exponential retry
│       ├── render.js        # Multi-mode render engine with 9:16 normalization
│       ├── setup-vps.sh     # One-click Ubuntu VPS setup script
│       ├── tts_chatterbox.py# Chatterbox neural TTS synthesis engine
│       ├── webhook-server.js# Express + BullMQ serial queue + SSE progress
│       └── whisper_align.py # Whisper transcript alignment with Urdu rejection
├── providers/                # Client state, Theme (Next-Themes) & Query Client wrappers
├── prisma/                   # Schema specification & DB Migration files
└── tailwind.config.ts        # Tailwind Design System customization file
```

---

## 4. Functional Logic & Webhook Flows

### OAuth 2.0 Integration

1. The user navigates to `/dashboard/[slug]/integrations` and triggers the Instagram connection.
2. Janus redirects the user to the Instagram Embedded OAuth screen.
3. Upon approval, Instagram redirects to `/callback/instagram` with an access code.
4. The Janus backend exchanges this code for a **Long-Lived Access Token** using `INSTAGRAM_TOKEN_URL`.
5. The token is encrypted and stored in the database's `Integrations` model associated with the user's account.

### Inbound Webhook Processing Loop

When a follower comments on a post or DMs the connected profile:
1. Instagram fires a payload to `/api/webhook/instagram` containing the message text and sender's ID.
2. The endpoint verifies the sender and fetches the associated active `Automation` by comparing the keywords set in the `Keyword` table against the message content.
3. **Keyword Matching Logic**:
   - Evaluates direct string equivalency (case-insensitive).
   - If a match is found, the listener type is parsed:
     - **Static Message (`MESSAGE`)**: Janus fires a payload containing the template reply to the follower via the Instagram Send API.
     - **Smart AI (`SMARTAI`)**: Janus builds a context window utilizing the user's defined system prompts (configured inside the automation details card). Janus calls OpenAI's GPT models to draft a responsive Hinglish/English answer tailored to the question, then dispatches the text response.
4. The system logs the contact details under `Contact` to ensure the lead is saved in the dashboard directory.

### AI Content Pipeline (4-Agent System)

Accessible via `/dashboard/[slug]/content-engine`, the engine coordinates four separate LLM sub-routines (agents) processing information sequentially:
1. **Agent 01 (Scraper)**: Extracts trends, hashtags, competitor references, and raw captions.
2. **Agent 02 (Validator)**: Computes a relevance check, filtering out noise and grouping validation indicators into thematic semantic clusters.
3. **Agent 03 (Writer)**: Drafts voice scripts tailored to defined Hinglish ratios, sentence lengths, and energy profiles.
4. **Agent 04 (Hooks)**: Designs 5 retention-optimized hooks, assigning confidence scores based on engagement metrics.

---

## 5. Theme Architecture (Neo-Glassmorphic Tech Sanctuary)

Janus implements a responsive, highly premium **Neo-Glassmorphic Tech Sanctuary** theme system configured inside `globals.css`:

```css
:root {
  /* Light Theme Tokens */
  --background: 210 20% 98%;            /* Slate-50 background tint */
  --foreground: 224 71.4% 4.1%;         /* Slate-950 main text */
  --primary: 262 80% 50%;               /* Violet-600 main accent (#7c3aed) */
  --radius: 12px;                       /* Curved card borders */
  --card-bg: oklch(100% 0 0);
  --border-color: oklch(92% 0.005 240);  /* Soft slate borders */
  --accent-magenta: oklch(60% 0.22 280); /* Violet theme indicator */
}

.dark {
  /* Dark Theme Tokens */
  --background: 240 10% 3.9%;           /* Zinc-950 dark mode background */
  --foreground: 0 0% 98%;               /* Zinc-50 bright grey copy */
  --primary: 263 70% 50%;               /* Violet-500 accent (#8b5cf6) */
  --card-bg: oklch(14% 0.005 240);
  --border-color: oklch(22% 0.005 240);
}
```

---

## 6. Detailed Changelog & Styling Revision History

### [Revision 08] — Content Factory 3.0 & Fix Pack v3
- **Dynamic Skill Precedence Resolution**: Implemented dynamic skill template resolution: `job.skillId` -> `<janus>/skills/<skillId>/config.json` -> `<business>/template.json` -> built-in default.
- **Chatterbox TTS Architecture**: Replaced legacy Bark with Chatterbox TTS engine (`tts_chatterbox.py`).
- **3-Tier Visual Judge Layer**: Implemented deterministic metric gates, vision judge, and 10-clip calibration matrix in `run_judge.js`.

### [Revision 09] — Content Factory Fix Pack v5 & Production Hardening Suite
- **Quantitative Skill Schema Contract (`skills/SCHEMA.json`)**:
  - Implemented strict quantitative validation mapping all skill config keys to `IMPLEMENTED`, `NOT_IMPLEMENTED`, or `UNKNOWN`.
  - Hard failure under `STRICT=1` on unknown key typos. Normalized property names (`subtitleFontSize`, `subtitleUppercase`, `fps`, `overlayStyle`).
- **Multi-Scene Pexels B-Roll Concatenation & ~60s Anti-Slop Screenplay**:
  - Machine 1 downloads, trims, and concatenates **8 distinct Pexels HD stock video MP4s** matching spoken scene boundaries.
  - ~60s screenplay engine (~150 words, 8 scenes) with concrete numbers/mechanisms per body line and zero generic stock openers.
- **Screen Recording Auto-Content Crop ($\ge 45\%$ Panel Height)**:
  - Machine 2 scales active content panel to **50% of frame height** ($1080 \times 960$ panel at Y=240 on blurred background).
  - Captions positioned at `subtitleY: 0.72` in the dark background panel below content.
- **Whisper Devanagari Enforcement & Urdu Script Rejection**:
  - Enforced `language="hi"` with Devanagari initial prompt hint (`"यह वीडियो हिंदी भाषा में है।"`) and filtered Urdu range characters (`U+0600..U+06FF`).
  - Cache keying format: `sha256(audio)__model__language.json` with `CACHE_BYPASS=1` support.
- **Serial Render Queue (BullMQ + Redis, Concurrency = 1)**:
  - Refactored `webhook-server.js` with Redis-backed BullMQ serial job queue. Supports overnight batching of 10+ video jobs without CPU/RAM OOM crashes.
- **Real-Time SSE Progress Streaming**:
  - Added `GET /progress/:jobId` Server-Sent Events endpoint streaming live stage updates (`QUEUED` → `FETCHING_SCRIPT` → `ALIGNING_SUBTITLES` → `RENDERING_FFMPEG` → `DONE`) directly to mobile UI.
- **TTF Font Bundling & Auto-Installer**:
  - Bundled `Montserrat-ExtraBold.ttf`, `Inter-Bold.ttf`, and `Komika-Axis.ttf` inside `marketing-machine/gpu-render-box/assets/fonts/`.
  - `setup-vps.sh` automatically installs fonts to `/usr/share/fonts/truetype/janus/` and refreshes fontconfig.
- **Input Aspect Ratio Auto-Normalization**:
  - Auto-normalizes any non-standard video upload (16:9 landscape, square 1:1, or screen recordings) to consistent 1080x1920 (9:16) vertical format before processing.
- **Pexels API Retry Protection**:
  - `broll_verifier.js` uses exponential backoff retry (3 attempts with 2s, 4s, 8s delays) on 429 rate limits, with solid color background fallbacks.
- **Audit Evidence Bundle (`factory_test_bundle_v5/`)**:
  - Complete evidence bundle containing rendered MP4 outputs, ASS subtitles, 15 frame stills, real SHA-256 digests (`11_PROVENANCE.json`), and self-audit reports (`20_SELF_AUDIT.md`, `21_SUMMARY.md`).

### [Revision 10] — Open-Source Fish-Speech Integration, Interactive Product Tour & Master Admin Suite
- **Open-Source Fish-Speech Engine Integration (`tts_fishaudio.py` & `setup_fish_speech_local.sh`)**:
  - Dual-mode support for self-hosted open-source Fish-Speech server (`python -m tools.api_server --listen 0.0.0.0:8080`, 100% free, zero API key) and Fish Audio Cloud API (`https://api.fish.audio/v1/tts`).
  - Automated fallback to Chatterbox TTS engine when local server or cloud key is not present.
- **Interactive Onboarding Product Tour Component (`OnboardingTour.tsx`)**:
  - 9-step guided spotlight product tour with non-overlapping focus cutout around target elements.
  - Features step navigation (Next/Back/Skip), auto tab-switching, step progress bar, and `Don't show again` preference saved in `localStorage`.
  - Permanent floating "Product Tour" pill button to restart the tour anytime.
- **Master Admin Auth & Session Handling**:
  - Configured middleware session check (`user_session` cookie) for strict dashboard route protection (`/dashboard/*`).
  - Master Admin account configured for `mindmaxxxing@gmail.com` with bcrypt password security.

---

## 7. Installation & Local Setup

### Installation Steps

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/Aryu55/SAAS-Instagram-DM-Automations.git
   cd SAAS-Instagram-DM-Automations
   ```

2. **Configure Environment Settings**:
   Copy `.env.example` into `.env` and fill out the Clerk, Neon PostgreSQL, OpenAI, Stripe, and R2 credentials.

3. **Install Core Dependencies**:
   ```bash
   npm install
   ```

4. **Sync Prisma Database Schemas**:
   ```bash
   npx prisma db push
   ```

5. **Deploy Hostinger VPS Render Box**:
   SSH into your Hostinger Ubuntu VPS (`srv1371866.hstgr.cloud`) and run:
   ```bash
   git clone https://github.com/Aryu55/SAAS-Instagram-DM-Automations.git /root/marketing-machine
   cd /root/marketing-machine/marketing-machine/gpu-render-box
   chmod +x setup-vps.sh
   ./setup-vps.sh
   ```

6. **Start Dev Server**:
   ```bash
   npm run dev
   ```

### Verification Checks
Before pushing to production, verify structural type integrity:
```bash
npx tsc --noEmit
npm run build
```
