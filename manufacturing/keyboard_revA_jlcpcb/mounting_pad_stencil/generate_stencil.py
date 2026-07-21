#!/usr/bin/env python3
"""Generate the Ducktop2 Rev A MX ULP fixation-pad microstencil."""

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
    import networkx  # noqa: F401 - trimesh uses it for connected-body checks
    import trimesh
    from manifold3d import Manifold
except ImportError as exc:
    raise SystemExit(
        "Missing CAD dependencies. Install with: "
        "pip install manifold3d trimesh networkx"
    ) from exc


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]
FOOTPRINT_PATH = PROJECT_ROOT / "ducktop2.pretty" / "Cherry_MX_ULP_SMD.kicad_mod"
PCB_PATH = PROJECT_ROOT / "12_keyboard_daughterboard.kicad_pcb"
STL_PATH = SCRIPT_DIR / "ducktop2_mx_ulp_fixation_microstencil_revA.stl"
MANIFEST_PATH = SCRIPT_DIR / "stencil_manifest.json"

# The membrane controls paste thickness. The tapered pegs point upward while
# printing; flip the finished stencil over so they enter the PCB locating holes.
MEMBRANE_THICKNESS = 0.12
PEG_LENGTH = 0.65
APERTURE_INSET = 0.20
MAIN_X = (-7.35, 7.10)
MAIN_Y = (-6.75, 6.75)
LIFT_TAB_X = (-10.35, -7.35)
LIFT_TAB_Y = (3.75, 6.75)
DIODE_OFFSET_X = 8.20
DIODE_BODY_HALF_X = 0.70
DIODE_COURTYARD_HALF_X = 0.95


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


def parse_board_geometry() -> tuple[int, int, float]:
    text = PCB_PATH.read_text(encoding="utf-8")
    thickness_match = re.search(r"\(general\s+\(thickness\s+([-0-9.]+)\)", text)
    if not thickness_match:
        raise ValueError("Could not read PCB thickness")
    pcb_thickness = float(thickness_match.group(1))
    if abs(pcb_thickness - 0.8) > 1e-6:
        raise ValueError(f"Expected 0.8 mm PCB, got {pcb_thickness} mm")

    switch_blocks = extract_footprint_blocks(text, "ducktop2:Cherry_MX_ULP_SMD")
    diode_blocks = extract_footprint_blocks(text, "Diode_SMD:D_SOD-323")
    switch_poses = [footprint_pose(block) for block in switch_blocks]
    diode_poses = [footprint_pose(block) for block in diode_blocks]

    if len(switch_poses) != 65:
        raise ValueError(f"Expected 65 MX ULP switches, got {len(switch_poses)}")
    if len(diode_poses) != 65:
        raise ValueError(f"Expected 65 SOD-323 diodes, got {len(diode_poses)}")
    if any(abs(rotation) > 1e-6 for _ref, _x, _y, rotation in switch_poses):
        raise ValueError("Not every MX ULP switch is at 0 degrees")

    # Each populated diode is 8.2 mm to the right of its switch. After its
    # 90-degree rotation, the courtyard begins at x=+7.25 mm and the nominal
    # package body begins at x=+7.50 mm relative to the switch center.
    diode_xy = {(round(x, 3), round(y, 3)) for _ref, x, y, _rot in diode_poses}
    for ref, x, y, _rotation in switch_poses:
        expected_diode = (round(x + DIODE_OFFSET_X, 3), round(y, 3))
        if expected_diode not in diode_xy:
            raise ValueError(f"No diode found at +8.2 mm from {ref}")

    return len(switch_poses), len(diode_poses), pcb_thickness


def translated_box(
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    z_min: float,
    z_max: float,
) -> Manifold:
    return Manifold.cube((x_max - x_min, y_max - y_min, z_max - z_min)).translate(
        (x_min, y_min, z_min)
    )


def print_y(use_y: float) -> float:
    """Mirror board Y so flipping the printed part produces the PCB pattern."""
    return -use_y


