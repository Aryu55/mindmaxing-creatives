#!/usr/bin/env python3
"""
Mindmaxing Delivery Monitor Daemon
Runs continuous 10-minute polling cycles across 25 sending mailboxes and 8 Gmail test inboxes.
"""

import time
from datetime import datetime, timezone
import delivery_monitor

def main():
    print(f"[{datetime.now(timezone.utc).isoformat()}] Starting Delivery Monitor Daemon (10-minute interval)...", flush=True)
    while True:
        try:
            delivery_monitor.run_monitor_cycle()
        except Exception as e:
            print(f"[{datetime.now(timezone.utc).isoformat()}] Error in monitor cycle: {e}", flush=True)
        
        print(f"[{datetime.now(timezone.utc).isoformat()}] Sleeping 600s until next sweep...", flush=True)
        time.sleep(600)

if __name__ == "__main__":
    main()
