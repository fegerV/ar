#!/bin/bash
set -euo pipefail

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_ROOT="${PROJECT_ROOT}/backups"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
CONFIG_FILES=(
  "vertex-ar/.env"
  "vertex-ar/.env.production"
  ".env"
  "nginx.conf"
  "docker-compose.yml"
  "Dockerfile.app"
)

mkdir -p "${BACKUP_DIR}"
echo "[INFO] Starting backup: ${TIMESTAMP}"

database_file="${PROJECT_ROOT}/vertex-ar/app_data.db"
if [[ -f "${database_file}" ]]; then
  mkdir -p "${BACKUP_DIR}/database"
  cp "${database_file}" "${BACKUP_DIR}/database/app_data.db"
  echo "[INFO] Database backup created"
else
  echo "[WARN] Database file not found: ${database_file}"
fi

storage_dir="${PROJECT_ROOT}/vertex-ar/storage"
if [[ -d "${storage_dir}" ]]; then
  tar -czf "${BACKUP_DIR}/storage.tar.gz" -C "${PROJECT_ROOT}/vertex-ar" storage
  echo "[INFO] Storage archive created"
else
  echo "[WARN] Storage directory not found: ${storage_dir}"
fi

config_temp_dir="${BACKUP_DIR}/config_files"
config_found=false
for config_path in "${CONFIG_FILES[@]}"; do
  full_path="${PROJECT_ROOT}/${config_path}"
  if [[ -f "${full_path}" ]]; then
    mkdir -p "${config_temp_dir}"
    cp "${full_path}" "${config_temp_dir}/"
    config_found=true
  fi
done

if [[ "${config_found}" == true ]]; then
  tar -czf "${BACKUP_DIR}/config.tar.gz" -C "${config_temp_dir}" .
  rm -rf "${config_temp_dir}"
  echo "[INFO] Configuration archive created"
else
  echo "[INFO] No configuration files found for backup"
fi

cat <<EOF > "${BACKUP_DIR}/backup.json"
{
  "created_at": "${TIMESTAMP}",
  "database_backed_up": $( [[ -f "${BACKUP_DIR}/database/app_data.db" ]] && echo "true" || echo "false" ),
  "storage_archived": $( [[ -f "${BACKUP_DIR}/storage.tar.gz" ]] && echo "true" || echo "false" ),
  "config_archived": $( [[ -f "${BACKUP_DIR}/config.tar.gz" ]] && echo "true" || echo "false" )
}
EOF

echo "[INFO] Applying retention policy: keep last ${RETENTION_DAYS} day(s)"
find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +"${RETENTION_DAYS}" -exec rm -rf {} +

offsite_target="${S3_BACKUP_BUCKET:-}"
if [[ -n "${offsite_target}" ]] && command -v aws >/dev/null 2>&1; then
  echo "[INFO] Syncing backup to S3 bucket: ${offsite_target}"
  aws s3 sync "${BACKUP_DIR}" "s3://${offsite_target}/${TIMESTAMP}" --delete
fi

echo "[INFO] Backup completed: ${BACKUP_DIR}"
