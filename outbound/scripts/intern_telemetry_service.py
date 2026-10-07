#!/usr/bin/env python3
"""
Mindmaxing High-Velocity Intern Outreach Telemetry & Founder Command Center.
FastAPI daemon running on VPS.
Provides append-only event ingestion, strict credential validation,
zero inferred delivery, in-dashboard intern key management, and a sleek real-time founder radar.
Enforces zero em dashes across all responses, templates, and logs.
"""
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
import uvicorn

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from intern_tracking_store import StoreError, TrackingStore, canonical_json

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = os.environ.get("MM_TRACKING_DB", str(DATA_DIR / "mindmaxing_crm.db"))
FOUNDER_KEY = os.environ.get("MM_FOUNDER_KEY", "mm_founder_secure_2026").strip()

store = TrackingStore(DB_PATH)

app = FastAPI(
    title="Mindmaxing Outreach Telemetry & Founder Radar",
    version="3.0.0",
    docs_url=None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_actor(
    request: Request,
    x_intern_key: Optional[str] = Header(None),
    x_founder_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    key: Optional[str] = Query(None),
):
    token = x_intern_key or x_founder_key
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:].strip()
        else:
            token = authorization.strip()
    if not token and key:
        token = key.strip()
    if not token:
        cookie_token = request.cookies.get("mm_founder_token")
        if cookie_token:
            token = cookie_token.strip()

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required. Missing token.")

    actor = store.authenticate(token)
    if not actor:
        raise HTTPException(status_code=401, detail="Invalid or revoked token.")
    return actor


def require_founder(actor: dict = Depends(get_actor)):
    if actor.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Founder access required.")
    return actor


# Request Models
class EventIngestRequest(BaseModel):
    event_id: str
    invocation_id: str
    kind: str
    occurred_at: str
    payload: dict


class LegacyLogRequest(BaseModel):
    platform: str = "instagram"
    target_handle: str
    target_url: Optional[str] = ""
    qualification_status: str
    qualification_reason: Optional[str] = ""
    disqualification_reason: Optional[str] = ""
    bottleneck_summary: Optional[str] = ""
    generated_dm: Optional[str] = ""
    generated_reply: Optional[str] = ""
    generated_email: Optional[str] = ""
    skill_version: Optional[str] = "3.0.0"


class SyncReportRequest(BaseModel):
    device_id: str
    pending_count: int = 0
    hook_version: Optional[str] = "3.0.0"
    last_error: Optional[str] = None


class CreateInternRequest(BaseModel):
    intern_id: str
    name: str
    daily_target: int = 100


class ToggleInternRequest(BaseModel):
    active: bool


# Public Health
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "mindmaxing-intern-telemetry",
        "version": "3.0.0",
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


# Ingestion API
@app.post("/api/v1/events")
def ingest_event(req: EventIngestRequest, actor: dict = Depends(get_actor)):
    # Option B: Support delegated intern attribution
    if actor.get("role") == "admin":
        body_intern_key = req.payload.get("intern_key")
        body_intern_id = req.payload.get("intern_id") or req.payload.get("intern_name")
        if body_intern_key:
            delegated_actor = store.authenticate(str(body_intern_key).strip())
            if delegated_actor:
                actor = delegated_actor
            else:
                raise HTTPException(status_code=401, detail="Invalid delegated intern_key.")
        elif body_intern_id:
            did = str(body_intern_id).strip()
            with store.connect() as c:
                row = c.execute(
                    "SELECT intern_id, name, role, daily_target, active FROM intern_accounts WHERE (intern_id = ? OR intern_id = ? OR LOWER(name) = ?) AND active = 1;",
                    (did, f"intern_{did}", did.lower()),
                ).fetchone()
                if row:
                    actor = dict(row)
                else:
                    raise HTTPException(status_code=404, detail=f"Active intern '{did}' not found in database.")

    try:
        res = store.add_event(
            actor=actor,
            event_id=req.event_id,
            invocation_id=req.invocation_id,
            kind=req.kind,
            occurred_at=req.occurred_at,
            payload=req.payload,
        )
        return res
    except StoreError as se:
        raise HTTPException(status_code=se.status, detail=se.message)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal ingestion error: {str(exc)}")


