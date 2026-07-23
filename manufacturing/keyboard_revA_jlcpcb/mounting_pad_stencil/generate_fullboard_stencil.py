#!/usr/bin/env python3
"""Generate the Ducktop2 Rev A full-board paste stencil.

Covers all 65 MX ULP switches in one piece with:
  - 5 fixation-pad apertures per switch (same 0.20 mm inset)
  - Through-hole diode clearance cutouts at every diode position
  - 3 alignment nibs registering on switch locating NPTHs
  - 3 mm handling border around the PCB outline
  - Lift tab at the FFC connector edge

Board: 273.5 x 80 mm, prints diagonally on a P1S (256 x 256 mm bed).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    import networkx  # noqa: F401
    import trimesh
    from manifold3d import Manifold
except ImportError as exc:
    raise SystemExit(
        "Missing CAD dependencies. Install with: "
        "pip install manifold3d trimesh networkx"
    ) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
PCB_PATH = PROJECT_ROOT / "12_keyboard_daughterboard.kicad_pcb"
FOOTPRINT_PATH = PROJECT_ROOT / "ducktop2.pretty" / "Cherry_MX_ULP_SMD.kicad_mod"
STL_PATH = SCRIPT_DIR / "ducktop2_fullboard_stencil_revA.stl"
MANIFEST_PATH = SCRIPT_DIR / "fullboard_stencil_manifest.json"


MEMBRANE_THICKNESS = 0.12
APERTURE_INSET = 0.20
DIODE_OFFSET_X = 8.2
DIODE_CUTOUT_X = 2.0
DIODE_CUTOUT_Y = 3.4
BOARD_BORDER = 3.0
LIFT_TAB_WIDTH = 15.0
LIFT_TAB_HEIGHT = 10.0
NIB_HEIGHT = 0.3
NIB_SEGMENTS = 24

EDGE_CUTS = (17.5, 291.0, 0.3, 80.3)
FFC_Y = 41.25


@dataclass(frozen=True)
class RectPad:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class Locator:
    x: float
    y: float
    pcb_hole_diameter: float
    peg_base_diameter: float
    peg_tip_diameter: float


FIXATION_PADS = (
    RectPad(-6.2, -3.9, 1.6, 3.8),
    RectPad(-6.2, 4.5, 1.6, 3.0),
    RectPad(6.2, -5.025, 1.6, 1.8),
    RectPad(6.2, 0.0, 1.6, 2.6),
    RectPad(6.2, 5.025, 1.6, 1.8),
)

LOCATORS = (
    Locator(-5.8, 1.2, 1.05, 0.80, 0.64),
    Locator(5.8, -3.26, 1.20, 0.95, 0.76),
    Locator(5.8, 3.26, 1.20, 0.95, 0.76),
)


def py(pcb_y: float) -> float:
    return -pcb_y


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_footprint_blocks(text: str, footprint_name: str) -> list[str]:
    marker = f'(footprint "{footprint_name}"'
    blocks: list[str] = []
    cursor = 0
    while True:
        start = text.find(marker, cursor)
        if start < 0:
            break
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    blocks.append(text[start : index + 1])
                    cursor = index + 1
                    break
        else:
            raise ValueError(f"Unterminated footprint block: {footprint_name}")
    return blocks


def footprint_pose(block: str) -> tuple[str, float, float, float]:
    ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    at_match = re.search(
        r"\n\s*\(at\s+([-0-9.]+)\s+([-0-9.]+)(?:\s+([-0-9.]+))?\)",
        block,
    )
    if not ref_match or not at_match:
        raise ValueError("Could not parse footprint reference and pose")
    return (
        ref_match.group(1),
        float(at_match.group(1)),
        float(at_match.group(2)),
        float(at_match.group(3) or 0.0),
    )


def parse_library_geometry() -> None:
    text = FOOTPRINT_PATH.read_text(encoding="utf-8")
    pad_pattern = re.compile(
        r'\(pad\s+""\s+smd\s+rect\s+'
        r"\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+"
        r"\(size\s+([-0-9.]+)\s+([-0-9.]+)\)",
        re.MULTILINE,
    )
    hole_pattern = re.compile(
        r'\(pad\s+""\s+np_thru_hole\s+circle\s+'
        r"\(at\s+([-0-9.]+)\s+([-0-9.]+)\)\s+"
        r"\(size\s+([-0-9.]+)\s+([-0-9.]+)\)\s+"
        r"\(drill\s+([-0-9.]+)\)",
        re.MULTILINE,
    )

    parsed_pads = {
        tuple(round(float(value), 4) for value in match)
        for match in pad_pattern.findall(text)
    }
    expected_pads = {
        (pad.x, pad.y, pad.width, pad.height) for pad in FIXATION_PADS
    }
    if parsed_pads != expected_pads:
        raise ValueError(
            f"Fixation-pad geometry changed: expected {expected_pads}, got {parsed_pads}"
        )

    parsed_holes = {
        (round(float(x), 4), round(float(y), 4), round(float(drill), 4))
        for x, y, _sx, _sy, drill in hole_pattern.findall(text)
    }
    expected_holes = {
        (locator.x, locator.y, locator.pcb_hole_diameter) for locator in LOCATORS
    }
    if parsed_holes != expected_holes:
        raise ValueError(
            f"Locator-hole geometry changed: expected {expected_holes}, got {parsed_holes}"
        )


def parse_board_geometry() -> tuple[list[tuple[float, float, str]], list[tuple[float, float, str]], float]:
    text = PCB_PATH.read_text(encoding="utf-8")
    thickness_match = re.search(r"\(general\s+\(thickness\s+([-0-9.]+)\)", text)
    if not thickness_match:
        raise ValueError("Could not read PCB thickness")
    pcb_thickness = float(thickness_match.group(1))
    if abs(pcb_thickness - 0.8) > 1e-6:
        raise ValueError(f"Expected 0.8 mm PCB, got {pcb_thickness} mm")

    switch_blocks = extract_footprint_blocks(text, "ducktop2:Cherry_MX_ULP_SMD")
    diode_blocks = extract_footprint_blocks(text, "Diode_SMD:D_SOD-323")
    switches = [footprint_pose(block) for block in switch_blocks]
    diodes = [footprint_pose(block) for block in diode_blocks]

    if len(switches) != 65:
        raise ValueError(f"Expected 65 MX ULP switches, got {len(switches)}")
    if len(diodes) != 65:
        raise ValueError(f"Expected 65 SOD-323 diodes, got {len(diodes)}")
    if any(abs(rotation) > 1e-6 for _ref, _x, _y, rotation in switches):
        raise ValueError("Not every MX ULP switch is at 0 degrees")

    diode_xy = {(round(x, 3), round(y, 3)) for _ref, x, y, _rot in diodes}
    for ref, x, y, _rotation in switches:
        expected_diode = (round(x + DIODE_OFFSET_X, 3), round(y, 3))
        if expected_diode not in diode_xy:
            raise ValueError(f"No diode found at +8.2 mm from {ref}")

    switch_list = [(x, y, ref) for ref, x, y, _ in switches]
    diode_list = [(x, y, ref) for ref, x, y, _ in diodes]
    return switch_list, diode_list, pcb_thickness


def translated_box(x1: float, x2: float, y1: float, y2: float, z1: float, z2: float) -> Manifold:
    lo = (min(x1, x2), min(y1, y2), min(z1, z2))
    hi = (max(x1, x2), max(y1, y2), max(z1, z2))
    return Manifold.cube((hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2])).translate(lo)


def build_stencil(
    switches: list[tuple[float, float, str]],
) -> Manifold:
    ec_x0, ec_x1, ec_y0, ec_y1 = EDGE_CUTS

    bx0 = ec_x0 - BOARD_BORDER
    bx1 = ec_x1 + BOARD_BORDER
    by0 = ec_y0 - BOARD_BORDER
    by1 = ec_y1 + BOARD_BORDER

    plate = translated_box(
        bx0, bx1,
        py(by0), py(by1),
        0.0, MEMBRANE_THICKNESS,
    )

    tab_x0 = bx1
    tab_x1 = bx1 + LIFT_TAB_WIDTH
    tab_y0 = FFC_Y - LIFT_TAB_HEIGHT / 2.0
    tab_y1 = FFC_Y + LIFT_TAB_HEIGHT / 2.0
    tab = translated_box(
        tab_x0, tab_x1,
        py(tab_y0), py(tab_y1),
        0.0, MEMBRANE_THICKNESS,
    )
    solid = plate + tab

    for sw_x, sw_y, _ref in switches:
        for pad in FIXATION_PADS:
            ap_w = pad.width - 2.0 * APERTURE_INSET
            ap_h = pad.height - 2.0 * APERTURE_INSET
            if ap_w <= 0.0 or ap_h <= 0.0:
                raise ValueError("Aperture inset consumed a fixation pad")
            cx = sw_x + pad.x
            cy = py(sw_y + pad.y)
            cutter = translated_box(
                cx - ap_w / 2.0,
                cx + ap_w / 2.0,
                cy - ap_h / 2.0,
                cy + ap_h / 2.0,
                -0.05,
                MEMBRANE_THICKNESS + 0.05,
            )
            solid -= cutter

    for sw_x, sw_y, _ref in switches:
        dx = sw_x + DIODE_OFFSET_X
        dy = py(sw_y)
        cutter = translated_box(
            dx - DIODE_CUTOUT_X / 2.0,
            dx + DIODE_CUTOUT_X / 2.0,
            dy - DIODE_CUTOUT_Y / 2.0,
            dy + DIODE_CUTOUT_Y / 2.0,
            -0.05,
            MEMBRANE_THICKNESS + 0.05,
        )
        solid -= cutter

    sorted_sw = sorted(switches, key=lambda s: s[0])
    leftmost = sorted_sw[0]
    rightmost = sorted_sw[-1]
    center_candidates = sorted_sw[len(sorted_sw) // 2 - 3: len(sorted_sw) // 2 + 3]
    center = min(center_candidates, key=lambda s: abs(s[0] - (sorted_sw[0][0] + sorted_sw[-1][0]) / 2.0))

    nib_switches = [leftmost, center, rightmost]

    for sw_x, sw_y, _ref in nib_switches:
        loc = LOCATORS[0]
        nx = sw_x + loc.x
        ny = py(sw_y + loc.y)
        nib = Manifold.cylinder(
            NIB_HEIGHT,
            loc.peg_base_diameter / 2.0,
            loc.peg_tip_diameter / 2.0,
            NIB_SEGMENTS,
        ).translate((nx, ny, MEMBRANE_THICKNESS))
        solid += nib

    return solid


def export_stl(solid: Manifold) -> trimesh.Trimesh:
    if solid.is_empty():
        raise ValueError("Generated stencil is empty")
    mesh_data = solid.to_mesh()
    vertices = np.asarray(mesh_data.vert_properties, dtype=np.float64)[:, :3]
    faces = np.asarray(mesh_data.tri_verts, dtype=np.int64)
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    mesh.export(STL_PATH, file_type="stl")
    return mesh


def validate_mesh(
    mesh: trimesh.Trimesh,
    switch_count: int,
    switches: list[tuple[float, float, str]],
) -> dict[str, object]:
    extents = mesh.extents

    ec_x0, ec_x1, ec_y0, ec_y1 = EDGE_CUTS
    expected_x = (ec_x1 + BOARD_BORDER + LIFT_TAB_WIDTH) - (ec_x0 - BOARD_BORDER)
    expected_y = (ec_y1 + BOARD_BORDER) - (ec_y0 - BOARD_BORDER)
    expected_z = MEMBRANE_THICKNESS + NIB_HEIGHT
    expected_extents = np.array([expected_x, expected_y, expected_z])
    if not np.allclose(extents, expected_extents, atol=0.002):
        raise ValueError(f"Unexpected STL extents: {extents}, expected {expected_extents}")

    if not mesh.is_watertight:
        raise ValueError("Generated STL is not watertight")
    if not mesh.is_winding_consistent:
        raise ValueError("Generated STL has inconsistent winding")
    if len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("Generated STL is not one connected body")

    diode_body_clearance = DIODE_OFFSET_X - 0.70 - 7.10
    diode_courtyard_clearance = DIODE_OFFSET_X - 0.95 - 7.10
    if diode_body_clearance < 0.35:
        raise ValueError(f"Insufficient diode body clearance: {diode_body_clearance}")
    if diode_courtyard_clearance < 0.10:
        raise ValueError(f"Insufficient diode courtyard clearance: {diode_courtyard_clearance}")

    aperture_rows = []
    for pad in FIXATION_PADS:
        width = round(pad.width - 2.0 * APERTURE_INSET, 3)
        height = round(pad.height - 2.0 * APERTURE_INSET, 3)
        area_pct = round(100.0 * width * height / (pad.width * pad.height), 1)
        aperture_rows.append({
            "copper_pad_mm": [pad.width, pad.height],
            "aperture_mm": [width, height],
            "area_coverage_percent": area_pct,
        })

    return {
        "stl": STL_PATH.name,
        "dimensions_print_orientation_mm": [round(float(v), 3) for v in extents],
        "membrane_thickness_mm": MEMBRANE_THICKNESS,
        "aperture_inset_per_edge_mm": APERTURE_INSET,
        "diode_cutout_mm": [DIODE_CUTOUT_X, DIODE_CUTOUT_Y],
        "diode_body_clearance_nominal_mm": round(diode_body_clearance, 3),
        "diode_courtyard_clearance_mm": round(diode_courtyard_clearance, 3),
        "board_border_mm": BOARD_BORDER,
        "alignment_nibs": 3,
        "nib_height_mm": NIB_HEIGHT,
        "switch_count": switch_count,
        "fixation_apertures_per_switch": len(FIXATION_PADS),
        "fixation_apertures": aperture_rows,
        "diode_cutouts": switch_count,
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "connected_bodies": len(mesh.split(only_watertight=False)),
        "triangle_count": int(len(mesh.faces)),
        "volume_mm3": round(float(mesh.volume), 4),
    }


def main() -> int:
    parse_library_geometry()
    switches, diodes, pcb_thickness = parse_board_geometry()

    solid = build_stencil(switches)
    mesh = export_stl(solid)
    validation = validate_mesh(mesh, len(switches), switches)

    manifest = {
        "design": "Ducktop2 Rev A full-board MX ULP paste stencil",
        "generated_from": {
            "pcb": str(PCB_PATH.relative_to(PROJECT_ROOT)),
            "pcb_sha256": sha256(PCB_PATH),
            "footprint": str(FOOTPRINT_PATH.relative_to(PROJECT_ROOT)),
            "footprint_sha256": sha256(FOOTPRINT_PATH),
            "switch_count": len(switches),
            "diode_count": len(diodes),
            "pcb_thickness_mm": pcb_thickness,
        },
        "validation": validation,
        "print_orientation": {
            "stl_is_pre_mirrored": True,
            "bed_side": "flat membrane",
            "nibs": "up while printing; down against PCB while using",
            "bed_fit": "273.5 x 80 mm board fits diagonally on 256 mm P1S bed",
        },
    }
    manifest["stl_sha256"] = sha256(STL_PATH)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    writer = csv.writer(sys.stdout)
    writer.writerow(["output", "value"])
    writer.writerow(["stl", STL_PATH])
    writer.writerow(["manifest", MANIFEST_PATH])
    writer.writerow(["dimensions_mm", validation["dimensions_print_orientation_mm"]])
    writer.writerow(["watertight", validation["watertight"]])
    writer.writerow(["triangles", validation["triangle_count"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
