#!/usr/bin/env bash
set -euo pipefail

echo "=================================================================="
echo " Nexus Career — Hosted Environment Deployment & Update Pipeline"
echo "=================================================================="

# 1. Ensure .env configuration is present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "[Config] Created .env from .env.example"
fi

# 2. Build and deploy updated containers with zero-orphan cleanup
echo "[Deploy] Building and starting services (db, backend, frontend)..."
docker compose up -d --build --remove-orphans

# 3. Apply approved database migrations and ensure demo/research dataset is seeded
echo "[Migrate] Applying database migrations..."
docker compose exec -T backend python manage.py migrate --noinput

echo "[Seed] Ensuring user-research dataset is populated..."
docker compose exec -T backend python manage.py seed_demo

# 4. Run Django system check and live availability verification
echo "[Check] Running Django production & system checks..."
docker compose exec -T backend python manage.py check

bash scripts/verify-hosted-availability.sh
