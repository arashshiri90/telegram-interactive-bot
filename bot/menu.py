# bot/menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# منوی اصلی شامل گزینه‌های اصلی ربات
main_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
# ردیف اول
main_keyboard.row(
    KeyboardButton("🎫 دریافت اشتراک VVIP"),
    KeyboardButton("🔋 اشتراک من")
)
# ردیف دوم
main_keyboard.add(
    KeyboardButton("🧮 تکنیک های مدیریت ریسک اختصاصی")
)
# ردیف سوم
main_keyboard.add(
    KeyboardButton("⚙️ اکسپرت فوق حرفه ای مدیریت ریسک")
)
# ردیف چهارم
main_keyboard.row(
    KeyboardButton("📲 آموزش ثبتنام در بروکر"),
    KeyboardButton("🎁 آفر و بونوس اختصاصی بروکر")
)
# ردیف پنجم
main_keyboard.add(
    KeyboardButton("📉 استراتژی و ستاپ های معاملاتی")
)

# کیبورد برای انتخاب صرافی در حالت رایگان (رفرال)
free_exchange_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
free_exchange_keyboard.add(
    KeyboardButton("توبیت (Toobit)")
)
free_exchange_keyboard.add(
    KeyboardButton("➡️ انصراف و بازگشت به منو اصلی")
)

# کیبورد برای انتخاب روش پرداخت در حالت پولی
paid_method_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
paid_method_keyboard.add(
    KeyboardButton("واریز از طریق شبکه TRC20"),
    KeyboardButton("واریز از طریق شبکه BEP20")
)
paid_method_keyboard.add(
    KeyboardButton("➡️ انصراف و بازگشت به منو اصلی")
)