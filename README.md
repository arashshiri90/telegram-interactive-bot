docker rm -f vip-bot
docker build -t aronsignals2/vip-bot:latest .
docker run -d --name vip-bot -p 5000:5000 --env-file .env aronsignals2/vip-bot:latest

docker run -d --name vip-bot -p 5000:5000 --env-file .env -v "${PWD.Path}/db:/app/db" aronsignals2/vip-bot:latest




# VIP Bot Project

## ساختار پروژه
- `bot/`: کد ربات تلگرام
- `config/`: تنظیمات قابل ویرایش
- `db/`: دیتابیس SQLite
- `panel/`: پنل مدیریت تحت وب (Flask)
- `Dockerfile`, `.env`, `README.md`

## راه‌اندازی
1. ساخت داکر ایمیج:
   ```
   docker build -t vip_bot .
   ```
2. اجرای کانتینر:
   ```
   docker run -d -p 5000:5000 vip_bot
   ```

## توضیحات
- ربات با aiogram ساخته شده.
- پنل با Flask ساده پیاده‌سازی شده.
- تنظیمات دکمه‌ها و پیام‌ها در `config/settings.json`.
