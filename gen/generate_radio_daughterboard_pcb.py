#!/usr/bin/env python3
"""Create the initial placed PCB for the removable radio daughterboard.

This is intentionally an initial-placement generator, not a router.  It refuses
to replace a board containing tracks or vias unless explicitly forced, so later
manual RF and power routing remains authoritative.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

import sync_main_pcb_from_netlist as pcb


ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = ROOT / "radio_daughterboard"
SCHEMATIC = BOARD_DIR / "radio_daughterboard.kicad_sch"
NETLIST = BOARD_DIR / "radio_daughterboard.net"
BOARD = BOARD_DIR / "radio_daughterboard.kicad_pcb"
KICAD_CLI = Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
KICAD_PYTHON = Path("/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3")


def grid(refs, xs, ys, rotation=0.0):
    positions = [(x, y, rotation) for y in ys for x in xs]
    if len(positions) < len(refs):
        raise ValueError(f"not enough placement slots for {refs}")
    return dict(zip(refs, positions))


ANCHORS = {
    # Mechanical support and mainboard interface.
    "H1": (24.0, 24.0, 0.0),
    "H2": (136.0, 24.0, 0.0),
    "H3": (24.0, 86.0, 0.0),
    "H4": (136.0, 86.0, 0.0),
    "J1": (80.0, 86.0, 0.0),
    "U1": (80.0, 77.0, 0.0),
    "C1": (74.0, 78.0, 0.0),
    "C2": (74.0, 74.0, 0.0),
    "C3": (78.0, 73.0, 0.0),
    "C4": (84.0, 74.0, 0.0),
    "C5": (87.5, 77.0, 0.0),

    # Rear-edge RF launches and short 50-ohm chains.
    "J241": (43.0, 20.0, 270.0),
    "J251": (112.0, 20.0, 270.0),
    "J240": (55.5, 28.0, 0.0),
    "J250": (122.0, 28.0, 0.0),
    "U240": (45.5, 29.5, 0.0),
    "U250": (106.5, 29.5, 0.0),
    "FL240": (35.0, 31.5, 0.0),
    "FL250": (96.0, 31.5, 0.0),
    "C243": (49.5, 35.5, 0.0),
    "C244": (50.0, 32.5, 0.0),
    "C245": (39.0, 25.5, 0.0),
    "C253": (113.5, 26.5, 0.0),
    "C254": (111.0, 32.5, 0.0),
    "C255": (100.0, 25.5, 0.0),
    "C270": (40.25, 31.5, 0.0),
    "C271": (44.5, 25.0, 90.0),
    "C272": (50.5, 28.0, 0.0),
    "C273": (101.25, 31.5, 0.0),
    "C274": (109.5, 25.0, 90.0),
    "C275": (113.5, 28.0, 0.0),

    # The two castellated modules face their RF pins toward the rear filters.
    "J70": (48.0, 49.0, 180.0),
    "J71": (109.0, 49.0, 180.0),

    # Dedicated 5 V to 4 V radio buck in the gap between the modules.
    "U70": (76.0, 35.0, 0.0),
    "L70": (83.0, 35.0, 0.0),
    "C220": (71.0, 30.0, 0.0),
    "C221": (71.0, 34.0, 0.0),
    "C222": (87.0, 30.0, 0.0),
    "C223": (86.0, 44.0, 0.0),
    "C224": (82.5, 40.0, 0.0),
    "C225": (82.0, 46.5, 0.0),
    "R220": (72.0, 39.0, 0.0),
    "R221": (76.0, 41.0, 0.0),
    "R222": (80.0, 41.0, 0.0),

    # Reset-safe PTT interlock between the two radio domains.
    "U260": (72.0, 64.0, 0.0),
    "C260": (72.0, 68.0, 0.0),
    "U261": (81.0, 64.0, 0.0),
    "C261": (81.0, 68.0, 0.0),

    # Radio-side translators and antenna-select controls.
    "U241": (32.0, 63.5, 0.0),
    "U242": (39.0, 63.5, 0.0),
    "U243": (46.0, 63.5, 0.0),
    "U251": (101.0, 63.5, 0.0),
    "U252": (108.0, 63.5, 0.0),
    "U253": (115.0, 63.5, 0.0),
    "R235": (55.0, 63.5, 0.0),
    "R237": (59.0, 63.5, 0.0),
    "R236": (123.0, 63.5, 0.0),
    "R238": (127.0, 63.5, 0.0),

    # USB audio codec and GNSS ICs occupy opposite lower corners.
    "U330": (56.0, 82.0, 90.0),
    "Y330": (67.0, 82.0, 0.0),
    "U40": (117.0, 81.0, 0.0),
    "U41": (104.0, 81.0, 90.0),
    "J42": (129.0, 79.0, 0.0),
}


ANCHORS.update(grid(
    ["C240", "C246", "C247", "C248", "R225", "R227", "R229",
     "R230", "R242", "R243", "R233", "C226"],
    [31.0, 35.0, 39.0, 43.0, 47.0, 51.0, 55.0],
    [68.0, 72.0],
))
ANCHORS.update(grid(
    ["C250", "C256", "C257", "C258", "R226", "R228", "R231",
     "R232", "R260", "R261", "R234", "C227"],
    [99.0, 103.0, 107.0, 111.0, 115.0, 119.0, 123.0],
    [68.0, 72.0],
))


CODEC_SMALL = [
    "C330", "C331", "C332", "C333", "C334", "C335", "C337", "C338", "C339",
    "C340", "C341", "C342", "C343", "D390", "D391", "D392", "D393", "Q330",
    "Q331", "Q332", "R330", "R331", "R334", "R335", "R336", "R337", "R338",
    "R340", "R341", "R342", "R343", "R344", "R345",
]
CODEC_SLOTS = [
    (x, y, 0.0)
    for y in (76.0, 79.5, 83.0, 86.5)
    for x in (30.0, 34.0, 38.0, 42.0, 46.0, 50.0, 62.0, 66.0, 70.0)
    if not (52.0 <= x <= 62.0 and 78.0 <= y <= 86.5)
    and not (64.0 <= x <= 70.0 and 79.0 <= y <= 85.0)
]
ANCHORS.update(dict(zip(CODEC_SMALL, CODEC_SLOTS)))
ANCHORS.update({
    "D391": (54.0, 75.5, 0.0),
    "R330": (58.0, 75.5, 0.0),
    "R338": (50.0, 88.0, 0.0),
    "R342": (54.0, 88.0, 0.0),
    "R343": (58.0, 88.0, 0.0),
    "R344": (62.0, 88.0, 0.0),
    "R345": (66.0, 88.0, 0.0),
})


def flip_footprint_to_back(board_path: Path, ref: str) -> None:
    script = """
