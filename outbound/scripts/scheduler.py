#!/usr/bin/env python3
"""
Mindmaxing Timezone-Aware Outbound Scheduler Daemon
- Strictly enforces B2B Golden Sending Windows:
    * Mon – Fri ONLY (Zero weekend sending: 100% pause on Saturday & Sunday).
    * UK / Europe Window: 08:30 – 15:30 UTC (09:30 – 16:30 BST / CEST).
    * US / Canada Window: 13:30 – 20:30 UTC (09:30 – 16:30 EDT / 06:30 – 13:30 PDT).
- Enforces Balanced Mailbox Ramp:
    * Max 1 send per mailbox per day across all 25 mailboxes (Total cap: 25 sends/day).
    * Biological Poisson delays (40s – 85s) between sends.
- Runs as a persistent background daemon, evaluating windows every 5 minutes.
- Synchronous logging to mindmaxing_crm.db and sent_history.json.
"""

import json
import os
import random
import smtplib
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "config", "mailboxes.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
ICP1_DIR = os.path.join(DATA_DIR, "icp1_shopify_dtc")
LEADS_FILE = os.path.join(ICP1_DIR, "leads.json")
HISTORY_FILE = os.path.join(DATA_DIR, "sent_history.json")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")
LOG_FILE = os.path.join(DATA_DIR, "scheduler.log")

try:
    from crm_manager import log_touch
except ImportError:
    try:
        from outbound.scripts.crm_manager import log_touch
    except ImportError:
        log_touch = None

try:
    import volume_controller
except ImportError:
    try:
        from outbound.scripts import volume_controller
    except ImportError:
        volume_controller = None

try:
    from contact_policy import evaluate_contact, ContactDecision
except ImportError:
    try:
        from outbound.scripts.contact_policy import evaluate_contact, ContactDecision
    except ImportError:
        evaluate_contact = None

try:
    from dispatcher import claim_outbound_job, update_outbound_job_status
except ImportError:
    try:
        from outbound.scripts.dispatcher import claim_outbound_job, update_outbound_job_status
    except ImportError:
        claim_outbound_job = None
        update_outbound_job_status = None

SMTP_HOST = os.environ.get("IONOS_SMTP_HOST", "smtp.ionos.com")
SMTP_PORT = int(os.environ.get("IONOS_SMTP_PORT", 587))
REPLY_TO = os.environ.get("REPLY_TO", "aryan@mindmaxing.info")
MAX_PER_MAILBOX_DAILY = 1  # Strictly 1 email per mailbox for safe warm-up ramp
DAILY_SEND_CAP = 25        # 25 mailboxes × 1 = 25 emails/day total

