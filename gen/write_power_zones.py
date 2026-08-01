#!/usr/bin/env python3
"""
Write first-pass copper zones for the Ducktop2 mainboard.

Implements the stackup plan (review section 9):
  L2 (In1.Cu) solid GND plane
  L5 (In4.Cu) solid GND plane
  L3 (In2.Cu) GND base pour + power islands
  L4 (In3.Cu) GND base pour + power islands

Zones are written UNFILLED (fill no) — refill only in a copied project
(merge_refilled_zone_blocks.py flow), and keep the outlines for review.
The board outline includes the left-edge fin-stack notch.

Usage:
  python3 gen/write_power_zones.py --input ducktop2.kicad_pcb \
      --output /tmp/zones.kicad_pcb
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

from analyze_placement_collisions import parse_board

EDGE = [(0, 0), (0, 124), (51, 124), (51, 176), (0, 176),
        (0, 185), (358, 185), (358, 0)]

POWER_ISLANDS_MM = 12.0   # island padding around each rail's component cluster


def island_rect(fps: dict, net_prefix: str) -> tuple[float, float, float, float] | None:
    """Bounding box of pads whose net contains the prefix, padded."""
    xs: list[float] = []
    ys: list[float] = []
    for ref, fp in fps.items():
        for pad in fp["pads"]:
            net = pad.get("net", "")
            if net_prefix in net:
                cx, cy = pad_abs(pad, fp)
                w = pad["size"][0] if pad["size"] else 0.5
                h = pad["size"][1] if pad["size"] else 0.5
                xs += [cx - w / 2, cx + w / 2]
                ys += [cy - h / 2, cy + h / 2]
    if not xs:
        return None
    return (min(xs) - POWER_ISLANDS_MM, min(ys) - POWER_ISLANDS_MM,
            max(xs) + POWER_ISLANDS_MM, max(ys) + POWER_ISLANDS_MM)


def pad_abs(pad: dict, fp: dict) -> tuple[float, float]:
    fx, fy, fr = fp["at"][0], fp["at"][1], (fp["at"][2] if len(fp["at"]) > 2 else 0.0)
    px, py = pad["at"][0], pad["at"][1]
    if fr:
        r = math.radians(fr)
        px, py = px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)
    return fx + px, fy + py



def keepout_block(layer: str, outline: list[tuple[float, float]], uuid: str) -> str:
    pts = " ".join(f"(xy {x:.4f} {y:.4f})" for x, y in outline)
    return (
        "(zone\n"
        f'\t(net "")\n'
        f'\t(layer "{layer}")\n'
        f'\t(uuid "{uuid}")\n'
        "\t(hatch edge 0.508)\n"
        "\t(keepout (tracks not_allowed) (vias not_allowed) (pads allowed))\n"
        "\t(polygon (pts " + pts + "))\n"
        ")"
    )


def circle_outline(cx: float, cy: float, r: float, n: int = 16) -> list[tuple[float, float]]:
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


KEEPOUT_HOLES_MM = {"H1": 4.0, "H2": 4.0, "H4": 3.0, "H10": 3.0,
                    "H11": 3.0, "H12": 3.0, "H17": 3.0}

def zone_block(net: str, layer: str, outline: list[tuple[float, float]],
               uuid: str) -> str:
    pts = " ".join(f"(xy {x:.4f} {y:.4f})" for x, y in outline)
    return (
        "(zone\n"
        f'\t(net "{net}")\n'
        f'\t(layer "{layer}")\n'
        f'\t(uuid "{uuid}")\n'
        "\t(hatch edge 0.508)\n"
        "\t(connect_pads yes (clearance 0.2))\n"
        "\t(min_thickness 0.2)\n"
        "\t(filled_areas_thickness no)\n"
        f"\t(polygon (pts {pts}))\n"
        ")"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    fps = parse_board(text)

    zones: list[str] = []
    n = 0

    def add(net: str, layer: str, outline: list[tuple[float, float]]) -> None:
        nonlocal n
        n += 1
        zones.append(zone_block(net, layer, outline, f"d5a0000{n:08x}-0000-4000-8000-00000000000{n % 10}"))

    # Solid GND planes on L2/L5 and base pours on L3/L4.
    for layer in ("In1.Cu", "In4.Cu", "In2.Cu", "In3.Cu"):
        add("GND", layer, EDGE)

    # Power islands on L3/L4 for the mainboard rails (actual net names;
    # RADIO_4V0/AON_3V3 from the review live on the radio daughterboard).
    rails = ["VSYS", "SYS_5V", "MCU_3V3", "MU_12V", "SYS_3V3",
             "USB_PORT_5V", "VBUS_RAW", "INTERNAL_USB_VBUS"]
    for rail in rails:
        rect = island_rect(fps, rail)
        if rect is None:
            print(f"no pads found for {rail}; skipping island")
            continue
        x0, y0, x1, y1 = rect
        outline = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        add(rail, "In2.Cu", outline)
        add(rail, "In3.Cu", outline)

    # Keepouts: mounting holes (screw/standoff copper clearance) on all
    # copper layers, and the mic acoustic-port region on L1/L2.
    keepouts: list[str] = []
    for ref, radius in KEEPOUT_HOLES_MM.items():
        fp = fps.get(ref)
        if fp is None:
            continue
        ax, ay = fp["at"][0], fp["at"][1]
        outline = circle_outline(ax, ay, radius)
        for layer in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"):
            keepouts.append(keepout_block(layer, outline, f"d5b0000{len(keepouts):08x}-0000-4000-8000-000000000000"))
    mic = fps.get("MK430")
    if mic is not None:
        mx, my = mic["at"][0], mic["at"][1]
        outline = circle_outline(mx, my, 6.0)
        keepouts.append(keepout_block("F.Cu", outline, "d5b0000ffff000-0000-4000-8000-000000000001"))

    insert = text.rfind("\n)")
    if insert < 0:
        raise SystemExit("no final close paren")
    text = text[:insert] + "\n" + "\n".join(zones) + "\n" + "\n".join(keepouts) + text[insert:]
    print(f"wrote {len(zones)} zones + {len(keepouts)} keepouts")

    args.output.write_text(text, encoding="utf-8")
    print(f"4 GND planes + {2 * len(rails)} power islands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
