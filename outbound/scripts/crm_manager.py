#!/usr/bin/env python3
"""
Mindmaxing CRM & Retargeting Engine v2
- Permanent SQLite storage for all scraped leads and email interactions.
- Stores full review clusters, country codes, founder names, and contact types.
- Full tracking: Touch 1, Touch 2, Touch 3, Replied, Won, Cooldown.
- 45-Day Retargeting Engine: automatically flags leads eligible for fresh re-engagement.
- Auto-syncs from scraper JSON and exports to clean CSV.
"""

import csv
import json
import os
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "mindmaxing_crm.db")
ICP1_DIR = os.path.join(DATA_DIR, "icp1_shopify_dtc")
ICP1_JSON = os.path.join(ICP1_DIR, "leads.json")
ICP1_CSV = os.path.join(ICP1_DIR, "leads.csv")

def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ICP1_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table 1: Master Leads Reservoir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT UNIQUE,
        company_name TEXT,
        contact_email TEXT,
        contact_type TEXT DEFAULT 'GENERIC_SUPPORT',
        contact_name TEXT,
        country_code TEXT,
        city TEXT,
        platform TEXT DEFAULT 'Shopify',
        pain_trigger TEXT,
        dominant_pattern TEXT,
        reviews_count INTEGER DEFAULT 1,
        review_freshest_date TEXT,
        reviews_json TEXT,
        captured_at TEXT,
        status TEXT DEFAULT 'READY',
        current_sequence_step INTEGER DEFAULT 0,
        last_contacted_at TEXT,
        cooldown_until TEXT,
        retarget_count INTEGER DEFAULT 0,
        client_won BOOLEAN DEFAULT 0,
        notes TEXT
    )
    """)
    
    # Add new columns if migrating from old schema
    existing_cols = [r[1] for r in cursor.execute("PRAGMA table_info(leads)").fetchall()]
    new_cols = [
        ("contact_type", "TEXT DEFAULT 'GENERIC_SUPPORT'"),
        ("contact_name", "TEXT"),
        ("country_code", "TEXT"),
        ("city", "TEXT"),
        ("platform", "TEXT DEFAULT 'Shopify'"),
        ("dominant_pattern", "TEXT"),
        ("reviews_count", "INTEGER DEFAULT 1"),
        ("review_freshest_date", "TEXT"),
        ("reviews_json", "TEXT")
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
            except Exception:
                pass
    
    # Table 2: Send & Touch History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS touch_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_domain TEXT,
        lead_email TEXT,
        sender_email TEXT,
        touch_number INTEGER,
        subject TEXT,
        sent_at TEXT,
        replied BOOLEAN DEFAULT 0,
        FOREIGN KEY (lead_domain) REFERENCES leads (domain)
    )
    """)
    conn.commit()
    conn.close()