PHYSICAL_FOOTER = """--
Mindmaxing Studio
102, Sunrise Business Park, Road No. 16, Wagle Estate, Thane, Maharashtra 400604, India
Reply "stop" to opt out"""

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [Outbound Scheduler] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_timezone_window_status(country_code: str, now_utc: datetime = None, state: str = None, city: str = None) -> tuple[bool, str]:
    """
    Evaluates whether the lead's location is currently inside the B2B Golden Sending Window:
    - Monday through Friday in recipient's LOCAL timezone ONLY (Weekend = PAUSE).
    - Local Business Hours: 09:00 to 16:30 local time.
    """
    if now_utc is None:
        now_utc = datetime.now(timezone.utc)

    cc = (country_code or "US").upper()
    hour_utc = now_utc.hour + (now_utc.minute / 60.0)

    # Determine approximate local UTC offset (hours)
    # Offsets during Daylight Saving Time (September)
    local_offset = 0.0

    if cc in ("GB", "UK", "IE"):
        # BST / Irish Standard Time (IST): UTC+1
        local_offset = 1.0
    elif cc in ("DE", "NL", "FR", "IT", "ES", "SE", "DK", "NO", "FI", "EU", "PL", "AT", "CH", "BE"):
        # CEST: UTC+2
        local_offset = 2.0
    elif cc in ("AU", "NZ"):
        # AEST: UTC+10
        local_offset = 10.0
    elif cc in ("US", "CA"):
        st = (state or "").upper().strip()
        eastern_states = {"ME", "NH", "VT", "MA", "RI", "CT", "NY", "NJ", "PA", "DE", "MD", "DC", "VA", "WV", "NC", "SC", "GA", "FL", "OH", "MI"}
        central_states = {"IL", "WI", "MN", "IA", "MO", "ND", "SD", "NE", "KS", "OK", "TX", "LA", "AR", "MS", "AL", "TN"}
        mountain_states = {"MT", "WY", "UT", "CO", "NM", "AZ"}
        pacific_states = {"WA", "OR", "CA", "NV"}

        if st in eastern_states:
            local_offset = -4.0  # EDT
        elif st in central_states:
            local_offset = -5.0  # CDT
        elif st in mountain_states:
            local_offset = -6.0  # MDT / MST
        elif st in pacific_states:
            local_offset = -7.0  # PDT
        else:
            # Conservative nationwide default: guaranteed business hours across all US zones
            # 16:00 UTC = 09:00 PDT / 12:00 EDT; 20:30 UTC = 13:30 PDT / 16:30 EDT
            local_dt = now_utc - timedelta(hours=7)  # check Pacific for local day
            weekday = local_dt.weekday()
            day_name = local_dt.strftime("%A")
            if weekday in (5, 6):
                return False, f"Weekend Holding Pattern in recipient local time ({day_name}). Outbound paused."
            if 16.0 <= hour_utc <= 20.5:
                return True, f"US/CA Nationwide Overlap Window OPEN ({hour_utc:.1f} UTC / 09:00 PDT - 16:30 EDT)"
            return False, f"US/CA Nationwide Overlap Window CLOSED ({hour_utc:.1f} UTC - outside 16:00-20:30 UTC)"
    else:
        local_offset = -4.0

    # Calculate exact local datetime with determined offset
    local_dt = now_utc + timedelta(hours=local_offset)
    local_weekday = local_dt.weekday()
    day_name = local_dt.strftime("%A")

    if local_weekday in (5, 6):
        return False, f"Weekend Holding Pattern in recipient local time ({day_name}). Outbound paused."

    local_hour = local_dt.hour + (local_dt.minute / 60.0)

    # Standard B2B business window: 09:00 to 16:30 local time
    if 9.0 <= local_hour <= 16.5:
        return True, f"Local Business Window OPEN ({local_hour:.1f} local / {local_dt.strftime('%H:%M')} {day_name})"
    return False, f"Local Business Window CLOSED ({local_hour:.1f} local - outside 09:00-16:30 {day_name})"

