# syntax=docker/dockerfile:1

# ---- Stage 1: build the Tailwind CSS bundle --------------------------------
# Needs every app's templates/ dir present (tailwind.config.js scans
# ./*/templates/**/*.html), so it copies the whole tree rather than
# cherry-picking paths.
FROM node:20-slim AS css-builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build:css

# ---- Stage 2: Python dependencies ------------------------------------------
FROM python:3.12-slim AS python-deps
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Stage 3: runtime -------------------------------------------------------
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=python-deps /install /usr/local
COPY . .
COPY --from=css-builder /app/static/css/dist/main.css ./static/css/dist/main.css

ENV DJANGO_SETTINGS_MODULE=config.settings.prod \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# collectstatic only touches the filesystem, but Django still evaluates
# DATABASES/SECRET_KEY at settings-import time — these placeholders are
# for the build step only and are never used to serve traffic.
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    AWS_STORAGE_BUCKET_NAME=build \
    AWS_S3_ENDPOINT_URL=https://build.example.com \
    AWS_S3_REGION_NAME=build \
    AWS_ACCESS_KEY_ID=build \
    AWS_SECRET_ACCESS_KEY=build \
    EMAIL_HOST=build \
    python manage.py collectstatic --noinput

RUN mkdir -p /app/media && chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
