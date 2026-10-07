#!/usr/bin/env python3
"""
CLI helper for interns to report manual message dispatch.
Usage:
  python3 outbound/scripts/report_sent.py <run_id> [--notes "optional text"]
Enforces zero em dashes.
"""
import argparse
import json
import os
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from log_intern_telemetry import TelemetryClient


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", help="UUID of the outreach run")
    parser.add_argument("--notes", default="", help="Optional notes about the send")
    parser.add_argument("--config", type=Path, help="Path to config.json")
    args = parser.parse_args(argv)

    try:
        telemetry = TelemetryClient.from_config(args.config)
        event_id = telemetry.report_sent(args.run_id, notes=args.notes)
        sync_res = telemetry.sync()

        if sync_res.get("status") == "synced":
            print(f"Send reported for run {args.run_id}. VPS record updated successfully.")
        else:
            print(f"Send recorded locally for run {args.run_id}. Queued for sync (status: {sync_res.get('status')}).")
        return 0
    except ValueError as ve:
        print(f"Error: {ve}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Reporting failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
