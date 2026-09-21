# Daily mailbox reporting and adaptive scheduling — audit and implementation plan

> For agentic workers: use superpowers:executing-plans for implementation. This file specifies the repair; it does not install a VPS scheduler or change live sending limits.

**Goal:** Generate an explainable daily report for all 25 senders, set conservative individual sending allowances, prioritize due follow-ups, and defer work when safe capacity falls.

**Architecture:** Collect evidence continuously; calculate versioned daily decisions from rolling history; enforce live holds and transactional budgets at dispatch. Keep recipient targeting/approval, mailbox health and campaign effectiveness separate. Use the existing Python/SQLite/VPS stack.

**Audit:** 21 September 2026, approximately 08:10–08:15 UTC. Production was read-only. Offline tests used temporary databases and mocked IMAP. No messages were sent, production data changed or live quotas adjusted. The separate mailbox snapshot lists all 25 accounts.

## 1. Actual state and defects

At the snapshot there were 27 message records: 25 campaigns and two diagnostics. Campaign classifications were 1 replied, 2 auto_response and 22 unknown downstream delivery. All 25 sender and eight seed collectors recently reported healthy access. Only one sender had diagnostic observations, across one Gmail seed. Two distinct tests generated 130 repeated observation events. One test simultaneously had smtp_status=temp_failure and delivery_state=inbox.

All senders were Level 1/active, with no HUMAN_APPROVED leads. The collector and outbound scheduler were running. The inspected root crontab, service inventory and application callsites did not show a recurring daily report, diagnostic rotation or promotion invocation. The saved daily summary was dated September 20. This is an inspection finding, not proof about every possible external scheduler.

Six inspected core sources initially matched VPS hashes: delivery_monitor.py, volume_controller.py, diagnostic_sender.py, test_delivery_system.py, dispatcher.py and scheduler.py. Dispatcher/scheduler changed during the audit and their newer versions also matched at the second check. outbound_status.py differed locally versus VPS. Recheck versions before implementation; do not overwrite concurrent work.

| Priority | Confirmed problem | Evidence |
|---|---|---|
| P1 | Unmatched bounce can modify another message | delivery_monitor.py:155–175 uses notes LIKE '%%' when recipient extraction fails, then selects the latest campaign globally. Mocked delayed notification marked an unrelated message bounced/perm_failure. |
| P1 | Delays, policy failures and invalid recipients are conflated | Bounce recognition relies on sender/subject and does not parse DSN Action/Status. All recognized recipients are permanently suppressed as hard bounces. |
| P1 | Missing monitoring data can pass as healthy | volume_controller.check_mailbox_health returned (True, Healthy) with no collector row. Seed collector availability is not checked there. |
| P1 | Promotion crashes on current timestamps | Production level_updated_at values have no UTC offset; evaluate_mailbox_promotion subtracts them from aware UTC time and raises TypeError. Reproduced offline. |
| P1 | Reply acknowledgement can hide later human interest | A mocked automatic reply followed by a human reply to the same outbound message stayed auto_response. The collector ignores further replies after either replied/auto_response. |
| P1 | Reply records do not stop the campaign state | delivery_monitor updates messages but not lead/sequence state. No suppression/stop path for a plain-text opt-out is implemented in this collector. |
| P1 | Campaign guard can disappear | Both sending modules permit volume_controller=None after import failure and fall back to older limits. Live dispatch must fail closed. |
| P1 | SMTP evidence and retries are lossy | Send helpers return False and an empty ID on exceptions; callers lose protocol stage/code, classify failures generically and refund quota. A failure after message acceptance can therefore be misrepresented and retried. |
| P2 | Repeated polling inflates evidence | No IMAP UID/UIDVALIDITY cursor or unique event key. Same two diagnostics repeatedly produce new inbox events and append duplicate notes. Replayed bounce created two events in the offline test. |
| P2 | Collector can miss messages and overstate coverage | Last 30 messages only, limited date windows, skipped folder failures; messages_scanned counts all search hits rather than fetched items. A successful login is not a complete scan. |
| P2 | No actual daily adaptive decision loop | Promotion function is defined but no production caller was found. There is no daily decrease/hold/increase decision ledger. |
| P2 | Seed rotation does not rotate over days | diagnostic_sender chooses seed[idx % count], assigning the same sender to the same seed every run, despite promotion requiring two seeds. |
| P2 | Reporting mixes meanings | Today's quota counters are shown beside all-time delivery states. Current acceptance is confused with cumulative SMTP submission acceptance; test records are called received even when unobserved; stale health flags can appear healthy. |
| P2 | Follow-up priority/capacity allocation absent | Queues follow source/recency order rather than due follow-ups first. Selection can choose an unavailable sender and skip work instead of allocating eligible new work elsewhere. |
| P2 | Thread continuity incomplete | Scheduler send function does not attach In-Reply-To/References; dispatcher supports an argument but its live call does not supply it. Re: alone does not establish threading. |
| P2 | Provider scope is guessed from the address string | Custom Google Workspace/Microsoft domains are classified other; Gmail seed placement is not evidence about those business recipients. |

