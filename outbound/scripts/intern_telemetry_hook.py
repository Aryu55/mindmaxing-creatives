#!/usr/bin/env python3
"""
Antigravity 2.17 native lifecycle hook for Mindmaxing outreach telemetry.
Inspects native user turns in transcript.jsonl for explicit unquoted commands.
Never executes transcript text. Zero em-dash invariant enforced.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

# Ensure local scripts directory is importable
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from log_intern_telemetry import TelemetryClient


class TranscriptFormatError(ValueError):
    pass


def latest_user_turn(path):
    """Read only the native envelope; keep unrelated conversation text local."""
    latest = None
    with Path(path).expanduser().open(encoding="utf-8") as transcript:
        for line in transcript:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                raise TranscriptFormatError("Native transcript contains an incomplete or invalid JSON line") from None
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("type"), str)
                or type(entry.get("step_index")) is not int
            ):
                raise TranscriptFormatError("Unsupported transcript envelope")
            if entry["type"] == "USER_INPUT":
                if not isinstance(entry.get("content"), str) or not isinstance(entry.get("created_at"), str):
                    raise TranscriptFormatError("Unsupported native user record")
                latest = entry
    if latest and "content" in latest.get("truncated_fields", []):
        raise TranscriptFormatError("User input was truncated; command detection is unavailable")
    return latest


def explicit_commands(content):
    """
    Extract unquoted slash commands from USER_REQUEST.
    Ignores markdown code blocks, backticks, and indented code.
    """
    if "<USER_REQUEST>" in content:
        match = re.match(r"^\s*<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.S)
        if not match:
            raise TranscriptFormatError("Incomplete native USER_REQUEST wrapper")
        content = match.group(1)
    elif content.lstrip().startswith("<"):
        raise TranscriptFormatError("Unknown native user content wrapper")

    commands = []
    fence = None
    for offset, line in enumerate(content.splitlines()):
        stripped = line.lstrip()
        marker = re.match(r"(`{3,}|~{3,})", stripped)
        if marker:
            if fence is None:
                fence = marker.group(1)[0]
            elif marker.group(1)[0] == fence:
                fence = None
            continue
        if fence or line.startswith(("    ", "\t")):
            continue
        match = re.match(r"^\s*(/(?:outreach|outbound|triage))(?=\s|$)", line)
        if match:
            commands.append((offset, match.group(1)))
    return commands


def failure_output(event, error_type):
    message = (
        "TRACKING NOTICE: "
        + error_type
        + ". Outreach command detected but local telemetry could not be confirmed. "
        "Check local configuration in ~/.config/mindmaxing-outreach/config.json."
    )
    print(message, file=sys.stderr)
    if event == "Stop":
        return {"decision": "allow", "reason": message}
    return {"injectSteps": [{"ephemeralMessage": message}]}


def handle_hook(event, payload, telemetry=None, config=None):
    try:
        if event not in ("PreInvocation", "PostInvocation", "Stop"):
            raise ValueError("Unsupported hook event: " + str(event))
        conversation = payload.get("conversationId")
        if not isinstance(conversation, str) or not conversation:
            raise TranscriptFormatError("Missing conversation ID in hook payload")
        turn = latest_user_turn(payload["transcriptPath"])
        commands = explicit_commands(turn["content"]) if turn else []
        if not commands:
            return {"decision": "allow"} if event == "Stop" else {}

        telemetry = telemetry or TelemetryClient.from_config(config, timeout=2.0)
        invocations = []
        for offset, command in commands:
            key = json.dumps([conversation, turn["step_index"], turn["created_at"], offset], separators=(",", ":"))
            invocation = telemetry.start_run(key, command)
            invocations.append(invocation)

        result = telemetry.sync(limit=10, heartbeat=False)
        active_id = invocations[0]
        sync_note = "synced to VPS" if result["status"] == "synced" else "queued in local outbox"

        message = (
            f"[Mindmaxing Telemetry Active]\n"
            f"Run ID: {active_id} ({sync_note})\n"
            f"Command: {commands[0][1]}\n"
            f"Mandatory Output Requirement:\n"
            f"You MUST include the exact text:\n"
            f"Draft generated. VPS record: {active_id}\n"
            f"After you actually send it, use /outreach-sent {active_id}\n"
        )

        if event == "Stop":
            return {"decision": "allow"}
        return {"injectSteps": [{"ephemeralMessage": message}]}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return failure_output(event, type(exc).__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", required=True, choices=["PreInvocation", "PostInvocation", "Stop"])
    parser.add_argument("--config", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.load(sys.stdin)
        output = handle_hook(args.event, payload, config=args.config)
    except Exception as exc:
        output = failure_output(args.event, type(exc).__name__)
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
