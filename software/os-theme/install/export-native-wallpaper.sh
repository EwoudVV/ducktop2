#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SVG="$REPO_ROOT/wallpapers/source/ducktop-hud-native.svg"
PNG="$REPO_ROOT/wallpapers/2560x1600/ducktop-hud-wallpaper.png"
KDE_PNG="$REPO_ROOT/wallpapers/ducktop-hud/contents/images/2560x1600.png"
SDDM_PNG="$REPO_ROOT/sddm/ducktop-hud/assets/wallpaper.png"
PLYMOUTH_PNG="$REPO_ROOT/plymouth/ducktop-hud/assets/wallpaper.png"

if ! command -v node >/dev/null 2>&1; then
  echo "node is required to generate the native SVG source." >&2
  exit 1
fi

node "$REPO_ROOT/tools/generate-native-wallpaper.mjs" "$SVG"

if command -v sips >/dev/null 2>&1; then
  sips -s format png "$SVG" --out "$PNG" >/dev/null
elif command -v rsvg-convert >/dev/null 2>&1; then
  rsvg-convert -w 2560 -h 1600 -f png -o "$PNG" "$SVG"
else
  echo "No SVG renderer found. Install librsvg2-tools on Fedora or run on macOS with sips." >&2
  exit 1
fi

cp "$PNG" "$KDE_PNG"
cp "$PNG" "$SDDM_PNG"
cp "$PNG" "$PLYMOUTH_PNG"

bash "$REPO_ROOT/install/check-wallpaper-resolution.sh"
