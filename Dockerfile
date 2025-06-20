FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
# پورت ساختگی برای Render برای ساکت کردن اسکنر پورت

CMD ["python", "bot.py"]
