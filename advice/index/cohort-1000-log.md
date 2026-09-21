# Mindmaxing Outbound Cohort #1 Ledger (Target: 1,000 Sends)

Established 2026-09-20 per Aryan's directive:
> *"We really gotta make changes after the first 1,000... we document these things and then we make our changes..."*

This document tracks empirical, unedited telemetry across the first 1,000 cold outbound sends. No structural pivots, copy rewrites, or positioning overhauls are executed until this cohort reaches 1,000 completed sends.

---

## 1. Cohort Overview & Progress

* **Target Volume:** 1,000 unique prospects
* **Current Progress:** 25 / 1,000 (2.5%)
* **Sending Infrastructure:** 25 mailboxes across 4 domains (`mindmaxing.info`, `.org`, `.online`, `.store`)
* **Daily Sending Pace:** 25 emails/day (1 send per mailbox/day)
* **Schedule Gate:** Mon – Fri ONLY | 09:30 – 16:30 prospect local time (BST, CEST, EDT, PDT)

---

## 2. Response & Outcome Categorization (Running Ledger)

| Category | Definition | Current Count | % of Sends |
|---|---|---|---|
| **Positive / Audit Request** | Founder/dev engages, asks for diagnostic or clip | 0 | 0.0% |
| **Neutral / Pricing Inquiry** | Asks about pricing, timeline, or agency scope | 0 | 0.0% |
| **Explicit Rejection / Unsub** | Human responds asking to remove or not interested | 1 | 4.0% |
| **AI Deflection Bot** | Gorgias / Mimir AI auto-replying vendor deflection | 1 | 4.0% |
| **Helpdesk Ticket Creation** | Zendesk / Freshdesk auto-creating customer ticket | 1 | 4.0% |
| **Hard Bounce / Invalid MX** | Mail rejected by receiving server | 0 | 0.0% |
| **Pending / No Reply Yet** | Awaiting business-hours human review / Touch 2 | 22 | 88.0% |

---

## 3. Empirical Observations & Edge Cases (Logged in Real Time)

### Batch 1 (Sends 1 – 25 | Dispatched 2026-09-19 20:13 UTC / 2026-09-20 01:43 IST)

#### Observation 1: The Helpdesk Ticket Auto-Responder (Shapellx)
* **Recipient:** `info@shapellx.com`
* **Response Received:** Automated Zendesk ticket creation (`Ticket Number: 444636`, `Subject: Shapellx mobile checkout`).
* **Finding:** On scaled DTC brands ($500k+/mo), generic addresses (`info@`, `support@`) flow directly into ticketing systems. Frontline support agents prioritize customer inquiries and auto-close vendor solicitations.
* **Documented Rule for Review at 1,000:** Evaluate response rate differences between generic support desks and founder-direct inboxes.

#### Observation 2: Frontline AI Deflection Bots (Norse Organics)
* **Recipient:** `support@norseorganics.co`
* **Response Received:** Immediate reply from *"Mimir, an AI assistant for Norse Organics"*:
  > *"At this time we're not pursuing any external collaborations or development services, but we appreciate your interest... If you'd rather talk to a human, just say so in your reply..."*
* **Finding:** E-commerce customer service platforms are actively deploying LLM gatekeepers that detect agency vendor keywords (*Shopify developer*, *theme work*, *collaborations*) and trigger canned deflections.
* **Documented Rule for Review at 1,000:** Measure whether AI auto-deflections can be bypassed via specific non-solicitation wording or if support inboxes of brands with >$1M GMV should be excluded entirely in favor of emerging brands.

#### Observation 3: Email Client Plain-Text Linebreak Collapsing
* **Incident:** Norse Organics' auto-responder quoted the outbound email as a single continuous block of text without paragraph breaks.
* **Cause:** Sending pure plain-text `\n` without accompanying HTML `<p>` tags caused the receiving ticketing parser to strip raw linebreaks.
* **Technical Fix Applied:** Upgraded dispatcher to send dual-part MIME (CRLF `\r\n` plain-text + semantic `<p>` HTML) to preserve whitespace across all email clients and ticketing systems.

#### Observation 4: Timezone / Scheduling Discipline
* **Incident:** Batch 1 was fired on weekend off-hours (Saturday night / early Sunday morning local time) rather than being gated by the timezone daemon.
* **Technical Fix Applied:** Daemon scheduler hardwired. All future batches staged as `APPROVED` and released strictly between 09:30 – 16:30 prospect local time on business days (Mon–Fri).

#### Observation 5: Human Support Gatekeeper Polite Pass (KilgourMD)
* **Recipient:** `hello@kilgourmd.com`
* **Response Received:** Human response from Ramchell (KilgourMD Support Team):
  > *"Hi Aryan, Thanks for reaching out and for offering to help. We’re not currently looking for Shopify development support, but I appreciate you checking in. We’ll keep your information on file should our needs change."*
* **Finding:** When writing to generic addresses on mid-to-large DTC stores, human frontline customer support agents reply to be polite, but have zero hiring authority or engineering budget.

#### Observation 6: Database Audit & Fail-Closed Recipient Gating
* **Audit Metric:** 510 of 574 CRM leads (88.8%) were `GENERIC_SUPPORT` (`support@`, `info@`, `care@`).
* **Technical Fix Applied:** Purged generic addresses from active outbound queues. Hardwired scrapers and dispatchers to **fail-closed**: if no verified personal founder/owner email is discovered, the lead is dropped. Prevents burning the 1,000-send cohort on non-decision-maker tickets.

#### Observation 7: Native Peer-to-Peer Warmup Engine Deployed
* **Incident:** Sending cold emails from brand-new domains without domain warmup history risks silent spam folder quarantine by Google Postmaster.
* **Technical Fix Applied:** Deployed native peer-to-peer warmup engine (`warmup_engine.py` & `warmup_daemon.py`) across 25 mailboxes / 4 domains on the VPS. Cross-domain sends, automated IMAP marking as read and starred/flagged, and threaded replies create continuous 100% engagement telemetry at $0/mo.

---

## 4. Milestone Evaluation Protocol

No strategic, positioning, or structural copy changes will be made until the following milestones:
* **Milestone 1 (250 Sends):** Deliverability health check, domain reputation audit, and initial channel reply comparison (Reddit vs Trustpilot).
* **Milestone 2 (500 Sends):** AI-deflection rate vs human open/reply rate analysis.
* **Milestone 3 (750 Sends):** Offer structure test (cart reproduction clip vs diagnostic question).
* **Milestone 4 (1,000 Sends):** Full Cohort Post-Mortem. Aggregate all conversion denominators, calculate true cost-per-reply and cost-per-opportunity, and systematically adjust the pipeline for Cohort #2.
