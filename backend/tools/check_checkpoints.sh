#!/usr/bin/env bash
set -euo pipefail
JOB_ID="${1:-}"
if [[ -z "${JOB_ID}" ]]; then
  echo "Uso: ./check_checkpoints.sh <job_id>"
  exit 1
fi
BASE="$(cd "$(dirname "$0")/../.." && pwd)"
DIR="${BASE}/data/jobs/${JOB_ID}/checkpoints"
echo "Checkpoint dir: ${DIR}"
ls -la "${DIR}" || true
