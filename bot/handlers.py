# handlers.py

from aiogram import types, Dispatcher
from .utils import check_uid, save_user
import os

# برداشتن آیدی کانال از متغیر محیطی
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002389535319"))

# آیدی ادمین‌ها (در صورت تمایل دستورهای مدیریتی)
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x}

async def start_handler(message: types.Message):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton('اشتراک رایگان', callback_data='vip_free'),
        types.InlineKeyboardButton('اشتراک پولی', callback_data='vip_paid'),
        types.InlineKeyboardButton('لینک ورود به کانال', url=f'https://t.me/+{CHANNEL_ID}'),
        types.InlineKeyboardButton('درخواست پشتیبانی', callback_data='support')
    )
    await message.answer("سلام! به ربات مدیریت VIP خوش آمدید.", reply_markup=kb)

async def vip_free_handler(callback: types.CallbackQuery):
    await callback.message.answer("لطفا UID رفرال خود را ارسال کنید:")

async def receive_uid_handler(message: types.Message):
    uid = message.text.strip()
    if not uid.isdigit():
        await message.answer("لطفا یک عدد معتبر ارسال کنید.")
        return

    if check_uid(uid):
        # شناسه تلگرام کاربر
        tg_id = message.from_user.id
        # ذخیره کاربر با پلن free و مرجع uid
        save_user(tg_id, 'free', uid)

        # ساخت لینک دعوت یک‌بارمصرف
        invite = await message.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1
        )
        await message.answer(
            "اشتراک رایگان شما فعال شد!\n\n"
            f"لینک دعوت (یک‌بارمصرف):\n{invite.invite_link}"
        )
    else:
        await message.answer("متاسفیم، UID شما در لیست رفرال‌ها نیست.")

async def vip_paid_handler(callback: types.CallbackQuery):
    await callback.message.answer("برای اشتراک پولی لطفا TXID تراکنش خود را ارسال کنید.")

async def receive_txid_handler(message: types.Message):
    txid = message.text.strip()
    if not txid.startswith("TXID-"):
        await message.answer("لطفا TXID را با پیش‌شماره‌ی TXID- ارسال کنید.")
        return

    tg_id = message.from_user.id
    save_user(tg_id, 'paid', txid)
    await message.answer(
        "TXID شما دریافت شد و در حال بررسی است.\n"
        "پس از تایید دستی لینک دعوت را برایتان ارسال خواهیم کرد."
    )

async def support_handler(callback: types.CallbackQuery):
    await callback.message.answer("برای پشتیبانی با @your_support_bot تماس بگیرید.")

async def list_users_handler(message: types.Message):
    # دستور مدیریتی: مشاهده تعداد کاربران
    if message.from_user.id not in ADMIN_IDS:
        return
    from .utils import get_all_users
    users = get_all_users()
    if not users:
        await message.answer("فعلاً هیچ کاربری ثبت نشده.")
        return
    text = "📋 لیست کاربران:\n\n"
    for u in users:
        text += f"ID: {u['id']} — TelegramID: {u['user_id']} — Plan: {u['plan_type']} — Ref: {u['reference']}\n"
    await message.answer(text)

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'])
    dp.register_callback_query_handler(vip_free_handler, lambda c: c.data=='vip_free')
    dp.register_message_handler(receive_uid_handler, lambda m: m.text.isdigit(), state=None)
    dp.register_callback_query_handler(vip_paid_handler, lambda c: c.data=='vip_paid')
    dp.register_message_handler(receive_txid_handler, lambda m: m.text.startswith("TXID-"), state=None)
    dp.register_callback_query_handler(support_handler, lambda c: c.data=='support')
    dp.register_message_handler(list_users_handler, commands=['list_users'])
