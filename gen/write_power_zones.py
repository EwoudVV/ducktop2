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
from pathlib import Path

from analyze_placement_collisions import parse_board

EDGE = [(0, 0), (358, 0), (358, 185), (0, 185)]


def pad_abs(pad, fp):
    fx, fy, fr = fp["at"][0], fp["at"][1], (fp["at"][2] if len(fp["at"]) > 2 else 0.0)
    px, py = pad["at"][0], pad["at"][1]
    if fr:
        r = math.radians(fr)
        px, py = px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r)
    return fx + px, fy + py


def island_rect(fps, net):
    xs, ys = [], []
    for _ref, fp in fps.items():
        for pad in fp["pads"]:
            # Exact net-name match.  Pads carry hierarchical names
            # ("/VSYS"); a bare prefix match ("VSYS") would size the island
            # from the right pads but then write a phantom zone net with
            # zero connections (2026-08-26 bug: every L5 island was dead).
            if pad.get("net") != net:
                continue
            cx, cy = pad_abs(pad, fp)
            w = pad["size"][0] if pad["size"] else 0.5
            h = pad["size"][1] if pad["size"] else 0.5
            xs += [cx - w / 2, cx + w / 2]
            ys += [cy - h / 2, cy + h / 2]
    if not xs:
        return None
    MARGIN = 8.0
    return (min(xs) - MARGIN, min(ys) - MARGIN,
            max(xs) + MARGIN, max(ys) + MARGIN)


def clip(outline):
    return [(max(0.0, min(358.0, x)), max(0.0, min(185.0, y)))
            for x, y in outline]


def zone_block(net, layer, outline, stamp):
    pts = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in outline)
    return (
        "(zone\n"
        f'\t(net "{net}")\n'
        f'\t(layer "{layer}")\n'
        f'\t(uuid "d5a0000{stamp:07x}-0000-4000-8000-000000000000")\n'
        "\t(hatch edge 0.508)\n"
        "\t(connect_pads yes (clearance 0.2))\n"
        "\t(min_thickness 0.2)\n"
        "\t(filled_areas_thickness no)\n"
        "\t(fill yes\n"
        "\t\t(thermal_gap 0.5)\n"
        "\t\t(thermal_bridge_width 0.5)\n"
        "\t\t(island_removal_mode 2)\n"
        "\t)\n"
        f"\t(polygon (pts {pts}))\n"
        ")"
    )


def keepout_block(layer, outline, stamp):
    pts = " ".join(f"(xy {x:.3f} {y:.3f})" for x, y in outline)
    return (
        "(zone\n"
        '\t(net "")\n'
        f'\t(layer "{layer}")\n'
        f'\t(uuid "d5b0000{stamp:07x}-0000-4000-8000-000000000000")\n'
        "\t(hatch edge 0.508)\n"
        "\t(keepout (tracks not_allowed) (vias not_allowed) (pads allowed))\n"
        f"\t(polygon (pts {pts}))\n"
        ")"
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
    stamp = 0

    def add(net, layer, outline):
        nonlocal stamp
        stamp += 1
        outline = clip(outline)
        blocks.append(zone_block(net, layer, outline, stamp))

    # GND planes on L2/L4/L7 (In1/In3/In6) — solid reference planes
    for layer in ("In1.Cu", "In3.Cu", "In6.Cu"):
        add("GND", layer, EDGE)

    # Power islands on L5 (In4.Cu) — clipped to board outline.
    # NOTE: rails MUST be the exact hierarchical net names as written on
    # the pads ("/VSYS", not "VSYS").  A bare name creates a phantom net
    # with zero pads: the island fills as isolated dead copper.
    # VBUS_RAW is two distinct nets on this board (one per PD port) and
    # cannot share a single zone, so it is listed twice.
    rails = ["/VSYS", "/SYS_5V", "/MCU_3V3", "/MU_12V", "/SYS_3V3",
             "/USB_PORT_5V", "/PD1_VBUS_RAW", "/PD2_VBUS_RAW",
             "/Mu Carrier/INTERNAL_USB_VBUS"]
    for rail in rails:
        rect = island_rect(fps, rail)
        if rect is None:
            print(f"no pads for {rail}; skipping")
            continue
        outline = [(rect[0], rect[1]), (rect[2], rect[1]),
                   (rect[2], rect[3]), (rect[0], rect[3])]
        clipped = clip(outline)
        add(rail, "In4.Cu", clipped)

    # Keepouts: mounting holes + mic region
    for ref in fps:
        if not ref.startswith("H"):
            continue
        ax, ay = fps[ref]["at"][0], fps[ref]["at"][1]
        for layer in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In6.Cu", "B.Cu"):
            blocks.append(keepout_block(layer, clip(circle(ax, ay, KEEPOUT_RADIUS)), stamp))
            stamp += 1

    # Mic acoustic keepout on every copper layer the pours touch (radius 5mm).
    # The GND planes (In1/In4) and the power islands (In2/In3) must not bring
    # copper within the 0.3 mm hole clearance of the bottom-port acoustic
    # opening (the pad-level DRU rule only covers pad/pad pairs).
    mic = fps.get("MK430")
    if mic:
        for layer in ("F.Cu", "In1.Cu", "In3.Cu", "In4.Cu", "In6.Cu"):
            blocks.append(keepout_block(layer, clip(circle(mic["at"][0], mic["at"][1], 5.0)), stamp))
            stamp += 1

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
