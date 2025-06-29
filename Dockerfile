FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir \
    aiogram==2.25.1 \
    flask \
    gunicorn \
    python-dotenv \
    requests

EXPOSE 5000

# اطمینان از وجود پوشه db - این مسیر درست است.
RUN mkdir -p /app/db

# تغییر بسیار مهم: حذف فایل دیتابیس موجود و سپس مقداردهی اولیه
CMD ["bash", "-c", \
    "echo 'Starting database initialization...' && rm -f /app/db/database.sqlite && python init_db.py && echo 'Database initialized. Starting other services...' && python update_referrals.py & python monitor_vvip.py & python -m bot.main & gunicorn --bind 0.0.0.0:5000 panel.app:app"]