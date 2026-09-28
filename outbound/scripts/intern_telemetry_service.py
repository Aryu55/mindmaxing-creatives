#!/usr/bin/env python3
"""
Mindmaxing High-Velocity Intern Telemetry & Audit Service
FastAPI daemon running on VPS to passively log every /outreach command in real time,
track daily KPI progress towards 100 leads, and give Aryan a live monitoring dashboard.
Zero blocking: Interns send immediately without waiting for manual approvals.
"""

import os
import sqlite3
import shutil
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")
PROOFS_DIR = os.path.join(DATA_DIR, "proofs")
os.makedirs(PROOFS_DIR, exist_ok=True)

ADMIN_TOKEN = os.environ.get("MM_ADMIN_TOKEN", "mindmaxing_founder_secure_2026")

app = FastAPI(title="Mindmaxing High-Velocity Outbound Telemetry", version="2.0.0")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Request Models
class TelemetryLogRequest(BaseModel):
    intern_id: str
    platform: str
    target_handle: str
    target_url: Optional[str] = None
    qualification_status: str
    disqualification_reason: Optional[str] = None
    bottleneck_summary: Optional[str] = None
    generated_dm: Optional[str] = None
    generated_reply: Optional[str] = None
    generated_email: Optional[str] = None

# Helpers
def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

def generate_lead_ref():
    today = datetime.now().strftime("%y%m%d")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM intern_command_logs WHERE date(created_at) = date('now');")
    count = cursor.fetchone()[0] + 1
    conn.close()
    return f"MM-{today}-{count:03d}"

def verify_intern_auth(x_intern_key: Optional[str] = Header(None)):
    if not x_intern_key:
        # Allow default intern if no key provided for maximum velocity
        return "intern_default"
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT intern_id, active FROM intern_accounts WHERE api_key = ?;", (x_intern_key,))
    row = cursor.fetchone()
    conn.close()
    if row and row["active"]:
        return row["intern_id"]
    return "intern_default"

# Endpoints
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "mindmaxing-high-velocity-telemetry",
        "time": datetime.now().isoformat()
    }

@app.post("/api/v1/telemetry/log")
def log_telemetry(payload: TelemetryLogRequest, intern_id: str = Depends(verify_intern_auth)):
    conn = get_db()
    cursor = conn.cursor()
    lead_ref = generate_lead_ref()
    today = get_today_str()

    is_qualified = payload.qualification_status.upper() == "QUALIFIED"
    status_label = "DISQUALIFIED" if not is_qualified else "READY_SENT"

    cursor.execute("""
    INSERT INTO intern_command_logs (
        lead_ref_id, intern_id, platform, target_handle, target_url,
        qualification_status, disqualification_reason, bottleneck_summary,
        generated_dm, generated_reply, generated_email, approval_status, dispatch_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AUTO_APPROVED', ?);
    """, (
        lead_ref, payload.intern_id or intern_id, payload.platform.lower(),
        payload.target_handle, payload.target_url, payload.qualification_status.upper(),
        payload.disqualification_reason, payload.bottleneck_summary,
        payload.generated_dm, payload.generated_reply, payload.generated_email,
        status_label
    ))

    # Update daily KPI ledger in real time
    cursor.execute("""
    INSERT INTO intern_daily_kpis (date, intern_id, total_screened, disqualified_count, approved_count, verified_sent_count)
    VALUES (?, ?, 1, ?, ?, ?)
    ON CONFLICT(date, intern_id) DO UPDATE SET
        total_screened = total_screened + 1,
        disqualified_count = disqualified_count + ?,
        approved_count = approved_count + ?,
        verified_sent_count = verified_sent_count + ?;
    """, (
        today, payload.intern_id or intern_id,
        0 if is_qualified else 1,
        1 if is_qualified else 0,
        1 if is_qualified else 0,
        0 if is_qualified else 1,
        1 if is_qualified else 0,
        1 if is_qualified else 0
    ))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "lead_ref_id": lead_ref,
        "action": "PROCEED_SEND",
        "message": "Lead logged to VPS. Ready to paste and send immediately."
    }

@app.get("/api/v1/feed/latest")
def get_latest_feed(limit: int = 50):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, lead_ref_id, intern_id, platform, target_handle, target_url,
           qualification_status, bottleneck_summary, generated_dm, generated_reply,
           generated_email, dispatch_status, created_at
    FROM intern_command_logs
    ORDER BY created_at DESC
    LIMIT ?;
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"count": len(rows), "leads": rows}