def build_stencil() -> Manifold:
    plate = translated_box(
        MAIN_X[0], MAIN_X[1], MAIN_Y[0], MAIN_Y[1], 0.0, MEMBRANE_THICKNESS
    )
    tab_y = sorted((print_y(LIFT_TAB_Y[0]), print_y(LIFT_TAB_Y[1])))
    tab = translated_box(
        LIFT_TAB_X[0],
        LIFT_TAB_X[1],
        tab_y[0],
        tab_y[1],
        0.0,
        MEMBRANE_THICKNESS,
    )
    solid = plate + tab

    for pad in FIXATION_PADS:
        aperture_width = pad.width - 2.0 * APERTURE_INSET
        aperture_height = pad.height - 2.0 * APERTURE_INSET
        if aperture_width <= 0.0 or aperture_height <= 0.0:
            raise ValueError("Aperture inset consumed a fixation pad")
        aperture_y = print_y(pad.y)
        cutter = translated_box(
            pad.x - aperture_width / 2.0,
            pad.x + aperture_width / 2.0,
            aperture_y - aperture_height / 2.0,
            aperture_y + aperture_height / 2.0,
            -0.05,
            MEMBRANE_THICKNESS + 0.05,
        )
        solid -= cutter

    for locator in LOCATORS:
        peg = Manifold.cylinder(
            PEG_LENGTH,
            locator.peg_base_diameter / 2.0,
            locator.peg_tip_diameter / 2.0,
            24,
        ).translate((locator.x, print_y(locator.y), MEMBRANE_THICKNESS))
        solid += peg

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


def validate_mesh(mesh: trimesh.Trimesh) -> dict[str, object]:
    extents = mesh.extents
    expected_extents = np.array(
        [
            MAIN_X[1] - LIFT_TAB_X[0],
            MAIN_Y[1] - MAIN_Y[0],
            MEMBRANE_THICKNESS + PEG_LENGTH,
        ]
    )
    if not np.allclose(extents, expected_extents, atol=0.002):
        raise ValueError(f"Unexpected STL extents: {extents}, expected {expected_extents}")
    if not mesh.is_watertight:
        raise ValueError("Generated STL is not watertight")
    if not mesh.is_winding_consistent:
        raise ValueError("Generated STL has inconsistent winding")
    if len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("Generated STL is not one connected body")

    diode_body_clearance = DIODE_OFFSET_X - DIODE_BODY_HALF_X - MAIN_X[1]
    diode_courtyard_clearance = (
        DIODE_OFFSET_X - DIODE_COURTYARD_HALF_X - MAIN_X[1]
    )
    if diode_body_clearance < 0.35:
        raise ValueError(f"Insufficient diode body clearance: {diode_body_clearance}")
    if diode_courtyard_clearance < 0.10:
        raise ValueError(
            f"Insufficient diode courtyard clearance: {diode_courtyard_clearance}"
        )

    aperture_rows = []
    for pad in FIXATION_PADS:
        width = pad.width - 2.0 * APERTURE_INSET
        height = pad.height - 2.0 * APERTURE_INSET
        aperture_rows.append(
            {
                "board_center_mm": [pad.x, pad.y],
                "copper_pad_mm": [pad.width, pad.height],
                "aperture_mm": [round(width, 3), round(height, 3)],
                "area_coverage_percent": round(
                    100.0 * width * height / (pad.width * pad.height), 1
                ),
            }
        )

    return {
        "stl": STL_PATH.name,
        "dimensions_print_orientation_mm": [round(float(v), 3) for v in extents],
        "membrane_thickness_mm": MEMBRANE_THICKNESS,
        "peg_length_mm": PEG_LENGTH,
        "aperture_inset_per_edge_mm": APERTURE_INSET,
        "diode_body_clearance_nominal_mm": round(diode_body_clearance, 3),
        "diode_courtyard_clearance_mm": round(diode_courtyard_clearance, 3),
        "fixation_apertures": aperture_rows,
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "connected_bodies": len(mesh.split(only_watertight=False)),
        "triangle_count": int(len(mesh.faces)),
        "volume_mm3": round(float(mesh.volume), 4),
    }


def main() -> int:
    parse_library_geometry()
    switch_count, diode_count, pcb_thickness = parse_board_geometry()
    mesh = export_stl(build_stencil())
    validation = validate_mesh(mesh)

    manifest = {
        "design": "Ducktop2 Rev A MX ULP fixation-pad microstencil",
        "generated_from": {
            "pcb": str(PCB_PATH.relative_to(PROJECT_ROOT)),
            "pcb_sha256": sha256(PCB_PATH),
            "footprint": str(FOOTPRINT_PATH.relative_to(PROJECT_ROOT)),
            "footprint_sha256": sha256(FOOTPRINT_PATH),
            "switch_count": switch_count,
            "diode_count": diode_count,
            "pcb_thickness_mm": pcb_thickness,
        },
        "validation": validation,
        "print_orientation": {
            "stl_is_pre_mirrored": True,
            "bed_side": "flat membrane",
            "pins": "up while printing; down against PCB while using",
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
