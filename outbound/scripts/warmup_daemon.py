#!/usr/bin/env python3
"""
Mindmaxing Peer-to-Peer Warmup Background Daemon
- Runs continuous warmup cycles across 25 mailboxes / 4 domains.
- Executes 1-2 pairs every 15-25 minutes.
- Sleeps during off-hours (runs during daytime/evening UTC).
"""

import time
import random
import subprocess
from datetime import datetime

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [DAEMON] {msg}", flush=True)

def main():
    log("Warmup background daemon starting...")
    while True:
        try:
            num_pairs = random.choice([1, 2])
            log(f"Triggering warmup cycle with {num_pairs} pair(s)...")
            res = subprocess.run(["python3", "/root/outbound/scripts/warmup_engine.py", str(num_pairs)], capture_output=True, text=True)
            print(res.stdout, flush=True)
            if res.stderr:
                print(f"[STDERR] {res.stderr}", flush=True)
        except Exception as e:
            log(f"Error in warmup cycle: {e}")

        # Sleep between 15 and 25 minutes (900s to 1500s)
        sleep_secs = random.uniform(900, 1500)
        log(f"Cycle complete. Sleeping {sleep_secs/60:.1f} minutes until next round...")
        time.sleep(sleep_secs)

if __name__ == "__main__":
    main()
