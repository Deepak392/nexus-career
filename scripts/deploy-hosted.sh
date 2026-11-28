#!/usr/bin/env bash
set -euo pipefail

echo "=================================================================="
echo " Nexus Career — Hosted Environment Deployment & Update Pipeline"
echo "=================================================================="

# Supports two modes:
# 1. Cloud / Vercel + Hosted PostgreSQL (when HOSTED_PGHOST is set)
# 2. Containerized Full-Stack Hosting (Docker Compose)

if [ -n "${HOSTED_PGHOST:-}" ]; then
  echo "[Cloud Mode] Running migrations and demo seed against hosted PostgreSQL (${HOSTED_PGHOST})..."
  docker compose run --rm --no-deps \
    -e PGHOST="$HOSTED_PGHOST" \
    -e PGPORT="${HOSTED_PGPORT:-5432}" \
    -e PGUSER="${HOSTED_PGUSER:?Set HOSTED_PGUSER}" \
    -e PGPASSWORD="${HOSTED_PGPASSWORD:?Set HOSTED_PGPASSWORD}" \
    -e PGDATABASE="${HOSTED_PGDATABASE:-nexus_career}" \
    -e PGSSLMODE="${HOSTED_PGSSLMODE:-require}" \
    backend sh -c "python manage.py migrate --noinput && python manage.py seed_demo && python manage.py check"
else
  if [ ! -f .env ]; then
    cp .env.example .env
    echo "[Config] Created .env from .env.example"
  fi

  echo "[Deploy] Building and starting services (db, backend, frontend)..."
  docker compose up -d --build --wait --remove-orphans

  echo "[Migrate] Applying database migrations..."
  docker compose exec -T backend python manage.py migrate --noinput

  echo "[Seed] Ensuring user-research dataset is populated..."
  docker compose exec -T backend python manage.py seed_demo

  echo "[Check] Running Django production & system checks..."
  docker compose exec -T backend python manage.py check
fi

bash scripts/verify-hosted-availability.sh
