#!/usr/bin/env python3
"""Generate the Hirose FH12-100S-0.5SH FPC connector footprint.

The standard KiCad library ships FH12-10/20/30/40/50S but not the 100-pin
variant needed for FPC-1 (75 signals) and FPC-2 (83 signals) in the board
split. The FH12 family is a fixed body geometry: 0.5mm-pitch 0.3x1.3mm pads
on a single row, one 1.8x2.2mm MP hold-down tab at each end, courtyard
= pads +/- 1.4mm. So the 100-pin part is derived from the verified 50-pin
footprint (KiCad's own Hirose_FH12-50S-0.5SH_1x50-1MP_P0.50mm_Horizontal)
by extending the pad array by 50 pins and translating the end graphics by
50 * 0.5 = 25mm.

Pad 1 of the 50-pin part sits at x=-12.25; pad 100 of the 100-pin part
sits at x=-24.75 (= -12.25 - 12.5). Everything mirrored for the right end.

3D model: FH12-100S step not shipped with KiCad, so the 50-pin step is
referenced as a visual placeholder (Phase 4 can drop in the real model).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_ducktop2 import PROJDIR

OUT = os.path.join(PROJDIR, "ducktop2.pretty", "FH12-100S-0.5SH_1x100-1MP_P0.50mm_Horizontal.kicad_mod")

PADS = 100
PITCH = 0.5
EXTRA = (PADS - 50) * PITCH / 2  # 12.5

TAB_X = 14.15 + EXTRA      # MP tab centres
CRTYD_X = 15.55 + EXTRA    # courtyard
SILK_X = 14.15 + EXTRA     # silk outer verticals
FAB_X = 14.05 + EXTRA      # fab body edge
PAD_EDGE = 12.25 + EXTRA   # pad 1 / pad 100 centres


def line(start, end, layer, width=0.12):
    return (
        f"\t(fp_line\n"
        f"\t\t(start {start[0]:g} {start[1]:g})\n"
        f"\t\t(end {end[0]:g} {end[1]:g})\n"
        f"\t\t(stroke\n"
        f"\t\t\t(width {width:g})\n"
        f"\t\t\t(type solid)\n"
        f"\t\t)\n"
        f"\t\t(layer \"{layer}\")\n"
        f"\t)\n"
    )


parts = []
parts.append('(footprint "FH12-100S-0.5SH_1x100-1MP_P0.50mm_Horizontal"')
parts.append("\t(version 20260206)")
parts.append('\t(generator "ducktop2 board-split FH12-100S derivation")')
parts.append('\t(layer "F.Cu")')
parts.append('\t(descr "Hirose FH12, FFC/FPC connector, FH12-100S-0.5SH, 100 Pins per row (board split FPC-1/FPC-2; derived from KiCad FH12-50S)")')
parts.append('\t(tags "connector Hirose FH12 horizontal")')
for prop in (
    ('Reference', "REF**", "F.SilkS", (0, -3.7), "hide no"),
    ('Value', "FH12-100S-0.5SH", "F.Fab", (0, 5.6), ""),
):
    name, val, layer, at, extra = prop
    parts.append(f'\t(property "{name}" "{val}"')
    parts.append(f"\t\t(at {at[0]:g} {at[1]:g} 0)")
    parts.append(f'\t\t(layer "{layer}")')
    if extra:
        parts.append(f"\t\t({extra})")
    parts.append("\t\t(effects")
    parts.append("\t\t\t(font")
    parts.append("\t\t\t\t(size 1 1)")
    parts.append("\t\t\t\t(thickness 0.15)")
    parts.append("\t\t\t)")
    parts.append("\t\t)")
    parts.append("\t)")
parts.append("\t(attr smd)")
parts.append("\t(duplicate_pad_numbers_are_jumpers no)")

# --- silkscreen ---
# left verticals
parts.append(line((-SILK_X, -1.3), (-SILK_X, 0.04), "F.SilkS"))
parts.append(line((-SILK_X, 2.76), (-SILK_X, 4.5), "F.SilkS"))
# top rail
parts.append(line((-SILK_X, 4.5), (SILK_X, 4.5), "F.SilkS"))
# left corner bracket
parts.append(line((-SILK_X + 1.49, -1.3), (-SILK_X, -1.3), "F.SilkS"))
parts.append(line((-SILK_X + 1.49, -1.3), (-SILK_X + 1.49, -2.5), "F.SilkS"))
# right corner bracket
parts.append(line((SILK_X - 1.49, -1.3), (SILK_X, -1.3), "F.SilkS"))
parts.append(line((SILK_X, -1.3), (SILK_X, 0.04), "F.SilkS"))
parts.append(line((SILK_X, 4.5), (SILK_X, 2.76), "F.SilkS"))

# --- courtyard ---
parts.append("\t(fp_rect")
parts.append(f"\t\t(start {-CRTYD_X:g} -3)")
parts.append(f"\t\t(end {CRTYD_X:g} 4.9)")
parts.append("\t\t(stroke")
parts.append("\t\t\t(width 0.05)")
parts.append("\t\t\t(type solid)")
parts.append("\t\t)")
parts.append("\t\t(fill no)")
parts.append('\t\t(layer "F.CrtYd")')
parts.append("\t)")

# --- fab ---
parts.append(line((-FAB_X, -1.2), (-FAB_X, 3.4), "F.Fab", 0.1))
parts.append(line((-FAB_X, 3.4), (-FAB_X + 0.6, 3.4), "F.Fab", 0.1))
parts.append(line((-FAB_X + 0.1, 3.7), (-FAB_X + 0.1, 4.4), "F.Fab", 0.1))
parts.append(line((-FAB_X + 0.1, 4.4), (0, 4.4), "F.Fab", 0.1))
parts.append(line((-FAB_X + 0.6, 3.4), (-FAB_X + 0.6, 3.7), "F.Fab", 0.1))
parts.append(line((-FAB_X + 0.6, 3.7), (-FAB_X + 0.1, 3.7), "F.Fab", 0.1))
# cable-entry chevron (left)
parts.append(line((-FAB_X + 1.3, -1.2), (-FAB_X + 1.8, -0.492893), "F.Fab", 0.1))
parts.append(line((-FAB_X + 1.8, -0.492893), (-FAB_X + 2.3, -1.2), "F.Fab", 0.1))
# bottom body lines
parts.append(line((0, -1.2), (-FAB_X, -1.2), "F.Fab", 0.1))
parts.append(line((0, -1.2), (FAB_X, -1.2), "F.Fab", 0.1))
# right fab mirror
parts.append(line((FAB_X - 0.6, 3.4), (FAB_X - 0.6, 3.7), "F.Fab", 0.1))
parts.append(line((FAB_X - 0.6, 3.7), (FAB_X - 0.1, 3.7), "F.Fab", 0.1))
parts.append(line((FAB_X - 0.1, 3.7), (FAB_X - 0.1, 4.4), "F.Fab", 0.1))
parts.append(line((FAB_X - 0.1, 4.4), (0, 4.4), "F.Fab", 0.1))
parts.append(line((FAB_X, -1.2), (FAB_X, 3.4), "F.Fab", 0.1))
parts.append(line((FAB_X, 3.4), (FAB_X - 0.6, 3.4), "F.Fab", 0.1))
parts.append('\t(fp_text user "${REFERENCE}"')
parts.append("\t\t(at 0 3.7 0)")
parts.append('\t\t(layer "F.Fab")')
parts.append("\t\t(effects")
parts.append("\t\t\t(font")
parts.append("\t\t\t\t(size 1 1)")
parts.append("\t\t\t\t(thickness 0.15)")
parts.append("\t\t\t)")
parts.append("\t\t)")
parts.append("\t)")

# --- pads ---
for i in range(1, PADS + 1):
    x = -PAD_EDGE + (i - 1) * PITCH
    parts.append(f'\t(pad "{i}" smd rect')
    parts.append(f"\t\t(at {x:g} -1.85)")
    parts.append("\t\t(size 0.3 1.3)")
    parts.append('\t\t(layers "F.Cu" "F.Mask" "F.Paste")')
    parts.append("\t)")
for s in (-1, 1):
    parts.append('\t(pad "MP" smd rect')
    parts.append(f"\t\t(at {s * TAB_X:g} 1.4)")
    parts.append("\t\t(size 1.8 2.2)")
    parts.append('\t\t(layers "F.Cu" "F.Mask" "F.Paste")')
    parts.append("\t)")

parts.append("\t(embedded_fonts no)")
parts.append('\t(model "${KICAD10_3DMODEL_DIR}/Connector_FFC-FPC.3dshapes/Hirose_FH12-50S-0.5SH_1x50-1MP_P0.50mm_Horizontal.step"')
parts.append("\t\t(offset")
parts.append("\t\t\t(xyz 0 0 0)")
parts.append("\t\t)")
parts.append("\t\t(scale")
parts.append("\t\t\t(xyz 1 1 1)")
parts.append("\t\t)")
parts.append("\t\t(rotate")
parts.append("\t\t\t(xyz 0 0 0)")
parts.append("\t\t)")
parts.append("\t)")
parts.append(")")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    f.write("\n".join(parts) + "\n")

# --- verification ---
import re
with open(OUT) as f:
    text = f.read()
pads = re.findall(r'\(pad "(\d+)" smd rect\s+\(at ([-\d.]+) -1\.85\)', text)
assert len(pads) == 100, f"expected 100 signal pads, got {len(pads)}"
xs = [float(x) for _, x in pads]
assert abs(xs[0] - -24.75) < 1e-6, xs[0]
assert abs(xs[-1] - 24.75) < 1e-6, xs[-1]
assert all(abs(xs[i + 1] - xs[i] - 0.5) < 1e-6 for i in range(99))
assert text.count('(pad "MP"') == 2
print(f"FH12-100S footprint written: {OUT}")
print(f"  pad span: {xs[0]} .. {xs[-1]} mm ({len(pads)} pads @ 0.5mm), MP tabs at +/-{TAB_X}")