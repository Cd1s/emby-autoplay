#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/emby-autoplay"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="$REPO_DIR/src"

if ! command -v systemd-run >/dev/null 2>&1; then
  echo "systemd-run not found. This project requires systemd." >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR/logs"
cp "$SRC_DIR/emby_keepalive.py" "$INSTALL_DIR/"
cp "$SRC_DIR/emby_keepalive_config.py" "$INSTALL_DIR/"
cp "$SRC_DIR/emby_keepalive_systemd_scheduler.py" "$INSTALL_DIR/"
cp "$SRC_DIR/emby_keepalive_systemd_runner.sh" "$INSTALL_DIR/"
cp "$SRC_DIR/run_emby_keepalive.sh" "$INSTALL_DIR/"
cp "$SRC_DIR/interactive_install.py" "$INSTALL_DIR/"
cp "$SRC_DIR/embyautoplay" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/emby_keepalive.py" "$INSTALL_DIR/emby_keepalive_systemd_scheduler.py" "$INSTALL_DIR/emby_keepalive_systemd_runner.sh" "$INSTALL_DIR/run_emby_keepalive.sh" "$INSTALL_DIR/interactive_install.py" "$INSTALL_DIR/embyautoplay"
ln -sf "$INSTALL_DIR/embyautoplay" /usr/local/bin/embyautoplay

if [[ ! -f "$INSTALL_DIR/emby_keepalive.env" ]]; then
  cp "$SRC_DIR/emby_keepalive.env.example" "$INSTALL_DIR/emby_keepalive.env"
  chmod 600 "$INSTALL_DIR/emby_keepalive.env"
fi

python3 - <<'PY'
import os, json, datetime
base='/opt/emby-autoplay'
path=os.path.join(base,'emby_keepalive_state.json')
if not os.path.exists(path):
    now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    state={
        'enabled': True,
        'last_run_at': None,
        'last_status': None,
        'last_duration_seconds': None,
        'next_run_at': None,
        'next_duration_seconds': None,
        'next_unit_name': None,
        'created_at': now,
        'updated_at': now,
    }
    with open(path,'w',encoding='utf-8') as f:
        json.dump(state,f,ensure_ascii=False,indent=2)
PY

echo
echo "Installed to: $INSTALL_DIR"
echo "Config file: $INSTALL_DIR/emby_keepalive.env"
echo "Play log:    $INSTALL_DIR/logs/emby_keepalive.log"
echo "Sched log:   $INSTALL_DIR/logs/emby_keepalive_scheduler.log"
echo "Command:     embyautoplay"
echo
EMBY_AUTOPLAY_HOME="$INSTALL_DIR" /usr/bin/python3 "$INSTALL_DIR/interactive_install.py"
