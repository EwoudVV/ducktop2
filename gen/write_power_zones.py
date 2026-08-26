#!/usr/bin/env python3
"""
Write first-pass copper zones and keepouts for the Ducktop2 mainboard.

  L2/L4/L7 (In1/In3/In6): solid GND planes.
  L5 (In4.Cu): power-rail islands, clipped to the board outline.  In2/In3
    (L3/L4) stay clear for the impedance pairs and general routing per the
    HIGH_SPEED_ROUTING_PLAN stackup.  Islands keep (island_removal_mode 2)
    so unconnected planes survive until the routing phase vias them in.
  Keepouts: mounting-hole screw clearance on all copper layers + mic
    acoustic region on F.Cu.

Usage:
  python3 gen/write_power_zones.py --input ducktop2.kicad_pcb \
      --output ducktop2.kicad_pcb
"""

from __future__ import annotations

import argparse
import math
import re
import uuid
from pathlib import Path

from analyze_placement_collisions import parse_board

EDGE = [(0, 0), (358, 0), (358, 185), (0, 185)]
UUID_NAMESPACE = uuid.UUID("6942fd12-9188-40a4-88ed-bb7d10608370")

# Source-local L5 copper. Long distribution to remote consumers is routed by
# hand; bounding every consumer created overlapping board-scale zones.
POWER_ISLANDS = {
    "/PD1_VBUS_RAW": [(1.0, 19.0, 75.0, 67.0)],
    "/PD2_VBUS_RAW": [(315.0, 19.0, 357.0, 84.0)],
    "/SYS_3V3": [(124.0, 19.0, 151.0, 44.0)],
    "/USB_PORT_5V": [(157.0, 19.0, 181.0, 45.0)],
    "/MU_12V": [(145.0, 69.0, 181.0, 99.0)],
    "/SYS_5V": [(119.0, 83.0, 143.0, 109.0)],
    "/Mu Carrier/INTERNAL_USB_VBUS": [(184.0, 83.0, 209.0, 101.0)],
    "/Mu Carrier/PCIE_3V3_IN": [(210.0, 83.0, 265.0, 117.0)],
    "/MCU_3V3": [(270.0, 85.0, 306.0, 103.0)],
    "/VSYS": [(54.0, 114.0, 119.0, 156.0)],
    "/Maker MCU/MAKER_3V3_CORE": [(247.0, 8.0, 308.0, 82.0)],
}


def pad_abs(pad, fp):
    fx, fy, fr = fp["at"][0], fp["at"][1], (fp["at"][2] if len(fp["at"]) > 2 else 0.0)
    px, py = pad["at"][0], pad["at"][1]
    if fr:
        r = math.radians(fr)
        px, py = px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)
    return fx + px, fy + py


def validate_power_islands(fps):
    nets = {pad.get("net") for fp in fps.values() for pad in fp["pads"]}
    missing = sorted(set(POWER_ISLANDS) - nets)
    if missing:
        raise RuntimeError(f"power islands name nets with no pads: {missing}")

    boxes = [(net, box) for net, items in POWER_ISLANDS.items() for box in items]
    for index, (net_a, a) in enumerate(boxes):
        if not (0.0 <= a[0] < a[2] <= 358.0 and 0.0 <= a[1] < a[3] <= 185.0):
            raise RuntimeError(f"out-of-bounds power island {net_a}: {a}")
        for net_b, b in boxes[index + 1:]:
            x_gap = max(a[0] - b[2], b[0] - a[2], 0.0)
            y_gap = max(a[1] - b[3], b[1] - a[3], 0.0)
            if x_gap == 0.0 and y_gap == 0.0:
                raise RuntimeError(f"overlapping power islands: {net_a} / {net_b}")
            if x_gap < 1.0 and y_gap < 1.0:
                raise RuntimeError(f"power-island gap below 1 mm: {net_a} / {net_b}")


def clip(outline):
    return [(max(0.0, min(358.0, x)), max(0.0, min(185.0, y)))
            for x, y in outline]


def stable_uuid(key):
    return str(uuid.uuid5(UUID_NAMESPACE, key))


