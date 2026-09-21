# Founder discovery: evidence review and repair implementation plan

> For agentic workers: use superpowers:executing-plans to implement this plan task by task. This document is a review and implementation handoff, not authorization to send outreach, subscribe to a service, or change a live campaign.

**Goal:** Reliably discover named founder business contacts, retain unresolved businesses, and prevent uncertain addresses from becoming approved recipients.

**Architecture:** Separate business/person identity, email discovery, mailbox verification, and campaign approval. All harvesters feed the same persistent contact-resolution queue. Discovery writes candidates and evidence; only a shared contact gate can select an address for a campaign.

**Tech stack:** Existing Python/SQLite pipeline, bounded public-web crawling/search, optional Hunter discovery and verification adapter, existing IONOS sending and delivery monitoring. No replacement sending stack.

**Review date:** 2026-09-21, Asia/Kolkata. Read-only production inspection; no prospect requests, SMTP probes, sends, or production mutations were performed for this review. Local offline tests used mocked network operations.

## 1. What was established 

The user clarified that the second attachment is the earlier explanation of the purge and proposed next steps. The first attachment is the later deployment dossier. Their different counts are not, by themselves, a contradiction.

Eleven inspected local scripts matched their VPS counterparts by SHA-256: founder_resolver, smtp_founder_prober, email_classifier, test_contact_system, harvester, reddit_harvester, pagespeed_harvester, crm_manager, sync_crm, dispatcher, and scheduler. Findings against those files therefore apply to the inspected production source. This is not a claim that every deployment file is synchronized.

The live database snapshot contained 640 businesses: 148 CRAWL_FAILED, 406 NO_PUBLIC_FOUNDER, 33 NAME_ONLY, 2 FOUNDER_FOUND, and 51 UNRESOLVED. No rows were HUMAN_APPROVED. The two FOUNDER_FOUND rows were idyl.com (CANDIDATE) and modgents.com (READY); neither had a touch_history record. Their saved resolved_evidence contained founder-name discovery, not the SMTP transcripts claimed in the dossier.

The inspected `/root/outbound/data/smtp_prober.log` contained a summary of 57 probes, zero verified, zero catch-all and 57 no-match. It contained no RCPT response transcripts. This might be a different run; it does not prove that the two claimed checks never occurred. It also does not substantiate their exact claimed responses.

### Earlier purge explanation

- Correct: clearing invalid names is sanitation, not contact discovery. The inspected purge_corrupted_names.py updates name/type fields and does not replace email addresses or delete businesses.
- Overclaim: names passing capitalization and a blocklist are not independently verified founders. This rule can both admit junk and reject legitimate names.
- Unsupported: five failed URL guesses do not prove Cloudflare protection or a dead domain; five successful pages without a match do not prove no founder is publicly identified.
- Unsupported: the claims that DTC founders never publish direct emails and that support routinely forwards founder-named pitches were not backed by measurements.
- Missing alternative: off-site public discovery and indexed data should have been explained before presenting permutation probing or support forwarding as the practical choices.
- The seven resolution columns hold a current snapshot. Repeated updates overwrite it; they do not constitute a permanent history of every decision.

### Later deployment dossier: priority findings

