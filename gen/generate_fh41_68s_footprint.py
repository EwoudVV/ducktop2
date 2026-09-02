#!/usr/bin/env python3
"""Generate the FH41-68S-0.5SH footprint (ducktop2 board split, Phase 4 deep audit).

The FH12 series tops out at 60 positions, so the "FH12-100S" used for
FPC-1/FPC-2 was fictional.  The FH41 series (shielded-FFC, 0.5mm pitch,
2.5mm height) offers 68 positions: FH41-68S-0.5SH.  FPC-1 uses pins
1-53, FPC-2 pins 1-61, both fit a 68-pin connector.

Pad geometry per the Hirose FH41-68S-0.5SH(05) drawing (FH41 catalog
D31607_en, 68-position row):
  - 68 signal pads, 0.5mm pitch, x = -16.75 .. +16.75 (span D=33.5),
    y = -2.975, land 0.3x0.65
  - 2 MP hold-down pads at x = +/-18.0 (span J=36), y = 2.275, 0.4x1.55
  - G = 13 SH solder-hold pads at 2.5mm pitch (span E=30); G is ODD so the
    row is CENTER-symmetric: x = 0, +/-2.5, +/-5.0, +/-7.5, +/-10.0,
    +/-12.5, +/-15.0, y = 2.7, land 0.3x1.2.
    (The first cut of this generator linearly extrapolated the FH41-30S
    offset pattern, which is only valid for an EVEN ground-contact count;
    that put all 14 pads 1.25mm off the real terminals.  Never extrapolate
    the SH row from a different pin count.)
  - body length C=38 (fab +/-19.0), silk +/-19.46, courtyard +/-20.0x3.8
    (x2 graphics scale of the 30-pin source, verified against the catalog).
3D model: project-local path (bundled under ducktop2.3dshapes); the KiCad
library ships no FH41 STEP, and a dangling ${KICADxx_3DMODEL_DIR} reference
silently renders nothing.
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
SCALE = 2.0  # 30-pin graphics x-extents -> 68-pin (C=38mm, verified)

# SH ground-contact row per datasheet: G=13 (odd) -> x = 0, +/-2.5*k
SH_PITCH = 2.5
SH_COUNT = 13


def sh_positions():
    xs = [0.0]
    for k in range(1, (SH_COUNT - 1) // 2 + 1):
        xs += [k * SH_PITCH, -k * SH_PITCH]
    assert len(xs) == SH_COUNT and sorted(xs)[SH_COUNT // 2] == 0.0
    return sorted(xs)


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
    for x in sh_positions():
        pads.append(pad_block("SH", x, 2.7, 0.3, 1.2))
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
    print(f"replaced {count} pads with {PINS + 2 + SH_COUNT}")

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

    # --- 3D model: project-local, never a dangling KICADxx_3DMODEL_DIR ---
    txt = re.sub(
        r'\(model "\$\{KICAD\d+_3DMODEL_DIR\}/[^"]*"',
        '(model "${KIPRJMOD}/ducktop2.3dshapes/'
        'Hirose_FH41-68S-0.5SH_1x68_1MP_1SH_P0.5mm_Horizontal.step"',
        txt)

    # --- metadata ---
    txt = txt.replace("Hirose_FH41-30S-0.5SH_1x30_1MP_1SH_P0.5mm_Horizontal",
                      "Hirose_FH41-68S-0.5SH_1x68_1MP_1SH_P0.5mm_Horizontal")
    txt = re.sub(r'\(descr "[^"]*"\)',
                 '(descr "Hirose FH41, FFC/FPC connector, FH41-68S-0.5SH, '
                 '68 Pins per row (board split FPC-1/FPC-2; per FH41 catalog '
                 'D31607 68-position row)")', txt)
    txt = re.sub(r"\(tags \"[^\"]*\"\)", '(tags "connector Hirose FH41 horizontal")', txt)
    txt = re.sub(r"\(property \"Value\" \"[^\"]*\"\n\t\t\(at 0 4\.625 0\)",
                 '(property "Value" "Hirose_FH41-68S-0.5SH_1x68_1MP_1SH_P0.5mm_Horizontal"\n\t\t(at 0 4.625 0)',
                 txt)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(txt)
    print(f"wrote {OUT}")
    verify(OUT)


def verify(path):
    """Self-check: pad count/positions vs the datasheet; hard-fail loudly."""
    txt = open(path).read()
    nums = re.findall(r'\t\(pad "([^"]+)" smd rect\n\t\t\(at ([-\d.]+) ([-\d.]+)\)', txt)
    sig = sorted((float(x), float(y)) for n, x, y in nums if n.isdigit())
    mp = sorted(float(x) for n, x, y in nums if n == "MP")
    sh = sorted(float(x) for n, x, y in nums if n == "SH")
    assert len(sig) == PINS, f"signal pads {len(sig)} != {PINS}"
    assert len(mp) == 2 and mp == [-18.0, 18.0], f"MP wrong: {mp}"
    assert len(sh) == SH_COUNT, f"SH pads {len(sh)} != {SH_COUNT} (datasheet G=13)"
    want = [round(v, 3) for v in sh_positions()]
    got = [round(v, 3) for v in sh]
    assert got == want, f"SH xs {got} != datasheet {want} (E=30, center-symmetric)"
    assert sig[0] == (-16.75, -2.975) and sig[-1] == (16.75, -2.975), \
        f"signal span {sig[0]}..{sig[-1]} != D=33.5"
    assert "KICAD10_3DMODEL_DIR" not in txt and "KICAD8_3DMODEL_DIR" not in txt \
        and "KICAD9_3DMODEL_DIR" not in txt, "dangling version-locked model path"
    fab = re.findall(r'\(fp_rect \(start ([-\d.]+) [-\d.]+\).*?\(end ([\d.]+) [-\d.]+\)[^)]*\)\s*\(layer "F\.Fab"\)', txt, re.S)
    print(f"verify OK: {PINS} sig (D=33.5), 2 MP (J=36), {SH_COUNT} SH "
          f"(E=30, G odd -> x=0, +/-2.5.. +/-15), model=project-local")


if __name__ == "__main__":
    main()
