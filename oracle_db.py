# oracle_db.py
"""
Mock Oracle DB connector for Workflow AI demo.
Uses SQLite locally to simulate Oracle tables and workflow operations.
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime

DB_PATH = "workflow_mock.db"


def init_db():
    """Initialize SQLite mock database and tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Workflow table
    c.execute("""
        CREATE TABLE IF NOT EXISTS wf_ai_workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT,
            item_key TEXT,
            error_message TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    # Audit log
    c.execute("""
        CREATE TABLE IF NOT EXISTS wf_ai_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_timestamp TEXT,
            user_name TEXT,
            action_type TEXT,
            item_type TEXT,
            item_key TEXT,
            result_message TEXT,
            incident_number TEXT
        )
    """)

    conn.commit()
    conn.close()


def query_failed_workflows():
    """Return all failed workflows (mock)."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM wf_ai_workflows WHERE status='FAILED'", conn)
    conn.close()
    return df.to_dict(orient="records")


def query_workflow_by_item(item_key):
    """Return workflow by item key."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM wf_ai_workflows WHERE item_key = ?", conn, params=(item_key,)
    )
    conn.close()
    if df.empty:
        return None
    return df.to_dict(orient="records")[0]


def retry_failed_workflow(item_type, item_key, user="system"):
    """
    Simulate retrying a failed workflow.
    In real Oracle, this would call a PL/SQL API.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE wf_ai_workflows SET status='RETRIED' WHERE item_key = ?", (item_key,)
    )
    conn.commit()
    conn.close()

    # Log the retry
    log_audit(
        action_type="RetryWorkflow",
        item_type=item_type,
        item_key=item_key,
        result_message="Workflow retried successfully",
        incident_number=None,
        user=user,
    )
    return {"status": "success", "message": f"{item_key} retried successfully"}


def log_audit(action_type, item_type, item_key, result_message, incident_number=None, user="system"):
    """Insert an entry into the audit log."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO wf_ai_audit_log 
        (log_timestamp, user_name, action_type, item_type, item_key, result_message, incident_number)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user,
            action_type,
            item_type,
            item_key,
            result_message,
            incident_number,
        ),
    )
    conn.commit()
    conn.close()


def fetch_audit(limit=100):
    """Fetch last N audit log entries."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        f"SELECT * FROM wf_ai_audit_log ORDER BY id DESC LIMIT {limit}", conn
    )
    conn.close()
    return df.to_dict(orient="records")
