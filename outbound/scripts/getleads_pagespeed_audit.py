#!/usr/bin/env python3
"""
PageSpeed Insights Audit for GetLeads Candidates
- Audits all GetLeads candidates against Google Lighthouse (Mobile).
- Extracts Mobile Score, LCP, TBT, and Render-Blocking Liquid/JS scripts.
- Updates SQLite CRM:
  - If LCP >= 3.8s or Score <= 40: sets signal_decision = 'INCIDENT_CANDIDATE'
  - If speed is fast/acceptable: marks status = 'PARKED_ACCEPTABLE_SPEED'
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "mindmaxing_crm.db")
API_KEY = os.getenv("GOOGLE_PAGESPEED_API_KEY", "AIzaSyBBVHkGo_Fqd4ieNhTcrks9ZmTqs5IUU5s")

def audit_domain(lead_id: int, domain: str, company: str, contact_name: str, email: str):
    clean_domain = domain.lower().replace("www.", "").strip()
    url = f"https://{clean_domain}"
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={urllib.parse.quote(url)}&strategy=mobile&key={API_KEY}"
    
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "MindmaxingAudit/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            lh = data.get("lighthouseResult", {})
            categories = lh.get("categories", {})
            perf_score = int((categories.get("performance", {}).get("score") or 0) * 100)
            
            audits = lh.get("audits", {})
            lcp_raw = audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000.0
            lcp_display = audits.get("largest-contentful-paint", {}).get("displayValue", f"{lcp_raw:.1f} s")
            tbt_display = audits.get("total-blocking-time", {}).get("displayValue", "N/A")
            
            rb = audits.get("render-blocking-resources", {})
            items = rb.get("details", {}).get("items", [])
            blocking_scripts = []
            for item in items[:4]:
                u = item.get("url", "")
                if u:
                    name = u.split("/")[-1].split("?")[0]
                    if len(name) > 3 and name not in blocking_scripts:
                        blocking_scripts.append(name)
                        
            return {
                "success": True,
                "lead_id": lead_id,
                "domain": clean_domain,
                "company": company,
                "contact_name": contact_name,
                "email": email,
                "score": perf_score,
                "lcp_numeric": round(lcp_raw, 2),
                "lcp_display": lcp_display,
                "tbt": tbt_display,
                "blocking_scripts": blocking_scripts
            }
    except Exception as e:
        return {
            "success": False,
            "lead_id": lead_id,
            "domain": clean_domain,
            "company": company,
            "contact_name": contact_name,
            "email": email,
            "error": str(e)[:80]
        }

def run_audit(max_workers: int = 5):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, domain, company_name, contact_name, contact_email 
        FROM leads 
        WHERE source = 'getleads' AND status = 'CANDIDATE'
    """)
    leads = cur.fetchall()
    conn.close()
    
    print(f"Loaded {len(leads)} GetLeads candidates for PageSpeed audit.")
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(audit_domain, l[0], l[1], l[2], l[3], l[4]): l[1] 
            for l in leads
        }
        
        count = 0
        for future in as_completed(futures):
            count += 1
            res = future.result()
            results.append(res)
            dom = res.get("domain")
            if res.get("success"):
                score = res["score"]
                lcp = res["lcp_display"]
                scripts = res["blocking_scripts"]
                print(f"[{count}/{len(leads)}] {dom}: Score {score}/100 | LCP {lcp} | Scripts: {len(scripts)}")
            else:
                err = res.get("error", "Unknown")
                print(f"[{count}/{len(leads)}] {dom}: FAILED ({err})")
                
    # Update CRM
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    
    qualified_count = 0
    parked_count = 0
    failed_count = 0
    
    for r in results:
        lead_id = r["lead_id"]
        if r.get("success"):
            score = r["score"]
            lcp_num = r["lcp_numeric"]
            lcp_disp = r["lcp_display"]
            tbt = r["tbt"]
            scripts = r["blocking_scripts"]
            
            telemetry = {
                "mobile_score": score,
                "lcp": lcp_disp,
                "lcp_numeric": lcp_num,
                "tbt": tbt,
                "blocking_scripts": scripts
            }
            
            is_incident = (score <= 40 or lcp_num >= 3.8)
            new_status = "CANDIDATE" if is_incident else "PARKED_ACCEPTABLE_SPEED"
            signal_decision = "INCIDENT_CANDIDATE" if is_incident else "ACCEPTABLE_SPEED"
            
            if is_incident:
                qualified_count += 1
            else:
                parked_count += 1
                
            cur.execute("""
                UPDATE leads 
                SET reviews_json = ?,
                    dominant_pattern = ?,
                    pain_trigger = 'slow',
                    signal_decision = ?,
                    signal_evidence = ?,
                    status = ?,
                    evaluated_at = ?
                WHERE id = ?
            """, (
                json.dumps(telemetry),
                f"Mobile LCP {lcp_disp} Latency",
                signal_decision,
                json.dumps(telemetry),
                new_status,
                now_iso,
                lead_id
            ))
        else:
            failed_count += 1
            
    conn.commit()
    conn.close()
    
    print("\n=== AUDIT SUMMARY ===")
    print(f"Total Scanned: {len(results)}")
    print(f"Qualified Incidents (LCP >= 3.8s or Score <= 40): {qualified_count}")
    print(f"Parked (Acceptable Speed): {parked_count}")
    print(f"Failed/Unreachable: {failed_count}")

if __name__ == "__main__":
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    run_audit(max_workers=workers)
