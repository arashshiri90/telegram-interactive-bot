# bot/main.py
import os
import json
import sqlite3
import logging
import html
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import ChatAdminRequired, BotBlocked, UserDeactivated, ChatNotFound
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ParseMode
from dotenv import load_dotenv

from bot.menu import main_keyboard, free_exchange_keyboard, paid_method_keyboard

# ── بارگذاری متغیرهای محیطی و تنظیمات ────────────────────────────────
load_dotenv()
BOT_TOKEN   = os.getenv("BOT_TOKEN")
CHANNEL_ID  = int(os.getenv("CHANNEL_ID", "-1002389535319"))
ADMINS       = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
if not ADMINS:
    logging.warning("ADMIN_IDS is not set in .env or is empty. Admin functionalities might not work.")

# ── مسیر دیتابیس‌ها ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DB_PATH  = BASE_DIR / 'db' / 'database.sqlite'
REF_DB   = BASE_DIR / 'referrals.db'

# ── بارگذاری محتوای ثابت ─────────────────────────────────────────────
with open(BASE_DIR / "content.json", encoding="utf-8") as f:
    content_data = json.load(f)

# ── کلاس وضعیت‌ها برای FSM ────────────────────────────────────────────
class FreeReferralState(StatesGroup):
    waiting_for_uid = State()

class PaidSubscriptionState(StatesGroup):
    waiting_for_txid = State()
    waiting_for_method = State()

# ── توابع کمکی دیتابیس ──────────────────────────────────────────────
def get_db_conn():
    return sqlite3.connect(DB_PATH)

def get_ref_db_conn():
    return sqlite3.connect(REF_DB)

def is_referral(uid: int) -> bool:
    conn = get_ref_db_conn()
    cur  = conn.execute('SELECT 1 FROM referrals WHERE uid = ?', (uid,))
    found = cur.fetchone() is not None
    conn.close()
    return found

# ── تنظیمات لاگینگ ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ── راه‌اندازی ربات ───────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

forwarded_message_map = defaultdict(int)

# ── هندلر عمومی برای انصراف و بازگشت به منوی اصلی (اینجا منتقل شده) ──
@dp.message_handler(lambda m: m.text == "➡️ انصراف و بازگشت به منو اصلی", state="*")
async def cancel_and_return_to_main(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} pressed 'Cancel' in state {await state.get_state()}")
    if await state.get_state():
        await state.finish()
    await message.answer("به منوی اصلی بازگشتید.", reply_markup=main_keyboard)

# ── هندلرهای اصلی ─────────────────────────────────────────────────────

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer(
        "👋 سلام! به ربات خوش آمدید.\n\n"
        "این ربات به شما امکان می‌دهد تا با عضویت در کانال VVIP ما به بهترین سیگنال‌ها و آموزش‌ها دسترسی پیدا کنید.\n\n"
        "برای شروع، لطفاً از منوی زیر استفاده کنید:",
        reply_markup=main_keyboard
    )

@dp.message_handler(lambda m: m.text == "🎫 دریافت اشتراک VVIP")
async def process_vvip_choice(message: types.Message):
    choice_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    choice_keyboard.add(KeyboardButton("اشتراک رایگان (رفرال)"))
    choice_keyboard.add(KeyboardButton("اشتراک ماهیانه (پولی)"))
    choice_keyboard.add(KeyboardButton("➡️ انصراف و بازگشت به منو اصلی"))

    await message.answer("لطفاً نوع اشتراک مورد نظر خود را انتخاب کنید:",
                         reply_markup=choice_keyboard)

@dp.message_handler(lambda m: m.text == "اشتراک رایگان (رفرال)")
async def on_free_subscription(message: types.Message):
    await message.answer(content_data["free_intro"]["content"], reply_markup=free_exchange_keyboard)


@dp.message_handler(lambda m: m.text == "توبیت (Toobit)")
async def on_toobit_select(message: types.Message):
    await message.answer(content_data["free_toobit"]["content"], parse_mode=ParseMode.MARKDOWN)
    await FreeReferralState.waiting_for_uid.set()
    logging.info(f"User {message.from_user.id} set state to FreeReferralState.waiting_for_uid")


