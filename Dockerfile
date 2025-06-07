FROM python:3.10

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080  # پورت ساختگی برای ساکت کردن Render

CMD ["python", "main.py"]
