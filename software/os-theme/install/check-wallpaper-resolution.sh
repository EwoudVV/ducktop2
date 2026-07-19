#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_WIDTH="${TARGET_WIDTH:-2560}"
TARGET_HEIGHT="${TARGET_HEIGHT:-1600}"
INCLUDE_NON_DEPLOYABLE=0

usage() {
  cat <<'USAGE'
Usage: bash install/check-wallpaper-resolution.sh [--include-non-deployable]

Checks active Ducktop2 wallpaper assets against the target 2560x1600 panel size.

Options:
  --include-non-deployable  Also check concepts and high-resolution masters.
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --include-non-deployable) INCLUDE_NON_DEPLOYABLE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; usage; exit 2 ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for wallpaper dimension checks." >&2
  exit 1
fi

files=()
while IFS= read -r file; do
  if [[ "$INCLUDE_NON_DEPLOYABLE" -eq 0 &&
        ( "$file" == *"/concepts/"* || "$file" == *"/masters/"* ) ]]; then
    continue
  fi
  files+=("$file")
done < <(
  find \
    "$REPO_ROOT/wallpapers" \
    "$REPO_ROOT/sddm/ducktop-hud/assets" \
    "$REPO_ROOT/plymouth/ducktop-hud/assets" \
    -type f \( -name '*.png' -o -name '*.svg' \) | sort
)

if ((${#files[@]} == 0)); then
  echo "No wallpaper assets found." >&2
  exit 1
fi

python3 - "$TARGET_WIDTH" "$TARGET_HEIGHT" "${files[@]}" <<'PY'
import pathlib
import re
import struct
import sys

target_width = int(sys.argv[1])
target_height = int(sys.argv[2])
paths = [pathlib.Path(p) for p in sys.argv[3:]]
failed = False

for path in paths:
    data = path.read_bytes()
    suffix = path.suffix.lower()

    if suffix == ".png":
        if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            print(f"FAIL {path}: not a valid PNG")
            failed = True
            continue
        width, height = struct.unpack(">II", data[16:24])
    elif suffix == ".svg":
        text = data.decode("utf-8", errors="replace")
        match = re.search(r"<svg[^>]*\bwidth=\"(\d+)\"[^>]*\bheight=\"(\d+)\"", text)
        if not match:
            print(f"FAIL {path}: SVG width/height not found")
            failed = True
            continue
        width, height = int(match.group(1)), int(match.group(2))
    else:
        print(f"FAIL {path}: unsupported file type")
        failed = True
        continue

    status = "OK" if (width, height) == (target_width, target_height) else "FAIL"
    print(f"{status} {path}: {width}x{height}")
    if status == "FAIL":
        failed = True

if failed:
    sys.exit(1)
PY
