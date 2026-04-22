#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${EMBY_AUTOPLAY_HOME:-/opt/emby-autoplay}"
ENV_FILE="$BASE_DIR/emby_keepalive.env"
LOG_DIR="$BASE_DIR/logs"
LOG_FILE="$LOG_DIR/emby_keepalive.log"

mkdir -p "$LOG_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"
EMBY_PLAY_SECONDS="${EMBY_PLAY_SECONDS:-${EMBY_PLAY_SECONDS_DEFAULT:-300}}"
export EMBY_AUTOPLAY_HOME="$BASE_DIR"
export EMBY_URL EMBY_USERNAME EMBY_PASSWORD EMBY_PLAY_SECONDS EMBY_DEVICE_ID EMBY_CLIENT_NAME EMBY_CLIENT_VERSION EMBY_VERIFY_SSL EMBY_TIMEOUT

{
  echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') START emby_keepalive ====="
  python3 "$BASE_DIR/emby_keepalive.py" && status=0 || status=$?
  echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') END emby_keepalive status=$status ====="
  exit $status
} >> "$LOG_FILE" 2>&1
