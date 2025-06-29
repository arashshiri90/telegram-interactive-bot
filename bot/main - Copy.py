# bot/main.py
import os
import json
import sqlite3
import logging
from pathlib import Path
from collections import defaultdict

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import ChatAdminRequired
from dotenv import load_dotenv

from bot.menu import main_keyboard, free_exchange_keyboard

# ── بارگذاری متغیرهای محیطی ─────────────────────────────────────────
load_dotenv()
BOT_TOKEN   = os.getenv("BOT_TOKEN")
CHANNEL_ID  = int(os.getenv("CHANNEL_ID", "-1002389535319"))
ADMINS      = set(int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit())

# ── مسیر دیتابیس ──────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
REF_DB   = BASE_DIR / 'referrals.db'
USER_DB  = BASE_DIR / 'db' / 'database.sqlite'

# ── بارگذاری محتوای ثابت ─────────────────────────────────────────────
with open(BASE_DIR / "content.json", encoding="utf-8") as f:
    content_data = json.load(f)

# ── کلاس وضعیت‌ها برای FSM ────────────────────────────────────────────
class FreeReferralState(StatesGroup):
    waiting_for_uid = State()

# ── توابع کمکی ────────────────────────────────────────────────────────
def is_referral(uid: int) -> bool:
    conn  = sqlite3.connect(REF_DB)
    found = conn.execute('SELECT 1 FROM referrals WHERE uid = ?', (uid,)).fetchone() is not None
    conn.close()
    return found

def get_user_conn():
    return sqlite3.connect(USER_DB)

def init_user_db():
    conn = get_user_conn()
    c    = conn.cursor()
    c.execute("DROP TABLE IF EXISTS users;")
    c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            plan_type TEXT,
            reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    conn.commit()
    conn.close()

# ── کیبورد روش‌های پرداخت ─────────────────────────────────────────────
paid_method_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
paid_method_keyboard.add(
    types.KeyboardButton("واریز از طریق شبکه TRC20"),
    types.KeyboardButton("واریز از طریق شبکه BEP20"),
    types.KeyboardButton("➡️ انصراف و بازگشت به منو اصلی")
)

# ── نگهداری نگاشت پیام‌های فوروارد شده ────────────────────────────────
forwarded_message_map = defaultdict(int)

