
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔹 گزینه اول", callback_data="option1")
    builder.button(text="🔸 گزینه دوم", callback_data="option2")
    return builder.as_markup()

def submenu(prefix: str):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ زیرگزینه ۱", callback_data=f"{prefix}_sub1")
    builder.button(text="✅ زیرگزینه ۲", callback_data=f"{prefix}_sub2")
    builder.button(text="⬅️ بازگشت", callback_data="back")
    return builder.as_markup()
