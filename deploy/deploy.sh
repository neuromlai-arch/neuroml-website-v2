#!/usr/bin/env bash
# Zero-downtime-ish deploy, run from the EC2 instance (either by hand as the
# `deploy` user, or over SSH from GitHub Actions — see
# .github/workflows/ci.yml's `deploy` job). Assumes deploy/setup.sh has
# already run once: the deploy user exists with Docker permissions,
# /opt/neuroml/.env.prod and deploy/.env are filled in, and this repo is
# cloned at /opt/neuroml/app.
#
# Usage:
#   /opt/neuroml/app/deploy/deploy.sh
#
# Every step is idempotent / safe to re-run — this is the same script for
# "first deploy ever" and "deploy #200".
set -euo pipefail

APP_DIR="/opt/neuroml/app"
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env"

log() { echo -e "\n\033[1;32m==> $*\033[0m"; }
fail() { echo -e "\033[1;31mFAILED: $*\033[0m" >&2; exit 1; }

cd "$APP_DIR" || fail "$APP_DIR doesn't exist — run deploy/setup.sh first"

[[ -f /opt/neuroml/.env.prod ]] || fail "/opt/neuroml/.env.prod is missing — fill it in from .env.prod.example first"
[[ -f deploy/.env ]] || fail "deploy/.env is missing — fill it in (POSTGRES_DB/USER/PASSWORD) first"

log "Pulling latest code (main)"
git fetch origin main
git reset --hard origin/main
COMMIT="$(git rev-parse --short HEAD)"
echo "    now at $COMMIT"

log "Building the image from the Dockerfile"
$COMPOSE build

log "Starting/ensuring the database is up"
$COMPOSE up -d db
# Compose's healthcheck (pg_isready, see docker-compose.prod.yml) covers
# this in `depends_on: condition: service_healthy` for web/worker below, but
# migrations run via a one-off `run` that bypasses depends_on, so wait here
# explicitly instead of racing a cold Postgres container on first deploy.
for _ in $(seq 1 30); do
  $COMPOSE exec -T db pg_isready -U "$(grep -oP '(?<=POSTGRES_USER=).*' deploy/.env)" >/dev/null 2>&1 && break
  sleep 2
done

log "Running migrations"
$COMPOSE run --rm web python manage.py migrate --noinput

log "Collecting static files (into the bind-mounted /opt/neuroml/staticfiles, which nginx serves directly)"
$COMPOSE run --rm web python manage.py collectstatic --noinput

log "Running bootstrap_superuser (idempotent — no-ops if the user already exists)"
$COMPOSE run --rm web python manage.py bootstrap_superuser

log "Restarting web and worker with the new image (zero-downtime: db is untouched, old containers stay up until the new ones pass their healthcheck)"
$COMPOSE up -d --build --no-deps web worker

log "Clearing the Django cache"
# LocMemCache (this project's default — see config/settings/base.py, no
# CACHES override) is per-process, so it's already empty in the freshly
# started containers above; this exists so the step is a real, verified
# clear (not just "restart implies it's probably fine") and so it keeps
# working unchanged if this ever moves to a shared cache backend
# (Memcached/Redis) that *would* survive the restart.
$COMPOSE exec -T web python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('cache cleared')"

log "Pruning old, now-unused images (keeps disk from filling up over many deploys)"
docker image prune -f >/dev/null

log "Health check"
sleep 2
# SECURE_PROXY_SSL_HEADER (config/settings/prod.py) makes Django trust
# X-Forwarded-Proto for request.is_secure() — nginx always sets it (see
# deploy/nginx.conf), but curling gunicorn directly here doesn't, so
# without it SECURE_SSL_REDIRECT turns every check into a 301 instead of
# the real status.
HEALTH="$(curl -s -o /dev/null -w '%{http_code}' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/healthz/)"
WORKER_HEALTH="$(curl -s -o /dev/null -w '%{http_code}' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/healthz/worker/)"
echo "    /healthz/         -> $HEALTH"
echo "    /healthz/worker/  -> $WORKER_HEALTH (503 here just after deploy is expected — the"
echo "                          heartbeat schedule needs a few minutes to check in; re-check"
echo "                          with: curl http://127.0.0.1:8000/healthz/worker/)"

if [[ "$HEALTH" != "200" ]]; then
  fail "web health check did not return 200 — check: docker compose -f deploy/docker-compose.prod.yml logs web"
fi

log "Deploy of $COMMIT complete."
