#!/usr/bin/env python3
"""Fix all 3D model issues across all 3 PCBs.

Phases:
  1. Fix dead library model paths (attempt partial name match, else remove)
  2. Fix custom model offsets/rotations (Cherry MX 180°, DRA818/ublox centering)
  3. Add missing (rotate (xyz 0 0 0)) to all entries lacking it
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHAPES = ROOT / "ducktop2.3dshapes"
KICAD_3D = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels")

# ── Phase 2: correct offsets and rotations for custom models ──────────────

# (x, y, z) offsets, and optional (rx, ry, rz) rotation.
# All values verified against cadquery bounding box analysis.
MODEL_FIXES: dict[str, tuple[tuple[float, float, float], tuple[float, float, float] | None]] = {
    "Cherry_MX_ULP_SMD":                      ((0, 5.50, 3.40), (0, 0, 180)),
    "DRA818_Castellated":                      ((0, -2.00, 9.50), None),
    "ublox_MAX":                               ((0.15, -0.06, 0.40), None),
}

# Models confirmed correct (no offset/rotate change needed)
MODELS_CORRECT = {
    "Coilcraft_XGL5030",
    "Amphenol_MDT420E01001_H4.2",
    "Amphenol_MDT420M01001_H4.2",
    "JXD1-1022NL_MidMount",
    "LattePanda_Mu_H8.0_Horizontal",
    "SSD1306_0.96in_Module_4Pin",
    "Hirose_FH12-30S-0.5SH_1x30-1MP_P0.50mm_Horizontal",
    "Infineon_IM68A130V01",
    "MiniCircuits_QA2224_PL484",
    "TDK_TFM201610",
    "Texas_RPA0010A_VQFN-HR-10_3x3mm",
    "Texas_RPW0010A_VQFN-HR-10_2x2mm",
    "Texas_RYQ0021A_VQFN-HR-21_3x5mm",
    "Texas_TPD1S514_YZ_WCSP-12_1.99x1.29mm_P0.5mm",
    "Wurth_9774055243R",
    "SMT_Standoff_12mm",
    "SMT_Standoff_7mm",
    "USB2_Trackpad_Cable",
}

# ── Helpers ────────────────────────────────────────────────────────────────

FV_RE = re.compile(r'[-\d.e+]+')


def fmt(v: float) -> str:
    if v == int(v):
        return str(int(v))
    return f'{v:g}'


def find_matching_paren(s: str, start: int) -> int:
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1


def resolve_vars(path: str) -> Path:
    """Resolve ${KICAD10_3DMODEL_DIR} and ${KIPRJMOD} to real paths."""
    p = path.replace("${KICAD10_3DMODEL_DIR}", str(KICAD_3D))
    p = p.replace("${KIPRJMOD}", str(ROOT))
    p = p.replace("${KISYS3DMOD}", str(KICAD_3D))
    return Path(p)


# IPC passive metric naming conversion (KiCad 7 → KiCad 10)
#   Old: 0201_1005Metric → New: 0201_0603Metric
#   1005 (1.0 × 0.5mm IEC) → 0603 (0.6 × 0.3mm JIS), etc.
METRIC_CONVERSION = {
    "1005": "0603", "1608": "1005", "2012": "1206",
    "3216": "1206", "3225": "1210", "4532": "1812",
    "4750": "1812", "5025": "2010", "6332": "2512",
}

PASSIVE_PREFIXES = ("C_", "R_", "L_", "D_", "CP_", "L_CommonMode_")


def try_find_matching_model(lib: str, fp_stem: str) -> str | None:
    """Try to find a real model file for a library footprint.

    Only performs safe metric-code conversion for IPC passives.
    Non-passive components with no exact match are not matched
    (assigning a wrong connector/IC model is worse than no model).
    """
    lib_dir = KICAD_3D / f"{lib}.3dshapes"
    if not lib_dir.exists():
        return None

    # Exact match on the basename
    if (lib_dir / f"{fp_stem}.step").exists():
        return f"${{KICAD10_3DMODEL_DIR}}/{lib}.3dshapes/{fp_stem}.step"

    # Metric code conversion for IPC passives
    if fp_stem.startswith(PASSIVE_PREFIXES):
        # Parse for pattern like C_0201_1005Metric → C_0201_0603Metric
        # Split stem into prefix + dimensions: e.g. [C, 0201_1005Metric]
        parts = fp_stem.split("_", 1)
        if len(parts) == 2:
            dim_part = parts[1]
            # Check if it ends with Metric and has _ separator
            if dim_part.endswith("Metric"):
                codes = dim_part[:-6]  # remove "Metric"
                im = codes.split("_")
                if len(im) == 2:
                    imperial, old_metric = im[0], im[1]
                    if old_metric in METRIC_CONVERSION:
                        new_metric = METRIC_CONVERSION[old_metric]
                        new_stem = f"{parts[0]}_{imperial}_{new_metric}Metric"
                        cand = lib_dir / f"{new_stem}.step"
                        if cand.exists():
                            return f"${{KICAD10_3DMODEL_DIR}}/{lib}.3dshapes/{cand.name}"

    return None


def extract_lib_and_name(fp_ref: str) -> tuple[str, str]:
    if ":" in fp_ref:
        lib, name = fp_ref.split(":", 1)
        return lib, name
    return "", fp_ref


# ── PCB parsing ────────────────────────────────────────────────────────────

def iter_footprints(content: str):
    """Yield (block, ref_full, start, end) for each (footprint ...) block."""
    i = 0
    while True:
        m = re.search(r'\(footprint\s+"([^"]+)"', content[i:])
        if not m:
            break
        ref = m.group(1)
        start = i + m.start()
        end = find_matching_paren(content, start)
        if end < 0:
            break
        yield content[start:end+1], ref, start, end + 1
        i = end + 1


def iter_models(fp_block: str):
    """Yield (model_block, path, off, rot, mstart, mend) within a footprint block."""
    base = 0
    while True:
        mm = re.search(r'\(model\s+"([^"]+)"', fp_block[base:])
        if not mm:
            break
        mstart = base + mm.start()
        mend = find_matching_paren(fp_block, mstart)
        if mend < 0:
            break
        mend += 1  # inclusive
        model_block = fp_block[mstart:mend]
        path = mm.group(1)

        off_m = re.search(r'\(offset\s+\(xyz\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)\)', model_block)
        off = (off_m.group(1), off_m.group(2), off_m.group(3)) if off_m else ("0", "0", "0")

        rot_m = re.search(r'\(rotate\s+\(xyz\s+([-\d.e+]+)\s+([-\d.e+]+)\s+([-\d.e+]+)\)', model_block)
        rot = (rot_m.group(1), rot_m.group(2), rot_m.group(3)) if rot_m else None

        yield model_block, path, off, rot, mstart, mend
        base = mend


# ── Apply fixes ────────────────────────────────────────────────────────────

def fix_pcb(path: Path, dry_run: bool = False) -> dict:
    content = path.read_text()
    changes = []
    stats = {"removed": 0, "fixed_path": 0, "fixed_offset_rot": 0, "added_rotate": 0}

    footblocks = list(iter_footprints(content))

    for fp_block, ref, fp_start, fp_end in footblocks:
        fp_lib, fp_name = extract_lib_and_name(ref)
        model_entries = list(iter_models(fp_block))

        if not model_entries:
            continue

        for model_block, model_path, off, rot, mstart_rel, mend_rel in model_entries:
            mstart = fp_start + mstart_rel
            mend = fp_start + mend_rel

            # ── Phase 1: Fix dead library model paths ─────────────────────
            if "${KICAD10_3DMODEL_DIR}" in model_path:
                resolved = resolve_vars(model_path)
                if not resolved.exists():
                    # Try to find a matching model
                    lib_dir_name = Path(model_path).parent.name.replace(".3dshapes", "")
                    model_stem = Path(model_path).stem
                    match = try_find_matching_model(lib_dir_name, model_stem) if lib_dir_name else None
                    if match:
                        new_block = model_block.replace(model_path, match)
                        changes.append((mstart, mend, new_block))
                        stats["fixed_path"] += 1
                    else:
                        # Can't fix — remove the model entry entirely
                        changes.append((mstart, mend, ""))
                        stats["removed"] += 1
                    continue  # moved on from this entry; skip Phases 2/3

            # ── Phase 2: Fix custom model offsets/rotations ──────────────
            if "${KIPRJMOD}" in model_path:
                model_stem = Path(model_path).stem

                if model_stem in MODEL_FIXES:
                    (ox, oy, oz), rotate = MODEL_FIXES[model_stem]
                    new_block = model_block

                    # Update offset — match the full (offset (xyz ...)) with both closing parens
                    off_m = re.search(r'\(offset\s+\(xyz\s+[^)]+\)\)', new_block)
                    if off_m:
                        new_off = f"(offset (xyz {fmt(ox)} {fmt(oy)} {fmt(oz)}))"
                        new_block = new_block[:off_m.start()] + new_off + new_block[off_m.end():]

                    # Update or add rotate
                    if rotate is not None:
                        rx, ry, rz = rotate
                        rot_m_inner = re.search(r'\(rotate\s+\(xyz\s+[^)]+\)\)', new_block)
                        new_rot = f"(rotate (xyz {fmt(rx)} {fmt(ry)} {fmt(rz)}))"
                        if rot_m_inner:
                            new_block = new_block[:rot_m_inner.start()] + new_rot + new_block[rot_m_inner.end():]
                        else:
                            # Add before closing paren
                            new_block = new_block.rstrip()
                            close = new_block.rfind(")")
                            if close >= 0:
                                new_block = new_block[:close] + f"  {new_rot}\n" + new_block[close:]

                    if new_block != model_block:
                        changes.append((mstart, mend, new_block))
                        stats["fixed_offset_rot"] += 1
                        # Update local vars so Phase 3 can see the new state
                        model_block = new_block
                        rot = str(rotate[0]) if rotate else None
                        # Fall through to Phase 3

            # ── Phase 3: Add missing (rotate ...) ────────────────────────
            if rot is None:
                # Check if current model_block already has rotate
                rot_m_inner = re.search(r'\(rotate\s+\(xyz\s+[^)]+\)', model_block)
                if not rot_m_inner:
                    # Add rotate before closing paren
                    new_block = model_block.rstrip()
                    close = new_block.rfind(")")
                    if close >= 0:
                        new_block = new_block[:close] + f"  (rotate (xyz 0 0 0))\n" + new_block[close:]
                    if new_block != model_block:
                        changes.append((mstart, mend, new_block))
                        stats["added_rotate"] += 1
                        model_block = new_block

    if dry_run:
        return stats

    # Apply changes in reverse order (preserve positions)
    if changes:
        changes.sort(key=lambda x: -x[0])
        for mstart, mend, new_content in changes:
            content = content[:mstart] + new_content + content[mend:]
        path.write_text(content)

    return stats


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    pcbs = [
        ("Main PCB", ROOT / "ducktop2.kicad_pcb"),
        ("Radio DB", ROOT / "radio_daughterboard" / "radio_daughterboard.kicad_pcb"),
        ("KBD DB", ROOT / "12_keyboard_daughterboard.kicad_pcb"),
    ]

    total = {}

    for label, pcb_path in pcbs:
        if not pcb_path.exists():
            print(f"  ! {label}: not found")
            continue

        stats = fix_pcb(pcb_path, dry_run=dry_run)
        mode = "DRY RUN" if dry_run else "APPLIED"

        parts = []
        for k, v in stats.items():
            if v:
                parts.append(f"{v} {k}")
                total.setdefault(k, 0)
                total[k] += v

        action = ", ".join(parts) if parts else "no changes"
        print(f"  {mode}  {label}: {action}")

        for k, v in total.items():
            total.setdefault(k, 0)

    if not dry_run:
        print()
        total_parts = [f"{v} {k}" for k, v in total.items() if v]
        if total_parts:
            print(f"Total: {', '.join(total_parts)}")
        else:
            print("Total: no changes")



if __name__ == "__main__":
    main()
