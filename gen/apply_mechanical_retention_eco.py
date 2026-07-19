#!/usr/bin/env python3
"""Apply only Ducktop2's reviewed retention and motherboard-mount ECO.

The main PCB is intentionally preserved outside the references listed here.
This script adds or normalizes the Mu and M.2 standoffs, adds isolated chassis
mounting holes, corrects the two M.2 socket datums to their card outlines, and
moves two formerly parked parts out of the physical 2280 retention area.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sync_main_pcb_from_netlist import (
    PCB,
    export_netlist,
    footprints,
    normalize_library_footprint,
    parse_netlist,
    update_metadata,
    update_pad_nets,
)


ANCHORS_MM = {
    # A1 is at (105.2, 143.75), rotated 90 degrees. These are the exact
    # LattePanda footprint support centers at local (+/-31.8, 57.0).
    "H1": (162.2, 175.55, 0.0),
    "H2": (162.2, 111.95, 0.0),

    # J10 is normalized to pad 1. At 90 degrees this aligns the 2280 card to
    # the existing 80 x 22 mm mechanical envelope from x=200..280, y=105..127.
    "J10": (196.425, 125.25, 90.0),
    "H3": (279.975, 116.0, 0.0),

    # The E-key card points toward the front edge. Moving the socket 3.5 mm
    # inward leaves the 2230 standoff courtyard fully inside the PCB.
    "J40": (276.0, 145.5, 0.0),
    "H4": (285.25, 179.05, 0.0),

    # Isolated M2.5 chassis holes. The pattern avoids hinge, antenna, side-I/O,
    # cooling, Mu/cold-plate, SSD, trackpad, and battery envelopes.
    "H10": (20.0, 28.0, 0.0),
    "H11": (110.0, 10.0, 0.0),
    "H12": (180.0, 10.0, 0.0),
    "H13": (20.0, 115.0, 0.0),
    "H14": (120.0, 70.0, 0.0),
    "H15": (240.0, 70.0, 0.0),
    "H16": (342.0, 120.0, 0.0),
    "H17": (300.0, 175.0, 0.0),

    # These old placements occupied the newly enforced 2280 retention area.
    # C26 returns to the STM32 cluster; the skin/hinge NTC header belongs by
    # the hinge and remains well clear of the eDP cable chase.
    "C26": (303.0, 120.0, 0.0),
    "J54": (95.0, 10.0, 0.0),
}

REQUIRED_EXISTING = {"J10", "J40", "C26", "J54"}
MECHANICAL_REFS = set(ANCHORS_MM)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pcb",
        type=Path,
        default=PCB,
        help="board file to update; defaults to the live Ducktop2 PCB",
    )
    args = parser.parse_args(argv)
    pcb_path = args.pcb.expanduser().resolve()
    if not pcb_path.exists():
        raise FileNotFoundError(pcb_path)

    export_netlist()
    components = parse_netlist()
    absent_components = MECHANICAL_REFS - set(components)
    if absent_components:
        raise RuntimeError(f"mechanical refs missing from schematic netlist: {sorted(absent_components)}")

    text = pcb_path.read_text(encoding="utf-8")
    board_footprints = footprints(text)
    existing = {fp.ref: fp for fp in board_footprints}
    if len(existing) != len(board_footprints):
        raise RuntimeError("duplicate footprint references are present on the PCB")
    absent_required = REQUIRED_EXISTING - set(existing)
    if absent_required:
        raise RuntimeError(f"required M.2 sockets missing from PCB: {sorted(absent_required)}")

    new_text = text
    normalized: list[str] = []
    pad_updates = 0
    for fp in reversed(board_footprints):
        if fp.ref not in MECHANICAL_REFS:
            continue
        comp = components[fp.ref]
        x, y, rotation = ANCHORS_MM[fp.ref]
        block = normalize_library_footprint(comp, x, y, rotation)
        block = update_metadata(block, comp)
        block, count = update_pad_nets(block, comp)
        pad_updates += count
        new_text = new_text[: fp.start] + block + new_text[fp.end :]
        normalized.append(fp.ref)

    missing = [ref for ref in ANCHORS_MM if ref not in existing]
    if missing:
        insert = new_text.rfind("\n)")
        if insert < 0:
            raise RuntimeError("could not find final board close parenthesis")
        blocks: list[str] = []
        for ref in missing:
            comp = components[ref]
            x, y, rotation = ANCHORS_MM[ref]
            block = normalize_library_footprint(comp, x, y, rotation)
            block = update_metadata(block, comp)
            block, count = update_pad_nets(block, comp)
            pad_updates += count
            blocks.append(block)
        new_text = new_text[:insert] + "\n" + "\n".join(blocks) + new_text[insert:]

    temporary = pcb_path.with_name(pcb_path.name + ".mechanical-eco-tmp")
    temporary.write_text(new_text, encoding="utf-8")
    temporary.replace(pcb_path)

    print(f"Updated PCB: {pcb_path}")
    print(f"Added: {', '.join(missing) if missing else 'none'}")
    print(f"Normalized/repositioned: {', '.join(sorted(normalized)) if normalized else 'none'}")
    print(f"Inserted or updated {pad_updates} pad net assignment(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
