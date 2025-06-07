
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from handlers import router
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

async def main():
    bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
