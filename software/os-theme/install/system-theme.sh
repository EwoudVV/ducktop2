#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_SDDM=0
ENABLE_SDDM=0
INSTALL_PLYMOUTH=0
ENABLE_PLYMOUTH=0

usage() {
  cat <<'USAGE'
Usage: sudo bash install/system-theme.sh [options]

Installs staged system-level login/boot themes.

Options:
  --install-sddm       Copy the Ducktop SDDM theme into /usr/share/sddm/themes.
  --enable-sddm        Set the SDDM current theme to ducktop-hud.
  --install-plymouth   Copy the Ducktop Plymouth theme into /usr/share/plymouth/themes.
  --enable-plymouth    Enable the Ducktop Plymouth theme and rebuild initramfs.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --install-sddm) INSTALL_SDDM=1 ;;
    --enable-sddm) ENABLE_SDDM=1; INSTALL_SDDM=1 ;;
    --install-plymouth) INSTALL_PLYMOUTH=1 ;;
    --enable-plymouth) ENABLE_PLYMOUTH=1; INSTALL_PLYMOUTH=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

if ((INSTALL_SDDM)); then
  install -d /usr/share/sddm/themes/ducktop-hud
  cp -R "$REPO_ROOT/sddm/ducktop-hud/." /usr/share/sddm/themes/ducktop-hud/
  echo "Installed SDDM theme: ducktop-hud"
fi

if ((ENABLE_SDDM)); then
  install -d /etc/sddm.conf.d
  cat >/etc/sddm.conf.d/ducktop-hud.conf <<'EOF'
[Theme]
Current=ducktop-hud
EOF
  echo "Enabled SDDM theme: ducktop-hud"
fi

if ((INSTALL_PLYMOUTH)); then
  install -d /usr/share/plymouth/themes/ducktop-hud
  cp -R "$REPO_ROOT/plymouth/ducktop-hud/." /usr/share/plymouth/themes/ducktop-hud/
  echo "Installed Plymouth theme: ducktop-hud"
fi

if ((ENABLE_PLYMOUTH)); then
  if ! command -v plymouth-set-default-theme >/dev/null 2>&1; then
    echo "plymouth-set-default-theme not found." >&2
    exit 1
  fi
  plymouth-set-default-theme -R ducktop-hud
  echo "Enabled Plymouth theme: ducktop-hud"
fi

if ! ((INSTALL_SDDM || INSTALL_PLYMOUTH)); then
  usage
fi
