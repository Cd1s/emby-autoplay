#!/usr/bin/env bash
set -euo pipefail

VERSION="20260322-0003"
REPO_RAW_BASE="https://raw.githubusercontent.com/Cd1s/emby-autoplay/main"
INSTALL_DIR="/opt/emby-autoplay"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "emby-autoplay online installer version: $VERSION"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

fetch() {
  local url="$1"
  local out="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -H 'Cache-Control: no-cache' -fsSL "${url}?v=${VERSION}" -o "$out"
  elif command -v wget >/dev/null 2>&1; then
    wget --header='Cache-Control: no-cache' -qO "$out" "${url}?v=${VERSION}"
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
fetch "$REPO_RAW_BASE/uninstall.sh" "$TMP_DIR/uninstall.sh"
fetch "$REPO_RAW_BASE/src/emby_keepalive.py" "$TMP_DIR/src/emby_keepalive.py"
fetch "$REPO_RAW_BASE/src/emby_keepalive_config.py" "$TMP_DIR/src/emby_keepalive_config.py"
fetch "$REPO_RAW_BASE/src/emby_keepalive_systemd_scheduler.py" "$TMP_DIR/src/emby_keepalive_systemd_scheduler.py"
fetch "$REPO_RAW_BASE/src/emby_keepalive_history.py" "$TMP_DIR/src/emby_keepalive_history.py"
fetch "$REPO_RAW_BASE/src/emby_keepalive_systemd_runner.sh" "$TMP_DIR/src/emby_keepalive_systemd_runner.sh"
fetch "$REPO_RAW_BASE/src/run_emby_keepalive.sh" "$TMP_DIR/src/run_emby_keepalive.sh"
fetch "$REPO_RAW_BASE/src/interactive_install.py" "$TMP_DIR/src/interactive_install.py"
fetch "$REPO_RAW_BASE/src/embyautoplay" "$TMP_DIR/src/embyautoplay"
fetch "$REPO_RAW_BASE/src/emby_keepalive.env.example" "$TMP_DIR/src/emby_keepalive.env.example"
chmod +x "$TMP_DIR/install.sh"

cd "$TMP_DIR"
EMBY_AUTOPLAY_SKIP_INTERACTIVE=1 ./install.sh

echo
echo "Base install complete."
AUTO_FLAG="${EMBY_AUTOPLAY_AUTO_SETUP:-}"
shopt -s nocasematch
if [[ "$AUTO_FLAG" =~ ^(1|true|yes)$ ]]; then
  echo "Starting automatic setup..."
  EMBY_AUTOPLAY_HOME="$INSTALL_DIR" EMBY_AUTOPLAY_AUTO_SETUP=1 /usr/bin/python3 "$INSTALL_DIR/interactive_install.py"
  echo
  echo "One-line install complete."
  echo "Manage with: embyautoplay"
elif [[ -t 0 ]]; then
  echo "Starting interactive setup..."
  EMBY_AUTOPLAY_HOME="$INSTALL_DIR" /usr/bin/python3 "$INSTALL_DIR/interactive_install.py"

  echo
  echo "One-line install complete."
  echo "Manage with: embyautoplay"
else
  echo "No interactive TTY detected."
  echo "Base install completed successfully."
  echo "Next step: run one of the following:"
  echo "  1) EMBY_AUTOPLAY_HOME=$INSTALL_DIR python3 $INSTALL_DIR/interactive_install.py"
  echo "  2) embyautoplay  # then choose 修改配置 / 重新预约下一次运行"
  echo
  echo "Tip: set EMBY_AUTOPLAY_AUTO_SETUP=1 with EMBY_* env vars for full unattended install."
fi