| Priority | Finding | Inspected source | Consequence |
|---|---|---|---|
| P1 | Synthesizes five address formats, labels the first SMTP acceptance VERIFIED | smtp_founder_prober.py:79–93 | Address inference is being presented as founder identity verification. |
| P1 | Any fake-address result other than 250 permits candidate probing | smtp_founder_prober.py:72–93 | A temporary failure or policy rejection can be misread as evidence against catch-all behaviour. |
| P1 | Missing Person role is replaced with Founder | founder_resolver.py:137–144 | Customers, employees, authors or unrelated people can become founders. |
| P1 | Page emails are pooled and linked to a founder by local-part matching | founder_resolver.py:355–372 | Another person's address can be attributed to the founder. |
| P1 | Uses classifier['type'], although the return key is classification; treats (False, '') as a Boolean | harvester.py:477–495 | The fallback can raise KeyError; invalid-name tuples are truthy. |
| P1 | CRM import overwrites contact email, name and type on conflict | crm_manager.py:131–143 | Scraped or stale JSON can undo discovery and change an active recipient. |
| P1 | Send paths check HUMAN_APPROVED but do not independently enforce founder contact evidence | dispatcher.py:375–401; scheduler.py:226–252 | Human approval alone can still admit a generic or misattributed contact. |
| P2 | Reddit/PageSpeed retain separate legacy extraction logic | reddit_harvester.py:407–429; pagespeed_harvester.py:360–379 | Cleanup is not a universal ingest fix. |
| P2 | No homepage/link traversal or off-site search; only five fixed paths | founder_resolver.py:50–56,270 | Low coverage is partly a crawler limitation, not proof that no data exists. |
| P2 | Does not traverse JSON-LD @graph; picks the first person | founder_resolver.py:118–156,334–335 | Missed founders and arbitrary person selection. |
| P2 | Failed/catch-all checks are not saved; other verdicts are logged as patterns returning 550 | smtp_founder_prober.py:158–163 | Logs misrepresent errors and cannot reproduce protocol claims. |
| P2 | Resolver batch only selects UNRESOLVED/null | founder_resolver.py:475–480 | Transient failures never become due for retry. |
| P2 | Export changes CANDIDATE into READY | sync_crm.py:40–43 | Export mutates campaign state; this alone does not bypass HUMAN_APPROVED. |
| P2 | No email means dropping the business | harvester.py:500–502 | Valuable pain signals disappear before later enrichment can help. |

Seven existing tests passed. The sequence test at test_contact_system.py:169–187 executes handwritten UPDATE SQL instead of audit_and_update_lead. It cannot establish that production code preserves sequences. There are no SMTP prober tests in that suite.

Offline reproductions against the matching code:

1. Person Alice Morgan with no role becomes Founder.
2. Founder Alice Morgan and press contact Alice Jones at alice@example.com become FOUNDER_FOUND for Alice Morgan.
3. Fake recipient receives 451; candidate receives 250: result VERIFIED.
4. Fake recipient receives 550 5.7.1 policy rejection; candidate receives 250: result VERIFIED.
5. A founder inside JSON-LD @graph is missed.
6. classify_email('support@example.com')['type'] raises KeyError.
7. bool(is_valid_founder_name('Customerservice')) is True, although the returned validity field is False.

## 2. What professional discovery services actually do

