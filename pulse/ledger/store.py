import sqlite3
import os
import logging
from pulse.config import DB_PATH
from pulse.ledger.models import RunRecord, DeliveryRecord

logger = logging.getLogger("pulse-ledger-store")

def init_db():
    """Initializes SQLite tables for run auditing."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            product TEXT NOT NULL,
            iso_week TEXT NOT NULL,
            status TEXT NOT NULL, -- 'pending', 'completed', 'failed'
            review_count INTEGER,
            window_weeks INTEGER,
            started_at TEXT,
            completed_at TEXT,
            error_message TEXT,
            UNIQUE(product, iso_week) ON CONFLICT REPLACE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deliveries (
            run_id TEXT,
            channel TEXT NOT NULL, -- 'google_doc', 'gmail'
            external_id TEXT NOT NULL,
            url TEXT,
            idempotency_key TEXT,
            FOREIGN KEY (run_id) REFERENCES runs (run_id)
        )
    """)
    
    conn.commit()
    conn.close()

# Ensure database tables exist on import
init_db()

def get_run(product: str, iso_week: str) -> sqlite3.Row:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM runs WHERE product = ? AND iso_week = ?", (product, iso_week))
    row = cursor.fetchone()
    conn.close()
    return row

def save_run(run: RunRecord):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO runs (run_id, product, iso_week, status, review_count, window_weeks, started_at, completed_at, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (run.run_id, run.product, run.iso_week, run.status, run.review_count, run.window_weeks, run.started_at, run.completed_at, run.error_message))
    conn.commit()
    conn.close()

def save_delivery(delivery: DeliveryRecord):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO deliveries (run_id, channel, external_id, url, idempotency_key)
        VALUES (?, ?, ?, ?, ?)
    """, (delivery.run_id, delivery.channel, delivery.external_id, delivery.url, delivery.idempotency_key))
    conn.commit()
    conn.close()

def get_deliveries(run_id: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deliveries WHERE run_id = ?", (run_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