# ── راه‌اندازی ربات با Markdown ─────────────────────────────────────
if __name__ == '__main__':
    init_user_db()
    bot     = Bot(token=BOT_TOKEN, parse_mode="Markdown")
    storage = MemoryStorage()
    dp      = Dispatcher(bot, storage=storage)

    @dp.message_handler(commands=['start'])
    async def cmd_start(msg: types.Message):
        await msg.answer("سلام! منو را انتخاب کنید:", reply_markup=main_keyboard)

    @dp.message_handler(lambda m: m.text == "🎫 دریافت اشتراک VVIP")
    async def vip_request(msg: types.Message):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        kb.add(
            types.KeyboardButton("اشتراک رایگان (رفرال)"),
            types.KeyboardButton("اشتراک ماهیانه (پولی)"),
            types.KeyboardButton("➡️ انصراف و بازگشت به منو اصلی")
        )
        await msg.answer("نوع اشتراک مورد نظر خود را انتخاب کنید:", reply_markup=kb)

    @dp.message_handler(lambda m: m.text == "اشتراک رایگان (رفرال)")
    async def on_free_intro(msg: types.Message):
        await msg.answer(content_data["free_intro"]["content"], reply_markup=free_exchange_keyboard)

    @dp.message_handler(lambda m: m.text == "توبیت (Toobit)")
    async def on_free_toobit(msg: types.Message, state: FSMContext):
        await msg.answer("لطفاً UID خود را ارسال کنید:")
        await FreeReferralState.waiting_for_uid.set()

    @dp.message_handler(lambda m: m.text == "➡️ انصراف و بازگشت به منو اصلی", state=FreeReferralState.waiting_for_uid)
    async def on_cancel_free(msg: types.Message, state: FSMContext):
        await state.finish()
        await msg.answer("❌ عملیات کنسل شد. بازگشت به منوی اصلی:", reply_markup=main_keyboard)

    @dp.message_handler(state=FreeReferralState.waiting_for_uid)
    async def on_uid(msg: types.Message, state: FSMContext):
        if not msg.text.isdigit():
            await msg.reply("❌ لطفاً یک عدد UID معتبر وارد کنید.")
            return
        uid   = int(msg.text)
        tg_id = msg.from_user.id
        if is_referral(uid):
            conn = get_user_conn()
            conn.execute(
                'INSERT OR REPLACE INTO users (user_id, plan_type, reference) VALUES (?, ?, ?)',
                (tg_id, "free", uid)
            )
            conn.commit()
            conn.close()
            try:
                invite = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
                await msg.answer(
                    f"🎉 اشتراک رایگان شما فعال شد!\n"
                    f"لینک یک‌بارمصرف:\n{invite.invite_link}\n"
                    "خوش آمدید! 🤗"
                )
            except ChatAdminRequired:
                await msg.answer("⚠️ خطا: ربات دسترسی مدیریتی به کانال ندارد.")
        else:
            await msg.answer(
                "اوه! UID شما ثبت نشده.\n"
                "[ثبت‌نام در Toobit](https://www.toobit.com/t/Aronsignals)",
                reply_markup=main_keyboard
            )
        await state.finish()

    @dp.message_handler(lambda m: m.text == "اشتراک ماهیانه (پولی)")
    async def on_paid_intro(msg: types.Message):
        await msg.answer(
            content_data["paid_intro"]["content"],
            reply_markup=paid_method_keyboard
        )

    @dp.message_handler(lambda m: m.text == "واریز از طریق شبکه TRC20")
    async def on_trc(msg: types.Message):
        await msg.answer(content_data["paid_trc20"]["content"])

    @dp.message_handler(lambda m: m.text == "واریز از طریق شبکه BEP20")
    async def on_bep(msg: types.Message):
        await msg.answer(content_data["paid_bep20"]["content"])

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
        await msg.answer("✅ TXID شما ثبت شد. پس از بررسی، لینک کانال ارسال خواهد شد.")
        for admin in ADMINS:
            await bot.send_message(
                admin,
                f"💰 واریز جدید برای اشتراک ماهیانه:\n\n"
                f"🆔 کاربر: @{msg.from_user.username or msg.from_user.id}\n"
                f"🔖 TXID: `{txid}`"
            )

    @dp.message_handler(lambda m: m.text == "➡️ انصراف و بازگشت به منو اصلی")
    async def on_back(msg: types.Message, state: FSMContext):
        await state.finish()
        await msg.answer("بازگشت به منوی اصلی:", reply_markup=main_keyboard)

    @dp.message_handler(lambda m: m.text == "لینک کانال VIP")
    async def on_link(msg: types.Message):
        tg_id = msg.from_user.id
        conn  = get_user_conn()
        has   = conn.execute('SELECT 1 FROM users WHERE user_id=?', (tg_id,)).fetchone()
        conn.close()
        if has:
            await msg.answer("📢 لینک کانال: https://t.me/your_private_channel")
        else:
            await msg.answer("❌ ابتدا اشتراک خود را فعال کنید.", reply_markup=main_keyboard)

    @dp.message_handler(lambda m: m.from_user.id not in ADMINS, content_types=types.ContentTypes.ANY)
    async def forward_to_admin(msg: types.Message):
        for adm in ADMINS:
            try:
                sent = await bot.copy_message(
                    chat_id=adm,
                    from_chat_id=msg.chat.id,
                    message_id=msg.message_id
                )
                forwarded_message_map[sent.message_id] = msg.from_user.id
            except Exception:
                await bot.send_message(
                    adm,
                    f"📨 پیام از `{msg.from_user.id}`:\n\n{msg.text or 'نوع پیام پشتیبانی نمی‌شود'}"
                )
                forwarded_message_map[msg.message_id] = msg.from_user.id
        await msg.answer("✅ پیام شما برای پشتیبانی ارسال شد. لطفاً منتظر پاسخ باشید.")

    @dp.message_handler(lambda m: m.from_user.id in ADMINS and m.reply_to_message, content_types=types.ContentTypes.ANY)
    async def reply_from_admin(msg: types.Message):
        original_msg_id = msg.reply_to_message.message_id
        user_id = forwarded_message_map.get(original_msg_id)
        if not user_id:
            await msg.answer("❌ کاربر مربوط به این پیام یافت نشد.")
            return
        try:
            await bot.send_message(user_id, f"📩 پاسخ پشتیبانی:\n\n{msg.text}")
            await msg.answer("✅ پاسخ شما برای کاربر ارسال شد.")
        except Exception as e:
            await msg.answer(f"❌ خطا در ارسال پیام: {e}")

    executor.start_polling(dp, skip_updates=True)
