#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="$HOME/.local/share/ducktop-theme-backups/$(date +%Y%m%d-%H%M%S)"
INSTALL_PACKAGES=0
APPLY_PANEL=0

usage() {
  cat <<'USAGE'
Usage: bash install/apply-theme.sh [--install-packages] [--panel]

Applies the user-level Ducktop2 KDE/Konsole/Starship theme.

Options:
  --install-packages  Install recommended Fedora packages with dnf.
  --panel             Apply the prototype Plasma top-panel layout.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --install-packages) INSTALL_PACKAGES=1 ;;
    --panel) APPLY_PANEL=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

backup_path() {
  local path="$1"
  if [[ -e "$path" || -L "$path" ]]; then
    local rel="${path#$HOME/}"
    mkdir -p "$BACKUP_ROOT/$(dirname "$rel")"
    cp -R "$path" "$BACKUP_ROOT/$rel"
  fi
}

install_packages() {
  if ! command -v dnf >/dev/null 2>&1; then
    echo "dnf not found; package install skipped."
    return
  fi

  mapfile -t packages < <(grep -vE '^\s*(#|$)' "$REPO_ROOT/install/packages-fedora-kde.txt")
  if ((${#packages[@]})); then
    sudo dnf install -y "${packages[@]}"
  fi
}

append_starship_init() {
  local rc_file="$1"
  local shell_name="$2"
  local init_line="$3"

  if [[ -e "$rc_file" ]]; then
    backup_path "$rc_file"
  fi

  touch "$rc_file"
  if ! grep -q "ducktop hud prompt" "$rc_file"; then
    {
      echo ""
      echo "# >>> ducktop hud prompt >>>"
      echo "if command -v starship >/dev/null 2>&1; then"
      echo "  $init_line"
      echo "fi"
      echo "# <<< ducktop hud prompt <<<"
    } >> "$rc_file"
    echo "Enabled Starship for $shell_name in $rc_file"
  fi
}

if ((INSTALL_PACKAGES)); then
  install_packages
fi

mkdir -p \
  "$HOME/.local/share/color-schemes" \
  "$HOME/.local/share/konsole" \
  "$HOME/.local/share/wallpapers" \
  "$HOME/.config"

backup_path "$HOME/.config/kdeglobals"
backup_path "$HOME/.config/konsolerc"
backup_path "$HOME/.config/starship.toml"
backup_path "$HOME/.local/share/wallpapers/ducktop-hud"

install -Dm0644 "$REPO_ROOT/plasma/color-schemes/DucktopHUD.colors" \
  "$HOME/.local/share/color-schemes/DucktopHUD.colors"
install -Dm0644 "$REPO_ROOT/konsole/DucktopHUD.colorscheme" \
  "$HOME/.local/share/konsole/DucktopHUD.colorscheme"
install -Dm0644 "$REPO_ROOT/konsole/DucktopHUD.profile" \
  "$HOME/.local/share/konsole/DucktopHUD.profile"
install -Dm0644 "$REPO_ROOT/starship/starship.toml" \
  "$HOME/.config/starship.toml"

rm -rf "$HOME/.local/share/wallpapers/ducktop-hud"
mkdir -p "$HOME/.local/share/wallpapers/ducktop-hud"
cp -R "$REPO_ROOT/wallpapers/ducktop-hud/." "$HOME/.local/share/wallpapers/ducktop-hud/"

if command -v kwriteconfig6 >/dev/null 2>&1; then
  kwriteconfig6 --file kdeglobals --group General --key ColorScheme DucktopHUD
  kwriteconfig6 --file kdeglobals --group General --key AccentColor "255,176,0"
  kwriteconfig6 --file konsolerc --group "Desktop Entry" --key DefaultProfile DucktopHUD.profile
elif command -v kwriteconfig5 >/dev/null 2>&1; then
  kwriteconfig5 --file kdeglobals --group General --key ColorScheme DucktopHUD
  kwriteconfig5 --file kdeglobals --group General --key AccentColor "255,176,0"
  kwriteconfig5 --file konsolerc --group "Desktop Entry" --key DefaultProfile DucktopHUD.profile
fi

if command -v plasma-apply-colorscheme >/dev/null 2>&1; then
  plasma-apply-colorscheme DucktopHUD || true
fi

WALLPAPER="$HOME/.local/share/wallpapers/ducktop-hud/contents/images/2560x1600.png"
if command -v plasma-apply-wallpaperimage >/dev/null 2>&1; then
  plasma-apply-wallpaperimage "$WALLPAPER" || true
fi

append_starship_init "$HOME/.bashrc" "bash" 'eval "$(starship init bash)"'
append_starship_init "$HOME/.zshrc" "zsh" 'eval "$(starship init zsh)"'

if ((APPLY_PANEL)); then
  if command -v qdbus6 >/dev/null 2>&1; then
    qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
      "$(cat "$REPO_ROOT/plasma/panel-layout/ducktop-panel.js")" || true
  elif command -v qdbus >/dev/null 2>&1; then
    qdbus org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript \
      "$(cat "$REPO_ROOT/plasma/panel-layout/ducktop-panel.js")" || true
  else
    echo "qdbus not found; panel layout skipped."
  fi
fi

echo "Ducktop2 theme installed."
echo "Backups, if any, are in: $BACKUP_ROOT"
echo "Log out and back in for all KDE settings to settle."