Hunter describes a maintained public-web index and distinguishes publicly sourced addresses from inferred company-pattern addresses. It does not need to crawl the whole internet afresh for each query. Its advantage is accumulated coverage, source history and verification infrastructure, not a special SMTP identity command. [Hunter data explanation](https://hunter.io/our-data)

Apollo describes a different combination: public crawling, contributors, engagement outcomes and third-party providers. Its database is not reproduced by installing an open-source scraper. A LinkedIn profile can help identify the person/company or serve as a lookup key; that does not establish access to a private LinkedIn registration address. [Apollo data overview](https://knowledge.apollo.io/hc/en-us/articles/45824429846669-Apollo-Data-Overview)

SMTP RCPT acceptance describes a server's response in a particular session. It does not bind an address to a named founder, guarantee final delivery, or predict inbox placement. A 550 can mean a policy rejection, not just a nonexistent mailbox. Catch-all acceptance is a routing behaviour, not a server lying. [RFC 5321](https://www.rfc-editor.org/rfc/rfc5321.html#section-4.2.2)

The current prober does not issue DATA, so it does not submit an email message. That limited claim is supported by the code. Sender/recipient envelope commands and network traffic still occur. The dossier's 0% bounce risk, 35–50% competitor bounce rates, instant blacklisting and 10x forwarding uplift have no supporting measurement in the supplied material.

## 3. Fixed policy and interfaces

Keep inference disabled for automatic recipient selection. Publicly advertised personal-provider business addresses can be stored when explicitly associated with the founder; unrelated private addresses are excluded. A provider's inferred result is a review candidate, never silently relabelled as published evidence.

Create `outbound/scripts/contact_policy.py` with a pure `evaluate_contact(candidate, campaign_state, now)` function returning `eligible` and reason codes. Every send path must use it. Conditions are conjunctive: verified business/person relationship, explicit email association, current verification, non-generic address, no applicable suppression, eligible campaign state, and existing delivery/quota checks. Passing contact checks must not create HUMAN_APPROVED status.

Keep these dimensions separate:

| Dimension | Values |
|---|---|
| Identity | UNCONFIRMED, FOUNDER_CONFIRMED, CONFLICT |
| Email origin | PUBLIC_SITE, PUBLIC_EXTERNAL, PROVIDER_FOUND, PROVIDER_INFERRED, LEGACY_UNKNOWN |
| Mailbox verification | UNCHECKED, VALID, INVALID, ACCEPT_ALL, UNKNOWN, TEMPFAIL, BLOCKED |
| Contact decision | ELIGIBLE, NEEDS_CONTACT, REVIEW_REQUIRED, RETRY_DUE |

Evidence must include name/role/company relationship, exact address association, requested/final page URL, retrieval time, HTTP result, supporting excerpt or structured-data path, source method/version and verification method/time. Provider scores are retained as provider scores, not converted into guarantees.

## 4. Implementation tasks, in order

### Task 1 — Contain unsubstantiated promotion and preserve evidence

- [ ] Take a consistent SQLite backup using its backup API and retain source hashes/process inventory. Do not restore an old database over current send history.
- [ ] Remove the prober's permission to update lead.contact_email, contact_type or campaign approval. Preserve its existing inferred candidates as LEGACY_UNKNOWN/REVIEW_REQUIRED until supported.
- [ ] Reassess all FOUNDER_FOUND and legacy FOUNDER_DIRECT rows, beginning with the two claimed wins. Preserve original values and history; do not replace them automatically with support addresses and send.
- [ ] Retain raw logs and attachments. Do not reconstruct missing protocol transcripts from the dossier's prose.

### Task 2 — Repair identity and email association

Modify founder_resolver.py and email_classifier.py; repair their consumers in harvester.py.

- [ ] Unpack `(valid, clean_name)` explicitly. Use `classification`, not `type`. Unknown non-role addresses must remain unclassified candidates rather than proven PERSONAL identities.
- [ ] Accept founder identity only from an explicit relationship to the target business: e.g. Organization.founder, or a named bio stating the role. Missing roles remain unknown. Employee, author, customer and unrelated-company entries do not inherit founder status.
- [ ] Traverse JSON-LD arrays, @graph and linked @id objects while preserving organization relationships. Preserve multiple founders and conflicts instead of selecting the first node.
- [ ] Use DOM-local association or explicit structured links to connect an email to a person. Matching first names across pooled pages is insufficient. Preserve Unicode/multipart names; capitalization and word count are heuristics, not identity proof.
- [ ] For multiple independently evidenced founders, keep candidates separately. Select at most one approved contact per company sequence; unresolved conflicts require review.

### Task 3 — Improve discovery coverage without rebuilding Hunter

Use the existing resolver as the orchestrator. Reuse useful pure OpenLeads extraction functions behind an adapter only if covered by the same contract tests; do not import its sending stack or equate its scores with verification. Name repository components/versions actually reused instead of listing unrelated repositories as evidence of quality.

- [ ] Fetch the homepage and follow actual About/Story/Team/Contact links, then use fixed paths as fallbacks. Preserve all page outcomes. Use two workers, one request per host at a time, ten on-site pages and five external pages per attempt; enforce response-size/time limits and verified TLS. Reject non-public destinations and unsafe redirects; do not bypass access challenges.
- [ ] Add DDGS public search capped at three queries per attempt: company/domain + founder; exact founder + company + contact; exact founder + company email domain. Inspect original pages, not just snippets. Use off-site business bios, interviews, press/contact pages and founder-owned professional sites as candidate sources. Historical material needs a current company-role cross-check.
- [ ] Add `outbound/scripts/contact_sources.py` for search and Hunter adapters. For unresolved, high-priority founders use `GET /v2/email-finder/found` with domain and full_name. This documented endpoint excludes generated addresses. Store sources and verification fields; review actual association before selection. [Hunter API](https://hunter.io/api-documentation/v2#email-finder-found)
- [ ] Use header authentication and redact credentials from logs. Disable the provider adapter if credentials are absent. Default paid spend is zero; cap pilot usage at 20 credits or the available free balance, whichever is lower. Stop on exhausted quota instead of upgrading or rotating accounts.
- [ ] Do not fall back to the ordinary inference-capable finder when the found-only call returns nothing. Preserve NO_RESULT, authentication failure, rate limit, unknown verification and removal requests as distinct outcomes. API removal requests must prevent alternate-source reprocessing of that contact.

Hunter currently lists a free allowance of 50 credits and API access; actual account availability and balance must be read before activation. This is a pilot option, not an assumption that every founder will be found. [Pricing](https://hunter.io/pricing)

### Task 4 — Verification with honest outcomes

- [ ] Prefer verification already returned by the found-only lookup. Verify locally discovered, identity-linked addresses with the configured provider when credits permit. Never pay twice for a still-current equivalent result.
- [ ] Only VALID, with verified identity/address association and no contradictory catch-all/block result, can pass the automatic contact gate. ACCEPT_ALL, UNKNOWN, BLOCKED, TEMPFAIL and provider-unverifiable webmail remain held. An explicit business Gmail address can therefore be a legitimate candidate while still requiring separate review.
- [ ] Keep the current homemade permutation prober disabled in normal discovery. If retained for diagnostics, it accepts an already sourced address and produces only a recorded protocol observation, never a founder verdict or CRM recipient swap.
- [ ] Diagnostic protocol handling must check greeting, HELO/EHLO and MAIL responses; classify 4xx/timeouts as temporary, 5.7.x as policy-blocked, and explicit 5.1.1 as recipient rejection. An inconclusive fake-address result cannot establish non-catch-all. Even candidate acceptance plus fake rejection is only acceptance evidence from that session. Always close sockets; never issue DATA.
- [ ] Preserve MX identity, command phase, numeric/enhanced reply, actual reply text and time if diagnostics are used. Use finally/context management. Log ERROR as ERROR, not as a nonexistent mailbox.
- [ ] Refresh identity evidence after 30 days and mailbox checks older than 7 days before a new sequence. These are conservative operating defaults, not guarantees. Insufficient credits holds the candidate.

### Task 5 — Shared ingest, persistent retries and real history

Modify harvester.py, reddit_harvester.py, pagespeed_harvester.py and any enabled legacy Reddit entry point to use a shared queue. Add `outbound/scripts/contact_jobs.py` and an additive contact-evidence migration.

- [ ] Persist the business and pain signal before attempting contact discovery. Remove no-email deletion. Raw addresses become observations; they cannot become approved recipients directly.
- [ ] Add contact_candidates and append-only contact_resolution_events tables, linked to business IDs. Keep the existing leads resolution fields as compatibility summaries. Events contain run ID, code version, inputs/evidence, outcome and before/after changes. Preserve every candidate considered, including rejection reasons.
- [ ] Add one pending/running contact job per business with next_attempt_at, attempt_count and lease expiry. Claim jobs transactionally, recover expired leases, and do not run duplicate work for concurrent harvesters.
- [ ] Retry transient failures after 1 hour, 1 day and 7 days; after the third retry hold for review. Retry genuine bounded-search no-results after 30 days or on new evidence. Honour longer provider Retry-After values. Stop a provider after auth/quota failure and report one actionable notice.
- [ ] Use bounded labels such as NOT_FOUND_IN_CHECKED_SOURCES. Split HTTP_404, ACCESS_BLOCKED, DNS_ERROR, TIMEOUT and PARSE_ERROR. A generic status must not invent the cause.

### Task 6 — CRM and send-path protection

- [ ] Change crm_manager.sync_from_json so imports update business/pain observations, never selected contacts, resolution evidence, sequence recipients or approval. Make exports read-only, including removing sync_crm's CANDIDATE-to-READY update.
- [ ] Make dispatcher.py and scheduler.py load the canonical selected contact from SQLite. JSON can supply no overriding recipient.
- [ ] Bind approval to the exact candidate/address version. A changed address invalidates that approval; it cannot inherit approval from a previously reviewed support desk.
- [ ] Enforce the shared contact gate at selection and revalidate it when claiming a message for dispatch. Retain current suppression, reply, quota and campaign checks. No founder-routing support fallback in this campaign.
- [ ] Freeze the recipient for a sequence and bind subsequent touches to that recipient. Use messages/touch_history and in-flight claims as well as current_sequence_step to detect activity. Perform contact changes transactionally against a current row/version; a stale pre-network SELECT cannot authorize a swap.
- [ ] Keep diagnostics explicitly typed so they do not require founder identity. This is not an alternative route for campaign messages.

### Task 7 — Tests that exercise production functions

Retain the seven existing tests, but replace the handwritten-SQL preservation test with calls to audit_and_update_lead using mocked discovery and an isolated database. Add tests in `outbound/scripts/test_contact_gatekeeper.py` with network disabled by default.

Required cases and assertions:

| Fixture | Required result |
|---|---|
| Person with no role; Organization.employee | Never promoted to founder |
| Organization.founder via @graph/@id | Correct name/role/company retained |
| Founder Alice Morgan; press Alice Jones with alice@example.com | No automatic association |
| Exact founder bio links an email | Correct association and source preserved |
| Generic address appears before direct founder address | Discovery continues |
| Founder on /about linked from homepage | Found despite missing guessed Shopify paths |
| Capitalization noise, non-Latin and multipart names | No identity certainty from typography; valid evidence preserved |
| Fake SMTP recipient returns 451 or 550 5.7.1 | Not VALID or non-catch-all |
| Candidate accepted, nonexistent recipient explicitly rejected | Recorded SMTP observation only; no founder identity promotion |
| Timeout, secondary routing, null MX and DNS transient | Separate failure/unknown states; no fabricated 550 |
| Found-only provider has no result or unknown result | No inferred fallback; no send |
| Provider includes found sources but wrong person/company | Held |
| Missing key, exhausted credits or removal request | No paid fallback; removal respected |
| JSON import after contact resolution | Selected contact unchanged |
| Existing sequence or send claim changes during discovery | Recipient cannot change |
| Approved generic address or approval for an older candidate | Both send paths reject |
| Opt-out/hard-bounce suppression after discovery | Send remains blocked |
| Duplicate jobs and worker crash | One effective claim; retry after lease expiry |
| Failed refresh | Prior history preserved, candidate held if required evidence expired |

Use the actual functions/adapters with mocked transport, not copied implementation branches. For each repair first demonstrate the failing regression, implement, then rerun the relevant tests. Full offline test entry point: `python3 -B -m unittest discover -s outbound/scripts -p 'test_contact*.py' -v` after confirming all matching tests use mocks/isolated databases. Do not run a live sender or prober to test discovery.

### Task 8 — Pilot, deployment and honest reporting

- [ ] Inspect 20 businesses, starting with both claimed wins plus cases spanning NAME_ONLY, failed crawls, no-results and unresolved. Retain their existing fit ranking. Compare local search and provider coverage on the same businesses.
- [ ] Review every proposed replacement against its source before enabling automatic contact selection. An empty result is valid. Zero observed false associations in 20 examples is a release check, not proof of zero future errors.
- [ ] Report businesses attempted, confirmed founder identities, published contacts, inferred candidates held, verification outcomes, contacts eligible, unresolved reasons, credits and processing time. Keep SMTP acceptance, actual delivery, replies and wins separate.
- [ ] Snapshot current VPS/local code again before deployment. The inspected source matches, but outbound remains untracked locally and the VPS is not a Git checkout. Some sanitizer scripts are VPS-only. Review/import missing source rather than overwriting it.
- [ ] Remove hardcoded credentials before staging an explicit source-file list; exclude mailbox configuration, databases, exports and logs. Retain existing service secrets outside Git. Commit tested source and record its hash.
- [ ] Back up SQLite consistently, pause only affected workers, drain/resolve in-flight claims, apply additive migrations and deploy a versioned source bundle. Restart only previously enabled services after non-sending checks. Preserve delivery monitoring and all campaign history.
- [ ] Roll back code if checks fail; do not revert the database over newly recorded sends. Do not use destructive directory mirroring.

## 5. Boundaries and success criteria

Do not build a global email index, buy a stack of enrichment subscriptions, invent conversion statistics, or expand the offer/copy work in this repair. The objective is a small supply of explainable contacts for qualified businesses. One good client remains the commercial objective; a large count of labelled founders is not a substitute.

Completion requires all regression tests above, a reviewable 20-business pilot, provenance for every selected contact, consistent gate enforcement across harvesters/imports/send paths, preserved send history, and a deployable source manifest. Reporting must state remaining unknowns. Actual prospect replies and bounces remain empirical outcomes, never guaranteed by discovery.
