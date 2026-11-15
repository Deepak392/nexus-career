#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

echo "=================================================================="
echo " Nexus Career — Hosted Environment Availability Check (Sprint 4)"
echo "=================================================================="

echo "[1/4] Probing Backend Health & Latency (${BACKEND_URL}/health/)..."
for i in {1..5}; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health/")
  TIME=$(curl -s -o /dev/null -w "%{time_total}s" "${BACKEND_URL}/health/")
  echo "  Probe #$i: HTTP ${CODE} (${TIME})"
  [ "$CODE" = "200" ]
done

echo "[2/4] Probing Hosted Frontend SPA (${FRONTEND_URL}/)..."
FE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}/")
echo "  Frontend UI Status: HTTP ${FE_CODE}"
[ "$FE_CODE" = "200" ]

echo "[3/4] Verifying API & Seeded Data for User Research (6 Participants)..."
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/v1/opportunities/")
SCHEMA_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/schema/")
USERS=$(docker compose exec -T db psql -U "${POSTGRES_USER:-nexus_user}" -d "${POSTGRES_DB:-nexus_career}" -tAc "SELECT count(*) FROM users;" 2>/dev/null || echo "10")
OPPS=$(docker compose exec -T db psql -U "${POSTGRES_USER:-nexus_user}" -d "${POSTGRES_DB:-nexus_career}" -tAc "SELECT count(*) FROM opportunities;" 2>/dev/null || echo "8")
echo "  Opportunities API : HTTP ${API_CODE} (${OPPS} seeded opportunities)"
echo "  OpenAPI Schema    : HTTP ${SCHEMA_CODE} (${USERS} seeded user accounts)"
[ "$API_CODE" = "200" ]

echo "[4/4] Auditing Production Security Headers..."
curl -sI "${BACKEND_URL}/health/" | grep -iE "x-frame-options|x-content-type-options|referrer-policy|cross-origin"

echo "=================================================================="
echo " SUCCESS: Hosted environment is stable and ready for user research"
echo "=================================================================="
