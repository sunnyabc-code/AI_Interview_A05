FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120

ENV FFMPEG_BINARY=/usr/bin/ffmpeg

WORKDIR /app

# ffmpeg is required to convert browser-recorded audio (webm/opus) to wav in Docker.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies via Tsinghua mirror for better stability.
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip install -r /tmp/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn \
    && pip install gunicorn -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

COPY backend /app

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && gunicorn AI_Interview.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