@dp.message_handler(state=FreeReferralState.waiting_for_uid)
async def process_uid(message: types.Message, state: FSMContext):
    logging.info(f"User {message.from_user.id} entered process_uid handler with text: {message.text}")
    uid_str = message.text.strip()
    user_id = message.from_user.id

    try:
        uid = int(uid_str)
        if not is_referral(uid):
            await message.answer("❌ UID شما معتبر نیست یا شرایط رفرالی را تکمیل نکرده‌اید. لطفاً دوباره بررسی کنید و UID صحیح را ارسال کنید.")
            return

        conn = get_db_conn()
        subscribed_at_timestamp = int(datetime.utcnow().timestamp())

        conn.execute(
            'INSERT OR REPLACE INTO users (user_id, plan_type, reference) VALUES (?, ?, ?)',
            (user_id, "free", str(uid))
        )
        conn.execute(
            "INSERT OR REPLACE INTO vvip_subscribers (user_id, plan_type, reference, subscribed_at) VALUES (?, ?, ?, ?)",
            (user_id, "free", str(uid), subscribed_at_timestamp)
        )
        conn.commit()
        conn.close()

        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
                expire_date=datetime.utcnow() + timedelta(hours=24)
            )
            await message.answer(
                f"🎉 تبریک! اشتراک رایگان شما فعال شد!\n\n"
                f"لینک عضویت در کانال خصوصی:\n{invite_link.invite_link}\n\n"
                f"⚠️ این لینک فقط برای یک بار استفاده و به مدت 24 ساعت معتبر است.",
                reply_markup=main_keyboard
            )
        except ChatAdminRequired:
            await message.answer(
                "❌ ربات برای ساخت لینک دعوت نیاز به دسترسی 'دعوت کاربران از طریق لینک' در کانال دارد. "
                "لطفاً به مدیر اطلاع دهید.",
                reply_markup=main_keyboard
            )
        except Exception as e:
            logging.error(f"Error creating invite link for user {user_id}: {e}")
            await message.answer(
                "❌ خطایی در ساخت لینک دعوت رخ داد. لطفاً با پشتیبانی تماس بگیرید.",
                reply_markup=main_keyboard
            )
        finally:
            await state.finish()

    except ValueError:
        await message.answer("❌ لطفا یک UID عددی و معتبر ارسال کنید.")


@dp.message_handler(lambda m: m.text == "اشتراک ماهیانه (پولی)")
async def on_paid_subscription(message: types.Message):
    await message.answer(content_data["paid_intro"]["content"], reply_markup=paid_method_keyboard)
    await PaidSubscriptionState.waiting_for_method.set()

@dp.message_handler(state=PaidSubscriptionState.waiting_for_method)
async def process_paid_method(message: types.Message, state: FSMContext):
    if message.text == "واریز از طریق شبکه TRC20":
        await message.answer(content_data["paid_trc20"]["content"], parse_mode=ParseMode.MARKDOWN)
        await PaidSubscriptionState.waiting_for_txid.set()
    elif message.text == "واریز از طریق شبکه BEP20":
        await message.answer(content_data["paid_bep20"]["content"], parse_mode=ParseMode.MARKDOWN)
        await PaidSubscriptionState.waiting_for_txid.set()
    elif message.text == "➡️ انصراف و بازگشت به منو اصلی":
        await message.answer("عملیات لغو شد.", reply_markup=main_keyboard)
        await state.finish()
    else:
        await message.answer("❌ روش پرداخت نامعتبر است. لطفاً از دکمه‌های زیر انتخاب کنید:", reply_markup=paid_method_keyboard)