def zone_block(net, layer, outline, key):
    pts = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in outline)
    return (
        "\t(zone\n"
        f'\t\t(net "{net}")\n'
        f'\t\t(layer "{layer}")\n'
        f'\t\t(uuid "{stable_uuid(key)}")\n'
        "\t\t(hatch edge 0.508)\n"
        "\t\t(connect_pads yes (clearance 0.2))\n"
        "\t\t(min_thickness 0.2)\n"
        "\t\t(filled_areas_thickness no)\n"
        "\t\t(fill yes\n"
        "\t\t\t(thermal_gap 0.5)\n"
        "\t\t\t(thermal_bridge_width 0.5)\n"
        "\t\t\t(island_removal_mode 2)\n"
        "\t\t)\n"
        f"\t\t(polygon (pts {pts}))\n"
        "\t)"
    )


def keepout_block(layer, outline, key):
    pts = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in outline)
    return (
        "\t(zone\n"
        '\t\t(net "")\n'
        f'\t\t(layer "{layer}")\n'
        f'\t\t(uuid "{stable_uuid(key)}")\n'
        "\t\t(hatch edge 0.508)\n"
        "\t\t(keepout (tracks not_allowed) (vias not_allowed) (pads allowed))\n"
        f"\t\t(polygon (pts {pts}))\n"
        "\t)"
    )


def circle(cx, cy, r, n=16):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


KEEPOUT_RADIUS = 3.5   # mm around each mounting hole


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    fps = parse_board(text)
    validate_power_islands(fps)

    # Remove any existing zones from the source text
    depth = 0; i = 0; out = []; last = 0
    while i < len(text):
        c = text[i]
        if c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1; continue
        if c == '(':
            depth += 1
            m = re.match(r'\(([A-Za-z0-9_.]+)', text[i:])
            token = m.group(1) if m else ""
            if depth == 2 and token == "zone":
                d = 1; k = i + 1
                while k < len(text):
                    if text[k] == '"':
                        k += 1
                        while k < len(text) and text[k] != '"':
                            k += 2 if text[k] == "\\" else 1
                        k += 1; continue
                    if text[k] == '(': d += 1
                    elif text[k] == ')':
                        d -= 1
                        if d == 0: break
                    k += 1
                out.append(text[last:i])
                last = k + 1
                i = k + 1
                depth -= 1
                continue
            i += len(m.group(0)) if m else 1
        elif c == ')':
            depth -= 1; i += 1
        else:
            i += 1
    out.append(text[last:])
    text = "".join(out)

    # Collect zones + keepouts
    blocks = []
    def add(net, layer, outline, key):
        outline = clip(outline)
        blocks.append(zone_block(net, layer, outline, key))

    # GND planes on L2/L4/L7 (In1/In3/In6) — solid reference planes
    for layer in ("In1.Cu", "In3.Cu", "In6.Cu"):
        add("GND", layer, EDGE, f"gnd:{layer}")

    for rail, rectangles in POWER_ISLANDS.items():
        for index, rect in enumerate(rectangles):
            outline = [(rect[0], rect[1]), (rect[2], rect[1]),
                       (rect[2], rect[3]), (rect[0], rect[3])]
            add(rail, "In4.Cu", outline, f"power:{rail}:{index}")

    # Keepouts: mounting holes + mic region
    for ref in fps:
        if not ref.startswith("H"):
            continue
        ax, ay = fps[ref]["at"][0], fps[ref]["at"][1]
        for layer in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu", "B.Cu"):
            blocks.append(keepout_block(
                layer, clip(circle(ax, ay, KEEPOUT_RADIUS)), f"hole:{ref}:{layer}"))

    # The acoustic port is a routing keepout on every copper layer.
    mic = fps.get("MK430")
    if mic:
        for layer in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu", "B.Cu"):
            blocks.append(keepout_block(
                layer, clip(circle(mic["at"][0], mic["at"][1], 5.0)),
                f"mic:MK430:{layer}"))

    # Insert before the final kicad_pcb close
    insert = text.rfind("\n)")
    if insert < 0:
        raise SystemExit("no final close paren")
    text = text[:insert] + "\n" + "\n".join(blocks) + text[insert:]

    print(f"{len(blocks)} zones+keepouts written")
    args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