def load_mailboxes():
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_crm_status():
    """Reads lead sequence states, contact evidence, and verification from SQLite CRM."""
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            l.id, l.domain, l.company_name, l.contact_email, l.status, 
            l.current_sequence_step, l.last_contacted_at, l.client_won,
            l.source, l.subreddit, l.post_title, l.post_url, l.post_author,
            l.contact_type, l.contact_name, l.resolved_name, l.resolved_email,
            l.resolved_role, l.resolved_evidence, l.resolution_status, l.resolved_at,
            l.original_contact_email,
            c.id AS candidate_id, c.full_name AS candidate_name, c.role AS candidate_role,
            c.email AS candidate_email, c.email_origin, c.mailbox_status,
            c.mailbox_checked_at, c.identity_status, c.identity_checked_at
        FROM leads l
        LEFT JOIN contact_candidates c ON l.id = c.lead_id AND c.is_selected = 1
    """)
    data = {}
    for r in cursor.fetchall():
        data[r["domain"]] = dict(r)
    conn.close()
    return data

def get_pinned_sender(domain: str, mailboxes: list, history: list, mailbox_usage: dict = None) -> dict:
    for h in reversed(history):
        if h.get("lead_domain") == domain and h.get("sender_email"):
            match = next((m for m in mailboxes if m["email"] == h["sender_email"]), None)
            if match:
                return match
    if mailbox_usage is not None:
        min_used = min(mailbox_usage.get(m["email"], 0) for m in mailboxes)
        available = [m for m in mailboxes if mailbox_usage.get(m["email"], 0) == min_used]
        if available:
            return random.choice(available)
    return random.choice(mailboxes)

def generate_copy(lead: dict, sender: dict, touch_step: int = 1) -> tuple[str, str]:
    from dispatcher import generate_touch_1_copy, generate_touch_2_copy, generate_touch_3_copy
    if touch_step == 1:
        return generate_touch_1_copy(lead, sender)
    elif touch_step == 2:
        return generate_touch_2_copy(lead, sender, "Re: quick question")
    else:
        return generate_touch_3_copy(lead, sender, "Re: quick question")

def send_email(sender: dict, password: str, to_email: str, subject: str, body: str, in_reply_to: str = None) -> tuple[str, str, str]:
    """
    Returns (status, message_id, error_msg):
      - 'SUCCESS': Message accepted and QUIT clean.
      - 'SUBMISSION_UNCERTAIN': DATA accepted by SMTP server, but exception occurred during QUIT or connection close. Quota must NOT be rolled back.
      - 'FAILED': Pre-submission error (connection, TLS, auth, or recipient rejection before DATA). Quota should be rolled back.
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{sender['name']} <{sender['email']}>"
    msg["To"] = to_email
    msg["Reply-To"] = REPLY_TO
    msg["Subject"] = subject
    msg_id = f"<{int(time.time())}.{random.randint(1000, 9999)}@{sender['email'].split('@')[1]}>"
    msg["Message-ID"] = msg_id

    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to

    msg.attach(MIMEText(body, "plain", "utf-8"))

    server = None
    data_accepted = False
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=25)
        server.starttls()
        server.login(sender["email"], password)
        refused = server.sendmail(sender["email"], [to_email], msg.as_string())
        if refused:
            try:
                server.quit()
            except Exception:
                pass
            return "FAILED", msg_id, f"Recipient refused: {refused}"

        data_accepted = True
        try:
            server.quit()
        except Exception as q_err:
            log(f"Warning: SMTP QUIT error after accepted submission: {q_err}")
            return "SUBMISSION_UNCERTAIN", msg_id, f"Post-DATA QUIT exception: {q_err}"

        return "SUCCESS", msg_id, "OK"
    except Exception as e:
        if data_accepted:
            log(f"Post-DATA SMTP exception from {sender['email']} to {to_email}: {e}")
            return "SUBMISSION_UNCERTAIN", msg_id, str(e)
        else:
            log(f"Pre-submission SMTP error from {sender['email']} to {to_email}: {e}")
            return "FAILED", msg_id, str(e)
    finally:
        if server:
            try:
                server.close()
            except Exception:
                pass

