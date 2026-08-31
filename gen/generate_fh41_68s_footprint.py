#!/usr/bin/env python3
"""Generate the FH41-68S-0.5SH footprint (ducktop2 board split, Phase 4 deep audit).

The FH12 series tops out at 60 positions, so the "FH12-100S" used for
FPC-1/FPC-2 was fictional.  The FH41 series (shielded-FFC, 0.5mm pitch,
2.5mm height) offers 68 positions: FH41-68S-0.5SH.  FPC-1 uses pins
1-53, FPC-2 pins 1-61, both fit a 68-pin connector.

Derived from KiCad's Hirose_FH41-30S-0.5SH footprint:
  - 68 signal pads, 0.5mm pitch, x = +/-16.75, y = -2.975, 0.3x0.65
  - 2 MP hold-down pads at x = +/-18.0, y = 2.275, 0.4x1.55
  - 14 SH solder-hold pads at 2.5mm steps (x = +/-1.25 .. +/-16.25),
    y = 2.7, 0.3x1.2
  - body/courtyard x-extents scaled x2 from the 30-pin (38mm catalog
    length for 68 positions)
The 3D model points at the FH41-30S step (placeholder).
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

from build_ducktop2 import U

SRC = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/Connector_FFC-FPC.pretty/Hirose_FH41-30S-0.5SH_1x30_1MP_1SH_P0.5mm_Horizontal.kicad_mod"
OUT = os.path.join(os.path.dirname(__file__), "..", "ducktop2.pretty",
                   "Hirose_FH41-68S-0.5SH_1x68_1MP_1SH_P0.5mm_Horizontal.kicad_mod")
PINS = 68
SCALE = 2.0  # 30-pin half-length ~9.6mm -> 68-pin ~19.2mm


def main():
    txt = open(SRC).read()

    # --- splice: replace every old pad block with generated ones ---
    def pad_block(num, x, y, w, h):
        return (
            f'\t(pad "{num}" smd rect\n'
            f"\t\t(at {x:g} {y:g})\n"
            f"\t\t(size {w:g} {h:g})\n"
            f'\t\t(layers "F.Cu" "F.Mask" "F.Paste")\n'
            f"\t\t(uuid {U()})\n"
            f"\t)"
        )

    half = (PINS - 1) * 0.5 / 2  # 16.75
    pads = []
    for n in range(1, PINS + 1):
        pads.append(pad_block(n, -half + (n - 1) * 0.5, -2.975, 0.3, 0.65))
    for sign in (-1, 1):
        pads.append(pad_block("MP", sign * (half + 1.25), 2.275, 0.4, 1.55))
    for k in range(0, 7):
        for sign in (-1, 1):
            pads.append(pad_block("SH", sign * (1.25 + 2.5 * k), 2.7, 0.3, 1.2))
    new_pads = "\n".join(pads)

    pos = 0
    out = []
    count = 0
    while True:
        m = re.search(r'\t\(pad "([^"]+)" smd', txt[pos:])
        if not m:
            out.append(txt[pos:])
            break
        start = pos + m.start()
        depth = 0
        j = start
        while j < len(txt):
            if txt[j] == "(":
                depth += 1
            elif txt[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(txt[pos:start])
        if count == 0:
            out.append(new_pads)
        pos = j + 1
        count += 1
    txt = "".join(out)
    print(f"replaced {count} pads with {PINS + 2 + 14}")

    # --- rescale graphics x-extents ---
    # KiCad fp_line/fp_rect write (start x y) and (end x y) on separate
    # lines; rescale the first coordinate of each.
    def rescale_xy(m):
        kw, x1, y1 = m.group(1), m.group(2), m.group(3)
        return f"{kw}{float(x1) * SCALE:g} {y1})"

    txt = re.sub(r"(\(start )([-\d.]+) ([-\d.]+)\)",
                 rescale_xy, txt)
    txt = re.sub(r"(\(end )([-\d.]+) ([-\d.]+)\)",
                 rescale_xy, txt)

    # --- metadata ---
    txt = txt.replace("Hirose_FH41-30S-0.5SH_1x30_1MP_1SH_P0.5mm_Horizontal",
                      "Hirose_FH41-68S-0.5SH_1x68_1MP_1SH_P0.5mm_Horizontal")
    txt = re.sub(r'\(descr "[^"]*"\)',
                 '(descr "Hirose FH41, FFC/FPC connector, FH41-68S-0.5SH, '
                 '68 Pins per row (board split FPC-1/FPC-2; derived from the '
                 'KiCad FH41-30S)")', txt)
    txt = re.sub(r"\(tags \"[^\"]*\"\)", '(tags "connector Hirose FH41 horizontal")', txt)
    txt = re.sub(r"\(property \"Value\" \"[^\"]*\"\n\t\t\(at 0 4\.625 0\)",
                 '(property "Value" "Hirose_FH41-68S-0.5SH_1x68_1MP_1SH_P0.5mm_Horizontal"\n\t\t(at 0 4.625 0)',
                 txt)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(txt)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()