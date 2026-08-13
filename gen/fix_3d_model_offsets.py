#!/usr/bin/env python3
"""Fix 3D model paths and offsets in PCB files for ducktop2.3dshapes models.

1. Fixes model paths from KICAD10_3DMODEL_DIR to KIPRJMOD/ducktop2.3dshapes/
   for custom models that have STEP files in the project directory.
2. Updates (xyz ...) offsets within each model's (offset ...) block to use
   the corrected values from bounding box analysis.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUCK2_3D = ROOT / "ducktop2.3dshapes"

# Offsets are (x, y, z).
# z_offset = -z_min  (brings model bottom to PCB surface at z=0).
# x,y_offset = 0 for connectors and modules (origin at pin 1).
# x,y_offset = -center for symmetric SMD components (centers at footprint origin).
MODEL_OFFSETS = {
    "Coilcraft_XGL5030":      (0, -1.45, +2.84),
    "Cherry_MX_ULP_SMD":     (0, +5.50, +3.40),
    "DRA818_Castellated":     (0,     0, +9.50),   # castellated module, origin at pin 1
    "JXD1-1022NL_MidMount":  (0,     0, +21.45),   # connector, origin at pin 1
    "Amphenol_MDT420E01001_H4.2": (0, 0, +3.95),   # M.2 socket, origin at pin 1
    "Amphenol_MDT420M01001_H4.2": (0, 0, +22.00),  # M.2 socket, origin at pin 1
    "SSD1306_0.96in_Module_4Pin": (0, 0, +8.50),   # symmetric module, centered ok
    "ublox_MAX":              (0,     0, +0.40),    # GPS module, origin at pin 1
    "LattePanda_Mu_H8.0_Horizontal": (0, 0, +27.91),  # socket connector
    "Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal": (0, 0, 0),  # FFC connector, standard model
}

# Models in ducktop2.3dshapes/ that should use KIPRJMOD paths
CUSTOM_MODELS = {f.stem: f.name for f in DUCK2_3D.glob("*.step")}


def format_float(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f'{v:g}'


def find_matching_paren(content: str, start: int) -> int:
    depth = 0
    for i in range(start, len(content)):
        if content[i] == '(':
            depth += 1
        elif content[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def fix_model_paths(content: str) -> tuple[str, int]:
    """Replace KICAD10_3DMODEL_DIR paths with KIPRJMOD for custom models."""
    pattern = r'"\$\{KICAD10_3DMODEL_DIR\}/([^"]+\.step)"'

    class Counter:
        def __init__(self): self.n = 0
        def inc(self): self.n += 1

    c = Counter()

    def _repl(m):
        path = m.group(1)
        model_file = Path(path).name
        model_stem = Path(model_file).stem
        if model_stem in CUSTOM_MODELS:
            c.inc()
            return f'"${{KIPRJMOD}}/ducktop2.3dshapes/{model_file}"'
        return m.group(0)

    content = re.sub(pattern, _repl, content)
    return content, c.n


def fix_offsets(content: str) -> tuple[str, int]:
    """Fix offsets in model blocks for ducktop2.3dshapes models."""
    changes = 0
    search_from = 0

    while True:
        model_start = content.find('(model "${KIPRJMOD}/ducktop2.3dshapes/', search_from)
        if model_start < 0:
            break

        path_start = model_start + len('(model "')
        path_end = content.index('"', path_start)
        model_path = content[path_start:path_end]
        model_name = Path(model_path).stem

        model_end = find_matching_paren(content, model_start)
        if model_end < 0:
            search_from = model_start + 1
            continue

        model_block = content[model_start:model_end + 1]

        # Find and fix (offset (xyz ...)) within the model block
        offset_start = model_block.find('(offset')
        if offset_start < 0:
            search_from = model_end + 1
            continue

        offset_end = find_matching_paren(model_block, offset_start)
        if offset_end < 0:
            search_from = model_end + 1
            continue

        offset_block = model_block[offset_start:offset_end + 1]

        if model_name not in MODEL_OFFSETS:
            search_from = model_end + 1
            continue

        ox, oy, oz = MODEL_OFFSETS[model_name]
        ox_s = format_float(ox)
        oy_s = format_float(oy)
        oz_s = format_float(oz)

        new_offset = re.sub(
            r'(xyz\s+)[-\d.e+]+\s+[-\d.e+]+\s+[-\d.e+]+(\s*\))',
            lambda m: f'{m.group(1)}{ox_s} {oy_s} {oz_s}{m.group(2)}',
            offset_block,
        )

        if new_offset == offset_block:
            search_from = model_end + 1
            continue

        # Rebuild model block with new offset
        new_model_block = (
            model_block[:offset_start]
            + new_offset
            + model_block[offset_start + len(offset_block):]
        )
        content = content[:model_start] + new_model_block + content[model_end + 1:]
        changes += 1
        search_from = model_start + len(new_model_block)

    return content, changes


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    pcbs = [
        ("Main PCB", ROOT / "ducktop2.kicad_pcb"),
        ("Radio DB", ROOT / "radio_daughterboard" / "radio_daughterboard.kicad_pcb"),
        ("KBD DB", ROOT / "12_keyboard_daughterboard.kicad_pcb"),
    ]

    for label, path in pcbs:
        if not path.exists():
            print(f"  ! {label}: {path.name} not found")
            continue

        content = path.read_text()

        # 1. Fix paths
        content_fixed, path_changes = fix_model_paths(content)

        if dry_run:
            # Count offset changes needed
            offset_count = 0
            tmp_content = content_fixed
            search_from = 0
            while True:
                ms = tmp_content.find('(model "${KIPRJMOD}/ducktop2.3dshapes/', search_from)
                if ms < 0:
                    break
                ps = ms + len('(model "')
                pe = tmp_content.index('"', ps)
                mn = Path(tmp_content[ps:pe]).stem
                if mn in MODEL_OFFSETS:
                    ox, oy, oz = MODEL_OFFSETS[mn]
                    if ox != 0 or oy != 0 or oz != 0:
                        offset_count += 1
                search_from = pe + 1

            parts = []
            if path_changes:
                parts.append(f"{path_changes} paths")
            if offset_count:
                parts.append(f"{offset_count} offsets")
            action = "update" if parts else "no changes"
            print(f"  {label}: would {action}" + (f" ({', '.join(parts)})" if parts else ""))
            continue

        # Apply path fixes
        if path_changes:
            content = content_fixed

        # Apply offset fixes
        content, offset_changes = fix_offsets(content)

        if path_changes or offset_changes:
            path.write_text(content)
            parts = []
            if path_changes:
                parts.append(f"{path_changes} paths")
            if offset_changes:
                parts.append(f"{offset_changes} offsets")
            print(f"  {label}: fixed {', '.join(parts)}")
        else:
            print(f"  {label}: no changes")


if __name__ == "__main__":
    main()