def run_scheduler_cycle(live_mode: bool = False, override_weekend: bool = False):
    mailboxes = load_mailboxes()
    leads = load_leads()
    crm_data = get_crm_status()
    now_utc = datetime.now(timezone.utc)
    today_str = datetime.now().strftime("%Y-%m-%d")

    password = os.environ.get("IONOS_SMTP_PASSWORD", "").strip("\"'")

    # Track usage today
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            history = json.load(open(HISTORY_FILE))
        except Exception:
            pass

    mailbox_usage = {m["email"]: sum(1 for h in history if h.get("sender_email") == m["email"] and h.get("sent_date") == today_str) for m in mailboxes}
    total_sent_today = sum(mailbox_usage.values())

    log(f"=== Scheduler Heartbeat: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} ({now_utc.strftime('%A')}) ===")
    log(f"Daily Sent Count: {total_sent_today}/{DAILY_SEND_CAP} across {len(mailboxes)} mailboxes.")

    if total_sent_today >= DAILY_SEND_CAP:
        log(f"Daily cap ({DAILY_SEND_CAP}) reached for today. Sleeping until tomorrow's window opens.")
        return

    # Check overall weekend gate (can be overridden with --now)
    if not override_weekend and now_utc.weekday() in (5, 6):
        log(f"⏸️  WEEKEND HOLDING PATTERN ACTIVE ({now_utc.strftime('%A')}).")
        log("    Inboxes paused to protect open rates and deliverability. Next window opens Monday 08:30 UTC.")
        log("    (Pass --now to dispatch human-reviewed leads immediately).")
        return

    if live_mode and not volume_controller:
        log("CRITICAL ERROR: volume_controller missing in live mode. Halting scheduler (Fail-Closed).")
        return

    # Build queue of eligible leads
    queue = []
    for l in leads:
        d = l.get("domain")
        email = l.get("contact_email", "").strip(".,;:'\"")
        if not email or "@" not in email:
            continue
        if email.startswith("u003e") or len(email.split("@")[0]) < 2:
            continue
        prefix = email.split("@")[0].lower()
        if prefix in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"] or prefix.endswith("-sms"):
            continue

        c_info = crm_data.get(d, {})
        status = c_info.get("status") or l.get("status", "CANDIDATE")
        step = c_info.get("current_sequence_step", 0)
        client_won = c_info.get("client_won", 0)
        last_str = c_info.get("last_contacted_at")

        if client_won or status in ["CLIENT_WON", "SEQUENCE_COMPLETED", "COOLDOWN", "REPLIED", "REJECTED_FROM_CAMPAIGN"]:
            continue

        # Astra Fail-Closed Gate:
        # In live mode, only dispatch 'HUMAN_APPROVED' leads.
        allowed = ["HUMAN_APPROVED"] if live_mode else ["HUMAN_APPROVED", "READY", "CANDIDATE"]
        if status not in allowed:
            continue

        # Enforce Shared Contact Policy Gate
        if live_mode:
            if not evaluate_contact:
                raise RuntimeError("FAIL-CLOSED: evaluate_contact missing in live scheduler")

            cand_name = c_info.get("candidate_name") or c_info.get("resolved_name") or l.get("contact_name", "")
            cand_role = c_info.get("candidate_role") or c_info.get("resolved_role") or "Founder"
            cand_email = c_info.get("candidate_email") or c_info.get("resolved_email") or email

            cand_origin = c_info.get("email_origin")
            if not cand_origin:
                if c_info.get("contact_type") == "FOUNDER_RESOLVED":
                    cand_origin = "PUBLIC_SITE"
                else:
                    cand_origin = "LEGACY_UNKNOWN"

            cand_id_status = c_info.get("identity_status")
            if not cand_id_status:
                if c_info.get("resolved_name") and c_info.get("resolved_at"):
                    cand_id_status = "FOUNDER_CONFIRMED"
                else:
                    cand_id_status = "UNCONFIRMED"

            cand_mailbox_status = c_info.get("mailbox_status") or c_info.get("mailbox_verification") or "UNCHECKED"
            cand_verif_time = c_info.get("mailbox_checked_at") or c_info.get("resolved_at")
            cand_id_time = c_info.get("identity_checked_at") or c_info.get("resolved_at")

            candidate = {
                "contact_name": cand_name,
                "contact_email": cand_email,
                "domain": l.get("domain"),
                "contact_role": cand_role,
                "identity_status": cand_id_status,
                "email_origin": cand_origin,
                "mailbox_verification": cand_mailbox_status,
                "verification_time": cand_verif_time,
                "identity_evidence_time": cand_id_time,
            }
            campaign_state = {
                "status": status,
                "current_sequence_step": step,
                "active_recipient": c_info.get("contact_email") or email,
                "is_suppressed": False,
                "quota_available": True
            }
            is_eligible, decision, reasons = evaluate_contact(candidate, campaign_state, now_utc)
            if not is_eligible:
                continue

        # Suppression Check
        if volume_controller:
            suppressed, s_reason = volume_controller.is_recipient_suppressed(email)
            if suppressed:
                continue

        # Timezone Window Gatekeeper
        c_code = l.get("country_code", "US")
        if not override_weekend:
            is_open, window_reason = get_timezone_window_status(c_code, now_utc)
            if not is_open:
                continue

        last_dt = None
        if last_str:
            try:
                last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
            except Exception:
                pass

        if step == 0:
            queue.append((l, 1, "TOUCH_1", status))
        elif step == 1 and last_dt and (now_utc - last_dt) >= timedelta(days=3):
            queue.append((l, 2, "TOUCH_2", status))
        elif step == 2 and last_dt and (now_utc - last_dt) >= timedelta(days=5):
            queue.append((l, 3, "TOUCH_3", status))

    # Prioritize Follow-ups (Touch 2, Touch 3) over new leads (Touch 1)
    def queue_sort_key(item):
        ld, t_step, t_lbl, st = item
        is_followup = 0 if t_step > 1 else 1  # follow-ups come first (0 < 1)
        c_i = crm_data.get(ld.get("domain", ""), {})
        last_str = c_i.get("last_contacted_at") or "9999-99-99"
        pain = float(ld.get("pain_score", 0) or 0)
        return (is_followup, last_str if is_followup == 0 else -pain)

    queue.sort(key=queue_sort_key)

    log(f"Eligible Leads in Currently Active Windows: {len(queue)}")

    if not queue:
        log("No eligible leads in open sending windows right now. Waiting for next window opening.")
        return

    worker_id = f"scheduler_{os.getpid()}_{int(time.time())}"

    # Process eligible leads
    for lead, touch_step, touch_label, lead_status in queue:
        if total_sent_today >= DAILY_SEND_CAP:
            log("Reached daily send cap. Pausing.")
            break

        to_email = lead["contact_email"].strip(".,;:'\"")

        # Suppression check
        if volume_controller:
            suppressed, s_reason = volume_controller.is_recipient_suppressed(to_email)
            if suppressed:
                log(f"  [SUPPRESSED] Skipping {to_email}: {s_reason}")
                continue

        sender = get_pinned_sender(lead.get("domain"), mailboxes, history, mailbox_usage)
        subject, body = generate_copy(lead, sender, touch_step)
        c_code = lead.get("country_code", "US")

        job_id = None
        # Outbound Job Durable Claim and Volume Controller Reservation (Fail-Closed)
        if live_mode:
            if not volume_controller:
                raise RuntimeError("FAIL-CLOSED: volume_controller missing in live scheduler")
            claimed, c_reason, claim_meta = volume_controller.reserve_and_claim_job(
                lead_id=lead.get("id", 0),
                domain=lead.get("domain", ""),
                touch_number=touch_step,
                mailbox=sender["email"],
                recipient=to_email,
                subject=subject,
                body=body,
                worker_id=worker_id,
                campaign_name=lead.get("source", "dealstrike-distributors")
            )
            if not claimed:
                log(f"  [TOUCH/QUOTA] Skipping {lead.get('domain')} touch {touch_step}: {c_reason}")
                continue
            job_id = claim_meta["job_id"]
        elif mailbox_usage.get(sender["email"], 0) >= MAX_PER_MAILBOX_DAILY:
            continue

        # Threading: fetch parent message ID for follow-up touches
        parent_msg_id = None
        if touch_step > 1 and volume_controller:
            try:
                conn_p = volume_controller.get_db_connection()
                cp = conn_p.cursor()
                cp.execute("SELECT message_id FROM messages WHERE recipient_email = ? AND purpose = 'campaign' ORDER BY sent_at DESC LIMIT 1", (to_email,))
                p_row = cp.fetchone()
                if p_row and p_row["message_id"]:
                    parent_msg_id = p_row["message_id"]
                conn_p.close()
            except Exception:
                pass

        if not parent_msg_id and touch_step > 1 and history:
            for h in reversed(history):
                if h.get("lead_email") == to_email and h.get("message_id"):
                    parent_msg_id = h.get("message_id")
                    break

        if not live_mode:
            log(f"[DRY-RUN] [{touch_label}] {sender['email']} -> {to_email} [{c_code}]")
            log(f"  Subject: {subject}")
            mailbox_usage[sender["email"]] = mailbox_usage.get(sender["email"], 0) + 1
            total_sent_today += 1
        else:
            log(f"[LIVE DISPATCH] [{touch_label}] Sending from {sender['email']} -> {to_email} [{c_code}] (In-Reply-To: {parent_msg_id})...")
            send_status, msg_id, err_msg = send_email(sender, password, to_email, subject, body, in_reply_to=parent_msg_id)
            if send_status == "SUCCESS":
                if job_id and update_outbound_job_status:
                    update_outbound_job_status(job_id, "SENT")
                if volume_controller:
                    volume_controller.record_campaign_message(
                        message_id=msg_id,
                        sender_email=sender["email"],
                        recipient_email=to_email,
                        prospect_domain=lead.get("domain", ""),
                        campaign_touch=touch_step,
                        subject=subject,
                        smtp_success=True
                    )
                record = {
                    "sender_email": sender["email"],
                    "lead_email": to_email,
                    "lead_domain": lead.get("domain"),
                    "touch_number": touch_step,
                    "subject": subject,
                    "message_id": msg_id,
                    "sent_date": today_str,
                    "timestamp": datetime.now().isoformat()
                }
                history.append(record)
                json.dump(history, open(HISTORY_FILE, "w"), indent=2)

                if log_touch:
                    try:
                        log_touch(lead.get("domain"), to_email, sender["email"], step=touch_step, subject=subject)
                    except Exception as e:
                        pass

                mailbox_usage[sender["email"]] = mailbox_usage.get(sender["email"], 0) + 1
                total_sent_today += 1
                log(f"  ✅ Delivered! Mailbox {sender['email']} (1/1 today). Total sent today: {total_sent_today}/{DAILY_SEND_CAP}.")

                delay = random.uniform(45.0, 85.0)
                log(f"  Pacing delay: resting {delay:.1f}s before next send...")
                time.sleep(delay)
            elif send_status == "SUBMISSION_UNCERTAIN":
                log(f"  [UNCERTAIN] Post-DATA exception to {to_email}: {err_msg}. Retaining quota reservation and holding touch for review.")
                if job_id and update_outbound_job_status:
                    update_outbound_job_status(job_id, "UNCERTAIN")
                if volume_controller:
                    volume_controller.record_campaign_message(
                        message_id=msg_id,
                        sender_email=sender["email"],
                        recipient_email=to_email,
                        prospect_domain=lead.get("domain", ""),
                        campaign_touch=touch_step,
                        subject=subject,
                        smtp_success=False,
                        error_msg=f"SUBMISSION_UNCERTAIN: {err_msg}"
                    )
            else:
                log(f"  ❌ Failed delivery to {to_email}: {err_msg}")
                if job_id and update_outbound_job_status:
                    update_outbound_job_status(job_id, "FAILED")
                if volume_controller:
                    volume_controller.rollback_quota(sender["email"], "campaign")
                    volume_controller.record_campaign_message(
                        message_id=msg_id or f"failed-{int(time.time())}",
                        sender_email=sender["email"],
                        recipient_email=to_email,
                        prospect_domain=lead.get("domain", ""),
                        campaign_touch=touch_step,
                        subject=subject,
                        smtp_success=False,
                        error_msg=f"SMTP send failure: {err_msg}"
                    )

def run_daemon(live_mode: bool = False, override_weekend: bool = False):
    mode_str = "LIVE DISPATCH MODE" if live_mode else "DRY-RUN SIMULATION MODE"
    log(f"Starting Mindmaxing Outbound Scheduler Daemon in {mode_str}...")
    log("Checking timezone windows every 10 minutes.")
    while True:
        try:
            run_scheduler_cycle(live_mode=live_mode, override_weekend=override_weekend)
        except Exception as e:
            log(f"Scheduler cycle error: {e}")
        time.sleep(600)  # Check every 10 minutes

if __name__ == "__main__":
    is_live = "--live" in sys.argv
    is_now = "--now" in sys.argv or "--override-weekend" in sys.argv

    if is_now:
        log("Executing immediate single reviewed dispatch cycle (--now flag detected)...")
        run_scheduler_cycle(live_mode=is_live, override_weekend=True)
    else:
        run_daemon(live_mode=is_live, override_weekend=False)
