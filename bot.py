import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from handlers import router
from dotenv import load_dotenv
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# سرور ساختگی برای Render
def dummy_http_server():
    PORT = 8080
    server = HTTPServer(("0.0.0.0", PORT), SimpleHTTPRequestHandler)
    print(f"Dummy server running on port {PORT}")
    server.serve_forever()

async def main():
    bot = Bot(token=TOKEN, parse_mode=ParseMode.MARKDOWN)
    await bot.delete_webhook(drop_pending_updates=True)

    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # اجرای سرور ساختگی در یک Thread جدا
    threading.Thread(target=dummy_http_server, daemon=True).start()

    # اجرای ربات Aiogram
    asyncio.run(main())
