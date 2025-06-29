# utils.py

import sqlite3
from pathlib import Path
import os

# مسیر دیتابیس
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / 'db' / 'database.sqlite'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_uid(uid: str) -> bool:
    conn = get_connection()
    cur  = conn.execute('SELECT 1 FROM referrals WHERE uid=?', (int(uid),))
    ok   = cur.fetchone() is not None
    conn.close()
    return ok

def save_user(user_id: int, plan: str, ref: str):
    conn = get_connection()
    conn.execute('''
        INSERT OR REPLACE INTO users (user_id, plan_type, reference)
        VALUES (?, ?, ?)
    ''', (user_id, plan, ref))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    cur  = conn.execute('SELECT * FROM users ORDER BY created_at DESC')
    rows = cur.fetchall()
    conn.close()
    return rows
