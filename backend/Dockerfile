# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies:
#   libpq-dev/gcc      -> psycopg build
#   libgeos-dev/proj   -> GeoAlchemy2/PostGIS client libs
#   libpango/libcairo  -> WeasyPrint PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgeos-dev \
    proj-bin \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .



    CMD curl -f http://localhost:8005/health/live || exit 1


# Dynamic port configuration matching Render's runtime env
EXPOSE 10000

# Start app binding dynamically to Render's system port
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:$PORT"]
