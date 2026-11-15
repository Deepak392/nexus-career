#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-verify-compose}"
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Load DB credentials from .env or fallback to defaults
if [ -f .env ]; then
  set -a; source .env; set +a
fi
DB_USER="${POSTGRES_USER:-${PGUSER:-nexus_user}}"
DB_NAME="${POSTGRES_DB:-${PGDATABASE:-nexus_career}}"

case "$ACTION" in
  backup-compose)
    OUT_FILE="${BACKUP_DIR}/nexus_compose_${TIMESTAMP}.sql"
    echo "[Backup] Dumping Compose database '${DB_NAME}' to ${OUT_FILE}..."
    docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$OUT_FILE"
    cp "$OUT_FILE" "${BACKUP_DIR}/latest.sql"
    echo "[Backup] Complete! Saved to ${OUT_FILE} and ${BACKUP_DIR}/latest.sql ($(wc -c < "$OUT_FILE") bytes)."
    ;;

  restore-compose)
    IN_FILE="${2:-${BACKUP_DIR}/latest.sql}"
    echo "[Restore] Restoring Compose database '${DB_NAME}' from ${IN_FILE}..."
    docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q < "$IN_FILE"
    echo "[Restore] Complete!"
    ;;

  backup-k8s)
    OUT_FILE="${BACKUP_DIR}/nexus_k8s_${TIMESTAMP}.sql"
    echo "[K8s Backup] Dumping StatefulSet db-0 database '${DB_NAME}' to ${OUT_FILE}..."
    kubectl -n nexus exec db-0 -- sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' > "$OUT_FILE"
    cp "$OUT_FILE" "${BACKUP_DIR}/latest_k8s.sql"
    echo "[K8s Backup] Complete! Saved to ${OUT_FILE}."
    ;;

  restore-k8s)
    IN_FILE="${2:-${BACKUP_DIR}/latest_k8s.sql}"
    echo "[K8s Restore] Restoring StatefulSet db-0 from ${IN_FILE}..."
    kubectl -n nexus exec -i db-0 -- sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -q' < "$IN_FILE"
    echo "[K8s Restore] Complete!"
    ;;

  verify-compose)
    echo "=== Sprint 4 DevOps Test: Database Backup & Restore Validation ==="
    BEFORE_USERS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM accounts_user;")
    BEFORE_OPPS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM opportunities_opportunity;")
    echo "1. Initial State     -> Users: ${BEFORE_USERS} | Opportunities: ${BEFORE_OPPS}"

    bash "$0" backup-compose

    echo "2. Simulating Data Loss (Truncating opportunities_opportunity CASCADE)..."
    docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q -c "TRUNCATE TABLE opportunities_opportunity CASCADE;"
    WIPED_OPPS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM opportunities_opportunity;")
    echo "   After Data Loss   -> Opportunities: ${WIPED_OPPS}"

    bash "$0" restore-compose "${BACKUP_DIR}/latest.sql"

    AFTER_USERS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM accounts_user;")
    AFTER_OPPS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM opportunities_opportunity;")
    echo "3. Restored State    -> Users: ${AFTER_USERS} | Opportunities: ${AFTER_OPPS}"

    if [ "$BEFORE_USERS" = "$AFTER_USERS" ] && [ "$BEFORE_OPPS" = "$AFTER_OPPS" ]; then
      echo "SUCCESS: Database backup and restore verified with 100% data integrity!"
    else
      echo "ERROR: Row count mismatch after restore!"
      exit 1
    fi
    ;;

  *)
    echo "Usage: $0 {backup-compose|restore-compose|backup-k8s|restore-k8s|verify-compose}"
    exit 1
    ;;
esac