Eight existing delivery tests passed. The test named duplicate_bounces tests only suppression-table upserts, not duplicate collector events. The Promotions test duplicates an expression rather than running IMAP handling. These tests do not cover the reproduced failures.

## 2. What the controller may infer

- SMTP acceptance by IONOS establishes submission acceptance, not a prospect inbox delivery.
- Diagnostic inbox/Spam results apply to those controlled seed messages. Current coverage is personal Gmail only. Do not extrapolate a prospect inbox-placement percentage.
- No reply is not an open, a spam placement or a complaint. Open tracking is absent and must stay absent in this version. Apple privacy protection also makes open-based conclusions unreliable. [Apple explanation](https://www.apple.com/legal/privacy/data/en/mail-privacy-protection/)
- A complete recipient complaint feed is not currently connected. Display complaint coverage as unavailable, with separately counted explicit received complaints. Google Postmaster reports concern personal Gmail and may omit low-volume data. Missing data is not zero complaints. [Google dashboards](https://support.google.com/mail/answer/14668346?hl=en)
- Recalculate daily; increase slowly; react to concrete faults immediately. Google recommends gradual increases and monitoring, not abrupt jumps after a quiet day. [Google sender guidance](https://support.google.com/mail/answer/81126?hl=en-GB)
- New numerical thresholds below are conservative operating defaults, not validated reputation tiers or estimated spam probabilities.

## 3. Repair evidence collection first

Modify delivery_monitor.py, volume_controller.py and the schema migration. Split parsing into pure functions in delivery_events.py so fixtures exercise the actual parser and reducer.

- [ ] Record IMAP account, folder, UIDVALIDITY, UID and scan boundaries. Advance a cursor only after durable ingestion. Fetch all due UIDs in bounded batches, continuing across cycles. Record incomplete coverage and folder errors instead of reporting full health.
- [ ] Deduplicate raw messages across folders using a stable provider ID where available, otherwise account/message ID plus content hash. Deduplicate semantic outcomes separately. Reinspection of the same placement is not a new independent diagnostic; retain real placement changes as transitions.
- [ ] Keep readonly=True and BODY.PEEK; discover localized special-use folders. Include permitted All Mail/archive coverage for seeds. Do not change flags, star, reply, or move messages to manufacture engagement.
- [ ] Parse multipart/report and message/delivery-status, including recipient-level Action, Status and Diagnostic-Code. Distinguish temporary delivery delay, invalid address, full mailbox, sender policy rejection and unknown failure. Parse returned message/envelope identifiers to correlate with an actual outgoing attempt. [DSN specification](https://www.rfc-editor.org/rfc/rfc3464.html)
- [ ] Reject empty/wildcard matching. An event without a trustworthy, unambiguous match is stored as unmatched for investigation; it does not modify a message or suppress an address. A human-readable fallback must be explicitly labelled lower-confidence and cannot auto-suppress without an exact corroborated match.
- [ ] Count each inbound reply independently. Use In-Reply-To and References, falling back to an unambiguous participant/thread match. Auto-Submitted and recognised system headers precede body heuristics. A word such as ticket in a human's text is insufficient to classify a bot.
- [ ] A human reply stops the automated sequence. Explicit opt-out suppresses the recipient across every mailbox. Ambiguous replies hold the sequence for review. An out-of-office notice defers until a credible stated return date, or seven days when absent; a ticket response holds for routing review. Later human responses remain processable.
- [ ] Record trusted receiver Authentication-Results with identity/alignment information, not substring pass anywhere in an arbitrary header. Only apply seed-based controls to an exact registered diagnostic ID, sender and intended seed. Unmatched or spoofed diagnostic-looking messages cannot pause a domain. [Authentication-Results trust boundaries](https://www.rfc-editor.org/rfc/rfc8601.html)
- [ ] Keep submission, transport outcome, placement observation and reply outcomes separate. Preserve original facts when a later inbox observation reconciles a transport-uncertain attempt. Rebuild summary views from events; never replace the attempt history.

## 4. Daily report and decision policy

Add daily_mailbox_planner.py. It calculates a pure `plan_day(snapshot, policy, day_utc)` result and persists an immutable revision in mailbox_daily_decisions. A separate report renderer produces JSON and Markdown from the same decision snapshot.

Schedule the collector every ten minutes, diagnostic planning daily at 00:05 UTC, and reporting/decision generation daily at 01:00 UTC (06:30 IST). Jobs missed during restart must run once on recovery. Do not replay missed diagnostics in a burst. Live safety checks run before every dispatch; report revisions may lower the day's allowance immediately. Normal increases occur only at the daily decision boundary.

Each of the 25 report rows must include:

- Yesterday's attempted, submission-accepted, confirmed pre-acceptance failed and uncertain sends; new versus follow-up versus diagnostic counts.
- Rolling seven-day outcomes and raw denominators, with cohort/source and event-occurrence versus discovery timestamps. Include lifetime/legacy figures only in a separately labelled section.
- Unique diagnostics sent/observed, seed diversity, dates, placement/authentication, missing tests and contradictory evidence.
- Latest successful complete scans, seed coverage and historical monitoring gaps.
- Current baseline cap, effective cap, used/reserved/remaining budget, decision reason and next reconsideration time.
- Due follow-ups, new work allocated, deferred work, oldest overdue item and whether each task is pinned to a sender.
- Visible statements: prospect opens unavailable; complete complaint coverage unavailable; personal-Gmail seed evidence only.

Keep the existing maximum campaign levels 1, 2 and 3 per mailbox/day. Diagnostics have a separate maximum of one/day; combined limits are respectively 2, 3 and 4. Follow-ups consume campaign capacity. Policy limits are ceilings, never required targets.

Apply these rules in priority order:

| Observation | Decision |
|---|---|
| Recipient opt-out, explicit complaint or confirmed invalid address | Suppress that recipient and cancel queued touches everywhere. Do not switch senders. |
| Confirmed authentication failure on an identified diagnostic | Campaign cap 0 for its sending domain; investigate configuration. |
| Identified seed message in Spam | Campaign cap 0 for its sender; freeze promotions for siblings on its domain pending scope assessment. Promotions folder alone is not Spam. |
| Missing/incomplete sender monitoring, or no complete successful sender scan for >60 minutes | Campaign cap 0 for that sender until fresh coverage is restored. |
| Required seed monitoring is unavailable | Hold affected campaigns; diagnostics remain queued until a usable seed is available. |
| New sender has no clean observed diagnostic; last qualifying diagnostic older than 36 hours | Campaign cap 0 until a valid diagnostic is observed. The 36-hour interval permits daily jobs without false midnight cutoffs. |
| Three consecutive genuine pre-acceptance 4xx submission failures, excluding successful/uncertain submissions | Transport hold at narrowest supported scope; honour Retry-After where available, otherwise wait at least one hour. |
| One invalid-address bounce | Suppress the address; freeze growth for the affected source/domain pending review, not an automatic declaration that the mailbox reputation is destroyed. |
| Two distinct invalid recipients among the latest 20 mature submissions from a source within seven days | Hold new prospects from that source for list review. Existing valid, unsuppressed follow-ups may continue within otherwise healthy caps. This is a conservative count trigger, not a stable percentage estimate. |
| Explicit complaint or provider policy block | Hold the affected campaign/route for review. Do not route the same problematic traffic through other domains. |
| Small sample, no replies, or unavailable complaint data | Hold the existing baseline; do not claim deterioration or promote merely because no faults are visible. |
| At least seven full days at the current level, five reliably recorded accepted campaign submissions aged >=48h at that level, three distinct clean diagnostics on three dates across >=2 seeds within seven days, latest <=36h, complete recent monitoring, no unresolved relevant incidents | Increase baseline by exactly one, capped at Level 3. Insufficient evidence holds. |

Historical imported campaign counts may appear in reports but cannot satisfy promotion gates unless independently reconciled to actual send records. Normalize legacy timestamps explicitly as UTC only after verifying the migration's time basis; never silently mix naive/aware datetime values.

For monitoring outages, recover automatically after two complete successful scans and a fresh qualifying diagnostic. For an isolated Spam hold, keep campaigns stopped until two clean recovery diagnostics on separate days and distinct seeds; resume at Level 1 with a new seven-day growth clock. Recovery diagnostic attempts remain capped at one/day and are allowed through campaign-only holds. Authentication/configuration and policy-block holds require a recorded resolution plus clean rechecks; they do not expire just because time passed. Manual holds never auto-clear.

Persist reason codes, evidence IDs, thresholds, prior/new caps and decision versions. Keep scope explicit: recipient, mailbox, domain, recipient provider/transport route, campaign/source or global. Determine business recipient provider from DNS MX when available; a gateway or unknown route remains unknown. The VPS does not control IONOS's complete shared IP pool, so reported IP-level conclusions must remain limited.

## 5. Allocation, follow-up priority and reliable sending

Modify dispatcher.py and scheduler.py to call one shared planner/dispatcher implementation. Remove their optional safety-controller fallback.

- [ ] Use an additive outbound_jobs table keyed uniquely by sequence ID and touch number. Store recipient/contact version, assigned sender, parent message ID, due_at, earliest_send_at, expiry, status and attempt/claim IDs.
- [ ] Schedule due unsuppressed follow-ups first, oldest due first, subject to the recipient's allowed time window and pinned sender. Reserve those slots before scheduling new contacts. Retain current approved sequence spacing; no acceleration or extra touches.
- [ ] After follow-ups, assign new unattempted prospects by existing pain-signal priority, then freshness. Choose among eligible senders by lowest fraction of today's allowance already consumed/reserved, with deterministic rotating ties. Persist the assignment when claiming the first send.
- [ ] Keep an existing conversation on its original sender and recipient. If that sender is paused, defer its follow-up. If the original sender is absent from configuration, hold for review instead of randomly choosing another account.
- [ ] Reassignment is limited to never-attempted new contacts, inside already approved healthy budgets. Do not increase another mailbox's allowance to recover lost capacity. Domain/provider/global holds apply before redistribution. An uncertain or blocked attempt is never rerouted to another sender.
- [ ] Defer overflow to the next eligible window; do not increase the next day's allowance to clear backlog. If a follow-up becomes more than 14 days overdue, expire it for review rather than sending a late catch-up burst. Report starvation/backlog explicitly.
- [ ] Keep original subject and actual Message-ID chain in In-Reply-To/References for follow-ups. Replies stop pending automation before job claiming.
- [ ] Transactionally claim a unique touch and reserve mailbox, domain, route and global budgets in SQLite. Re-read suppression, campaign/contact approval and current holds in the claim transaction. Quota reservation alone does not stop two workers sending the same touch.
- [ ] Create an immutable attempt/message ID before SMTP. Preserve stage-specific response codes, enhanced codes and raw response. Treat post-DATA ambiguity as SUBMISSION_UNCERTAIN; hold the attempt for reconciliation without quota refund or automatic resend. A QUIT error after explicit submission acceptance does not turn the send into a failure.
- [ ] Refund accepted-send capacity only for a confirmed pre-acceptance rejection, to the original reservation day. Maintain a separate attempt budget of campaign cap plus two definite transport retries/day/mailbox, paced with backoff; invalid-recipient rejections are not retried. This prevents infinite retries after refunds.
- [ ] Count diagnostics and every follow-up against the corresponding budgets. Never log Delivered when only submission acceptance is known. Loss of telemetry persistence after SMTP is an uncertain outcome, not permission to repeat.

Example (illustrative, not current live caps): three mailboxes have campaign caps 2, 1 and 0. Sender A has one due follow-up, sender B has two, sender C has one. Schedule A's follow-up and one new prospect; schedule B's oldest follow-up; defer B's other follow-up and C's pinned follow-up. Total campaign capacity is three. No extra capacity is created elsewhere to compensate for C.

## 6. Implementation sequence, tests and release

1. Snapshot/back up production consistently; reconcile the old 25 campaign records and the observed diagnostic with a failed submission status. Preserve unknowns and source evidence. Do not silently rewrite past facts.
2. Fix collector attribution, replay safety, reply/opt-out processing and scan completeness. Build raw MIME/IMAP fixture tests first.
3. Repair timestamp handling and create the pure daily decision engine plus immutable reports. Add rotating seed assignment using a persisted next-seed index per sender; zero seed configuration must hold cleanly rather than divide by zero.
4. Add persistent jobs/attempts and unified claiming; wire both existing command entry points to them. Remove fallbacks that bypass monitoring and quotas.
5. Replay historical snapshots and synthetic scenarios offline, then run shadow decisions on production reads. No live caps increase during shadow operation. Compare every proposed decision with its evidence.
6. Deploy versioned source and additive migrations, then activate daily reporting and conservative decisions after tests pass and each sender's required diagnostic coverage exists. Preserve current campaign approvals; this work must not authorize more leads.

Acceptance scenarios:

- Delayed DSN, recipient unknown, policy rejection, full inbox and malformed DSN remain distinct; unmatched notices never alter an unrelated send.
- Repeat the same IMAP cycle three times: unique outcome counts unchanged; real folder movement creates one transition; UIDVALIDITY reset and >30 messages recover without loss.
- Auto-response followed by a human reply is retained and cancels automation; opt-out suppresses all mailboxes; a missing campaign foreign key is flagged for reconciliation.
- Missing/stale/failing folder or seed collectors cannot report fully healthy; spoofed/unmatched diagnostic headers cannot pause domains.
- Naive legacy timestamp handling is deterministic; zero activity and small samples hold; seven-day clean fixtures grow one level; any unresolved incident blocks growth.
- Seed assignment changes across days; paused campaigns can perform bounded recovery diagnostics; no fake engagement actions occur.
- Two simultaneous workers cannot exceed any budget or send one touch twice; SQLite restart preserves claims; an expired pre-SMTP claim can retry, but a claim that may have submitted remains uncertain.
- Sender pause mid-day shrinks remaining capacity; follow-ups stay pinned; new never-attempted work can move only within existing healthy capacity; no backlog catch-up burst.
- Connection loss before DATA versus after submission, QUIT failure, DB error after acceptance, midnight retry and 4xx/5xx responses produce the correct attempt state and quota accounting.
- Daily reports contain all configured 25 senders including zero-activity/missing-coverage rows, consistent seven-day/yesterday denominators and the exact decision revision enforced by dispatch.

Use temporary databases and mocked SMTP/IMAP in tests. No live prospect sends for validation. The initial eight tests passed but are insufficient; extend them to the above actual code paths rather than testing copied expressions.

Add systemd services/timers to the existing VPS project deployment, with explicit working directory and private environment file. Use a single-instance lock/DB lease, idempotent missed-run recovery and restart policies. Alert locally in the report/operations log on failure; do not create another outbound notification channel without configuration. Keep logs redacted. Remove hardcoded credential fallbacks and rotate exposed credentials as part of deployment hygiene.

Verify source hashes again because Gemini is changing files concurrently. Import the VPS-only schema migration and review local/VPS reporter differences. Take SQLite backups through the backup API rather than plain copying a live database. Deploy only source/tests/migrations; preserve secrets, quota decisions, suppression lists and message history. Rollback code separately from operational data. No destructive directory mirroring.

**Definition of done:** daily reports are generated automatically, all 25 senders receive evidence-linked decisions, dispatch uses those decisions, follow-ups take priority without sender hopping, uncertain signals remain unknown, and regression tests cover replay, concurrency and delivery ambiguity. No claim of guaranteed inbox placement or reply probability.
