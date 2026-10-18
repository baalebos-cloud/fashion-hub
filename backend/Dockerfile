# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8005 \
    WEB_CONCURRENCY=2
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libgeos-c1v5 proj-bin \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
COPY requirements.txt .
RUN pip install --require-hashes -r requirements.txt
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c 'import os, urllib.request; urllib.request.urlopen("http://127.0.0.1:" + os.environ["PORT"] + "/health/live", timeout=3)'
CMD ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers ${WEB_CONCURRENCY} --bind 0.0.0.0:${PORT} --access-logfile - --error-logfile -"]
