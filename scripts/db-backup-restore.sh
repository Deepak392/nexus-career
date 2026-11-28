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

  backup-hosted)
    OUT_FILE="${BACKUP_DIR}/nexus_hosted_${TIMESTAMP}.sql"
    echo "[Hosted Backup] Dumping hosted PostgreSQL database '${DB_NAME}' on ${PGHOST:-localhost} to ${OUT_FILE}..."
    docker compose run --rm --no-deps -T \
      -e PGHOST="${PGHOST:?Set PGHOST for hosted backup}" \
      -e PGPORT="${PGPORT:-5432}" \
      -e PGUSER="$DB_USER" \
      -e PGPASSWORD="${PGPASSWORD:?Set PGPASSWORD for hosted backup}" \
      -e PGDATABASE="$DB_NAME" \
      -e PGSSLMODE="${PGSSLMODE:-require}" \
      db pg_dump -h "$PGHOST" -p "${PGPORT:-5432}" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$OUT_FILE"
    cp "$OUT_FILE" "${BACKUP_DIR}/latest_hosted.sql"
    echo "[Hosted Backup] Complete! Saved to ${OUT_FILE}."
    ;;

  restore-hosted)
    IN_FILE="${2:-${BACKUP_DIR}/latest_hosted.sql}"
    echo "[Hosted Restore] Restoring hosted PostgreSQL database '${DB_NAME}' on ${PGHOST:-localhost} from ${IN_FILE}..."
    docker compose run --rm --no-deps -T \
      -e PGHOST="${PGHOST:?Set PGHOST for hosted restore}" \
      -e PGPORT="${PGPORT:-5432}" \
      -e PGUSER="$DB_USER" \
      -e PGPASSWORD="${PGPASSWORD:?Set PGPASSWORD for hosted restore}" \
      -e PGDATABASE="$DB_NAME" \
      -e PGSSLMODE="${PGSSLMODE:-require}" \
      db psql -h "$PGHOST" -p "${PGPORT:-5432}" -U "$DB_USER" -d "$DB_NAME" -q < "$IN_FILE"
    echo "[Hosted Restore] Complete!"
    ;;

  verify-compose)
    echo "=== Sprint 4 DevOps Test: Database Backup & Restore Validation ==="
    BEFORE_USERS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM users;")
    BEFORE_OPPS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM opportunities;")
    echo "1. Initial State     -> Users: ${BEFORE_USERS} | Opportunities: ${BEFORE_OPPS}"

    bash "$0" backup-compose

    echo "2. Simulating Data Loss (Truncating opportunities CASCADE)..."
    docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q -c "TRUNCATE TABLE opportunities CASCADE;"
    WIPED_OPPS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM opportunities;")
    echo "   After Data Loss   -> Opportunities: ${WIPED_OPPS}"

    bash "$0" restore-compose "${BACKUP_DIR}/latest.sql"

    AFTER_USERS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM users;")
    AFTER_OPPS=$(docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM opportunities;")
    echo "3. Restored State    -> Users: ${AFTER_USERS} | Opportunities: ${AFTER_OPPS}"

    if [ "$BEFORE_USERS" = "$AFTER_USERS" ] && [ "$BEFORE_OPPS" = "$AFTER_OPPS" ]; then
      echo "SUCCESS: Database backup and restore verified with 100% data integrity!"
    else
      echo "ERROR: Row count mismatch after restore!"
      exit 1
    fi
    ;;

  *)
    echo "Usage: $0 {backup-compose|restore-compose|backup-hosted|restore-hosted|verify-compose}"
    exit 1
    ;;
esac
