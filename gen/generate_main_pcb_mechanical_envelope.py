#!/usr/bin/env python3
"""Generate the ducktop2 main PCB mechanical outline.

This intentionally creates no component footprints, tracks, zones, or nets.
The floorplan JSON remains the planning reference, but the PCB file gets only
Edge.Cuts geometry so routing/placement can start on a clean canvas.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FLOORPLAN = ROOT / "mechanical" / "floorplan_revA.json"
OUT = ROOT / "ducktop2.kicad_pcb"

UUID_NS = uuid.uuid5(uuid.NAMESPACE_URL, "ducktop2/main-pcb-mechanical-envelope")


def stable_uuid(name: str) -> str:
    return str(uuid.uuid5(UUID_NS, name))


def fmt(value: float) -> str:
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def stroke(width: float, line_type: str = "solid") -> str:
    return (
        "\t\t(stroke\n"
        f"\t\t\t(width {fmt(width)})\n"
        f"\t\t\t(type {line_type})\n"
        "\t\t)\n"
    )


def gr_line(x1: float, y1: float, x2: float, y2: float, layer: str, uid: str, width: float = 0.1, line_type: str = "solid") -> str:
    return (
        "\t(gr_line\n"
        f"\t\t(start {fmt(x1)} {fmt(y1)})\n"
        f"\t\t(end {fmt(x2)} {fmt(y2)})\n"
        f"{stroke(width, line_type)}"
        f"\t\t(layer {q(layer)})\n"
        f"\t\t(uuid {q(uid)})\n"
        "\t)\n"
    )


def gr_polyline(points: list[tuple[float, float]], layer: str, uid_prefix: str, width: float = 0.1, line_type: str = "solid") -> list[str]:
    closed = points if points[0] == points[-1] else points + [points[0]]
    lines = []
    for idx, ((x1, y1), (x2, y2)) in enumerate(zip(closed, closed[1:])):
        lines.append(gr_line(x1, y1, x2, y2, layer, stable_uuid(f"{uid_prefix}-{idx}"), width, line_type))
    return lines


def part_world(part: dict, planes: dict) -> tuple[float, float, float, float]:
    plane = planes[part["zone"]]
    return plane["x"] + part["x"], plane["y"] + part["y"], part["w"], part["h"]


def part_by_id(data: dict, part_id: str) -> dict:
    for part in data["parts"]:
        if part["id"] == part_id:
            return part
    raise KeyError(part_id)


def expanded_rect(data: dict, part_id: str, margin: float) -> tuple[float, float, float, float]:
    planes = data["planes"]
    x, y, w, h = part_world(part_by_id(data, part_id), planes)
    base = planes["base"]
    x1 = max(base["x"], x - margin)
    y1 = max(base["y"], y - margin)
    x2 = min(base["x"] + base["w"], x + w + margin)
    y2 = min(base["y"] + base["h"], y + h + margin)
    return x1, y1, x2, y2


def rect_points(x1: float, y1: float, x2: float, y2: float) -> list[tuple[float, float]]:
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def edge_cut_items(data: dict) -> list[str]:
    base = data["planes"]["base"]
    bx, by, bw, bh = base["x"], base["y"], base["w"], base["h"]
    margin = 2.0

    items = gr_polyline([
        (bx, by),
        (bx + bw, by),
        (bx + bw, by + bh),
        (bx, by + bh),
    ], "Edge.Cuts", "edge-main-outline")

    cutouts: list[list[tuple[float, float]]] = []
    for part_id in ["battery-1", "battery-2", "battery-3"]:
        x1, y1, x2, y2 = expanded_rect(data, part_id, margin)
        cutouts.append(rect_points(x1, y1, x2, y2))

    screen = expanded_rect(data, "screen-pcb", margin)
    sx1, sy1, sx2, sy2 = screen
    cutouts.append(rect_points(sx1, sy1, sx2, sy2))

    for idx, points in enumerate(cutouts):
        items.extend(gr_polyline(points, "Edge.Cuts", f"edge-cutout-{idx}"))
    return items


def generated_board(data: dict) -> str:
    items: list[str] = []

    # Actual rough board outline and internal relief cuts.
    items.extend(edge_cut_items(data))

    body = "".join(items)
    return f"""(kicad_pcb
\t(version 20260206)
\t(generator "pcbnew")
\t(generator_version "10.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(paper "A3")
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(2 "B.Cu" signal)
\t\t(9 "F.Adhes" user "F.Adhesive")
\t\t(11 "B.Adhes" user "B.Adhesive")
\t\t(13 "F.Paste" user)
\t\t(15 "B.Paste" user)
\t\t(5 "F.SilkS" user "F.Silkscreen")
\t\t(7 "B.SilkS" user "B.Silkscreen")
\t\t(1 "F.Mask" user)
\t\t(3 "B.Mask" user)
\t\t(17 "Dwgs.User" user "User.Drawings")
\t\t(19 "Cmts.User" user "User.Comments")
\t\t(21 "Eco1.User" user "User.Eco1")
\t\t(23 "Eco2.User" user "User.Eco2")
\t\t(25 "Edge.Cuts" user)
\t\t(27 "Margin" user)
\t\t(31 "F.CrtYd" user "F.Courtyard")
\t\t(29 "B.CrtYd" user "B.Courtyard")
\t\t(35 "F.Fab" user)
\t\t(33 "B.Fab" user)
\t\t(39 "User.1" user)
\t\t(41 "User.2" user)
\t\t(43 "User.3" user)
\t\t(45 "User.4" user)
\t\t(47 "User.5" user)
\t\t(49 "User.6" user)
\t\t(51 "User.7" user)
\t\t(53 "User.8" user)
\t\t(55 "User.9" user)
\t)
\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00000000_00000000_000010fc_ffffffff)
\t\t\t(plot_on_all_layers_selection 0x00000000_00000000_00000000_00000000)
\t\t\t(disableapertmacros no)
\t\t\t(usegerberextensions no)
\t\t\t(usegerberattributes yes)
\t\t\t(usegerberadvancedattributes yes)
\t\t\t(creategerberjobfile yes)
\t\t\t(svgprecision 4)
\t\t\t(plotframeref no)
\t\t\t(mode 1)
\t\t\t(useauxorigin no)
\t\t\t(pdf_front_fp_property_popups yes)
\t\t\t(pdf_back_fp_property_popups yes)
\t\t\t(pdf_metadata yes)
\t\t\t(pdf_single_document no)
\t\t\t(dxfpolygonmode yes)
\t\t\t(dxfimperialunits yes)
\t\t\t(dxfusepcbnewfont yes)
\t\t\t(psnegative no)
\t\t\t(plot_black_and_white yes)
\t\t\t(sketchpadsonfab no)
\t\t\t(plotpadnumbers no)
\t\t\t(hidednponfab no)
\t\t\t(sketchdnponfab yes)
\t\t\t(crossoutdnponfab yes)
\t\t\t(subtractmaskfromsilk no)
\t\t\t(outputformat 1)
\t\t\t(mirror no)
\t\t\t(drillshape 0)
\t\t\t(scaleselection 1)
\t\t\t(outputdirectory "")
\t\t)
\t)
{body}\t(embedded_fonts no)
)
"""


def main() -> None:
    data = json.loads(FLOORPLAN.read_text())
    OUT.write_text(generated_board(data))


if __name__ == "__main__":
    main()