import pcbnew
import sys

board_path, reference = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(board_path)
footprint = next(fp for fp in board.GetFootprints() if fp.GetReference() == reference)
if not footprint.IsFlipped():
    footprint.SetLayerAndFlip(pcbnew.B_Cu)
pcbnew.SaveBoard(board_path, board)
"""
    subprocess.run(
        [str(KICAD_PYTHON), "-c", script, str(board_path), ref],
        cwd=ROOT,
        check=True,
    )


ANCHORS.update({
    "C40": (99.0, 78.0, 0.0),
    "C41": (99.0, 86.0, 0.0),
    "C42": (103.0, 86.0, 0.0),
    "R40": (99.0, 74.0, 0.0),
    "R41": (104.0, 74.0, 0.0),
    "R42": (109.0, 74.0, 0.0),
})


def export_netlist():
    subprocess.run(
        [
            str(KICAD_CLI),
            "sch",
            "export",
            "netlist",
            "--format",
            "kicadxml",
            "--output",
            str(NETLIST),
            str(SCHEMATIC),
        ],
        cwd=ROOT,
        check=True,
    )


def board_header():
    return '''(kicad_pcb
\t(version 20260206)
\t(generator "pcbnew")
\t(generator_version "10.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(4 "In1.Cu" power)
\t\t(6 "In2.Cu" power)
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
\t)
\t(setup
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(tenting (front yes) (back yes))
\t)
'''


def board_graphics():
    return f'''\t(gr_rect
\t\t(start 20 20)
\t\t(end 140 90)
\t\t(stroke (width 0.15) (type solid))
\t\t(fill none)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{pcb.stable_uuid('radio-db:outline')}")
\t)
\t(gr_text "DUCKTOP2 RADIO / GNSS DAUGHTERBOARD"
\t\t(at 80 88.5 0)
\t\t(layer "B.SilkS")
\t\t(uuid "{pcb.stable_uuid('radio-db:title')}")
\t\t(effects (font (size 1 1) (thickness 0.15)) (justify mirror))
\t)
\t(gr_text "REAR / ANTENNA EDGE"
\t\t(at 80 21.5 0)
\t\t(layer "B.SilkS")
\t\t(uuid "{pcb.stable_uuid('radio-db:rear-label')}")
\t\t(effects (font (size 1 1) (thickness 0.15)) (justify mirror))
\t)
'''


def generate_board(force_rebuild=False):
    if BOARD.exists() and not force_rebuild:
        existing = BOARD.read_text(encoding="utf-8")
        if re.search(r"\n\s*\((?:segment|via|arc)\b", existing):
            raise RuntimeError(
                "radio daughterboard contains routing; refusing to replace it without --force-rebuild"
            )

    export_netlist()
    pcb.NETLIST = NETLIST
    components = {
        ref: comp
        for ref, comp in pcb.parse_netlist().items()
        if "exclude_from_board" not in comp.properties
    }
    missing_anchors = sorted(set(components) - set(ANCHORS))
    stale_anchors = sorted(set(ANCHORS) - set(components))
    if missing_anchors:
        raise RuntimeError(f"unplaced schematic references: {missing_anchors}")
    if stale_anchors:
        raise RuntimeError(f"stale placement references: {stale_anchors}")

    blocks = []
    for ref in sorted(components):
        component = components[ref]
        x, y, rotation = ANCHORS[ref]
        block = pcb.normalize_library_footprint(component, x, y, rotation)
        block = pcb.update_metadata(block, component)
        block, _count = pcb.update_pad_nets(block, component)
        blocks.append(block)

    text = board_header() + "\n".join(blocks) + "\n" + board_graphics() + ")\n"
    temporary = BOARD.with_suffix(".kicad_pcb.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(BOARD)
    flip_footprint_to_back(BOARD, "J1")
    print(f"Generated {BOARD.relative_to(ROOT)} with {len(components)} placed footprints")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-rebuild", action="store_true")
    args = parser.parse_args(argv)
    generate_board(force_rebuild=args.force_rebuild)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
