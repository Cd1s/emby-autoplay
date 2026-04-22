#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${EMBY_AUTOPLAY_HOME:-/opt/emby-autoplay}"
STATE_PATH="$BASE_DIR/emby_keepalive_state.json"
SCHEDULER="$BASE_DIR/emby_keepalive_systemd_scheduler.py"
LOG_FILE="$BASE_DIR/logs/emby_keepalive_scheduler.log"
RUNNER="$BASE_DIR/run_emby_keepalive.sh"

python3 - <<'PY'
import json, os, datetime
base = os.environ.get('EMBY_AUTOPLAY_HOME', '/opt/emby-autoplay')
path = os.path.join(base, 'emby_keepalive_state.json')
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
state = {}
if os.path.exists(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        state = {}
state['last_status'] = 'running'
state['updated_at'] = now
with open(path + '.tmp', 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
os.replace(path + '.tmp', path)
PY

{
  echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') SYSTEMD due run start ====="
  "$RUNNER" && status=0 || status=$?
  echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') SYSTEMD due run end status=$status ====="
  python3 "$SCHEDULER"
  exit $status
} >> "$LOG_FILE" 2>&1