@app.post("/api/v1/telemetry/log")
def ingest_telemetry_legacy_compat(req: Request, actor: dict = Depends(get_actor)):
    try:
        raw_bytes = req._body if hasattr(req, "_body") else None
        if not raw_bytes:
            import asyncio
            raw_bytes = asyncio.run(req.body())
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if "event_id" in data and "invocation_id" in data and "kind" in data:
        # Option B: Support delegated intern attribution
        if actor.get("role") == "admin":
            body_intern_key = data.get("intern_key") or data.get("payload", {}).get("intern_key")
            body_intern_id = data.get("intern_id") or data.get("payload", {}).get("intern_id") or data.get("intern_name")
            if body_intern_key:
                delegated_actor = store.authenticate(str(body_intern_key).strip())
                if delegated_actor:
                    actor = delegated_actor
                else:
                    raise HTTPException(status_code=401, detail="Invalid delegated intern_key.")
            elif body_intern_id:
                did = str(body_intern_id).strip()
                with store.connect() as c:
                    row = c.execute(
                        "SELECT intern_id, name, role, daily_target, active FROM intern_accounts WHERE (intern_id = ? OR intern_id = ? OR LOWER(name) = ?) AND active = 1;",
                        (did, f"intern_{did}", did.lower()),
                    ).fetchone()
                    if row:
                        actor = dict(row)
                    else:
                        raise HTTPException(status_code=404, detail=f"Active intern '{did}' not found in database.")

        try:
            return store.add_event(
                actor=actor,
                event_id=data["event_id"],
                invocation_id=data["invocation_id"],
                kind=data["kind"],
                occurred_at=data.get("occurred_at", datetime.now(timezone.utc).isoformat()),
                payload=data.get("payload", {}),
            )
        except StoreError as se:
            raise HTTPException(status_code=se.status, detail=se.message)

    # Option B: Support delegated intern attribution for flat format
    if actor.get("role") == "admin":
        delegated_key = data.get("intern_key")
        delegated_id = data.get("intern_id") or data.get("intern_name")
        if delegated_key:
            delegated_actor = store.authenticate(str(delegated_key).strip())
            if delegated_actor:
                actor = delegated_actor
            else:
                raise HTTPException(status_code=401, detail="Invalid delegated intern_key.")
        elif delegated_id:
            did = str(delegated_id).strip()
            with store.connect() as c:
                row = c.execute(
                    "SELECT intern_id, name, role, daily_target, active FROM intern_accounts WHERE (intern_id = ? OR intern_id = ? OR LOWER(name) = ?) AND active = 1;",
                    (did, f"intern_{did}", did.lower()),
                ).fetchone()
                if row:
                    actor = dict(row)
                else:
                    raise HTTPException(status_code=404, detail=f"Active intern '{did}' not found in database.")

    # Convert legacy flat format into DRAFT_GENERATED event
    import uuid
    inv_id = str(uuid.uuid4())
    event_id = str(uuid.uuid5(uuid.UUID(inv_id), "DRAFT_GENERATED:compat"))
    payload = {
        "platform": data.get("platform", "instagram"),
        "target_handle": data.get("target_handle", "@unknown"),
        "target_url": data.get("target_url", ""),
        "qualification_status": data.get("qualification_status", "QUALIFIED").upper(),
        "qualification_reason": data.get("qualification_reason") or data.get("disqualification_reason") or "Legacy log",
        "bottleneck_summary": data.get("bottleneck_summary", ""),
        "generated_dm": data.get("generated_dm", ""),
        "generated_reply": data.get("generated_reply", ""),
        "generated_email": data.get("generated_email", ""),
        "skill_version": data.get("skill_version", "3.0.0"),
    }
    store.add_event(
        actor=actor,
        event_id=str(uuid.uuid5(uuid.UUID(inv_id), "COMMAND_USED:compat")),
        invocation_id=inv_id,
        kind="COMMAND_USED",
        occurred_at=datetime.now(timezone.utc).isoformat(),
        payload={"command": "/outreach", "compat": True},
    )
    res = store.add_event(
        actor=actor,
        event_id=event_id,
        invocation_id=inv_id,
        kind="DRAFT_GENERATED",
        occurred_at=datetime.now(timezone.utc).isoformat(),
        payload=payload,
    )
    return {
        "status": "synced",
        "intern_id": actor.get("intern_id"),
        "lead_ref_id": inv_id,
        "invocation_id": inv_id,
        "event_id": event_id,
        "action": "DRAFT_RECORDED",
        "message": f"Draft recorded to VPS telemetry under {actor.get('name')} ({actor.get('intern_id')}).",
    }


