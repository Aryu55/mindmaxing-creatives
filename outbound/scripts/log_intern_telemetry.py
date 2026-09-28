#!/usr/bin/env python3
"""
Mindmaxing Outbound Telemetry Client
Logs lead triage events directly to the VPS database in the background.
Supports zero-blocking execution: generates lead reference ID and records KPI metrics.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

# Live VPS Telemetry Endpoint
DEFAULT_API_URL = os.environ.get(
    "MM_TELEMETRY_URL",
    "https://correction-breach-thanks-folders.trycloudflare.com/api/v1/telemetry/log"
)
DEFAULT_INTERN_KEY = os.environ.get("MM_INTERN_KEY", "mm_key_intern_default_2026")

def log_lead(
    handle: str,
    platform: str,
    status: str,
    intern_id: str = "intern_1",
    url: str = None,
    bottleneck: str = None,
    dm: str = None,
    reply: str = None,
    email: str = None,
    disqual_reason: str = None,
    api_url: str = DEFAULT_API_URL,
    api_key: str = DEFAULT_INTERN_KEY
):
    payload = {
        "intern_id": intern_id,
        "platform": platform,
        "target_handle": handle,
        "target_url": url,
        "qualification_status": status.upper(),
        "disqualification_reason": disqual_reason,
        "bottleneck_summary": bottleneck,
        "generated_dm": dm,
        "generated_reply": reply,
        "generated_email": email
    }

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Intern-Key": api_key
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data
    except Exception as e:
        # Failsafe: return local fallback ID if network is down so intern is never blocked
        return {
            "status": "offline_fallback",
            "lead_ref_id": "OFFLINE-LOG",
            "action": "PROCEED_SEND",
            "error": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Log outreach lead to VPS")
    parser.add_argument("--handle", required=True, help="Target handle (e.g. @brand)")
    parser.add_argument("--platform", default="instagram", help="Platform (instagram, x, email)")
    parser.add_argument("--status", default="QUALIFIED", choices=["QUALIFIED", "DISQUALIFIED"])
    parser.add_argument("--intern", default="intern_1", help="Intern ID")
    parser.add_argument("--url", default="", help="Profile or post URL")
    parser.add_argument("--bottleneck", default="", help="Identified bottleneck")
    parser.add_argument("--dm", default="", help="Generated DM text")
    parser.add_argument("--reply", default="", help="Generated public reply")
    parser.add_argument("--email", default="", help="Generated cold email")
    parser.add_argument("--reason", default="", help="Disqualification reason")

    args = parser.parse_args()

    result = log_lead(
        handle=args.handle,
        platform=args.platform,
        status=args.status,
        intern_id=args.intern,
        url=args.url,
        bottleneck=args.bottleneck,
        dm=args.dm,
        reply=args.reply,
        email=args.email,
        disqual_reason=args.reason
    )

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
