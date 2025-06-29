# monitor_vvip.py

import os
import time
import sqlite3
import hmac
import hashlib
import requests
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot

# ── بارگذاری متغیرهای محیطی ─────────────────────────────────────
load_dotenv()
BOT_TOKEN    = os.getenv("BOT_TOKEN")
API_KEY      = os.getenv("API_KEY")
SECRET_KEY   = os.getenv("SECRET_KEY")
CHANNEL_ID   = int(os.getenv("CHANNEL_ID", "-1002389535319"))
DB_PATH      = os.getenv("MONITOR_DB", "database.sqlite")

# ── تنظیمات زمان‌بندی ────────────────────────────────────────────
BALANCE_CHECK_INTERVAL_HOURS = 6    # هر 6 ساعت مانیتور موجودی
EXPIRY_CHECK_INTERVAL_HOURS  = 24   # هر 24 ساعت چک انقضا
PAID_EXPIRE_DAYS             = 90   # انقضای اشتراک پولی پس از 90 روز

# ── لاگ‌سازی ───────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

bot = Bot(token=BOT_TOKEN)

# ── init جدول vvip_subscribers ───────────────────────────────────
def init_vvip_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS vvip_subscribers (
        user_id        INTEGER PRIMARY KEY,
        last_warning   INTEGER,
        removed_at     INTEGER
    );
    """)
    # ستون joined_at برای مشترکین پولی در users فرض می‌کنیم
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id       INTEGER UNIQUE,
        plan_type     TEXT,
        reference     TEXT,
        joined_at     INTEGER,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()
    logging.info("✅ Tables initialized.")

# ── HMAC-SHA256 signature ────────────────────────────────────────
def sign(qs: str) -> str:
    return hmac.new(SECRET_KEY.encode(), qs.encode(), hashlib.sha256).hexdigest()

# ── فراخوانی API برای دریافت مجموع balanceVolume ─────────────────
def get_balance(uid: int) -> float:
    ts = int(time.time() * 1000)
    params = f"uid={uid}&timestamp={ts}&recvWindow=5000"
    signature = sign(params)
    url = f"https://api.toobit.com/api/v1/agent/depositDetailList?{params}&signature={signature}"
    headers = {
        "X-BM-KEY":       API_KEY,
        "X-BM-TIMESTAMP": str(ts),
        "X-BM-SIGN":      signature
    }
    resp = requests.get(url, headers=headers, timeout=10).json()
    return sum(
        float(item.get("balanceVolume", 0))
        for item in resp.get("data", {}).get("list", [])
    )

# ── حلقهٔ مانیتورینگ موجودی VVIP ─────────────────────────────────
async def monitor_vvip_balance():
    init_vvip_table()
    while True:
        now = int(time.time())
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        for user_id, last_warn, removed_at in c.execute(
            "SELECT user_id, last_warning, removed_at FROM vvip_subscribers"
        ):
            bal = get_balance(user_id)
            # ۱) هشدار اول هر 6 ساعت
            if bal < 40:
                if not last_warn or now - last_warn > BALANCE_CHECK_INTERVAL_HOURS * 3600:
                    c.execute(
                        "UPDATE vvip_subscribers SET last_warning=? WHERE user_id=?",
                        (now, user_id)
                    )
                    await bot.send_message(
                        user_id,
                        "⚠️ موجودی شما زیر 40 USDT رسیده. لطفاً تا 24 ساعت آینده شارژ کنید."
                    )
                # ۲) اگر 24h از هشدار اول گذشته و هنوز removed_at تنظیم نشده
                elif last_warn and now - last_warn > 24 * 3600 and not removed_at:
                    remove_time = now + 24 * 3600
                    c.execute(
                        "UPDATE vvip_subscribers SET removed_at=? WHERE user_id=?",
                        (remove_time, user_id)
                    )
                    await bot.send_message(
                        user_id,
                        "❌ اگر تا 24 ساعت آینده شارژ نکنید، از کانال حذف می‌شوید."
                    )
                # ۳) اگر زمان حذف فرا رسیده => حذف از کانال
                elif removed_at and now >= removed_at:
                    try:
                        await bot.kick_chat_member(CHANNEL_ID, user_id)
                        logging.info(f"Removed VVIP user {user_id} due to low-balance expiry.")
                    except Exception as e:
                        logging.error(f"Error removing VVIP {user_id}: {e}")

        conn.commit()
        conn.close()
        await asyncio.sleep(BALANCE_CHECK_INTERVAL_HOURS * 3600)

# ── حلقهٔ مانیتورینگ انقضای اشتراک پولی ─────────────────────────
async def monitor_paid_expiry():
    while True:
        cutoff = int((datetime.utcnow() - timedelta(days=PAID_EXPIRE_DAYS)).timestamp())
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        for user_id, joined_at in c.execute(
            "SELECT user_id, joined_at FROM users WHERE plan_type='paid' AND joined_at <= ?",
            (cutoff,)
        ):
            try:
                await bot.kick_chat_member(CHANNEL_ID, user_id)
                logging.info(f"Removed paid subscriber {user_id} after {PAID_EXPIRE_DAYS} days.")
            except Exception as e:
                logging.error(f"Error removing paid {user_id}: {e}")
        conn.close()
        await asyncio.sleep(EXPIRY_CHECK_INTERVAL_HOURS * 3600)

# ── اجرا در asyncio loop ────────────────────────────────────────────
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_vvip_balance())
    loop.create_task(monitor_paid_expiry())
    loop.run_forever()