@app.post("/api/v1/telemetry/sent")
def report_sent_endpoint(req: Request, actor: dict = Depends(get_actor)):
    try:
        raw_bytes = req._body if hasattr(req, "_body") else None
        if not raw_bytes:
            import asyncio
            raw_bytes = asyncio.run(req.body())
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    run_id = data.get("run_id") or data.get("lead_ref_id") or data.get("invocation_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="Missing run_id")

    import uuid
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError:
        run_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, str(run_id))
    event_id = str(uuid.uuid5(run_uuid, "SENT_REPORTED:compat"))
    try:
        res = store.add_event(
            actor=actor,
            event_id=event_id,
            invocation_id=str(run_uuid),
            kind="SENT_REPORTED",
            occurred_at=datetime.now(timezone.utc).isoformat(),
            payload={"notes": data.get("notes", ""), "compat": True},
        )
        return {
            "status": "synced",
            "intern_id": actor.get("intern_id"),
            "lead_ref_id": str(run_uuid),
            "event_id": event_id,
            "action": "SEND_RECORDED",
            "message": f"Send recorded to VPS telemetry under {actor.get('name')} ({actor.get('intern_id')}).",
        }
    except StoreError as se:
        raise HTTPException(status_code=se.status, detail=se.message)


@app.post("/api/v1/sync")
def sync_device(req: SyncReportRequest, actor: dict = Depends(get_actor)):
    store.update_device_sync(
        actor=actor,
        device_id=req.device_id,
        pending_count=req.pending_count,
        hook_version=req.hook_version or "3.0.0",
        last_error=req.last_error,
    )
    return {"status": "synced", "device_id": req.device_id}


# Founder Protected APIs
@app.get("/api/v1/feed")
def get_feed(limit: int = 100, actor: dict = Depends(require_founder)):
    runs = store.get_runs(actor, limit=limit)
    return {"count": len(runs), "runs": runs}


@app.get("/api/v1/summary")
def get_summary(date: Optional[str] = None, actor: dict = Depends(require_founder)):
    return store.get_kpi_summary(actor, date_str=date)


@app.get("/api/v1/interns")
def list_interns(actor: dict = Depends(require_founder)):
    with store.connect() as c:
        rows = c.execute(
            "SELECT intern_id, name, role, active, daily_target, created_at FROM intern_accounts WHERE role = 'intern';"
        ).fetchall()
        return {"interns": [dict(r) for r in rows]}


@app.post("/api/v1/interns")
def create_intern(req: CreateInternRequest, request: Request, actor: dict = Depends(require_founder)):
    raw_token = store.create_account(
        intern_id=req.intern_id,
        name=req.name,
        daily_target=req.daily_target,
    )
    # Derive host URL
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or "localhost:8089"
    proto = request.headers.get("x-forwarded-proto") or ("https" if "trycloudflare.com" in host or "mindmaxing.online" in host else "http")
    base_url = f"{proto}://{host}"

    return {
        "status": "created",
        "intern_id": req.intern_id,
        "name": req.name,
        "daily_target": req.daily_target,
        "token": raw_token,
        "config_snippet": {
            "base_url": base_url,
            "intern_key": raw_token
        },
        "note": "Save this token now. It cannot be recovered from the database.",
    }


@app.post("/api/v1/interns/{intern_id}/toggle")
def toggle_intern(intern_id: str, req: ToggleInternRequest, actor: dict = Depends(require_founder)):
    store.set_active(intern_id, req.active)
    return {"status": "updated", "intern_id": intern_id, "active": req.active}


# Founder Dashboard View
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
def dashboard_view(request: Request):
    token = request.query_params.get("founder_key") or request.cookies.get("mm_founder_token")
    actor = None
    if token:
        actor = store.authenticate(token)
        if actor and actor.get("role") != "admin":
            actor = None

    if not actor:
        return HTMLResponse(content=render_login_page(), status_code=200)

    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    today_str = now_ist.date().isoformat()
    kpi_data = store.get_kpi_summary(actor, date_str=today_str)
    recent_runs = store.get_runs(actor, limit=60)

    html_content = render_dashboard_page(
        founder_name=actor["name"],
        date_str=today_str,
        time_str=now_ist.strftime("%H:%M:%S IST"),
        summary=kpi_data["summary"],
        runs=recent_runs,
        founder_token=token or FOUNDER_KEY,
    )
    resp = HTMLResponse(content=html_content, status_code=200)
    if token and not request.cookies.get("mm_founder_token"):
        resp.set_cookie(key="mm_founder_token", value=token, httponly=True, samesite="lax")
    return resp