@app.get("/api/v1/kpi/stats")
def get_kpi_stats(date: Optional[str] = None):
    target_date = date or get_today_str()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT k.date, k.intern_id, a.name as intern_name, a.daily_quota,
           k.total_screened, k.disqualified_count, k.approved_count,
           k.verified_sent_count, k.quota_reached
    FROM intern_daily_kpis k
    LEFT JOIN intern_accounts a ON k.intern_id = a.intern_id
    WHERE k.date = ?;
    """, (target_date,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"date": target_date, "stats": rows}

# Founder Real-Time Live Stream Dashboard
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Mindmaxing Outbound | Live Stream & KPI Radar</title>
  <style>
    :root {
      --bg: #090a0f;
      --card-bg: #12141c;
      --border: #232738;
      --text: #e2e8f0;
      --text-muted: #8492a6;
      --primary: #3b82f6;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
    }
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 24px;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 20px;
      margin-bottom: 24px;
    }
    .brand {
      font-size: 22px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }
    .brand span { color: var(--primary); }
    .live-pulse {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: var(--success);
      font-weight: 600;
    }
    .pulse-dot {
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--success);
    }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .kpi-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 18px;
    }
    .kpi-title { font-size: 13px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }
    .kpi-value { font-size: 32px; font-weight: 700; margin-top: 6px; }
    .feed-title {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .lead-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .lead-card.disqualified {
      border-left: 4px solid var(--danger);
      opacity: 0.75;
    }
    .lead-card.qualified {
      border-left: 4px solid var(--success);
    }
    .lead-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .lead-info { font-size: 16px; font-weight: 600; }
    .lead-meta { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
    .badge {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .badge-qual { background: rgba(16, 185, 129, 0.2); color: var(--success); }
    .badge-disqual { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
    .lead-bottleneck {
      background: rgba(59, 130, 246, 0.1);
      border-left: 3px solid var(--primary);
      padding: 10px 14px;
      font-size: 14px;
      border-radius: 4px;
    }
    .copy-box {
      background: #0d0f15;
      border: 1px solid #1c202d;
      border-radius: 8px;
      padding: 14px;
      font-size: 14px;
      line-height: 1.5;
      white-space: pre-wrap;
    }
    .empty-state {
      text-align: center;
      padding: 40px;
      color: var(--text-muted);
      border: 1px dashed var(--border);
      border-radius: 10px;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="brand">MINDMAXING <span>LIVE OUTBOUND RADAR</span></div>
    <div class="live-pulse">
      <div class="pulse-dot"></div> Live Telemetry Active
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-title">Screened Today</div>
      <div class="kpi-value" id="kpi-screened">0</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Disqualified (Skipped)</div>
      <div class="kpi-value" id="kpi-disqualified" style="color: var(--danger);">0</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">Sent Today</div>
      <div class="kpi-value" id="kpi-sent" style="color: var(--success);">0</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-title">100-Lead Daily Progress</div>
      <div class="kpi-value" id="kpi-progress" style="color: var(--primary);">0%</div>
    </div>
  </div>

  <div class="feed-title">
    Live Activity Stream (Auto-updating)
  </div>

  <div id="leads-container">
    <div class="empty-state">Loading live stream...</div>
  </div>

  <script>
    async function loadData() {
      try {
        // Load KPIs
        const kpiRes = await fetch("/api/v1/kpi/stats");
        const kpiData = await kpiRes.json();
        let screened = 0, disqualified = 0, sent = 0;
        if (kpiData.stats && kpiData.stats.length > 0) {
          kpiData.stats.forEach(s => {
            screened += s.total_screened;
            disqualified += s.disqualified_count;
            sent += s.verified_sent_count;
          });
        }
        document.getElementById("kpi-screened").innerText = screened;
        document.getElementById("kpi-disqualified").innerText = disqualified;
        document.getElementById("kpi-sent").innerText = sent;
        const progressPct = Math.min(100, Math.round((sent / 100) * 100));
        document.getElementById("kpi-progress").innerText = progressPct + "%";

        // Load Feed
        const feedRes = await fetch("/api/v1/feed/latest?limit=30");
        const feedData = await feedRes.json();

        const container = document.getElementById("leads-container");
        if (feedData.leads.length === 0) {
          container.innerHTML = '<div class="empty-state">No leads logged yet today. Stream is waiting for /outreach calls.</div>';
          return;
        }

        container.innerHTML = feedData.leads.map(lead => {
          const isQual = lead.qualification_status === "QUALIFIED";
          return `
            <div class="lead-card ${isQual ? "qualified" : "disqualified"}">
              <div class="lead-header">
                <div>
                  <div class="lead-info">${lead.target_handle} (${lead.platform.toUpperCase()})</div>
                  <div class="lead-meta">Ref: <strong>${lead.lead_ref_id}</strong> | Intern: ${lead.intern_id} | ${lead.created_at}</div>
                </div>
                <div>
                  <span class="badge ${isQual ? "badge-qual" : "badge-disqual"}">${lead.qualification_status}</span>
                </div>
              </div>
              ${isQual ? `
                <div class="lead-bottleneck">
                  <strong>Bottleneck:</strong> ${lead.bottleneck_summary || "None noted"}
                </div>
                <div>
                  <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600;">SENT DM COPY:</div>
                  <div class="copy-box">${lead.generated_dm || "No DM generated"}</div>
                </div>
              ` : `
                <div style="font-size: 13px; color: var(--danger);">
                  <strong>Reason Skipped:</strong> ${lead.disqualification_reason || "Failed qualification criteria"}
                </div>
              `}
            </div>
          `;
        }).join("");
      } catch (err) {
        console.error(err);
      }
    }

    loadData();
    setInterval(loadData, 5000);
  </script>
</body>
</html>
    """

if __name__ == "__main__":
    uvicorn.run("intern_telemetry_service:app", host="0.0.0.0", port=8089, reload=False)
