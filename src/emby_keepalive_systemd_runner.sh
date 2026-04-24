#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${EMBY_AUTOPLAY_HOME:-/opt/emby-autoplay}"
STATE_PATH="$BASE_DIR/emby_keepalive_state.json"
SCHEDULER="$BASE_DIR/emby_keepalive_systemd_scheduler.py"
LOG_FILE="$BASE_DIR/logs/emby_keepalive_scheduler.log"
RUNNER="$BASE_DIR/run_emby_keepalive.sh"

mkdir -p "$(dirname "$LOG_FILE")"

set_run_status() {
  local run_status="$1"
  python3 - "$run_status" <<'PY'
import datetime
import json
import os
import sys

run_status = sys.argv[1]
base = os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay')
path = os.path.join(base, 'emby_keepalive_state.json')
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
state = {}
if os.path.exists(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        state = {}

state['last_status'] = run_status
if run_status in ('success', 'failed'):
    state['last_run_at'] = now
    state['last_duration_seconds'] = state.get('next_duration_seconds')
state['updated_at'] = now

os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path + '.tmp', 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
os.replace(path + '.tmp', path)
PY
}

{
  set_run_status running
  echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') SYSTEMD due run start ====="
  if "$RUNNER"; then
    status=0
    run_status=success
  else
    status=$?
    run_status=failed
  fi
  echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') SYSTEMD due run end status=$status ====="
  set_run_status "$run_status"
  python3 "$SCHEDULER" || echo "WARNING: scheduler exited non-zero (see scheduler log)"
  exit $status
} >> "$LOG_FILE" 2>&1
