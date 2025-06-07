
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards import main_menu, submenu

router = Router()

@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "**به ربات خوش اومدی!**\n\nبرای شروع یکی از دکمه‌های زیر رو انتخاب کن:",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "option1")
async def handle_option1(callback: CallbackQuery):
    await callback.message.edit_text(
        "_زیرمنوی گزینه اول_:",
        reply_markup=submenu("option1")
    )

@router.callback_query(F.data == "option2")
async def handle_option2(callback: CallbackQuery):
    await callback.message.edit_text(
        "`شما گزینه دوم رو انتخاب کردید.`",
        reply_markup=submenu("option2")
    )

@router.callback_query(F.data.startswith("back"))
async def handle_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "**بازگشت به منوی اصلی:**",
        reply_markup=main_menu()
    )
