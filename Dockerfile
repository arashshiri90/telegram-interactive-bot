FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# پورت ساختگی برای ساکت کردن Render
EXPOSE 8080

CMD ["python", "bot.py"]
