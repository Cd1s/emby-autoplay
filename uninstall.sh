#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/emby-autoplay"
STATE_FILE="$INSTALL_DIR/emby_keepalive_state.json"

if [[ -f "$STATE_FILE" ]]; then
  unit_name=$(python3 - <<'PY'
import json, os
path='/opt/emby-autoplay/emby_keepalive_state.json'
if os.path.exists(path):
    with open(path,'r',encoding='utf-8') as f:
        state=json.load(f)
    print(state.get('next_unit_name') or '')
PY
)
  if [[ -n "$unit_name" ]]; then
    systemctl stop "$unit_name.timer" "$unit_name.service" 2>/dev/null || true
    systemctl reset-failed "$unit_name.timer" "$unit_name.service" 2>/dev/null || true
  fi
fi

rm -rf "$INSTALL_DIR"
echo "Removed $INSTALL_DIR"
