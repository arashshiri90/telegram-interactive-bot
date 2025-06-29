```python
# bot/main.py

import asyncio
import os
import sqlite3
from pathlib import Path

from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.exceptions import ChatAdminRequired

# ── بارگذاری متغیرها ─────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002389535319"))  # آیدی کانال خصوصی

# ── مسیر دیتابیس رفرال ───────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
REF_DB   = BASE_DIR / 'referrals.db'
USER_DB  = BASE_DIR / 'db' / 'database.sqlite'

# ── توابع کمکی ───────────────────────────────────────────────

def is_referral(uid: int) -> bool:
    conn = sqlite3.connect(REF_DB)
    cur  = conn.execute('SELECT 1 FROM referrals WHERE uid = ?', (uid,))
    found = cur.fetchone() is not None
    conn.close()
    return found

# اتصال به دیتابیس کاربران
 def get_user_conn():
    conn = sqlite3.connect(USER_DB)
    return conn

# ایجاد جدول کاربران
 def init_user_db():
    conn = get_user_conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            plan_type TEXT,
            reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

# ── راه‌اندازی ربات ───────────────────────────────────────────
if __name__ == '__main__':
    init_user_db()

    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(bot)

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("اشتراک رایگان", "اشتراک پولی")
    kb.add("لینک کانال VIP", "درخواست پشتیبانی")

    @dp.message_handler(commands=['start'])
    async def cmd_start(msg: types.Message):
        await msg.answer("سلام! منو را انتخاب کنید:", reply_markup=kb)

    @dp.message_handler(lambda m: m.text == "اشتراک رایگان")
    async def on_free(msg: types.Message):
        await msg.answer("لطفا UID رفرال خود را ارسال کنید:")

    @dp.message_handler(lambda m: m.text.isdigit())
    async def on_uid(msg: types.Message):
        uid   = int(msg.text)
        tg_id = msg.from_user.id

        if is_referral(uid):
            # ذخیره کاربر
            conn = get_user_conn()
            conn.execute(
                'INSERT OR REPLACE INTO users (user_id, plan_type, reference) VALUES (?, ?, ?)',
                (tg_id, "free", uid)
            )
            conn.commit()
            conn.close()

            # ساخت لینک یک‌بارمصرف
            try:
                invite = await bot.create_chat_invite_link(
                    chat_id=CHANNEL_ID,
                    member_limit=1,
                    expire_date=None
                )
                text = (
                    "🎉 اشتراک رایگان شما فعال شد!\n"
                    f"لینک یک‌بارمصرف شما برای ورود به کانال VIP:\n{invite.invite_link}\n"
                    "خوش آمدید! 🤗"
                )
                await msg.answer(text)
            except ChatAdminRequired:
                await msg.answer("خطا: من دسترسی مدیریت کانال را ندارم.")
        else:
            await msg.answer("❌ UID شما معتبر نیست. لطفا دوباره بررسی کنید.", reply_markup=kb)

    @dp.message_handler(lambda m: m.text == "اشتراک پولی")
    async def on_paid(msg: types.Message):
        await msg.answer("لطفا TXID تراکنش خود را ارسال کنید:")

    @dp.message_handler(lambda m: m.text.startswith("TXID-"))
    async def on_txid(msg: types.Message):
        tg_id = msg.from_user.id
        txid  = msg.text.strip()
        conn = get_user_conn()
        conn.execute(
            'INSERT OR REPLACE INTO users (user_id, plan_type, reference) VALUES (?, ?, ?)',
            (tg_id, "paid", txid)
        )
        conn.commit()
        conn.close()
        await msg.answer("TXID شما ثبت شد، پس از تایید لینک کانال را ارسال خواهیم کرد.", reply_markup=kb)

    @dp.message_handler(lambda m: m.text == "لینک کانال VIP")
    async def on_link(msg: types.Message):
        tg_id = msg.from_user.id
        conn  = get_user_conn()
        cur   = conn.execute('SELECT plan_type FROM users WHERE user_id=?', (tg_id,))
        if cur.fetchone():
            await msg.answer("📢 لینک کانال خصوصی: https://t.me/your_private_channel")
        else:
            await msg.answer("ابتدا اشتراک خود را فعال کنید.", reply_markup=kb)
        conn.close()

    @dp.message_handler(lambda m: m.text == "درخواست پشتیبانی")
    async def on_support(msg: types.Message):
        await msg.answer("برای پشتیبانی به @your_support_bot پیام دهید.")

    executor.start_polling(dp, skip_updates=True)
```
