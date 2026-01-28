FROM python:3.11-slim

# evita stdout buffered
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY upload_screenshots.py .

CMD ["python", "bot.py"]

#docker compose build {discord-bot / upload-audio}
#docker compose up discord-bot / upload-audio
#@tasks.loop(time=time(hour=21, minute=31, second=0, tzinfo=TZ))
