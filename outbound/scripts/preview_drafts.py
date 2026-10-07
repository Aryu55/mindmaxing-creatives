#!/usr/bin/env python3
import sys
import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta

sys.path.append("/root/outbound/scripts")
import dispatcher
import volume_controller

mailboxes = dispatcher.load_mailboxes()
clean_mbs = [m for m in mailboxes if volume_controller.check_mailbox_health(m["email"], purpose="campaign")[0]]
leads = dispatcher.load_leads()
crm_data = dispatcher.get_crm_status()

for l in leads:
    d = l.get("domain")
    c_info = crm_data.get(d, {})
    if c_info:
        for k in ["source", "subreddit", "post_title", "post_url", "post_author", "status", "timezone"]:
            if c_info.get(k):
                l[k] = c_info[k]
        if c_info.get("id"):
            l["id"] = c_info["id"]

now = datetime.now(timezone.utc)

for tz_name in ["east", "west"]:
    print("============================================================")
    print(f"   WAVE PREVIEW: {tz_name.upper()} (SCHEDULED LIMIT: 20)")
    print("============================================================")
    if tz_name == "east":
        tz_leads = [
            l for l in leads
            if (l.get("timezone") or crm_data.get(l.get("domain"), {}).get("timezone", "")) in ["America/New_York", "America/Chicago"]
            or not (l.get("timezone") or crm_data.get(l.get("domain"), {}).get("timezone"))
        ]
    else:
        tz_leads = [
            l for l in leads
            if (l.get("timezone") or crm_data.get(l.get("domain"), {}).get("timezone", "")) in ["America/Los_Angeles", "America/Denver", "America/Phoenix", "Pacific/Honolulu", "America/Anchorage"]
        ]

    q = []
    for l in tz_leads:
        contact_email = (l.get("contact_email") or "").strip()
        if not contact_email or "@" not in contact_email:
            continue
        pfx = contact_email.split("@")[0].lower()
        if pfx in ["legal", "privacy", "abuse", "dmca", "press", "media", "investor", "careers", "jobs", "compliance", "sms"]:
            continue
        c_info = crm_data.get(l.get("domain"), {})
        st = c_info.get("status") or l.get("status")
        step = c_info.get("current_sequence_step", 0)
        last_str = c_info.get("last_contacted_at")
        if st not in ["HUMAN_APPROVED", "TOUCH_1_SENT", "TOUCH_2_SENT"]:
            continue

        if st == "HUMAN_APPROVED":
            q.append((1, l, "Touch 1 (Cold Initial)"))
        elif st == "TOUCH_1_SENT" or step == 1:
            if last_str:
                dt_l = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
                if dt_l.tzinfo is None:
                    dt_l = dt_l.replace(tzinfo=timezone.utc)
                if now >= dt_l + timedelta(hours=72):
                    q.append((2, l, "Touch 2 (Follow-up)"))

    for idx, (touch_num, lead_obj, touch_label) in enumerate(q[:20], 1):
        dom = lead_obj.get("domain")
        to_addr = lead_obj.get("contact_email")
        sender = dispatcher.get_pinned_sender(dom, clean_mbs, [])
        c_info = crm_data.get(dom, {})
        orig_subj = c_info.get("touch_1_subject", "quick question")
        if touch_num == 1:
            subj, body = dispatcher.generate_touch_1_copy(lead_obj, sender)
        else:
            subj, body = dispatcher.generate_touch_2_copy(lead_obj, sender, orig_subj)

        founder = lead_obj.get("contact_name") or c_info.get("candidate_name") or c_info.get("resolved_name") or "Founder"
        company = lead_obj.get("company_name", dom)
        s_name = sender.get("name", "Aryan Panchal")
        s_email = sender.get("email", "")

        print(f"[{idx:02d}] {touch_label}")
        print(f"     To:      {founder} <{to_addr}> ({company} - {dom})")
        print(f"     From:    {s_name} <{s_email}>")
        print(f"     Subject: {subj}")
        print("     Body:")
        for ln in body.strip().split("\n"):
            print(f"       {ln}")
        print()
