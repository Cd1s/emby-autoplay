#!/usr/bin/env bash
set -euo pipefail

REPO_RAW_BASE="https://raw.githubusercontent.com/Cd1s/emby-autoplay/main"
INSTALL_DIR="/opt/emby-autoplay"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

fetch() {
  local url="$1"
  local out="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$out"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$out" "$url"
  else
    echo "Need curl or wget" >&2
    exit 1
  fi
}

need_cmd bash
need_cmd python3
need_cmd systemd-run

mkdir -p "$TMP_DIR/src"
fetch "$REPO_RAW_BASE/install.sh" "$TMP_DIR/install.sh"
fetch "$REPO_RAW_BASE/src/emby_keepalive.py" "$TMP_DIR/src/emby_keepalive.py"
fetch "$REPO_RAW_BASE/src/emby_keepalive_config.py" "$TMP_DIR/src/emby_keepalive_config.py"
fetch "$REPO_RAW_BASE/src/emby_keepalive_systemd_scheduler.py" "$TMP_DIR/src/emby_keepalive_systemd_scheduler.py"
fetch "$REPO_RAW_BASE/src/emby_keepalive_systemd_runner.sh" "$TMP_DIR/src/emby_keepalive_systemd_runner.sh"
fetch "$REPO_RAW_BASE/src/run_emby_keepalive.sh" "$TMP_DIR/src/run_emby_keepalive.sh"
fetch "$REPO_RAW_BASE/src/interactive_install.py" "$TMP_DIR/src/interactive_install.py"
fetch "$REPO_RAW_BASE/src/embyautoplay" "$TMP_DIR/src/embyautoplay"
fetch "$REPO_RAW_BASE/src/emby_keepalive.env.example" "$TMP_DIR/src/emby_keepalive.env.example"
chmod +x "$TMP_DIR/install.sh"

cd "$TMP_DIR"
if [[ -t 0 ]]; then
  ./install.sh
elif [[ -r /dev/tty ]]; then
  ./install.sh < /dev/tty
else
  echo "No interactive TTY available. Please run in a real terminal." >&2
  exit 1
fi

echo
echo "One-line install complete."
echo "Edit config: $INSTALL_DIR/emby_keepalive.env"
