import sqlite3
from pathlib import Path

# مسیر پروژه
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'db' / 'database.sqlite'

# اطمینان از وجود پوشه db
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# اتصال و ساخت دیتابیس
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ساخت جدول کاربران عمومی
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY UNIQUE,
    plan_type TEXT,
    reference TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
''')

# ساخت جدول رفرال‌ها
c.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    uid INTEGER PRIMARY KEY,
    ownInviteCode TEXT,
    inviteSid INTEGER,
    invitationCode TEXT,
    registerTime INTEGER,
    directInvitation BOOLEAN,
    deposit BOOLEAN,
    balanceVolume REAL,
    trade BOOLEAN,
    level INTEGER,
    spotCommissionRatio REAL,
    contractCommissionRatio REAL
);
""")

# ساخت جدول کاربران VVIP
c.execute("""
CREATE TABLE IF NOT EXISTS vvip_subscribers (
    user_id     INTEGER PRIMARY KEY,
    plan_type   TEXT,
    reference   TEXT,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_balance_check INTEGER,
    last_warning    INTEGER,
    removed_at      INTEGER
);
""")

conn.commit()
conn.close()
print("✅ DB initialized.")
