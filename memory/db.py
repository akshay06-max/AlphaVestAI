"""SQLite persistent conversation memory + long-term investor profile + report archive — Module 9 & 12."""
import os
import sqlite3
from datetime import datetime
import json

DB_PATH = "data/memory.db"


def init_db(path: str = DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, role TEXT, content TEXT, timestamp TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS investor_profile (
            client_name TEXT PRIMARY KEY,
            risk_profile TEXT,
            preferred_industries TEXT,
            investment_interests TEXT,
            preferred_report_style TEXT,
            frequently_researched TEXT,
            client_email TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS generated_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            company_name TEXT,
            report_type TEXT,
            content_json TEXT,
            summary_text TEXT,
            created_at TEXT
        )
    """)
    # Migration helper for existing DBs if columns are missing
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE investor_profile ADD COLUMN investment_interests TEXT")
    except Exception:
        pass
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE investor_profile ADD COLUMN preferred_report_style TEXT")
    except Exception:
        pass
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE investor_profile ADD COLUMN client_email TEXT")
    except Exception:
        pass
    conn.commit()
    return conn


def save_message(conn, session_id: str, role: str, content: str):
    conn.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?,?,?,?)",
        (session_id, role, content, datetime.now().isoformat()),
    )
    conn.commit()


def load_history(conn, session_id: str):
    return conn.execute(
        "SELECT role, content, timestamp FROM conversations WHERE session_id=? ORDER BY id",
        (session_id,),
    ).fetchall()


def list_sessions(conn):
    rows = conn.execute("SELECT DISTINCT session_id FROM conversations").fetchall()
    return [r[0] for r in rows]


def save_preference(
    conn,
    client_name: str,
    risk_profile: str = None,
    preferred_industries: str = None,
    investment_interests: str = None,
    preferred_report_style: str = None,
    client_email: str = None,
):
    """Save or update long-term investor profile (Module 9)."""
    conn.execute(
        """INSERT INTO investor_profile (client_name, risk_profile, preferred_industries, investment_interests, preferred_report_style, client_email)
           VALUES (?,?,?,?,?,?)
           ON CONFLICT(client_name) DO UPDATE SET
             risk_profile=COALESCE(excluded.risk_profile, investor_profile.risk_profile),
             preferred_industries=COALESCE(excluded.preferred_industries, investor_profile.preferred_industries),
             investment_interests=COALESCE(excluded.investment_interests, investor_profile.investment_interests),
             preferred_report_style=COALESCE(excluded.preferred_report_style, investor_profile.preferred_report_style),
             client_email=COALESCE(excluded.client_email, investor_profile.client_email)
        """,
        (client_name, risk_profile, preferred_industries, investment_interests, preferred_report_style, client_email),
    )
    conn.commit()


def get_preference(conn, client_name: str):
    """Retrieve full investor profile with fallback email defaults."""
    row = conn.execute(
        "SELECT client_name, risk_profile, preferred_industries, frequently_researched, investment_interests, preferred_report_style, client_email FROM investor_profile WHERE client_name=?",
        (client_name,),
    ).fetchone()
    if row:
        email = row[6] if row[6] else os.getenv("EMAIL_SENDER", "akshayanilnair06@gmail.com")
        return (row[0], row[1], row[2], row[3], row[4], row[5], email)
    return None


def add_researched_company(conn, client_name: str, company: str):
    """Add company to client's frequently researched companies list."""
    if not company:
        return
    row = get_preference(conn, client_name)
    existing = row[3] if row and row[3] else ""
    companies = set(c.strip() for c in existing.split(",") if c.strip())
    companies.add(company)
    conn.execute(
        """INSERT INTO investor_profile (client_name, frequently_researched)
           VALUES (?,?)
           ON CONFLICT(client_name) DO UPDATE SET
             frequently_researched=excluded.frequently_researched
        """,
        (client_name, ", ".join(sorted(companies))),
    )
    conn.commit()


def save_report_archive(conn, client_name: str, company_name: str, report_type: str, content_data: dict, summary_text: str):
    """Save generated investment report to persistent archive (Module 12)."""
    conn.execute(
        "INSERT INTO generated_reports (client_name, company_name, report_type, content_json, summary_text, created_at) VALUES (?,?,?,?,?,?)",
        (client_name, company_name, report_type, json.dumps(content_data), summary_text, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()


def list_archived_reports(conn, client_name: str = None):
    """List historical reports."""
    if client_name:
        return conn.execute(
            "SELECT id, company_name, report_type, summary_text, created_at FROM generated_reports WHERE client_name=? ORDER BY id DESC",
            (client_name,),
        ).fetchall()
    return conn.execute(
        "SELECT id, company_name, report_type, summary_text, created_at FROM generated_reports ORDER BY id DESC"
    ).fetchall()


def get_archived_report(conn, report_id: int):
    """Retrieve a specific archived report by ID."""
    row = conn.execute(
        "SELECT id, client_name, company_name, report_type, content_json, summary_text, created_at FROM generated_reports WHERE id=?",
        (report_id,),
    ).fetchone()
    if row:
        return {
            "id": row[0],
            "client_name": row[1],
            "company_name": row[2],
            "report_type": row[3],
            "content": json.loads(row[4]) if row[4] else {},
            "summary_text": row[5],
            "created_at": row[6],
        }
    return None