def render_login_page() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mindmaxing Radar | Founder Access</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #090b10;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .card {
      background: #111622;
      border: 1px solid #1e293b;
      border-radius: 12px;
      padding: 36px;
      width: 100%;
      max-width: 420px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
    }
    .badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.1);
      padding: 4px 10px;
      border-radius: 999px;
      margin-bottom: 16px;
    }
    h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; color: #f8fafc; }
    p { font-size: 14px; color: #94a3b8; margin-bottom: 24px; }
    label { display: block; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 8px; }
    input[type="password"] {
      width: 100%;
      background: #0a0f18;
      border: 1px solid #334155;
      color: #f8fafc;
      padding: 12px 14px;
      border-radius: 8px;
      font-size: 14px;
      margin-bottom: 20px;
      outline: none;
    }
    input[type="password"]:focus { border-color: #38bdf8; }
    button {
      width: 100%;
      background: #0284c7;
      color: #fff;
      font-weight: 600;
      font-size: 14px;
      border: none;
      padding: 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.2s;
    }
    button:hover { background: #0369a1; }
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">Mindmaxing Creatives</div>
    <h1>Outreach Radar</h1>
    <p>Enter your founder key to monitor live intern pipeline telemetry.</p>
    <form method="GET" action="/dashboard">
      <label for="key">Founder Key</label>
      <input type="password" id="key" name="founder_key" placeholder="Enter founder secret" required autofocus>
      <button type="submit">Authenticate Session</button>
    </form>
  </div>
</body>
</html>"""


def render_dashboard_page(founder_name: str, date_str: str, time_str: str, summary: list, runs: list, founder_token: str) -> str:
    total_commands = sum(s["commands_used"] for s in summary)
    total_drafts = sum(s["drafts_generated"] for s in summary)
    total_sends = sum(s["sends_reported"] for s in summary)
    conversion = f"{(total_sends / total_drafts * 100):.1f}%" if total_drafts > 0 else "0.0%"

    # Render intern summary rows with Status & Action controls
    summary_rows_html = ""
    for s in summary:
        iid = html.escape(s["intern_id"])
        name = html.escape(s["name"])
        target = s["daily_target"]
        sends = s["sends_reported"]
        is_active = s.get("active", True)
        progress_pct = min(100, int((sends / max(1, target)) * 100))

        sync_badge = (
            '<span class="badge-err">Sync Error</span>' if s["has_sync_error"]
            else f'<span class="badge-ok">Active ({s["pending_sync"]} queued)</span>'
        )

        status_pill = '<span class="status-active">ACTIVE</span>' if is_active else '<span class="status-revoked">REVOKED</span>'
        action_btn = (
            f'<button class="btn-action-revoke" onclick="toggleIntern(\'{iid}\', false)">Revoke</button>'
            if is_active else
            f'<button class="btn-action-activate" onclick="toggleIntern(\'{iid}\', true)">Activate</button>'
        )

        summary_rows_html += f"""
        <tr>
          <td><strong>{name}</strong><br><small class="muted">{iid}</small></td>
          <td>{s['commands_used']}</td>
          <td>{s['drafts_generated']}</td>
          <td><strong class="highlight">{sends}</strong> / {target}</td>
          <td>
            <div class="progress-wrap">
              <div class="progress-bar" style="width: {progress_pct}%;"></div>
            </div>
            <small class="muted">{progress_pct}%</small>
          </td>
          <td>{sync_badge}</td>
          <td>{status_pill}</td>
          <td>{action_btn}</td>
        </tr>
        """

    if not summary_rows_html:
        summary_rows_html = '<tr><td colspan="8" class="muted text-center">No intern accounts created yet. Click "+ New Intern" above.</td></tr>'

    # Render runs cards
    runs_html = ""
    for r in runs:
        run_id = r["run_id"]
        draft = r.get("draft") or {}
        handle = html.escape(draft.get("target_handle") or "@unknown")
        platform = html.escape(draft.get("platform") or "unknown").upper()
        q_status = draft.get("qualification_status", "UNKNOWN")
        bottleneck = html.escape(draft.get("bottleneck_summary") or draft.get("qualification_reason") or "No bottleneck logged")
        dm = html.escape(draft.get("generated_dm") or "")
        reply = html.escape(draft.get("generated_reply") or "")
        email = html.escape(draft.get("generated_email") or "")
        whatsapp = html.escape(draft.get("generated_whatsapp") or "")
        url = draft.get("target_url") or ""

        if r.get("sent_reported"):
            status_badge = '<span class="badge-sent">CONFIRMED SENT</span>'
        elif r.get("status") == "DRAFT_GENERATED":
            status_badge = '<span class="badge-draft">Draft Generated</span>'
        else:
            status_badge = '<span class="badge-cmd">Command Logged</span>'

        q_badge = '<span class="badge-pass">PASS</span>' if q_status == "QUALIFIED" else '<span class="badge-fail">DISQUALIFIED</span>'
        target_link = f'<a href="{html.escape(url)}" target="_blank" rel="noopener" class="lead-link">{handle}</a>' if url else handle

        time_ist = ""
        if r.get("started_at"):
            try:
                dt = datetime.fromisoformat(r["started_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("Asia/Kolkata"))
                time_ist = dt.strftime("%H:%M:%S")
            except Exception:
                time_ist = r["started_at"][:19]

        runs_html += f"""
        <div class="run-card" data-handle="{handle.lower()}" data-platform="{platform.lower()}" data-status="{r.get('status')}">
          <div class="run-header">
            <div class="run-meta">
              <span class="platform-tag">{platform}</span>
              <span class="handle-title">{target_link}</span>
              {q_badge}
              {status_badge}
            </div>
            <div class="run-time">
              <span class="muted">{time_ist} IST</span> | <span class="intern-pill">{html.escape(r.get('intern_name', ''))}</span>
            </div>
          </div>
          <div class="run-bottleneck">
            <strong>Friction:</strong> {bottleneck}
          </div>
          <div class="copy-accordions">
            {f'''<div class="copy-box"><div class="copy-header"><span>Direct Message (DM)</span><button class="btn-copy" onclick="copyText(this, `{dm}`)">Copy</button></div><div class="copy-content">{dm}</div></div>''' if dm else ''}
            {f'''<div class="copy-box"><div class="copy-header"><span>Public Reply</span><button class="btn-copy" onclick="copyText(this, `{reply}`)">Copy</button></div><div class="copy-content">{reply}</div></div>''' if reply else ''}
            {f'''<div class="copy-box"><div class="copy-header"><span>Cold Email</span><button class="btn-copy" onclick="copyText(this, `{email}`)">Copy</button></div><div class="copy-content">{email}</div></div>''' if email else ''}
            {f'''<div class="copy-box"><div class="copy-header"><span>WhatsApp Drop</span><button class="btn-copy" onclick="copyText(this, `{whatsapp}`)">Copy</button></div><div class="copy-content">{whatsapp}</div></div>''' if whatsapp else ''}
          </div>
          <div class="run-footer">
            <span class="muted">Run ID: <code>{run_id}</code></span>
          </div>
        </div>
        """

    if not runs_html:
        runs_html = '<div class="empty-state">No outreach runs recorded yet today. Commands invoked by interns will appear here in real time.</div>'

    safe_token = html.escape(founder_token)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mindmaxing Outreach Radar</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #090b10;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid #1e293b;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .brand-logo {{
      width: 32px;
      height: 32px;
      background: linear-gradient(135deg, #0284c7, #38bdf8);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      color: #fff;
    }}
    h1 {{ font-size: 20px; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em; }}
    .header-actions {{ display: flex; align-items: center; gap: 12px; }}
    .founder-badge {{
      background: #1e293b;
      padding: 6px 14px;
      border-radius: 999px;
      font-size: 13px;
      color: #94a3b8;
    }}
    .founder-badge strong {{ color: #38bdf8; }}
    .btn-create-intern {{
      background: linear-gradient(135deg, #0284c7, #0ea5e9);
      color: #ffffff;
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      transition: opacity 0.2s;
    }}
    .btn-create-intern:hover {{ opacity: 0.9; }}
    
    /* Metrics Row */
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .metric-card {{
      background: #111622;
      border: 1px solid #1e293b;
      border-radius: 10px;
      padding: 20px;
    }}
    .metric-label {{ font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 8px; }}
    .metric-value {{ font-size: 32px; font-weight: 800; color: #f8fafc; }}
    .metric-value.highlight {{ color: #10b981; }}
    
    /* Section styling */
    .section-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }}
    .section-title {{ font-size: 16px; font-weight: 700; color: #cbd5e1; }}
    
    /* Intern Table */
    .table-card {{
      background: #111622;
      border: 1px solid #1e293b;
      border-radius: 10px;
      overflow-x: auto;
      margin-bottom: 28px;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
    th {{ background: #0c111a; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.05em; padding: 12px 16px; border-bottom: 1px solid #1e293b; }}
    td {{ padding: 14px 16px; border-bottom: 1px solid #182234; white-space: nowrap; }}
    tr:last-child td {{ border-bottom: none; }}
    .progress-wrap {{ background: #1e293b; border-radius: 999px; height: 6px; width: 120px; overflow: hidden; margin-bottom: 4px; }}
    .progress-bar {{ background: #10b981; height: 100%; border-radius: 999px; }}
    
    .status-active {{ background: rgba(16, 185, 129, 0.15); color: #10b981; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 999px; }}
    .status-revoked {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; font-weight: 700; font-size: 10px; padding: 2px 8px; border-radius: 999px; }}
    .btn-action-revoke {{ background: transparent; border: 1px solid #ef4444; color: #ef4444; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; cursor: pointer; }}
    .btn-action-revoke:hover {{ background: #ef4444; color: #fff; }}
    .btn-action-activate {{ background: transparent; border: 1px solid #10b981; color: #10b981; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; cursor: pointer; }}
    .btn-action-activate:hover {{ background: #10b981; color: #fff; }}

    /* Filter Bar */
    .filter-bar {{
      display: flex;
      gap: 12px;
      margin-bottom: 16px;
      flex-wrap: wrap;
    }}
    .search-input {{
      flex: 1;
      min-width: 240px;
      background: #111622;
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 10px 14px;
      color: #f8fafc;
      font-size: 13px;
      outline: none;
    }}
    .search-input:focus {{ border-color: #38bdf8; }}
    
    /* Run Cards */
    .run-card {{
      background: #111622;
      border: 1px solid #1e293b;
      border-radius: 10px;
      padding: 18px;
      margin-bottom: 14px;
      transition: border-color 0.2s;
    }}
    .run-card:hover {{ border-color: #334155; }}
    .run-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }}
    .run-meta {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
    .platform-tag {{
      background: #1e293b;
      color: #38bdf8;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }}
    .handle-title {{ font-weight: 700; font-size: 15px; color: #f8fafc; }}
    .lead-link {{ color: #38bdf8; text-decoration: none; }}
    .lead-link:hover {{ text-decoration: underline; }}
    .run-time {{ font-size: 12px; color: #94a3b8; }}
    .intern-pill {{ background: #0c111a; padding: 2px 8px; border-radius: 4px; border: 1px solid #1e293b; color: #cbd5e1; }}
    
    /* Badges */
    .badge-pass {{ background: rgba(16, 185, 129, 0.15); color: #10b981; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 999px; }}
    .badge-fail {{ background: rgba(239, 68, 68, 0.15); color: #ef4444; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 999px; }}
    .badge-sent {{ background: #064e3b; color: #34d399; font-weight: 800; font-size: 11px; padding: 3px 10px; border-radius: 999px; letter-spacing: 0.05em; }}
    .badge-draft {{ background: #78350f; color: #fde68a; font-weight: 600; font-size: 11px; padding: 3px 8px; border-radius: 999px; }}
    .badge-cmd {{ background: #1e293b; color: #94a3b8; font-size: 11px; padding: 3px 8px; border-radius: 999px; }}
    .badge-ok {{ color: #10b981; font-weight: 600; }}
    .badge-err {{ color: #ef4444; font-weight: 600; }}
    
    .run-bottleneck {{ font-size: 13px; color: #cbd5e1; margin-bottom: 12px; line-height: 1.4; }}
    .copy-accordions {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 12px; }}
    .copy-box {{ background: #0a0f18; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; }}
    .copy-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 11px; font-weight: 700; text-transform: uppercase; color: #94a3b8; }}
    .btn-copy {{ background: #1e293b; border: none; color: #38bdf8; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 4px; cursor: pointer; }}
    .btn-copy:hover {{ background: #334155; }}
    .copy-content {{ font-size: 12px; color: #e2e8f0; white-space: pre-wrap; word-break: break-word; font-family: inherit; }}
    
    .run-footer {{ font-size: 11px; color: #64748b; }}
    .run-footer code {{ background: #0a0f18; padding: 2px 6px; border-radius: 4px; }}
    
    /* Modal Styles */
    .modal-overlay {{
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(4, 7, 13, 0.8);
      backdrop-filter: blur(4px);
      z-index: 1000;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }}
    .modal-overlay.active {{ display: flex; }}
    .modal-dialog {{
      background: #111622;
      border: 1px solid #334155;
      border-radius: 12px;
      width: 100%;
      max-width: 520px;
      padding: 28px;
      box-shadow: 0 24px 48px rgba(0, 0, 0, 0.8);
    }}
    .modal-dialog h2 {{ font-size: 18px; font-weight: 700; margin-bottom: 6px; color: #f8fafc; }}
    .modal-dialog p {{ font-size: 13px; color: #94a3b8; margin-bottom: 20px; }}
    .form-group {{ margin-bottom: 16px; }}
    .form-group label {{ display: block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #94a3b8; margin-bottom: 6px; }}
    .form-group input {{
      width: 100%;
      background: #0a0f18;
      border: 1px solid #334155;
      color: #f8fafc;
      padding: 10px 12px;
      border-radius: 6px;
      font-size: 13px;
      outline: none;
    }}
    .form-group input:focus {{ border-color: #38bdf8; }}
    .modal-actions {{ display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }}
    .btn-secondary {{ background: #1e293b; color: #cbd5e1; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 13px; cursor: pointer; }}
    .btn-secondary:hover {{ background: #334155; }}
    
    .credential-result {{ display: none; margin-top: 16px; }}
    .token-box {{
      background: #0a0f18;
      border: 1px solid #10b981;
      border-radius: 8px;
      padding: 14px;
      margin-bottom: 16px;
    }}
    .token-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; color: #34d399; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; }}
    .token-input {{ width: 100%; background: transparent; border: none; color: #f8fafc; font-family: monospace; font-size: 13px; outline: none; }}
    .config-code {{
      background: #0a0f18;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 12px;
      font-family: monospace;
      font-size: 12px;
      color: #e2e8f0;
      white-space: pre-wrap;
      word-break: break-all;
      margin-bottom: 16px;
      max-height: 160px;
      overflow-y: auto;
    }}
    .alert-warning {{
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #fbbf24;
      padding: 10px 12px;
      border-radius: 6px;
      font-size: 12px;
      margin-bottom: 16px;
    }}

    .muted {{ color: #64748b; }}
    .text-center {{ text-align: center; }}
    .empty-state {{ text-align: center; padding: 48px; background: #111622; border: 1px dashed #1e293b; border-radius: 10px; color: #94a3b8; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-logo">M</div>
        <div>
          <h1>Mindmaxing Outreach Radar</h1>
          <small class="muted">Live Intern Pipeline Telemetry | {date_str} {time_str}</small>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn-create-intern" onclick="openInternModal()">+ New Intern</button>
        <div class="founder-badge">
          Founder: <strong>{html.escape(founder_name)}</strong>
        </div>
      </div>
    </header>

    <!-- Top KPI Cards -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-label">Commands Invoked</div>
        <div class="metric-value">{total_commands}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Drafts Generated</div>
        <div class="metric-value">{total_drafts}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Sends Confirmed</div>
        <div class="metric-value highlight">{total_sends}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Send / Draft Ratio</div>
        <div class="metric-value">{conversion}</div>
      </div>
    </div>

    <!-- Intern Daily Target Progress -->
    <div class="section-header">
      <div class="section-title">Intern Daily Execution</div>
      <button class="btn-copy" onclick="openInternModal()">+ Add Intern</button>
    </div>
    <div class="table-card">
      <table>
        <thead>
          <tr>
            <th>Intern</th>
            <th>Commands</th>
            <th>Drafts</th>
            <th>Sends / Target</th>
            <th>Progress</th>
            <th>Device Telemetry</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {summary_rows_html}
        </tbody>
      </table>
    </div>

    <!-- Activity Feed -->
    <div class="section-title" style="margin-bottom: 12px;">Recent Prospect Generations & Dispatch Feed</div>
    <div class="filter-bar">
      <input type="text" id="searchInput" class="search-input" placeholder="Search by handle or brand..." onkeyup="filterFeed()">
    </div>

    <div id="runsContainer">
      {runs_html}
    </div>
  </div>

  <!-- Create Intern Modal -->
  <div id="internModal" class="modal-overlay">
    <div class="modal-dialog">
      <div id="modalFormContainer">
        <h2>Generate New Intern Key</h2>
        <p>Creates an authenticated outreach account and secret 32-byte API token.</p>
        <form id="createInternForm" onsubmit="submitCreateIntern(event)">
          <div class="form-group">
            <label for="internIdInput">Intern Handle / Slug</label>
            <input type="text" id="internIdInput" placeholder="e.g. intern_neha" required pattern="^[a-zA-Z0-9_-]+$">
          </div>
          <div class="form-group">
            <label for="internNameInput">Full Name</label>
            <input type="text" id="internNameInput" placeholder="e.g. Neha Sharma" required>
          </div>
          <div class="form-group">
            <label for="internTargetInput">Daily Outreach Target</label>
            <input type="number" id="internTargetInput" value="100" min="1" max="1000" required>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" onclick="closeInternModal()">Cancel</button>
            <button type="submit" class="btn-create-intern" id="btnSubmitIntern">Generate Key & Account</button>
          </div>
        </form>
      </div>

      <div id="modalResultContainer" class="credential-result">
        <h2>Account Created Successfully!</h2>
        <p>Send the token and configuration block below to the intern.</p>
        <div class="alert-warning">
          <strong>One-Time Secret:</strong> This API key is hashed with SHA-256 and never stored in plaintext. Copy it now.
        </div>
        <div class="token-box">
          <div class="token-label">
            <span>Raw Secret Token</span>
            <button type="button" class="btn-copy" onclick="copyResultToken()">Copy Key</button>
          </div>
          <input type="text" id="resultToken" class="token-input" readonly>
        </div>
        <div class="token-label" style="margin-bottom: 6px;">
          <span>~/.config/mindmaxing-outreach/config.json</span>
          <button type="button" class="btn-copy" onclick="copyResultConfig()">Copy Config JSON</button>
        </div>
        <pre id="resultConfig" class="config-code"></pre>
        <div class="modal-actions">
          <button type="button" class="btn-create-intern" onclick="closeInternModalAndRefresh()">Done & Refresh Table</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const FOUNDER_KEY = "{safe_token}";

    function copyText(btn, text) {{
      navigator.clipboard.writeText(text).then(() => {{
        const prev = btn.innerText;
        btn.innerText = "Copied!";
        btn.style.color = "#10b981";
        setTimeout(() => {{
          btn.innerText = prev;
          btn.style.color = "#38bdf8";
        }}, 1500);
      }});
    }}

    function filterFeed() {{
      const query = document.getElementById("searchInput").value.toLowerCase();
      const cards = document.querySelectorAll(".run-card");
      cards.forEach(card => {{
        const handle = card.getAttribute("data-handle") || "";
        const platform = card.getAttribute("data-platform") || "";
        if (handle.includes(query) || platform.includes(query)) {{
          card.style.display = "";
        }} else {{
          card.style.display = "none";
        }}
      }});
    }}

    function openInternModal() {{
      document.getElementById("modalFormContainer").style.display = "block";
      document.getElementById("modalResultContainer").style.display = "none";
      document.getElementById("createInternForm").reset();
      document.getElementById("internTargetInput").value = "100";
      document.getElementById("internModal").classList.add("active");
    }}

    function closeInternModal() {{
      document.getElementById("internModal").classList.remove("active");
    }}

    function closeInternModalAndRefresh() {{
      closeInternModal();
      window.location.reload();
    }}

    function copyResultToken() {{
      const val = document.getElementById("resultToken").value;
      navigator.clipboard.writeText(val).then(() => alert("Token copied to clipboard!"));
    }}

    function copyResultConfig() {{
      const val = document.getElementById("resultConfig").innerText;
      navigator.clipboard.writeText(val).then(() => alert("Configuration JSON copied to clipboard!"));
    }}

    async function submitCreateIntern(e) {{
      e.preventDefault();
      const btn = document.getElementById("btnSubmitIntern");
      btn.disabled = true;
      btn.innerText = "Generating...";

      const internId = document.getElementById("internIdInput").value.trim().toLowerCase();
      const name = document.getElementById("internNameInput").value.trim();
      const target = parseInt(document.getElementById("internTargetInput").value, 10) || 100;

      try {{
        const res = await fetch("/api/v1/interns", {{
          method: "POST",
          headers: {{
            "Content-Type": "application/json",
            "X-Founder-Key": FOUNDER_KEY
          }},
          body: JSON.stringify({{ intern_id: internId, name: name, daily_target: target }})
        }});

        if (!res.ok) {{
          const err = await res.json();
          throw new Error(err.detail || "Failed to create intern account");
        }}

        const data = await res.json();
        document.getElementById("resultToken").value = data.token;
        document.getElementById("resultConfig").innerText = JSON.stringify(data.config_snippet, null, 2);

        document.getElementById("modalFormContainer").style.display = "none";
        document.getElementById("modalResultContainer").style.display = "block";
      }} catch (err) {{
        alert("Error creating intern: " + err.message);
      }} finally {{
        btn.disabled = false;
        btn.innerText = "Generate Key & Account";
      }}
    }}

    async function toggleIntern(internId, makeActive) {{
      const actionText = makeActive ? "activate" : "revoke";
      if (!confirm(`Are you sure you want to ${{actionText}} intern account "${{internId}}"?`)) {{
        return;
      }}
      try {{
        const res = await fetch(`/api/v1/interns/${{internId}}/toggle`, {{
          method: "POST",
          headers: {{
            "Content-Type": "application/json",
            "X-Founder-Key": FOUNDER_KEY
          }},
          body: JSON.stringify({{ active: makeActive }})
        }});
        if (!res.ok) {{
          const err = await res.json();
          throw new Error(err.detail || "Failed to update intern status");
        }}
        window.location.reload();
      }} catch (err) {{
        alert("Error updating intern: " + err.message);
      }}
    }}

    // Auto-refresh page every 25 seconds to keep telemetry live
    setTimeout(() => {{
      if (!document.getElementById("internModal").classList.contains("active")) {{
        window.location.reload();
      }}
    }}, 25000);
  </script>
</body>
</html>"""


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8089)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
