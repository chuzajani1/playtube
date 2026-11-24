FROM python:3.12-slim

# ffmpeg: format merge / MP3 / 3GP conversion ke liye lazmi
# aria2: tez parallel download ke liye (speed optimization)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg aria2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY playtube_website_v2_chuza.py .

ENV PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["sh", "-c", "gunicorn --workers 1 --threads 8 --timeout 300 --bind 0.0.0.0:$PORT playtube_website_v2_chuza:app"]