def sync_from_json(json_path=None):
    """Ingests leads from scraper JSON into the SQLite CRM database without duplicates."""
    init_db()
    path = json_path or ICP1_JSON
    if not os.path.exists(path):
        return 0

    with open(path, "r", encoding="utf-8") as f:
        try:
            leads = json.load(f)
        except Exception:
            return 0

    conn = get_connection()
    cursor = conn.cursor()
    new_count = 0

    for l in leads:
        domain = l.get("domain", "").strip()
        if not domain:
            continue
        try:
            reviews = l.get("reviews_collection", [])
            rev_json = json.dumps(reviews) if reviews else ""
            
            cursor.execute("""
            INSERT INTO leads (
                domain, company_name, contact_email, contact_type, contact_name,
                country_code, city, platform, pain_trigger, dominant_pattern,
                reviews_count, review_freshest_date, reviews_json, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(domain) DO UPDATE SET
                company_name = COALESCE(NULLIF(leads.company_name, ''), excluded.company_name),
                contact_email = CASE 
                    WHEN leads.contact_email IS NULL OR leads.contact_email = '' THEN excluded.contact_email 
                    ELSE leads.contact_email 
                END,
                contact_type = CASE 
                    WHEN leads.contact_type IS NULL OR leads.contact_type = '' THEN excluded.contact_type 
                    ELSE leads.contact_type 
                END,
                contact_name = CASE 
                    WHEN leads.contact_name IS NULL OR leads.contact_name = '' THEN excluded.contact_name 
                    ELSE leads.contact_name 
                END,
                country_code = COALESCE(NULLIF(leads.country_code, ''), excluded.country_code),
                city = COALESCE(NULLIF(leads.city, ''), excluded.city),
                platform = COALESCE(NULLIF(leads.platform, ''), excluded.platform),
                pain_trigger = excluded.pain_trigger,
                dominant_pattern = excluded.dominant_pattern,
                reviews_count = excluded.reviews_count,
                review_freshest_date = excluded.review_freshest_date,
                reviews_json = excluded.reviews_json
            """, (
                domain,
                l.get("company_name") or domain,
                l.get("contact_email", "").strip(".,;:'\""),
                l.get("contact_type", "GENERIC_SUPPORT"),
                l.get("contact_name", ""),
                l.get("country_code", "US"),
                l.get("city", ""),
                l.get("platform", "Shopify"),
                l.get("pain_trigger", "checkout"),
                l.get("dominant_pattern", l.get("pain_trigger", "checkout")),
                len(reviews) if reviews else 1,
                l.get("review_freshest_date") or l.get("review_date", ""),
                rev_json,
                l.get("captured_at") or datetime.now().isoformat()
            ))
            new_count += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    return new_count

def log_touch(domain: str, to_email: str, sender_email: str, step: int, subject: str):
    """Logs sent email, updates lead status, and sets next cooldown."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    # Record interaction
    cursor.execute("""
    INSERT INTO touch_history (lead_domain, lead_email, sender_email, touch_number, subject, sent_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (domain, to_email, sender_email, step, subject, now_str))

    # Update lead status
    status = f"TOUCH_{step}_SENT" if step < 3 else "SEQUENCE_COMPLETED"
    cooldown = (datetime.now() + timedelta(days=45)).isoformat() if step >= 3 else None

    cursor.execute("""
    UPDATE leads SET
        status = ?,
        current_sequence_step = ?,
        last_contacted_at = ?,
        cooldown_until = COALESCE(?, cooldown_until)
    WHERE domain = ?
    """, (status, step, now_str, cooldown, domain))

    conn.commit()
    conn.close()

def get_retargetable_leads():
    """Returns leads that finished previous sequence and completed their 45-day cooldown."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    cursor.execute("""
    SELECT * FROM leads
    WHERE status = 'SEQUENCE_COMPLETED'
      AND client_won = 0
      AND (cooldown_until IS NULL OR cooldown_until <= ?)
    """, (now_str,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def export_to_csv():
    """Exports ICP1 leads from SQLite to clean CSV."""
    init_db()
    sync_from_json()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT domain, company_name, contact_email, contact_type, contact_name, 
               country_code, city, platform, pain_trigger, dominant_pattern, 
               reviews_count, review_freshest_date, status, current_sequence_step, last_contacted_at
        FROM leads 
        WHERE platform = 'Shopify'
        ORDER BY review_freshest_date DESC
    """)
    rows = cursor.fetchall()
    
    if not rows:
        conn.close()
        return

    headers = rows[0].keys()
    with open(ICP1_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(list(r))

    conn.close()
    print(f"Exported {len(rows)} verified leads to {ICP1_CSV}")

def get_stats():
    init_db()
    sync_from_json()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT count(*) as total, 
               sum(case when status='READY' then 1 else 0 end) as ready, 
               sum(case when contact_type='FOUNDER_DIRECT' then 1 else 0 end) as founders,
               sum(case when client_won=1 then 1 else 0 end) as won 
        FROM leads
    """)
    row = cursor.fetchone()
    conn.close()
    return dict(row)

if __name__ == "__main__":
    import sys
    if "--export" in sys.argv:
        export_to_csv()
    else:
        stats = get_stats()
        print(f"Mindmaxing CRM Status: {stats['total']} total leads | Ready: {stats['ready']} | Founders: {stats['founders']}")