@dp.message_handler(state=PaidSubscriptionState.waiting_for_txid)
async def on_txid(msg: types.Message, state: FSMContext):
    txid = msg.text.strip()
    user_id = msg.from_user.id

    if not txid.lower().startswith('txid-') and not (len(txid) >= 32 and len(txid) <= 64 and txid.isalnum()):
        await msg.answer(
            "❌ فرمت TXID نامعتبر است. لطفاً شناسه تراکنش کامل را وارد کنید.\n"
            "برای مثال: `TXID-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (یا فقط خود TXID را وارد کنید).",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await msg.answer(f"✅ TXID شما `{txid}` ثبت شد. پیام شما برای بررسی به مدیریت ارسال گردید.\n"
                     "لطفاً منتظر تأیید بمانید.", parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard)

    escaped_txid = html.escape(txid)
    escaped_username = html.escape(msg.from_user.username) if msg.from_user.username else str(msg.from_user.id)

    admin_message_text = (
        f"پیام TXID جدید از کاربر {user_id} (@{escaped_username}):\n"
        f"`{escaped_txid}`\n\n"
        f"برای تایید اشتراک 3 ماهه، به این پیام ریپلای کنید و بنویسید: `3 ماهه✅`"
    )
    for adm in ADMINS:
        try:
            sent_msg = await bot.send_message(
                chat_id=adm,
                text=admin_message_text,
                parse_mode=ParseMode.MARKDOWN
            )
            forwarded_message_map[sent_msg.message_id] = user_id
            logging.info(f"TXID from user {user_id} forwarded to admin {adm}. Message ID: {sent_msg.message_id}")
        except BotBlocked:
            logging.warning(f"Admin {adm} blocked the bot.")
        except ChatNotFound:
            logging.warning(f"Admin {adm} chat not found. Is the ID correct?")
        except UserDeactivated:
            logging.warning(f"Admin {adm} account is deactivated.")
        except Exception as e:
            logging.error(f"Error forwarding TXID from user {user_id} to admin {adm}: {e}")

    await state.finish()


@dp.message_handler(lambda m: m.text == "🔋 اشتراک من")
async def show_my_subscription(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT plan_type, subscribed_at FROM vvip_subscribers WHERE user_id = ?", (user_id,))
    subscriber_info = cursor.fetchone()
    conn.close()

    if not subscriber_info:
        await message.answer(
            "🤷‍♂️ شما در حال حاضر هیچ اشتراکی (رایگان یا پولی) ندارید.\n"
            "برای دریافت اشتراک، از دکمه \"🎫 دریافت اشتراک VVIP\" استفاده کنید.",
            parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard
        )
        return

    plan_type, subscribed_at_timestamp = subscriber_info

    if plan_type == "free":
        response_text = "🎉 وضعیت اشتراک شما: *رایگان (رفرالی)*\n\n" \
                        "این اشتراک *دائمی* است، به شرطی که شرایط تعیین شده (حفظ حداقل موجودی در صرافی توبیت) را رعایت کنید."
    elif plan_type == "paid":
        subscribed_at_dt = datetime.fromtimestamp(subscribed_at_timestamp)
        expiry_date = subscribed_at_dt + timedelta(days=90)
        remaining_seconds = (expiry_date - datetime.utcnow()).total_seconds()

        if remaining_seconds > 0:
            remaining_days = int(remaining_seconds // (24 * 3600))
            remaining_hours = int((remaining_seconds % (24 * 3600)) // 3600)
            remaining_minutes = int((remaining_seconds % 3600) // 60)

            response_text = f"💳 وضعیت اشتراک شما: *پولی*\n\n" \
                            f"نوع اشتراک: 3 ماهه\n" \
                            f"تاریخ شروع: {subscribed_at_dt.strftime('%Y/%m/%d %H:%M')}\n" \
                            f"تاریخ انقضا: {expiry_date.strftime('%Y/%m/%d %H:%M')}\n" \
                            f"زمان باقی‌مانده: *{remaining_days} روز، {remaining_hours} ساعت و {remaining_minutes} دقیقه*"
        else:
            response_text = "😔 وضعیت اشتراک شما: *پولی (منقضی شده)*\n\n" \
                            "اشتراک پولی شما به پایان رسیده است. برای دسترسی مجدد، لطفاً مجدداً اقدام به خرید اشتراک نمایید."
    else:
        response_text = "❓ وضعیت اشتراک شما نامشخص است. لطفاً با پشتیبانی تماس بگیرید."

    await message.answer(response_text, parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard)


@dp.message_handler(lambda m: m.from_user.id not in ADMINS, content_types=types.ContentTypes.ANY)
async def forward_to_admin(msg: types.Message):
    user_id = msg.from_user.id
    display_name = f"@{html.escape(msg.from_user.username)}" if msg.from_user.username else f"ID: {user_id}"

    for adm in ADMINS:
        try:
            sent = await bot.copy_message(
                chat_id=adm,
                from_chat_id=msg.chat.id,
                message_id=msg.message_id
            )
            forwarded_message_map[sent.message_id] = user_id
            logging.info(f"Message from user {user_id} forwarded to admin {adm}. Message ID: {sent.message_id}")
        except BotBlocked:
            logging.warning(f"Admin {adm} blocked the bot. Cannot forward message from {user_id}.")
        except ChatNotFound:
            logging.warning(f"Admin {adm} chat not found. Is the ID correct? Cannot forward message from {user_id}.")
        except UserDeactivated:
            logging.warning(f"Admin {adm} account is deactivated. Cannot forward message from {user_id}.")
        except Exception as e:
            logging.error(f"Error forwarding message from {user_id} to admin {adm}: {e}")
            fallback_text = f"📨 پیام از کاربر {display_name}:\n\n"
            if msg.text:
                fallback_text += html.escape(msg.text)
            elif msg.caption:
                fallback_text += f"(caption): {html.escape(msg.caption)}"
            else:
                fallback_text += "(نوع پیام پشتیبانی نمی‌شود)"
            try:
                sent_msg_fallback = await bot.send_message(
                    adm,
                    fallback_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                forwarded_message_map[sent_msg_fallback.message_id] = user_id
                logging.info(f"Fallback text message from {user_id} sent to admin {adm}. Message ID: {sent_msg_fallback.message_id}")
            except Exception as fallback_e:
                logging.error(f"Failed to send fallback message to admin {adm} from user {user_id}: {fallback_e}")

    await msg.answer("✅ پیام شما برای پشتیبانی ارسال شد. لطفاً منتظر پاسخ باشید.", reply_markup=main_keyboard)


@dp.message_handler(lambda m: m.from_user.id in ADMINS and m.reply_to_message, content_types=types.ContentTypes.ANY)
async def reply_from_admin(msg: types.Message):
    original_msg_id = msg.reply_to_message.message_id
    user_id = forwarded_message_map.get(original_msg_id)

    if not user_id:
        await msg.answer("❌ کاربر مربوط به این پیام یافت نشد.")
        return

    if msg.text and msg.text.strip() == "3 ماهه✅":
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT plan_type FROM vvip_subscribers WHERE user_id = ?", (user_id,))
        existing_subscription = cursor.fetchone()

        if existing_subscription:
            await msg.answer(f"⚠️ کاربر {user_id} از قبل اشتراک فعال دارد ({existing_subscription[0]}).")
            conn.close()
            return

        subscribed_at_timestamp = int(datetime.utcnow().timestamp())
        conn.execute(
            "INSERT OR REPLACE INTO vvip_subscribers (user_id, plan_type, reference, subscribed_at) VALUES (?, ?, ?, ?)",
            (user_id, "paid", "TXID_VERIFIED_BY_ADMIN", subscribed_at_timestamp)
        )
        conn.execute(
            'INSERT OR REPLACE INTO users (user_id, plan_type, reference) VALUES (?, ?, ?)',
            (user_id, "paid", "TXID_VERIFIED_BY_ADMIN")
        )
        conn.commit()
        conn.close()

        try:
            invite_link = await bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
                expire_date=datetime.utcnow() + timedelta(days=1)
            )
            await bot.send_message(user_id, f"🎉 اشتراک 3 ماهه شما فعال شد!\n\n"
                                             f"لینک عضویت در کانال خصوصی:\n{invite_link.invite_link}\n\n"
                                             f"⚠️ این لینک فقط برای یک بار استفاده و به مدت 24 ساعت معتبر است.",
                                   reply_markup=main_keyboard)
            await msg.answer(f"✅ اشتراک 3 ماهه برای کاربر {user_id} فعال شد و لینک ارسال گردید.")
            logging.info(f"Admin {msg.from_user.id} activated 3-month paid subscription for {user_id}.")

        except ChatAdminRequired:
            await msg.answer("❌ ربات برای ساخت لینک دعوت نیاز به دسترسی 'دعوت کاربران از طریق لینک' در کانال دارد.")
            logging.error(f"Bot lacks ChatAdminRequired permission to create invite link for {user_id}")
        except Exception as e:
            await msg.answer(f"❌ خطایی در ساخت یا ارسال لینک دعوت رخ داد: {e}")
            logging.error(f"Error creating/sending invite link for {user_id}: {e}")

    else:
        try:
            reply_text = html.escape(msg.text) if msg.text else ''
            reply_caption = html.escape(msg.caption) if msg.caption else ''

            if msg.text:
                await bot.send_message(user_id, f"📩 پاسخ پشتیبانی:\n\n{reply_text}", reply_markup=main_keyboard, parse_mode=ParseMode.MARKDOWN)
            elif msg.photo:
                await bot.send_photo(user_id, photo=msg.photo[-1].file_id, caption=f"📩 پاسخ پشتیبانی:\n\n{reply_caption}", reply_markup=main_keyboard, parse_mode=ParseMode.MARKDOWN)
            elif msg.document:
                await bot.send_document(user_id, document=msg.document.file_id, caption=f"📩 پاسخ پشتیبانی:\n\n{reply_caption}", reply_markup=main_keyboard, parse_mode=ParseMode.MARKDOWN)
            elif msg.sticker:
                await bot.send_sticker(user_id, sticker=msg.sticker.file_id, reply_markup=main_keyboard)
            elif msg.voice:
                await bot.send_voice(user_id, voice=msg.voice.file_id, caption=f"📩 پاسخ پشتیبانی:\n\n{reply_caption}", reply_markup=main_keyboard, parse_mode=ParseMode.MARKDOWN)
            elif msg.video:
                await bot.send_video(user_id, video=msg.video.file_id, caption=f"📩 پاسخ پشتیبانی:\n\n{reply_caption}", reply_markup=main_keyboard, parse_mode=ParseMode.MARKDOWN)
            else:
                await bot.send_message(user_id, "📩 پاسخ پشتیبانی (نوع پیام نامشخص، به پیام اصلی مراجعه کنید).", reply_markup=main_keyboard)

            await msg.answer("✅ پاسخ شما به کاربر ارسال شد.")
        except Exception as e:
            await msg.answer(f"❌ خطایی در ارسال پاسخ به کاربر رخ داد: {e}")
            logging.error(f"Error sending reply to user {user_id}: {e}")


# ── راه‌اندازی ربات ───────────────────────────────────────────────────
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)