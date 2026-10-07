#!/usr/bin/env python3
"""
Mindmaxing Automated Radar Dashboard Deployer v1.0
Exports real-time operational telemetry from SQLite CRM and publishes
the updated snapshot to Cloudflare Pages (mindmaxing.one/radar).

Runs automatically on VPS via cron:
1. Hourly background heartbeat
2. Triggered immediately after each dispatch wave
3. Triggered immediately after nightly mailbox review
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("MINDMAXING_BASE_DIR") or (
    "/root/outbound" if os.path.exists("/root/outbound/data") else os.path.dirname(SCRIPT_DIR)
)
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
DIST_DIR = os.path.join(BASE_DIR, "dist")
EXPORT_SCRIPT = os.path.join(DASHBOARD_DIR, "export_snapshot.py")
SOURCE_JSON = os.path.join(DASHBOARD_DIR, "radar_data.json")
SOURCE_HTML = os.path.join(DASHBOARD_DIR, "index.html")


def log(msg: str):
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{now_str}] [RADAR-DEPLOY] {msg}", flush=True)


def main():
    log("Starting automated radar telemetry refresh cycle...")

    if not os.path.exists(EXPORT_SCRIPT):
        log(f"ERROR: export_snapshot.py not found at {EXPORT_SCRIPT}")
        sys.exit(1)

    if not os.path.exists(DIST_DIR):
        log(f"ERROR: dist directory not found at {DIST_DIR}")
        sys.exit(1)

    # 1. Regenerate radar_data.json from live SQLite database
    log("Regenerating radar_data.json from live CRM database...")
    res = subprocess.run([sys.executable, EXPORT_SCRIPT], capture_output=True, text=True)
    if res.returncode != 0:
        log(f"ERROR: export_snapshot.py failed (code {res.returncode}):\n{res.stderr}")
        sys.exit(res.returncode)
    log(f"Snapshot exported: {res.stdout.strip()}")

    # 2. Sync to dist directory
    radar_sub = os.path.join(DIST_DIR, "radar")
    os.makedirs(radar_sub, exist_ok=True)

    if os.path.exists(SOURCE_JSON):
        shutil.copy2(SOURCE_JSON, os.path.join(DIST_DIR, "radar_data.json"))
        shutil.copy2(SOURCE_JSON, os.path.join(radar_sub, "radar_data.json"))
        log("Copied radar_data.json to dist targets.")

    if os.path.exists(SOURCE_HTML):
        shutil.copy2(SOURCE_HTML, os.path.join(DIST_DIR, "radar.html"))
        shutil.copy2(SOURCE_HTML, os.path.join(radar_sub, "index.html"))
        log("Copied index.html to dist targets.")

    # 3. Publish to Cloudflare Pages
    log("Publishing updated assets to Cloudflare Pages (mindmaxing-creatives)...")
    env = os.environ.copy()
    if not env.get("CLOUDFLARE_API_TOKEN"):
        toml_path = os.path.expanduser("~/.config/.wrangler/config/default.toml")
        if os.path.exists(toml_path):
            with open(toml_path) as tf:
                for line in tf:
                    if "oauth_token" in line or "api_token" in line:
                        token_val = line.split("=")[-1].strip().strip('"\'')
                        if token_val:
                            env["CLOUDFLARE_API_TOKEN"] = token_val
                            break

    cmd = [
        "npx", "wrangler", "pages", "deploy", DIST_DIR,
        "--project-name", "mindmaxing-creatives",
        "--branch", "main",
        "--commit-dirty=true"
    ]
    deploy_res = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE_DIR, env=env)
    if deploy_res.returncode != 0:
        log(f"ERROR: Wrangler deploy failed:\n{deploy_res.stderr}\n{deploy_res.stdout}")
        sys.exit(deploy_res.returncode)

    log("Deployment successful. mindmaxing.one/radar is updated.")


if __name__ == "__main__":
    main()
