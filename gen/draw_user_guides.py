#!/usr/bin/env python3
"""
Regenerate the Dwgs.User guide layer to reflect the CURRENT board.

Removes every Dwgs.User graphic, then re-draws:
  - component labels with a leader line to the component's live position
  - module/area outlines: Mu module, NVMe 2280, Wi-Fi 2230, trackpad zone,
    provisional hinge cutouts (40x20 at (8,0)/(310,0) until task-2 hinge
    geometry lands)

Labels carry the component reference as the first token so the leader can
be re-targeted automatically whenever a part moves.
"""

from __future__ import annotations

import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "ducktop2.kicad_pcb"

# anchor: (x, y) on Dwgs.User where the label text sits.
ANCHORS: dict[str, tuple[float, float]] = {
    "J22": (2.59, 21.38), "J21": (2.59, 43.88), "J23": (2.59, 66.38),
    "J420": (16.225, 179.3), "MK430": (39.725, 110.94), "J422": (49.8, 3.1),
    "J2300": (57.25, 183.315), "J52": (57.97, 119.3), "J2": (89.53, 165.15),
    "U425": (138.825, 157.625), "J58": (171.3, 130.9), "A1": (177.075, 8.2),
    "J10": (197.475, 106.275), "J40": (228.95, 157.525), "J45": (280.35, 156.15),
    "J41": (310.35, 156.15), "J310": (318.9, 41.75), "J500": (331.475, 88.72),
    "J11": (344.5, 26.0),  # J11 now sits at the top of the right edge (353.475, 30)
    "J30": (348.905, 66.0), "J12": (351.315, 44.38),
}

LABELS: dict[str, str] = {
    "J22": "J22 left USB-C receptacle #1",
    "J21": "J21 left USB-C receptacle #2",
    "J23": "J23 left USB-C receptacle #3",
    "J420": "J420 speaker connector",
    "MK430": "MK430 MEMS microphone",
    "J422": "J422 3.5mm headphone jack",
    "J2300": "J2300 radio daughterboard connector",
    "J52": "J52 12V fan connector",
    "J2": "J2 Mega-Fit battery connector",
    "U425": "U425 TPA6130A2 headphone amp",
    "J58": "J58 trackpad USB2 solder lands",
    "A1": "A1 LattePanda Mu module",
    "J10": "J10 M.2 2280 NVMe socket",
    "J40": "J40 M.2 E-key Wi-Fi socket",
    "J45": "J45 SSD1306 OLED B",
    "J41": "J41 SSD1306 OLED A",
    "J310": "J310 keyboard FFC connector",
    "J500": "J500 JXD1-1022NL Ethernet jack (mid-mount)",
    "J11": "J11 right USB-C receptacle",
    "J30": "J30 HDMI-A receptacle",
    "J12": "J12 right USB-C receptacle (rear)",
}

# provisional hinge cutouts - replaced by real hinge geometry (task 2)
HINGE_KEEPOUTS = [(8, 0, 40, 20), (310, 0, 40, 20)]


def component_positions(text: str) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for block in re.finditer(r'\t\(footprint "([^"]+)"[\s\S]*?\n\t\)', text):
        ref = re.search(r'\(property "Reference" "([^"]+)"', block.group(0))
        at = re.search(r'\t\t\(at ([-\d.]+) ([-\d.]+)', block.group(0))
        if ref and at:
            out[ref.group(1)] = (float(at.group(1)), float(at.group(2)))
    return out


def U() -> str:
    return str(uuid.uuid4())


def gr_text(text: str, x: float, y: float) -> str:
    return (
        f'(gr_text "{text}"\n'
        f'\t(at {x} {y} 0)\n'
        f'\t(layer "Dwgs.User")\n'
        f'\t(uuid "{U()}")\n'
        f'\t(effects\n'
        f'\t\t(font\n'
        f'\t\t\t(size 1.15 1.15)\n'
        f'\t\t\t(thickness 0.16)\n'
        f'\t\t)\n'
        f'\t\t(justify left)\n'
        f'\t)\n'
        f')\n'
    )


def gr_line(x1: float, y1: float, x2: float, y2: float) -> str:
    return (
        f'(gr_line\n'
        f'\t(start {x1} {y1})\n'
        f'\t(end {x2} {y2})\n'
        f'\t(stroke (width 0.1) (type default))\n'
        f'\t(layer "Dwgs.User")\n'
        f'\t(uuid "{U()}")\n'
        f')\n'
    )


def gr_rect(x1: float, y1: float, x2: float, y2: float) -> str:
    return (
        f'(gr_rect\n'
        f'\t(start {x1} {y1})\n'
        f'\t(end {x2} {y2})\n'
        f'\t(stroke (width 0.1) (type dash))\n'
        f'\t(layer "Dwgs.User")\n'
        f'\t(uuid "{U()}")\n'
        f')\n'
    )


def main() -> int:
    text = BOARD.read_text(encoding="utf-8")
    positions = component_positions(text)

    # strip existing Dwgs.User graphics (line/text/rect/arc) at top level
    depth = 0
    i = 0
    out: list[str] = []
    last = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            i += 1
            continue
        if c == "(":
            depth += 1
            m = re.match(r"\(([a-z_]+)", text[i:])
            token = m.group(1) if m else ""
            if depth == 2 and token in ("gr_line", "gr_text", "gr_rect", "gr_arc", "gr_circle"):
                d = 1
                k = i + 1
                while k < n:
                    if text[k] == '"':
                        k += 1
                        while k < n and text[k] != '"':
                            k += 2 if text[k] == "\\" else 1
                        k += 1
                        continue
                    if text[k] == "(":
                        d += 1
                    elif text[k] == ")":
                        d -= 1
                        if d == 0:
                            break
                    k += 1
                blk = text[i:k + 1]
                if '(layer "Dwgs.User")' in blk:
                    out.append(text[last:i])
                    last = k + 1
                i = k + 1
                depth -= 1
                continue
            i += len(m.group(0)) if m else 1
        elif c == ")":
            depth -= 1
            i += 1
        else:
            i += 1
    out.append(text[last:])
    text = "".join(out)

    blocks: list[str] = []
    for ref, label in LABELS.items():
        ax, ay = ANCHORS[ref]
        blocks.append(gr_text(label, ax, ay))
        pos = positions.get(ref)
        if pos:
            blocks.append(gr_line(ax, ay + 0.5, pos[0], pos[1]))

    # module area outlines (dashed) from live positions
    if "A1" in positions:
        x, y = positions["A1"]
        blocks.append(gr_rect(x - 38.75, y - 32.75, x + 38.75, y + 32.75))  # Mu carrier
    if "J10" in positions:
        x, y = positions["J10"]
        blocks.append(gr_rect(x - 3, y - 11, x + 77, y + 11))  # NVMe 2280 card
    if "J40" in positions:
        x, y = positions["J40"]
        blocks.append(gr_rect(x - 3, y - 11, x + 27, y + 11))  # Wi-Fi 2230 card
    # trackpad zone (palmrest height above the battery band)
    blocks.append(gr_rect(109, 143, 249, 185))
    # provisional hinge keepouts
    for hx, hy, hw, hh in HINGE_KEEPOUTS:
        blocks.append(gr_rect(hx, hy, hx + hw, hy + hh))

    insert = text.rfind("\n)")
    if insert < 0:
        raise SystemExit("no final close paren")
    text = text[:insert] + "\n" + "\n".join(blocks) + text[insert:]
    BOARD.write_text(text, encoding="utf-8")
    print(f"{len(blocks)} Dwgs.User items written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())