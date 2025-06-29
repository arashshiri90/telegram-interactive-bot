import requests
import time
import hmac
import hashlib
import sqlite3
import threading
from urllib.parse import urlencode

# تنظیمات API و دیتابیس
API_KEY = "lQATIfRTcr3ddvWIMSYUe5UyEUBjb5TO0Iylr7AXmcfxb9aXDOcj7p6wMFIlQSJ0"
SECRET_KEY = "9eMOolzbhAxmg8g4RztrKKUKEv9w3ZW0O8YG2CB8R15vus0mpG7XKv8Iq6UHn3l5"
BASE_URL = "https://api.toobit.com"
DB_FILE = "referrals.db"

# ساخت امضای HMAC-SHA256
def generate_signature(query_string, secret_key):
    return hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# گرفتن لیست ریفرال‌ها از API
def fetch_referrals(page=1, page_size=200):
    timestamp = int(time.time() * 1000)
    params = {
        "pageIndex": page,
        "pageSize": page_size,
        "timestamp": timestamp,
        "recvWindow": 5000,
        "accessKey": API_KEY
    }
    query_string = urlencode(params)
    signature = generate_signature(query_string, SECRET_KEY)
    params["signature"] = signature

    url = f"{BASE_URL}/api/v1/agent/inviteUserList?{urlencode(params)}"

    headers = {
        "X-BM-KEY": API_KEY,
        "X-BM-TIMESTAMP": str(timestamp),
        "X-BM-SIGN": signature
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Exception while fetching referrals: {e}")
        return {"code": -1, "msg": str(e)}

# ایجاد جدول دیتابیس اگر وجود نداشته باشد
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            uid INTEGER PRIMARY KEY,
            ownInviteCode TEXT,
            inviteSid INTEGER,
            invitationCode TEXT,
            registerTime INTEGER,
            directInvitation BOOLEAN,
            deposit BOOLEAN,
            balanceVolume TEXT,
            trade BOOLEAN,
            level INTEGER,
            spotCommissionRatio TEXT,
            contractCommissionRatio TEXT
        )
    ''')
    conn.commit()
    conn.close()

# آپدیت کردن دیتابیس با داده‌های API
def update_referral_data():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    page = 1
    total_rows = 0

    while True:
        data = fetch_referrals(page=page)
        if data.get("code") != 200:
            print(f"❌ API Error (page {page}): {data.get('msg')}")
            break

        rows = data.get("data", {}).get("list", [])
        if not rows:
            break

        for user in rows:
            c.execute('''
                INSERT OR REPLACE INTO referrals (
                    uid, ownInviteCode, inviteSid, invitationCode, registerTime,
                    directInvitation, deposit, balanceVolume, trade,
                    level, spotCommissionRatio, contractCommissionRatio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(user["uid"]),
                user.get("ownInviteCode", ""),
                int(user.get("inviteSid", 0)),
                user.get("invitationCode", ""),
                int(user.get("registerTime", 0)),
                bool(user.get("directInvitation", False)),
                bool(user.get("deposit", False)),
                user.get("balanceVolume", "0"),
                bool(user.get("trade", False)),
                int(user.get("level", 0)),
                user.get("spotCommissionRatio", "0"),
                user.get("contractCommissionRatio", "0")
            ))

        conn.commit()
        print(f"✅ Updated page {page} with {len(rows)} users")
        total_rows += len(rows)
        page += 1

    conn.close()
    print(f"✅ All done. Total {total_rows} users updated.\n")

# اجرای خودکار هر چند دقیقه
def start_scheduler(interval_minutes=5):
    def run():
        while True:
            print("⏳ Starting referral data update...")
            try:
                update_referral_data()
            except Exception as e:
                print(f"❌ Error during update: {e}")
            print(f"🕓 Waiting {interval_minutes} minutes for next update...\n")
            time.sleep(interval_minutes * 60)

    threading.Thread(target=run, daemon=True).start()

# اجرای برنامه
if __name__ == "__main__":
    start_scheduler()
    while True:
        time.sleep(3600)  # نگه داشتن برنامه در حالت اجرا
