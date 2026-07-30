#!/usr/bin/env python3
"""
Add 3D model paths to KiCad PCB footprints that are missing them.

Scans each PCB file, identifies footprints without (model ...) entries,
and adds the standard KiCad 3D library path where the .step file exists.
For custom ducktop2 footprints, checks the project's ducktop2.3dshapes/ directory.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DUCK2_3D = ROOT / "ducktop2.3dshapes"
KICAD_3D = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels"

# Mapping from ducktop2 footprint names to model filenames where they differ
FOOTPRINT_TO_MODEL = {
    "LattePanda_Module_H8.0mm_Horizontal": "LattePanda_Mu_H8.0_Horizontal.step",
}

# Mapping from ducktop2 footprint names to standard KiCad 3D library paths
FOOTPRINT_TO_KICAD_MODEL = {
    "PE42820_QFN-32-1EP_5x5mm_P0.5mm": "${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/QFN-32-1EP_5x5mm_P0.5mm_EP3.3x3.3mm.step",
}

# 3D model offset/rotation corrections (x, y, z) for each model filename.
# Calculated by analyzing each STEP file's bounding box relative to KiCad's convention:
#   - z=0 at PCB surface (bottom of component)
#   - x,y origin at footprint origin (center for symmetrical parts, pin 1 for connectors)
# z_offset = -z_min (brings bottom of model to z=0)
# x,y_offset = -center (centers symmetric models at origin)
MODEL_OFFSETS = {
    "Coilcraft_XGL5030": (0, -1.45, +2.84),
    "Cherry_MX_ULP_SMD": (0, +5.50, +3.40),
    "DRA818_Castellated": (0, -2.00, +9.50),
    "JXD1-1022NL_MidMount": (0, 0, +21.45),
    "Amphenol_MDT420E01001_H4.2": (0, 0, +3.95),
    "Amphenol_MDT420M01001_H4.2": (0, 0, +22.00),
    "SSD1306_0.96in_Module_4Pin": (0, 0, +8.50),
    "ublox_MAX": (0.15, -0.06, +0.40),
    "LattePanda_Mu_H8.0_Horizontal": (0, 0, +27.91),
    "Hirose_DF40C(2.0)-60DS-0.4V_2x30_P0.4mm": (0, 0, +9.42),
}


def find_footprints(content: str) -> list[dict]:
    """Parse all (footprint ...) blocks from PCB content."""
    fps = []
    idx = 0
    while True:
        start = content.find('(footprint "', idx)
        if start == -1:
            break

        # Extract footprint name (library:name)
        name_end = content.find('"', start + 12)
        fp_name_full = content[start + 11:name_end]

        # Extract lib and name
        if ":" in fp_name_full:
            lib, _, name = fp_name_full.partition(":")
            lib = lib.strip('"')
        else:
            lib = ""
            name = fp_name_full

        # Find end of this footprint block
        end = content.find('(footprint "', start + 12)
        if end == -1:
            depth = 0
            for i in range(start, len(content)):
                if content[i] == "(":
                    depth += 1
                elif content[i] == ")":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

        block = content[start:end]
        has_model = "(model" in block

        # Extract reference
        ref = ""
        ref_m = __import__("re").search(r'"Reference" "([^"]+)"', block)
        if ref_m:
            ref = ref_m.group(1)

        fps.append({
            "lib": lib,
            "name": name,
            "ref": ref,
            "has_model": has_model,
            "start": start,
            "end": end,
            "block": block,
        })
        idx = end
    return fps


def find_3d_model_path(lib: str, name: str) -> str | None:
    """Find the appropriate 3D model path for a footprint.

    Returns the model path string to insert, or None if not found.
    """
    # Standard KiCad library footprint
    if lib and lib != "ducktop2":
        # Check ducktop2.3dshapes/ first (for project-specific models)
        step_name = f"{name}.step"
        if name in FOOTPRINT_TO_MODEL:
            step_name = FOOTPRINT_TO_MODEL[name]
        project_model = DUCK2_3D / step_name
        if project_model.exists():
            return f"${{KIPRJMOD}}/ducktop2.3dshapes/{step_name}"

        # Fall back to KiCad standard library
        model_path = os.path.join(KICAD_3D, f"{lib}.3dshapes", step_name)
        if os.path.exists(model_path):
            return f'${{KICAD10_3DMODEL_DIR}}/{lib}.3dshapes/{step_name}'
        return None

    # Custom ducktop2 footprint
    if lib == "ducktop2":
        # Check explicit mapping first
        if name in FOOTPRINT_TO_MODEL:
            step_name = FOOTPRINT_TO_MODEL[name]
            model_path = DUCK2_3D / step_name
            if model_path.exists():
                return f"${{KIPRJMOD}}/ducktop2.3dshapes/{step_name}"
            return None

        # Check explicit KiCad standard library mapping
        if name in FOOTPRINT_TO_KICAD_MODEL:
            return FOOTPRINT_TO_KICAD_MODEL[name]

        # Try matching by footprint name
        step_name = f"{name}.step"
        model_path = DUCK2_3D / step_name
        if model_path.exists():
            return f"${{KIPRJMOD}}/ducktop2.3dshapes/{step_name}"
        return None

    # Mounting hole, test point, etc. (no library prefix)
    if not lib:
        step_name = f"{name}.step"
        model_path = os.path.join(KICAD_3D, f"{name}.3dshapes", step_name)
        if os.path.exists(model_path):
            return f'${{KICAD10_3DMODEL_DIR}}/{name}.3dshapes/{step_name}'
        # Try direct in various library directories
        for lib_dir in ["MountingHole.3dshapes", "TestPoint.3dshapes", "Connector.3dshapes"]:
            cand = os.path.join(KICAD_3D, lib_dir, step_name)
            if os.path.exists(cand):
                return f"${{KICAD10_3DMODEL_DIR}}/{lib_dir}/{step_name}"
        return None

    return None


def add_model_to_block(block: str, model_path: str) -> str:
    """Add a (model ...) entry to a footprint block, before the closing paren."""
    last_close = block.rstrip().rfind(")")
    if last_close < 0:
        return block

    model_name = Path(model_path).stem
    ox, oy, oz = MODEL_OFFSETS.get(model_name, (0, 0, 0))

    indent = "  "
    model_line = (
        f'{indent}(model "{model_path}"\n'
        f'{indent}  (offset (xyz {ox} {oy} {oz}))\n'
        f'{indent}  (scale (xyz 1 1 1))\n'
        f'{indent})'
    )

    new_block = block[:last_close] + model_line + "\n" + block[last_close:]
    return new_block


def patch_pcb(pcb_path: Path, dry_run: bool = False) -> dict:
    """Patch 3D models into footprints missing them. Returns stats."""
    content = pcb_path.read_text()
    fps = find_footprints(content)
    stats = {"total": len(fps), "with_model": 0, "added": 0, "skipped_no_model": 0, "errors": 0}

    # Build patches in reverse order (preserve offsets)
    patches = []
    for fp in fps:
        if fp["has_model"]:
            stats["with_model"] += 1
            continue

        model_path = find_3d_model_path(fp["lib"], fp["name"])
        if model_path is None:
            stats["skipped_no_model"] += 1
            continue

        # Add model to the block
        new_block = add_model_to_block(fp["block"], model_path)
        patches.append((fp["start"], fp["end"], new_block))
        stats["added"] += 1

    if dry_run or not patches:
        return stats

    # Apply patches (reverse order to preserve positions)
    for start, end, new_block in reversed(patches):
        content = content[:start] + new_block + content[end:]

    pcb_path.write_text(content)
    return stats


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    pcbs = [
        ("Main PCB", ROOT / "ducktop2.kicad_pcb"),
        ("Radio DB", ROOT / "radio_daughterboard" / "radio_daughterboard.kicad_pcb"),
        ("KBD DB", ROOT / "12_keyboard_daughterboard.kicad_pcb"),
    ]

    total_added = 0
    total_skipped = 0

    for label, path in pcbs:
        if not path.exists():
            print(f"  ! {label}: {path.name} not found")
            continue

        stats = patch_pcb(path, dry_run=dry_run)

        print(f"{'DRY RUN' if dry_run else 'APPLIED'}  {label} ({path.name}): "
              f"{stats['total']} footprints, "
              f"{stats['with_model']} with model, "
              f"{stats['added']} models added, "
              f"{stats['skipped_no_model']} skipped (no model file)")

        total_added += stats["added"]
        total_skipped += stats["skipped_no_model"]

    print(f"\nTotal: {total_added} models added, {total_skipped} skipped (no model file)")


if __name__ == "__main__":
    main()
