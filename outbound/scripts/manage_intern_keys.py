#!/usr/bin/env python3
"""
Mindmaxing Intern Key Management CLI
Creates, lists, and revokes intern API keys.
Stores only SHA-256 hashes of keys on the server.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from intern_tracking_store import TrackingStore

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data/mindmaxing_crm.db"

def main():
    parser = argparse.ArgumentParser(description="Manage Intern Outreach Keys")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create new intern credentials")
    p_create.add_argument("--intern-id", required=True, help="Unique intern ID (e.g. intern_neha)")
    p_create.add_argument("--name", required=True, help="Intern full name")
    p_create.add_argument("--role", default="intern", choices=["intern", "admin"], help="Role")
    p_create.add_argument("--target", type=int, default=100, help="Daily target")

    # list
    p_list = subparsers.add_parser("list", help="List all accounts")

    # revoke
    p_revoke = subparsers.add_parser("revoke", help="Revoke intern access")
    p_revoke.add_argument("--intern-id", required=True, help="Intern ID to revoke")

    # activate
    p_activate = subparsers.add_parser("activate", help="Activate intern access")
    p_activate.add_argument("--intern-id", required=True, help="Intern ID to activate")

    args = parser.parse_args()
    store = TrackingStore(args.db)

    if args.command == "create":
        token = store.create_account(
            intern_id=args.intern_id,
            name=args.name,
            role=args.role,
            daily_target=args.target
        )
        print("=" * 60)
        print(f"ACCOUNT CREATED: {args.intern_id} ({args.name})")
        print(f"ROLE: {args.role}")
        print("=" * 60)
        print("RAW API KEY (Copy this now. It is NEVER stored in plaintext):")
        print(token)
        print("=" * 60)
        print("Configuration block for intern's ~/.config/mindmaxing-outreach/config.json:")
        config_block = {
            "base_url": "https://telemetry.mindmaxing.online",
            "intern_key": token
        }
        print(json.dumps(config_block, indent=2))
        print("=" * 60)

    elif args.command == "list":
        with store.connect() as c:
            rows = c.execute("SELECT intern_id, name, role, active, daily_target, created_at FROM intern_accounts;").fetchall()
        print(f"{'INTERN ID':<20} {'NAME':<20} {'ROLE':<8} {'ACTIVE':<8} {'TARGET':<8} {'CREATED AT'}")
        print("-" * 80)
        for r in rows:
            print(f"{r['intern_id']:<20} {r['name']:<20} {r['role']:<8} {str(bool(r['active'])):<8} {r['daily_target']:<8} {r['created_at']}")

    elif args.command == "revoke":
        store.set_active(args.intern_id, False)
        print(f"Account {args.intern_id} has been REVOKED.")

    elif args.command == "activate":
        store.set_active(args.intern_id, True)
        print(f"Account {args.intern_id} has been ACTIVATED.")

if __name__ == "__main__":
    main()
